# Learning Roadmap: From LLM Prompt Chains to Multi-Agent Systems

> Context: You're at EY, have automated compliance/audit/ITR workflows using
> LLM calls + prompt engineering. Manager says: convert to multi-agentic system.
> This roadmap takes you from where you are to where you need to be.

---

## Where You Are Now (Single-Agent / Prompt Chain)

```
User → Prompt Template → LLM Call → Parse Response → Business Logic → Output
          ↑                                              │
          └──────────── maybe loop once ─────────────────┘
```

**Problems with this approach at scale:**
- One LLM call handles everything (tax rules + document parsing + formatting)
- No parallelism -- sequential, slow
- Context window overflow on large documents
- No memory across sessions
- Brittle -- one bad response breaks the whole chain
- Can't mix models (cheap model for extraction, expensive for reasoning)

---

## Where You Need to Go (Multi-Agent System)

```
User Query
    │
    ▼
┌────────────────────────────────────────────┐
│         ORCHESTRATOR AGENT                  │
│  "Tax Engagement Manager"                   │
│  Understands the full workflow               │
│  Delegates to specialists                    │
│  Merges results, handles errors              │
└──┬──────┬──────┬──────┬──────┬─────────────┘
   │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼
[Data   [Tax    [Audit  [Doc   [QA
Extract] Rules]  Logic]  Gen]   Review]
Agent   Agent   Agent   Agent  Agent
```

---

## The 7 Learning Steps

### Step 1: Understand the Mental Model Shift
**Duration: 2-3 days**

Read these in order:

| # | Resource | What you'll learn | Link |
|---|----------|-------------------|------|
| 1 | **Anthropic: How we built our multi-agent research system** | The BEST production architecture blog. Orchestrator-subagent pattern, token economics, prompt engineering for agents, evaluation. | [anthropic.com/engineering/multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system) |
| 2 | **EY: How agentic AI is reshaping the tax function** | YOUR company's perspective on exactly this problem. | [ey.com/en_gl/insights/tax/how-agentic-ai-can-reshape-your-tax-function](https://www.ey.com/en_gl/insights/tax/how-agentic-ai-can-reshape-your-tax-function) |
| 3 | **Deloitte: Agentic AI in audit** | How your competitor thinks about this. | [deloitte.com/.../agentic-ai-in-audit](https://www.deloitte.com/us/en/services/audit-assurance/blogs/accounting-finance-perspectives/agentic-ai-in-audit.html) |
| 4 | **Azure: AI Agent orchestration patterns** | Sequential, concurrent, handoff, group chat patterns. | [learn.microsoft.com](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) |

**Key mental shift:** Stop thinking "one LLM call does everything." Start thinking "which SPECIALIST agent handles this sub-task?"

---

### Step 2: Learn the Frameworks (Pick ONE to start)
**Duration: 1 week**

| Framework | When to use | Tutorial |
|-----------|-------------|----------|
| **OpenAI Agents SDK** (recommended start) | Simplest. Handoffs + tool calling built-in. Works with Azure OpenAI. | [openai.github.io/openai-agents-python/quickstart](https://openai.github.io/openai-agents-python/quickstart/) |
| **LangGraph** (graduate to this) | Complex stateful workflows, cycles, conditional routing. Enterprise choice 2026. | [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/) |
| **CrewAI** (alternative) | Role-based agents, fastest MVP for business workflows. | [docs.crewai.com](https://docs.crewai.com/) |

**Exercise:** Build a toy 2-agent system:
- Agent A: Extract numbers from a text
- Agent B: Compute tax on those numbers
- Orchestrator: Route between them

---

### Step 3: Map Your Existing EY Workflows to Agents
**Duration: 3-5 days**

Take each workflow you've already automated and decompose it:

#### Example: Income Tax Return (ITR) Filing

**Current (single prompt chain):**
```
Input: Client docs (Form 16, 26AS, bank statements)
  → One big prompt: "Extract income, compute tax, fill ITR form"
  → Output: Filled ITR JSON
```

**Multi-agent redesign:**
```
ORCHESTRATOR: "ITR Filing Manager"
  │
  ├→ [Document Extraction Agent]
  │    Tools: read_pdf, read_excel, OCR
  │    Task: "Extract salary, TDS, other income from Form 16 and 26AS"
  │    Output: structured JSON of income components
  │
  ├→ [Tax Computation Agent]
  │    Tools: tax_calculator, deduction_validator
  │    Task: "Compute tax liability under old/new regime"
  │    Input: JSON from extraction agent
  │    Output: {old_regime_tax, new_regime_tax, recommended_regime}
  │
  ├→ [Deduction Optimizer Agent]
  │    Tools: section_80C_checker, HRA_calculator, NPS_checker
  │    Task: "Suggest optimal deductions to minimize tax"
  │    Output: recommended deductions with amounts
  │
  ├→ [ITR Form Generator Agent]
  │    Tools: itr_form_filler, json_generator
  │    Task: "Fill ITR-1/ITR-2 JSON as per income-tax.gov.in schema"
  │    Output: ITR JSON ready for upload
  │
  └→ [QA / Validation Agent]
       Tools: cross_validator, 26AS_matcher
       Task: "Validate filled ITR against 26AS, check for mismatches"
       Output: {status: pass/fail, issues: [...]}
```

#### Example: Audit Compliance

```
ORCHESTRATOR: "Audit Engagement Manager"
  │
  ├→ [Financial Statement Reader Agent]
  │    Tools: read_excel, read_word (OOXML engine)
  │    Task: "Extract trial balance, P&L, balance sheet from client files"
  │
  ├→ [Materiality Calculator Agent]
  │    Tools: materiality_formula, benchmark_lookup
  │    Task: "Compute planning materiality and performance materiality"
  │
  ├→ [Risk Assessment Agent]
  │    Tools: risk_matrix, industry_benchmark, fraud_indicator_checker
  │    Task: "Identify significant risks, fraud risks, related party risks"
  │
  ├→ [Substantive Procedures Agent]
  │    Tools: sampling_calculator, vouching_checker, recalculation
  │    Task: "Design and execute analytical procedures for revenue, expenses"
  │
  ├→ [Report Drafting Agent]
  │    Tools: word_ooxml_engine (from plan.md), template_filler
  │    Task: "Draft audit report with findings in the EY template"
  │
  └→ [Review Agent]
       Tools: checklist_validator, standards_checker (SA 200-720)
       Task: "Review report against auditing standards, flag gaps"
```

#### Example: GST Compliance

```
ORCHESTRATOR: "GST Filing Manager"
  │
  ├→ [Invoice Extraction Agent] → reads Excel/CSV of sales/purchases
  ├→ [GSTR-1 Builder Agent]     → builds outward supply JSON
  ├→ [GSTR-3B Computation Agent] → computes ITC, liability, net payable
  ├→ [Reconciliation Agent]     → matches 2A/2B with purchase register
  └→ [Filing Agent]             → generates JSON for GST portal upload
```

---

### Step 4: Build Your First Real Multi-Agent System
**Duration: 2 weeks**

**Pick ONE of these real problems from the web to implement:**

| Problem | Difficulty | Source/Inspiration |
|---------|-----------|-------------------|
| **ITR-1 auto-filler from Form 16 PDF** | Medium | [taxbuddy.com](https://www.taxbuddy.com/blog/ai-income-tax-filing-india-2025), income-tax.gov.in JSON schema |
| **Audit working paper generator** | Hard | EY internal templates, SA 500-530 standards |
| **GST reconciliation (2A vs purchase register)** | Medium | Common CA pain point, Excel-heavy |
| **Financial statement analysis + commentary** | Medium | Annual reports on BSE/NSE, openpyxl + Word |
| **Transfer pricing documentation** | Hard | OECD guidelines, multi-country data |

**Research papers to implement:**

| Paper | What it solves | Link |
|-------|---------------|------|
| **Governance-as-a-Service: Multi-Agent Framework for AI System Compliance** | Multi-agent compliance monitoring | [arxiv.org/html/2508.18765v2](https://arxiv.org/html/2508.18765v2) |
| **Multi-Agent Security Tax** | Security vs collaboration tradeoffs in multi-agent | [arxiv.org/abs/2502.19145](https://arxiv.org/abs/2502.19145) |
| **Audit-LLM: Multi-agent collaboration for log-based insider threat detection** | Multi-agent audit system | Referenced in [OpenReview survey](https://openreview.net/pdf?id=Ylh8617Qyd) |
| **Agentic AI Survey (comprehensive)** | Full taxonomy of agent architectures | [arxiv.org/html/2510.25445v1](https://arxiv.org/html/2510.25445v1) |
| **Towards a Science of Scaling Agent Systems** | How to scale from 1 agent to N agents | [arxiv.org/html/2512.08296v1](https://arxiv.org/html/2512.08296v1) |
| **Agent-DocEdit** | LLM agent for document editing | [openreview.net/forum?id=1ba209BACA](https://openreview.net/forum?id=1ba209BACA) |

---

### Step 5: Learn the Thinking & Design Tools
**Duration: ongoing**

These tools help you design agent flows BEFORE coding:

| Tool | What for | Best at | Link |
|------|----------|---------|------|
| **Excalidraw** | Hand-drawn style diagrams. FREE. | Quick agent flow sketches, system design | [excalidraw.com](https://excalidraw.com) |
| **Whimsical AI** | Generate flowcharts from text prompts | "Draw a multi-agent tax filing flow" → instant diagram | [whimsical.com/ai](https://whimsical.com/ai) |
| **Miro** | Collaborative whiteboard | Team brainstorming with Satvik, sticky notes for agent roles | [miro.com](https://miro.com) |
| **draw.io / diagrams.net** | Full-featured diagramming. FREE. | Formal architecture diagrams, state machines | [app.diagrams.net](https://app.diagrams.net) |
| **Jupyter Notebook** | Code + visualize + document in one place | Prototype agent flows with live code cells | Already on your machine or use [colab.google.com](https://colab.google.com) |
| **Obsidian** | Markdown notes with graph view | Connect ideas: "Agent A" links to "Tax Rules" links to "Form 16" | [obsidian.md](https://obsidian.md) |
| **LangGraph Studio** | Visual debugger for LangGraph agents | See agent state transitions in real-time | [github.com/langchain-ai/langgraph-studio](https://github.com/langchain-ai/langgraph-studio) |

**Recommended notebook flow for designing an agent system:**

```
Notebook Cell 1: Problem Statement
   "Automate ITR-1 filing from Form 16 PDF"

Notebook Cell 2: Agent Decomposition (markdown)
   - Agent A: PDF Extractor
   - Agent B: Tax Computor
   - Agent C: Form Filler
   - Agent D: Validator

Notebook Cell 3: Tool Definitions (code)
   tools = [read_pdf, compute_tax, fill_itr_json, validate_26as]

Notebook Cell 4: Agent Definitions (code)
   extractor = Agent(name="Extractor", tools=[read_pdf], ...)
   computor = Agent(name="TaxComputer", tools=[compute_tax], ...)

Notebook Cell 5: Orchestrator (code)
   orchestrator = Agent(name="Manager", handoffs=[extractor, computor, ...])

Notebook Cell 6: Test with sample Form 16
   result = orchestrator.run("File ITR for this Form 16: ...")

Notebook Cell 7: Evaluate
   assert result.total_income == expected
   assert result.tax_payable == expected
```

---

### Step 6: Patterns That Matter for EY Work
**Duration: 1 week**

| Pattern | When to use | EY example |
|---------|-------------|------------|
| **Orchestrator-Worker** | One manager, many specialists | Audit engagement: manager assigns substantive procedures to specialist agents |
| **Parallel Fan-out** | Independent tasks that can run simultaneously | GST: extract invoices from 5 Excel files at once |
| **Sequential Pipeline** | Each step depends on the previous | ITR: extract → compute → fill → validate |
| **Handoff** | Agent A realizes Agent B should handle this | Document extraction agent finds a scanned image → hands off to OCR agent |
| **Debate / Review** | Two agents check each other's work | Computation agent calculates tax, Review agent verifies against manual calculation |
| **Human-in-the-loop** | High-stakes decisions need human approval | Audit opinion: agent drafts, partner reviews before signing |

---

### Step 7: Production Concerns
**Duration: 2 weeks**

| Concern | What to learn | Resource |
|---------|---------------|----------|
| **Cost control** | Token budgets per agent, cheap models for extraction, expensive for reasoning | Anthropic blog: "agents use 15x more tokens than chat" |
| **Error recovery** | Checkpointing, retry with backoff, graceful degradation | LangGraph built-in state persistence |
| **Evaluation** | LLM-as-judge for output quality, small eval sets first (20 cases) | Anthropic blog section on evals |
| **Memory** | Our CONCLAW.md + auto-memory system for cross-session context | Already built in conclaw |
| **Security** | API key management, PII handling, audit trail | EY internal policies + our safety layer |
| **Observability** | Trace every agent decision, tool call, handoff | LangSmith, OpenTelemetry, or custom logging |

---

## Suggested First Project: ITR-1 Auto-Filler

**Why this is perfect for learning:**
- You know the domain (tax)
- Clear input (Form 16 PDF) and output (ITR-1 JSON)
- 4-5 agents with distinct roles
- Testable with real data (download sample Form 16)
- Can demo to manager as "here's the multi-agent version"

**Input:** Form 16 PDF + 26AS PDF
**Output:** ITR-1 JSON (income-tax.gov.in schema) + validation report

**Agents:**
1. **PDF Reader** → extracts structured data from Form 16
2. **26AS Matcher** → cross-references TDS entries
3. **Tax Calculator** → old vs new regime comparison
4. **ITR JSON Builder** → fills ITR-1 schema
5. **Validator** → checks completeness, flags mismatches

**Implementation steps:**
```
Week 1: Build individual tools (PDF reader, tax calc, JSON builder)
Week 2: Wrap each tool in an agent with OpenAI Agents SDK
Week 3: Build orchestrator that routes between agents
Week 4: Add memory, evaluation, error handling
```

---

## Summary: Your Learning Stack

```
Day 1-3:    Read Anthropic + EY + Azure blogs (mental model)
Day 4-7:    OpenAI Agents SDK tutorial (hands-on)
Day 8-12:   Map your existing EY workflows to agents (on paper/Excalidraw)
Day 13-26:  Build ITR-1 auto-filler as multi-agent system
Day 27-30:  Add memory, evals, present to manager
Day 31+:    Graduate to LangGraph for complex workflows
```

**Tools for your notebook/thinking:**
- Excalidraw for quick sketches
- Jupyter for prototyping
- Obsidian for connecting ideas
- LangGraph Studio for debugging agent flows
