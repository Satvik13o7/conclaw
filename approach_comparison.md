# Conclaw -- Document Editing Approaches: Deep Comparison

## Target Document Profile: Complex Accountancy / Tax / Legal

These documents are the hardest to edit programmatically because they contain:

| Feature | Why it's hard |
|---------|---------------|
| **Nested numbered paragraphs** | Multi-level numbering (`1.`, `1.1`, `1.1.a`, `1.1.a.i`) stored in `numbering.xml` with abstract/concrete numbering defs. One wrong edit breaks all subsequent numbering. |
| **Company logos** | Embedded in headers via DrawingML (`wp:anchor` or `wp:inline` → `a:blip` with relationship ID to `word/media/image1.png`). |
| **Watermarks** | Stored as VML shapes (`v:shape`) or DrawingML in the header part. "DRAFT", "CONFIDENTIAL" etc. are positioned behind text with rotation. |
| **Headers / Footers** | Per-section (`w:sectPr`), can differ for first page, odd/even pages. Contain field codes (`{PAGE}`, `{NUMPAGES}`) that python-docx destroys. |
| **Tables with merged cells** | `w:gridSpan`, `w:vMerge` attributes. Complex tax schedules have irregular merges. |
| **Tracked changes / revisions** | `w:ins`, `w:del`, `w:rPr` revision markup with author/date. Must be preserved or intentionally managed. |
| **Field codes** | `w:fldChar` + `w:instrText` for TOC, cross-references, page numbers, calculated fields. |
| **Content controls** | `w:sdt` (structured document tags) used in templates for fillable fields. |
| **Footnotes / Endnotes** | Separate XML parts (`footnotes.xml`, `endnotes.xml`) linked via relationship IDs. |
| **Conditional sections** | Sections with different page orientations (landscape schedules in portrait reports). |
| **Custom styles** | Firm-specific styles (`EYBody`, `KPMGHeading2`, `DTCaption`) defined in `styles.xml`. |
| **Bookmarks** | `w:bookmarkStart` / `w:bookmarkEnd` pairs for cross-references and TOC anchors. |

---

## The 10 Approaches

### 1. Harvey Reversible Text Mapping

**How it works**: OOXML → anchored plain-text representation (each element gets stable ID) → LLM edits text → deterministic mapping back to XML mutations. Orchestrator splits large docs into chunks, subagents edit locally.

**Source**: [harvey.ai/blog](https://www.harvey.ai/blog/enabling-document-wide-edits-in-harveys-word-add-in)

**Key insight**: LLM never sees XML. Separation of reasoning (text) and structure (XML) maximizes accuracy on both. Backed by research from Cornell ([arxiv.org/abs/2411.10541](https://arxiv.org/abs/2411.10541)) showing format restrictions degrade reasoning.

### 2. Direct OOXML XML Patching (lxml + XPath)

**How it works**: Parse ZIP, load XML parts into lxml trees, apply surgical mutations via XPath targeting. Only modified elements re-serialized.

**Source**: Our `plan.md`, python-docx internals, [lxml extending python-docx](https://gist.github.com/jdthorpe/498b6c462929d7c4fe1700b4eddfda90)

**Key insight**: Maximum fidelity -- unmodified XML stays byte-identical. But LLM must understand XPath, increasing error rate.

### 3. Pandoc AST (JSON intermediate)

**How it works**: `pandoc -f docx -t json` → JSON AST → edit tree → `pandoc -f json -t docx`.

**Source**: [pandoc.org](https://pandoc.org/MANUAL.html), [github.com/jgm/pandoc](https://github.com/jgm/pandoc)

**Key insight**: Clean AST, great ecosystem. But **lossy round-trip** -- drops custom styles, tracked changes, field codes, watermarks, content controls. Pandoc's docx reader is intentionally simplified.

### 4. Morph Fast Apply

**How it works**: Specialized 7B model merges AI-generated edits into structured files. You send instruction + original + update, get merged output.

**Source**: [morphllm.com](https://www.morphllm.com/use-cases/ai-document-editor-agents)

**Key insight**: Fast (10,500 tok/s), structure-aware. But treats document as text, not XML tree. Cannot handle watermarks, DrawingML, or complex OOXML features. External API.

### 5. IBM Docling

**How it works**: Vision-language model (Granite-Docling-258M) converts PDF/DOCX into unified `DoclingDocument` with layout, tables, formulas detected.

**Source**: [arxiv.org/html/2501.17887v1](https://arxiv.org/html/2501.17887v1), [github.com/docling-project/docling](https://github.com/docling-project/docling)

**Key insight**: Best extraction/reading. MIT-licensed. But **one-directional** -- no write-back to docx. Cannot be used for editing round-trips.

### 6. officeParser AST (Node.js)

**How it works**: Parses .docx into hierarchical AST with formatting metadata per node.

**Source**: [github.com/harshankur/officeParser](https://github.com/harshankur/officeParser)

**Key insight**: Clean tree structure for reading. **Read-only** -- no write-back. Node.js only.

### 7. python-ooxml (booktype)

**How it works**: Python library parsing .docx closer to raw OOXML than python-docx.

**Source**: [github.com/booktype/python-ooxml](https://github.com/booktype/python-ooxml)

**Key insight**: More faithful parsing. But **unmaintained** (last commit years ago), incomplete features, no write-back guarantee.

### 8. SuperDoc Document Engine

**How it works**: Web-based DOCX editor with full Word compatibility. API for AI agents. Handles tracked changes, complex tables.

**Source**: [docs.superdoc.dev](https://docs.superdoc.dev/getting-started/ai-agents)

**Key insight**: Full Word compatibility including tracked changes. But **closed-source SaaS**, cannot self-host or inspect internals.

### 9. Python-Redlines (tracked changes)

**How it works**: Generates Word documents with `w:ins`/`w:del` revision markup at the OOXML level.

**Source**: [github.com/JSv4/Python-Redlines](https://github.com/JSv4/Python-Redlines)

**Key insight**: Only tool that generates proper tracked changes in Python. Narrow scope -- only handles redline generation, not general editing.

### 10. Aspose.Words (commercial)

**How it works**: Full-featured commercial document manipulation library. Python/.NET/Java/C++. Complete OOXML DOM with read/write for every feature.

**Source**: [aspose.com/words](https://docs.aspose.com/words/python-net/)

**Key insight**: Most complete feature coverage in the market. Handles watermarks, headers, footers, tracked changes, field codes, nested lists, content controls -- everything. But **commercial license required** ($999+/dev), not open-source.

### 11. docx4j (Java)

**How it works**: JAXB-based Java library with full OOXML type-safe object model. Round-trip preserving.

**Source**: [github.com/plutext/docx4j](https://github.com/plutext/docx4j)

**Key insight**: Best open-source round-trip fidelity. JAXB binding means every OOXML element has a Java class. But **Java-only**, heavy runtime.

### 12. python-docx (baseline)

**How it works**: High-level Python API for .docx. Paragraphs, runs, tables, styles as Python objects.

**Source**: [github.com/python-openxml/python-docx](https://github.com/python-openxml/python-docx)

**Key insight**: Most popular Python library. Easy API. But **destructive round-trip** -- rewrites XML, drops unknown elements, destroys field codes, cannot handle watermarks/logos in headers, breaks numbering on nested lists.

---

## Scoring Matrix

Scored 1-5 for each capability relevant to complex accountancy/tax/legal documents.

**1** = Cannot do / Destroys on round-trip
**2** = Partial / Unreliable
**3** = Works with workarounds
**4** = Works well
**5** = Perfect / Production-grade

| Capability | Harvey (1) | OOXML Patch (2) | Pandoc AST (3) | Morph (4) | Docling (5) | officeParser (6) | python-ooxml (7) | SuperDoc (8) | Redlines (9) | Aspose (10) | docx4j (11) | python-docx (12) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Nested numbered paragraphs** | 5 | 5 | 2 | 3 | 3 | 2 | 3 | 5 | 1 | 5 | 5 | 2 |
| **Company logos (header)** | 4 | 5 | 1 | 1 | 3 | 2 | 2 | 5 | 1 | 5 | 5 | 2 |
| **Watermarks** | 4 | 5 | 1 | 1 | 1 | 1 | 1 | 4 | 1 | 5 | 4 | 1 |
| **Headers / Footers** | 4 | 5 | 2 | 2 | 2 | 2 | 2 | 5 | 1 | 5 | 5 | 3 |
| **Field codes (PAGE, TOC)** | 4 | 5 | 1 | 1 | 1 | 1 | 1 | 4 | 1 | 5 | 5 | 1 |
| **Tables with merged cells** | 4 | 5 | 2 | 2 | 4 | 2 | 3 | 5 | 1 | 5 | 5 | 3 |
| **Tracked changes** | 5 | 4 | 1 | 1 | 1 | 1 | 1 | 5 | 5 | 5 | 4 | 1 |
| **Content controls (sdt)** | 4 | 5 | 1 | 1 | 1 | 1 | 1 | 4 | 1 | 5 | 4 | 1 |
| **Footnotes / Endnotes** | 4 | 5 | 3 | 2 | 3 | 2 | 2 | 4 | 1 | 5 | 5 | 2 |
| **Custom styles preservation** | 5 | 5 | 2 | 2 | 2 | 2 | 3 | 5 | 1 | 5 | 5 | 3 |
| **Bookmarks / Cross-refs** | 4 | 5 | 1 | 1 | 1 | 1 | 1 | 4 | 1 | 5 | 5 | 1 |
| **Multi-section layouts** | 4 | 5 | 2 | 1 | 2 | 1 | 2 | 5 | 1 | 5 | 5 | 2 |
| **rsid / revision ID preservation** | 5 | 5 | 1 | 1 | 1 | 1 | 1 | 4 | 3 | 5 | 5 | 1 |
| **DrawingML (shapes, charts)** | 3 | 5 | 1 | 1 | 3 | 1 | 1 | 4 | 1 | 5 | 4 | 1 |
| **Round-trip fidelity** | 5 | 5 | 2 | 2 | 1 | 1 | 2 | 5 | 2 | 5 | 5 | 2 |
| **LLM reasoning quality** | 5 | 3 | 4 | 4 | N/A | N/A | N/A | 3 | N/A | N/A | N/A | N/A |
| **100+ page documents** | 5 | 4 | 3 | 3 | 4 | 3 | 2 | 4 | 2 | 5 | 4 | 3 |
| | | | | | | | | | | | | |
| **TOTAL (out of 85)** | **74** | **81** | **30** | **29** | **33** | **26** | **29** | **76** | **24** | **85** | **80** | **30** |
| **Open-source** | No | Yes | Yes | No | Yes | Yes | Yes | No | Yes | No | Yes | Yes |
| **Python** | No | Yes | CLI | API | Yes | No (Node) | Yes | API | Yes | Yes | No (Java) | Yes |
| **Write-back** | Yes | Yes | Yes (lossy) | Yes | No | No | Partial | Yes | Yes | Yes | Yes | Yes (lossy) |

---

## Ranking for Complex Tax/Accountancy Documents

| Rank | Approach | Score | Verdict |
|------|----------|-------|---------|
| **1** | **Aspose.Words** | 85/85 | Perfect fidelity. Handles everything. Commercial license ($999+). |
| **2** | **Direct OOXML Patch (lxml)** | 81/85 | Best open-source fidelity. Full XML control. LLM must understand XPath (harder). |
| **3** | **docx4j** | 80/85 | Excellent round-trip. Java-only. Type-safe OOXML binding. |
| **4** | **SuperDoc** | 76/85 | Full Word compat via API. Closed-source SaaS. |
| **5** | **Harvey Reversible Mapping** | 74/85 | Best LLM+doc combo. Proprietary, not available to use. |
| **6** | **IBM Docling** | 33/85 | Great for reading/extraction. Cannot write back. |
| **7** | **python-docx** | 30/85 | Easy to use. Destroys complex features. |
| **8** | **Pandoc AST** | 30/85 | Clean AST. Lossy round-trip. |
| **9** | **Morph Fast Apply** | 29/85 | Fast text merging. No XML-level awareness. |
| **10** | **python-ooxml** | 29/85 | Unmaintained. Incomplete. |
| **11** | **officeParser** | 26/85 | Read-only. Node.js. |
| **12** | **Python-Redlines** | 24/85 | Tracked changes only. |

---

## Recommended Strategy for Conclaw

### The Hybrid Stack (combining top approaches)

```
Layer 1: OOXML Engine (Approach 2)
├── lxml + XPath for surgical XML mutations
├── ZIP in-memory handling
├── Full namespace preservation
├── Byte-identical unmodified content
│
Layer 2: Reversible Text Mapping (Approach 1, Harvey-inspired)
├── OOXML elements → anchored plain-text with stable IDs
├── Each paragraph/run gets a unique anchor: [P3], [P3.R1], [P3.R2]
├── Formatting stored as metadata alongside text, not mixed in
├── LLM sees: "[P3] Executive Summary {style:Heading1, bold}"
│   NOT: "<w:p w:rsidR='00A77427'><w:pPr>..."
│
Layer 3: LLM Agent (text-only reasoning)
├── Receives anchored text representation
├── Proposes edits: "Change [P3.R1] text to 'Q4 Financial Summary'"
├── Never generates XML
│
Layer 4: Deterministic Writeback
├── Maps text edits back to exact XML mutations
├── Handles: text changes, property changes, insertions, deletions
├── Generates tracked changes markup (w:ins/w:del) via Python-Redlines (Approach 9)
│
Layer 5: Orchestrator (for large docs)
├── Splits 100+ page docs into bounded chunks
├── Global constraints: defined terms, numbering continuity, style consistency
├── Subagents edit chunks, orchestrator merges
```

### Why this beats every individual approach

| Problem | How we solve it |
|---------|-----------------|
| **python-docx destroys formatting** | We never use python-docx for writing. Direct lxml mutations only. |
| **LLM produces invalid XML** | LLM never sees XML. It edits anchored plain text. |
| **Watermarks/logos lost** | Unmodified XML parts (headers with logos, watermarks) stay byte-identical. |
| **Nested numbering breaks** | numbering.xml is read-only unless explicitly targeted by the agent. |
| **Field codes destroyed** | w:fldChar elements are preserved -- we only mutate what the agent targets. |
| **"Lost in the middle" on long docs** | Orchestrator-subagent splits work into chunks. |
| **No tracked changes** | Python-Redlines generates proper w:ins/w:del markup. |
| **Closed-source dependency** | Everything is open-source (lxml, Python stdlib zipfile, Python-Redlines). |
| **Cost** | $0 in library licenses (vs $999+ for Aspose). |

### What this gives you for tax/accountancy docs

- Edit a 200-page KPMG audit report without losing the KPMG watermark, logo, or custom styles.
- Update tax schedule tables (merged cells, formulas) with precision.
- Modify numbered paragraphs in a Deloitte engagement letter without breaking 1.1.a.i numbering.
- Generate tracked changes so the partner can review edits in Word's built-in review mode.
- Preserve every field code, bookmark, cross-reference, and content control.

---

## Research Papers Referenced

1. **Cornell/ACL**: Format restrictions degrade LLM reasoning quality ([arxiv.org/abs/2411.10541](https://arxiv.org/abs/2411.10541))
2. **"Lost in the middle"**: Position bias in long-context models ([MIT TACL 2024](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/))
3. **Agent-DocEdit**: Language-instructed agent for content-rich document editing ([OpenReview 2024](https://openreview.net/forum?id=1ba209BACA))
4. **Docling (AAAI 2025)**: Unified document representation ([arxiv.org/html/2501.17887v1](https://arxiv.org/html/2501.17887v1))
5. **Document Parsing Survey**: Techniques, challenges, prospects ([arxiv.org/html/2410.21169v2](https://arxiv.org/html/2410.21169v2))
6. **LLMs as Pattern Matchers**: Editing semi-structured outputs ([arxiv.org/html/2409.07732v1](https://arxiv.org/html/2409.07732v1))

## Key Open-Source Repos

- [pandoc](https://github.com/jgm/pandoc) -- Universal markup converter with JSON AST
- [python-docx](https://github.com/python-openxml/python-docx) -- High-level .docx manipulation
- [python-ooxml](https://github.com/booktype/python-ooxml) -- Lower-level OOXML parsing
- [Python-Redlines](https://github.com/JSv4/Python-Redlines) -- Tracked changes generation
- [officeParser](https://github.com/harshankur/officeParser) -- Office file AST (Node.js)
- [docling](https://github.com/docling-project/docling) -- IBM's document conversion toolkit
- [docx4j](https://github.com/plutext/docx4j) -- Java OOXML library with JAXB binding
- [modern-office-git-diff](https://github.com/TomasHubelbauer/modern-office-git-diff) -- Git diff for Office files
