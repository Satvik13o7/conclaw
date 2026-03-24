# Conclaw -- Low-Level OOXML Word Editing Agent Framework

## 1. Problem

`python-docx` operates at a high-level abstraction (paragraphs, runs, tables as Python objects). This causes:
- **Formatting loss**: editing a paragraph can strip custom XML attributes, rsid tracking, revision marks.
- **Inaccurate changes**: inserting/modifying content through the high-level API often reorganizes the underlying XML, breaking styles, numbering, and tracked changes.
- **No surgical edits**: you cannot target a specific `w:r` (run) inside a `w:p` (paragraph) by index or content match without dropping to raw XML.
- **Missing features**: bookmarks, content controls, custom XML parts, field codes, and comment ranges are not exposed by python-docx at all.

The agent needs to work at the **OOXML XML level** for precision -- the same level Microsoft Word itself operates at internally.

---

## 2. OOXML Internals Primer

A `.docx` file is a ZIP archive containing XML files:

```
docx (ZIP)
├── [Content_Types].xml          # MIME type registry
├── _rels/.rels                  # Top-level relationships
├── word/
│   ├── document.xml             # Main body (paragraphs, tables, images)
│   ├── styles.xml               # Style definitions (Normal, Heading1, etc.)
│   ├── numbering.xml            # List/numbering definitions
│   ├── settings.xml             # Document settings (track changes, etc.)
│   ├── fontTable.xml            # Font declarations
│   ├── footer1.xml              # Footer content
│   ├── header1.xml              # Header content
│   ├── comments.xml             # Comment content
│   ├── footnotes.xml            # Footnote content
│   ├── endnotes.xml             # Endnote content
│   ├── _rels/document.xml.rels  # Relationships for document.xml
│   └── media/                   # Embedded images, etc.
│       └── image1.png
├── docProps/
│   ├── app.xml                  # Application properties
│   └── core.xml                 # Dublin Core metadata (author, title, dates)
```

### Key XML elements in `word/document.xml`

```xml
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p w:rsidR="00A77427">          <!-- paragraph -->
      <w:pPr>                          <!-- paragraph properties -->
        <w:pStyle w:val="Heading1"/>
        <w:jc w:val="center"/>
      </w:pPr>
      <w:r w:rsidRPr="00B12345">      <!-- run (text fragment) -->
        <w:rPr>                        <!-- run properties -->
          <w:b/>                       <!-- bold -->
          <w:sz w:val="28"/>           <!-- font size (half-points) -->
          <w:color w:val="FF0000"/>
        </w:rPr>
        <w:t>Hello World</w:t>         <!-- text content -->
      </w:r>
      <w:r>
        <w:t xml:space="preserve"> more text</w:t>
      </w:r>
    </w:p>
    <w:tbl>                            <!-- table -->
      <w:tblPr>...</w:tblPr>
      <w:tr>                           <!-- table row -->
        <w:tc>                         <!-- table cell -->
          <w:p>...</w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:sectPr>...</w:sectPr>           <!-- section properties (page layout) -->
  </w:body>
</w:document>
```

### Namespaces

| Prefix | URI | Used for |
|--------|-----|----------|
| `w` | `http://schemas.openxmlformats.org/wordprocessingml/2006/main` | Body, paragraphs, runs, tables |
| `r` | `http://schemas.openxmlformats.org/officeDocument/2006/relationships` | Relationship IDs (images, hyperlinks) |
| `wp` | `http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing` | Inline/anchor drawings |
| `a` | `http://schemas.openxmlformats.org/drawingml/2006/main` | DrawingML (shapes, charts) |
| `mc` | `http://schemas.openxmlformats.org/markup-compatibility/2006` | Markup compatibility |
| `w14` | `http://schemas.microsoft.com/office/word/2010/wordml` | Word 2010+ extensions |
| `w15` | `http://schemas.microsoft.com/office/word/2012/wordml` | Word 2013+ extensions |

---

## 3. Architecture

### 3.1 Layer Diagram

```
User (natural language)
    │
    ▼
┌───────────────────────────────────────────────┐
│  Agent Orchestrator (LLM)                     │
│  - Understands task, plans approach            │
│  - Calls tools below as function calls         │
│  - Reviews results, iterates if needed         │
└───────────┬───────────────────────────────────┘
            │ tool calls
            ▼
┌───────────────────────────────────────────────┐
│  Document Tools (callable by agent)           │
│                                               │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │ inspect      │  │ xpath_query          │   │
│  │ (read-only)  │  │ (read-only)          │   │
│  └─────────────┘  └──────────────────────┘   │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │ patch_xml    │  │ insert_xml           │   │
│  │ (surgical)   │  │ (add elements)       │   │
│  └─────────────┘  └──────────────────────┘   │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │ delete_xml   │  │ replace_text         │   │
│  │ (remove)     │  │ (text-level find/rep)│   │
│  └─────────────┘  └──────────────────────┘   │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │ style_ops    │  │ relationship_ops     │   │
│  │ (styles.xml) │  │ (images, links)      │   │
│  └─────────────┘  └──────────────────────┘   │
│  ┌─────────────┐                              │
│  │ save / backup│                             │
│  └─────────────┘                              │
└───────────┬───────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────┐
│  OOXML Engine (low-level)                     │
│  - ZIP extract/repack                          │
│  - lxml.etree XML parsing with full namespaces │
│  - XPath queries on document.xml               │
│  - Element-level insert/modify/delete          │
│  - Relationship management (images, links)     │
│  - Backup before every write                   │
└───────────────────────────────────────────────┘
            │
            ▼
        .docx file (ZIP of XML)
```

### 3.2 Core Principle: Never Rewrite, Only Patch

The key difference from python-docx:
- **python-docx**: deserializes XML → Python objects → serializes back. Information loss happens at both boundaries.
- **Our approach**: parse XML with `lxml.etree`, apply minimal surgical mutations (insert/replace/remove specific elements), then write back. All unmodified XML stays byte-identical.

---

## 4. OOXML Engine (`src/conclaw/ooxml/`)

### 4.1 Module Layout

```
src/conclaw/ooxml/
    __init__.py
    archive.py          # ZIP extract/repack with backup
    namespaces.py       # All OOXML namespace constants + qname helper
    parser.py           # Parse document.xml, styles.xml, etc. into lxml trees
    query.py            # XPath helper with namespace-aware queries
    mutate.py           # Surgical XML mutations (patch, insert, delete)
    relationships.py    # Manage _rels/*.rels (add/remove images, hyperlinks)
    styles.py           # Read/modify styles.xml
    inspector.py        # Read-only document structure extraction
    serializer.py       # Serialize lxml tree back to XML bytes (preserving declaration)
    validator.py        # Validate mutations (schema checks, namespace integrity)
```

### 4.2 archive.py -- ZIP handling

```python
class DocxArchive:
    """Open a .docx, expose its XML parts, and repack safely."""

    def __init__(self, path: Path):
        ...

    def read_part(self, part_name: str) -> bytes:
        """Read raw XML bytes for a part (e.g. 'word/document.xml')."""

    def write_part(self, part_name: str, data: bytes) -> None:
        """Stage a modified part for saving."""

    def list_parts(self) -> list[str]:
        """List all parts in the archive."""

    def save(self, output_path: Path | None = None) -> None:
        """Repack ZIP. If output_path is None, overwrite in-place (after backup)."""

    def backup(self) -> Path:
        """Copy original to <file>.bak before any mutation."""
```

**Key**: we never extract to a temp directory. We read parts on demand, mutate in memory, and repack. Only modified parts are re-serialized; unmodified parts are copied byte-for-byte.

### 4.3 namespaces.py

```python
NSMAP = {
    "w":   "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r":   "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp":  "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a":   "http://schemas.openxmlformats.org/drawingml/2006/main",
    "mc":  "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "v":   "urn:schemas-microsoft-com:vml",
    "o":   "urn:schemas-microsoft-com:office:office",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "ct":  "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

def qn(tag: str) -> str:
    """Convert 'w:p' to '{http://...}p' for lxml."""
    prefix, local = tag.split(":", 1)
    return f"{{{NSMAP[prefix]}}}{local}"
```

### 4.4 query.py -- XPath with namespaces

```python
def xpath(tree, expr: str) -> list:
    """Run XPath on an lxml tree with full OOXML namespace map."""
    return tree.xpath(expr, namespaces=NSMAP)

# Example queries the agent would use:
# xpath(tree, "//w:p")                          → all paragraphs
# xpath(tree, "//w:p[w:pPr/w:pStyle[@w:val='Heading1']]")  → all Heading1 paragraphs
# xpath(tree, "//w:r[w:t[contains(text(),'Hello')]]")       → runs containing "Hello"
# xpath(tree, "//w:tbl")                        → all tables
# xpath(tree, "//w:p[3]")                       → 3rd paragraph
# xpath(tree, "//w:bookmarkStart[@w:name='toc']")           → bookmark by name
```

### 4.5 mutate.py -- Surgical mutations

```python
def patch_element(element, attrib_updates: dict) -> None:
    """Update attributes on an existing element without replacing it."""

def replace_text_in_run(run_element, old: str, new: str) -> bool:
    """Find and replace text inside a w:r/w:t, preserving all run properties."""

def insert_after(target, new_element) -> None:
    """Insert new_element as a sibling after target."""

def insert_before(target, new_element) -> None:
    """Insert new_element as a sibling before target."""

def insert_child(parent, new_element, index: int = -1) -> None:
    """Insert new_element as a child of parent at position."""

def remove_element(element) -> None:
    """Remove element from its parent, preserving surrounding siblings."""

def set_run_property(run, prop_tag: str, attribs: dict | None = None) -> None:
    """Set/update a property inside w:rPr (e.g. bold, italic, font size)."""

def set_paragraph_property(para, prop_tag: str, attribs: dict | None = None) -> None:
    """Set/update a property inside w:pPr (e.g. style, alignment)."""

def build_element(tag: str, attribs: dict = None, text: str = None, children: list = None):
    """Create a new lxml element with OOXML namespace resolution."""
```

### 4.6 inspector.py -- Read-only structure extraction

```python
def inspect_document(archive: DocxArchive) -> dict:
    """Return a structured summary of the document for the LLM context."""
    # Returns:
    # {
    #   "paragraphs": 42,
    #   "tables": 3,
    #   "images": 5,
    #   "headings": [
    #     {"level": 1, "text": "Introduction", "para_index": 0},
    #     {"level": 2, "text": "Background", "para_index": 3},
    #   ],
    #   "styles_used": ["Normal", "Heading1", "Heading2", "TableGrid"],
    #   "page_count_estimate": 12,
    #   "has_headers": true,
    #   "has_footers": true,
    #   "has_comments": true,
    #   "has_tracked_changes": false,
    #   "sections": 2,
    # }

def inspect_paragraph(archive: DocxArchive, index: int) -> dict:
    """Return detailed info about a specific paragraph (runs, properties, raw XML)."""

def inspect_table(archive: DocxArchive, index: int) -> dict:
    """Return table structure (rows, cols, merged cells, content preview)."""

def dump_xml(archive: DocxArchive, part: str, xpath_expr: str = None) -> str:
    """Return raw XML for a part, optionally filtered by XPath. For agent debugging."""
```

---

## 5. Agent Tools (function-calling definitions)

These are the tools the LLM orchestrator calls. Each maps to OOXML engine functions.

### 5.1 `inspect_document`

```json
{
  "name": "inspect_document",
  "description": "Read-only. Returns document structure: paragraph count, headings, tables, images, styles used, metadata.",
  "parameters": {
    "file_path": {"type": "string"}
  }
}
```

### 5.2 `xpath_query`

```json
{
  "name": "xpath_query",
  "description": "Run a namespace-aware XPath query on document.xml (or another part). Returns matching elements as serialized XML snippets.",
  "parameters": {
    "file_path": {"type": "string"},
    "part": {"type": "string", "default": "word/document.xml"},
    "xpath": {"type": "string"},
    "max_results": {"type": "integer", "default": 10}
  }
}
```

### 5.3 `replace_text`

```json
{
  "name": "replace_text",
  "description": "Find and replace text across all runs in the document. Preserves all formatting on each run.",
  "parameters": {
    "file_path": {"type": "string"},
    "find": {"type": "string"},
    "replace": {"type": "string"},
    "scope": {"type": "string", "enum": ["all", "first"], "default": "all"}
  }
}
```

### 5.4 `patch_xml`

```json
{
  "name": "patch_xml",
  "description": "Apply a surgical XML patch: find element(s) by XPath, then modify attributes, text, or child elements. Does NOT rewrite unrelated XML.",
  "parameters": {
    "file_path": {"type": "string"},
    "part": {"type": "string", "default": "word/document.xml"},
    "xpath": {"type": "string", "description": "XPath to target element(s)"},
    "action": {"type": "string", "enum": ["set_attrib", "set_text", "add_child", "remove_child", "set_property"]},
    "attribs": {"type": "object", "description": "Attributes to set (for set_attrib)"},
    "text": {"type": "string", "description": "New text content (for set_text)"},
    "child_xml": {"type": "string", "description": "Raw XML string of child to add (for add_child)"},
    "property_tag": {"type": "string", "description": "e.g. 'w:b', 'w:sz' (for set_property)"},
    "property_attribs": {"type": "object", "description": "Attributes for the property element"}
  }
}
```

### 5.5 `insert_xml`

```json
{
  "name": "insert_xml",
  "description": "Insert a new XML element (paragraph, run, table row, etc.) relative to an XPath target.",
  "parameters": {
    "file_path": {"type": "string"},
    "part": {"type": "string", "default": "word/document.xml"},
    "xpath": {"type": "string", "description": "XPath to reference element"},
    "position": {"type": "string", "enum": ["before", "after", "first_child", "last_child"]},
    "xml": {"type": "string", "description": "Raw OOXML string to insert"}
  }
}
```

### 5.6 `delete_xml`

```json
{
  "name": "delete_xml",
  "description": "Remove element(s) matched by XPath from a document part.",
  "parameters": {
    "file_path": {"type": "string"},
    "part": {"type": "string", "default": "word/document.xml"},
    "xpath": {"type": "string"},
    "max_deletions": {"type": "integer", "default": 1, "description": "Safety limit"}
  }
}
```

### 5.7 `modify_style`

```json
{
  "name": "modify_style",
  "description": "Read or modify a style definition in styles.xml.",
  "parameters": {
    "file_path": {"type": "string"},
    "action": {"type": "string", "enum": ["list", "get", "set_property"]},
    "style_id": {"type": "string"},
    "property_tag": {"type": "string"},
    "property_attribs": {"type": "object"}
  }
}
```

### 5.8 `manage_relationship`

```json
{
  "name": "manage_relationship",
  "description": "Add, list, or remove relationships (images, hyperlinks) in document.xml.rels.",
  "parameters": {
    "file_path": {"type": "string"},
    "action": {"type": "string", "enum": ["list", "add_image", "add_hyperlink", "remove"]},
    "rel_id": {"type": "string"},
    "target": {"type": "string"},
    "image_bytes_b64": {"type": "string", "description": "Base64-encoded image for add_image"}
  }
}
```

### 5.9 `save_document`

```json
{
  "name": "save_document",
  "description": "Save all pending changes to the docx file. Auto-creates backup before first save.",
  "parameters": {
    "file_path": {"type": "string"},
    "output_path": {"type": "string", "description": "Optional. If omitted, overwrites in-place after backup."}
  }
}
```

### 5.10 `dump_raw_xml`

```json
{
  "name": "dump_raw_xml",
  "description": "Return raw XML of a document part or XPath match. For debugging and understanding structure.",
  "parameters": {
    "file_path": {"type": "string"},
    "part": {"type": "string", "default": "word/document.xml"},
    "xpath": {"type": "string", "description": "Optional. If provided, returns only matching elements."}
  }
}
```

---

## 6. Agent Loop for Document Editing

```
User: "Make the third paragraph bold and change its font to Arial 14pt"
    │
    ▼
1. [inspect_document]  → Get structure: 15 paragraphs, styles used, etc.
    │
    ▼
2. [xpath_query]       → "//w:p[3]" to see the 3rd paragraph's current XML
    │                     (returns runs, current rPr, text content)
    ▼
3. [Agent reasons]     → "Para 3 has 2 runs. I need to set w:b, w:rFonts, w:sz
    │                      on each run's w:rPr. I'll use patch_xml for each."
    ▼
4. [patch_xml]         → xpath="//w:p[3]/w:r[1]", action="set_property",
    │                     property_tag="w:b"
    │                  → xpath="//w:p[3]/w:r[1]", action="set_property",
    │                     property_tag="w:rFonts", attribs={"w:ascii":"Arial","w:hAnsi":"Arial"}
    │                  → xpath="//w:p[3]/w:r[1]", action="set_property",
    │                     property_tag="w:sz", attribs={"w:val":"28"}  (14pt = 28 half-points)
    │                  → (repeat for w:r[2])
    ▼
5. [xpath_query]       → Verify: "//w:p[3]" -- confirm bold, Arial, 14pt applied
    │
    ▼
6. [save_document]     → Backup created, file saved
    │
    ▼
7. [Agent responds]    → "Done. Paragraph 3 is now bold, Arial 14pt. Backup at report.docx.bak"
```

### Why this is better than python-docx

| Operation | python-docx | Our approach |
|-----------|-------------|--------------|
| Bold a run | `run.bold = True` (may lose rsid, w14 attrs) | `set_property(run, "w:b")` -- only adds `<w:b/>`, everything else untouched |
| Change font | `run.font.name = "Arial"` (rewrites rPr) | `set_property(run, "w:rFonts", {"w:ascii":"Arial"})` -- surgical |
| Find/replace | `paragraph.text` (destroys run boundaries) | XPath to exact run, replace `w:t` text only |
| Insert paragraph | `doc.add_paragraph()` (appends to end) | `insert_xml` at any XPath position |
| Table cell edit | Limited API | Direct XPath to `w:tc/w:p/w:r/w:t` |

---

## 7. Safety and Backup

1. **Auto-backup**: before the first `save_document` call per file per session, copy original to `<file>.bak`.
2. **Max deletions**: `delete_xml` has a `max_deletions` limit (default 1) to prevent mass removal.
3. **Dry-run mode**: agent can call `dump_raw_xml` after mutations but before save to review changes.
4. **Validation**: after mutations, optionally validate the XML tree against OOXML schema elements.
5. **User confirmation**: before `save_document`, the TUI shows a diff summary (elements added/modified/removed).

---

## 8. Dependencies

| Library | Purpose |
|---------|---------|
| `lxml` | XML parsing, XPath, element manipulation |
| `python-docx` | Optional: only for high-level convenience operations (read-only inspection fallback) |

**No new heavy dependencies.** `lxml` is the only required addition. The ZIP handling uses Python's built-in `zipfile` module.

---

## 9. Implementation Phases

### Phase A: OOXML Engine Core (Week 1)

- [ ] `archive.py` -- ZIP read/write/backup
- [ ] `namespaces.py` -- all OOXML namespace constants
- [ ] `parser.py` -- parse XML parts into lxml trees
- [ ] `serializer.py` -- serialize back to bytes
- [ ] `query.py` -- XPath helper with namespace map
- [ ] `mutate.py` -- core mutation functions
- [ ] `inspector.py` -- read-only document structure extraction
- [ ] Unit tests with sample .docx fixtures

### Phase B: Agent Tools (Week 2)

- [ ] Tool definitions (OpenAI function-calling JSON schemas)
- [ ] Tool executor that maps tool calls → ooxml engine functions
- [ ] `relationships.py` -- image/hyperlink management
- [ ] `styles.py` -- style read/modify
- [ ] Integration into LLM client (tools parameter in chat calls)

### Phase C: Agent Loop Integration (Week 3)

- [ ] Wire tools into the existing `cli/app.py` chat flow
- [ ] Agent system prompt update: teach LLM about OOXML structure and available tools
- [ ] Multi-turn agentic loop: inspect → plan → mutate → verify → save
- [ ] `/inspect` and `/diff` slash commands
- [ ] Backup management and `/undo` command

### Phase D: Excel Low-Level (Future)

- [ ] Similar OOXML engine for `.xlsx` (SpreadsheetML)
- [ ] `xl/worksheets/sheet1.xml`, `xl/sharedStrings.xml`, `xl/styles.xml`
- [ ] XPath-based cell/row/column operations

---

## 10. Example: What the Agent Sees

When the agent calls `inspect_document("report.docx")`:

```json
{
  "file": "report.docx",
  "paragraphs": 42,
  "tables": 3,
  "images": 5,
  "headings": [
    {"level": 1, "text": "Executive Summary", "index": 0},
    {"level": 2, "text": "Revenue Analysis", "index": 5},
    {"level": 2, "text": "Cost Breakdown", "index": 18},
    {"level": 1, "text": "Recommendations", "index": 30}
  ],
  "styles_used": ["Normal", "Heading1", "Heading2", "TableGrid", "Caption"],
  "has_tracked_changes": false,
  "has_comments": true,
  "comment_count": 4,
  "sections": 2,
  "parts": ["word/document.xml", "word/styles.xml", "word/numbering.xml",
            "word/header1.xml", "word/footer1.xml", "word/comments.xml"]
}
```

When the agent calls `xpath_query("report.docx", "//w:p[1]")`:

```xml
<w:p w:rsidR="00A77427" w:rsidRDefault="00A77427">
  <w:pPr>
    <w:pStyle w:val="Heading1"/>
  </w:pPr>
  <w:r w:rsidRPr="00B12345">
    <w:rPr>
      <w:b/>
      <w:sz w:val="32"/>
    </w:rPr>
    <w:t>Executive Summary</w:t>
  </w:r>
</w:p>
```

The agent now has **full visibility** into the exact XML structure and can make precise, surgical edits.

---

## 11. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **lxml over ElementTree** | lxml has full XPath 1.0 support, namespace handling, and C-level speed |
| **ZIP in-memory, not temp dir** | Avoids filesystem race conditions; faster for small docs |
| **Agent sees raw XML** | The LLM needs to understand exact structure to make accurate edits |
| **Patch, don't rewrite** | Only modified elements are serialized; preserves rsid, revision marks, unknown extensions |
| **Tool-based, not code-gen** | Agent calls structured tools instead of generating arbitrary Python scripts -- safer, more predictable |
| **Backup before first write** | Non-negotiable safety net; every save checks for existing backup |
