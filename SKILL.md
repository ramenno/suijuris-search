---
name: suijuris-search
description: >-
  Searches open and free primary legal, regulatory, statutory, case law, and corporate filing
  sources across the US, EU, and UK (SEC EDGAR, EUR-Lex CELLAR, CourtListener / RECAP US Case Law,
  US Federal Register, US eCFR, Legislation.gov.uk, UK Find Case Law, USPTO / PatentsView, and
  Delaware / EU national open sources) for any keyword, legal doctrine, statute, regulation, or
  corporate topic. Use when a user asks to search open legal data sources, run a multi-jurisdictional
  legal/regulatory/case-law search, or generate a detailed SuiJuris legal intelligence report on a
  keyword or topic across all or a selected subset of free legal databases.
license: Apache-2.0
compatibility: Python 3.9+ (uses standard library only; zero external pip dependencies required)
metadata:
  author: ramnathn
  version: "1.0.0"
  category: LegalIntelligence
  display_name: SuiJuris Open Legal Search
  display_description: Multi-source legal, regulatory, case law, and corporate filing search across free US, EU, and UK primary databases.
  spec_url: https://agentskills.io/specification
---

# SuiJuris Open Legal Search (`suijuris-search`)

**SuiJuris Open Legal Search** is an [Agent Skills (`agentskills.io`)](https://agentskills.io/)-compliant skill that searches across **open and free primary legal, statutory, regulatory, judicial case law, corporate filing, and IP databases** across the United States, European Union, and United Kingdom.

Users can supply **any keyword, legal concept, clause type, statute, regulation, or corporate topic** and specify whether to search **all open sources** or a **targeted subset / practice-area bundle**. The skill executes modular source scripts under `scripts/sources/` via a concurrent orchestrator (`scripts/suijuris_search_runner.py`) and synthesizes an exhaustive, citation-grounded **SuiJuris Multi-Jurisdictional Legal Intelligence Report** (pairing formal legal citations with plain-English explanations).

---

## 1. Directory Structure (`agentskills.io` Compliant)

```text
suijuris-search/
├── SKILL.md                                     # Skill manifest & step-by-step execution instructions
├── scripts/
│   ├── suijuris_search_runner.py                # Concurrent multi-source CLI orchestrator & dossier builder
│   └── sources/                                 # Modular per-source open legal API adapters
│       ├── search_sec_edgar.py                  # US SEC EDGAR (10-K/10-Q/8-K/S-1 & Exhibit 10.x Material Contracts)
│       ├── search_us_caselaw.py                 # Free Law Project CourtListener (10M+ US Opinions, Delaware Chancery, RECAP)
│       ├── search_us_regulations.py             # US Federal Register API v1, eCFR API v1 (Titles 1-50), US Code / IRS Tax
│       ├── search_eur_lex.py                    # EU EUR-Lex / CELLAR SPARQL (Regulations, Directives, CJEU Case Law)
│       ├── search_uk_law.py                     # UK Legislation (legislation.gov.uk), Find Case Law & Companies House
│       └── search_ip_patents.py                 # USPTO Open Data Portal, PatentsView, PTAB IPRs & Global Patents
├── references/
│   └── open_legal_sources_registry.md           # Detailed API endpoints, rate limits, and source coverage matrix
└── assets/
    └── report_template.md                       # Standardized template for the final Legal Intelligence Report
```

---

## 2. Supported Open Legal Data Sources & Preset Bundles

### Individual Source IDs (`--sources <id1,id2,...>`)
| Source ID | Script | Jurisdiction & Scope | Official Open API / Feed |
| :--- | :--- | :--- | :--- |
| **`courtlistener`** | `scripts/sources/search_courtlistener.py` | **US Federal & 50-State Courts, Dockets & Citator** | Free Law Project **CourtListener REST API v4/v3** (`/search/` for Opinions `type=o`, RECAP PACER Dockets `type=r`, Oral Arguments `type=oa`, Judges `type=p`, and `/citation-lookup/` Open Citator Verification). |
| **`sec_edgar`** | `scripts/sources/search_sec_edgar.py` | **US Corporate & Securities** | SEC EDGAR Full-Text Search (`efts.sec.gov`) & Submissions API (`10-K`, `10-Q`, `8-K`, `S-1`, `DEF 14A`, and **Exhibit 10.x / 2.1 executed material contracts**). |
| **`us_caselaw`** | `scripts/sources/search_us_caselaw.py` | **US Federal & 50-State Courts** | Alias to CourtListener / Harvard CAP US case law adapter (`court=scotus`, `court=delch`, etc.). |
| **`us_regulations`** | `scripts/sources/search_us_regulations.py` | **US Statutory & Regulatory** | **Federal Register API v1** (Final/Proposed Rules, Executive Orders) + **eCFR Search API v1** (Titles 1–50 CFR, including Title 17 SEC & Title 26 IRS Tax) + **US Code**. |
| **`eur_lex`** | `scripts/sources/search_eur_lex.py` | **European Union & Member States** | **EU Publications Office CELLAR SPARQL Endpoint** (Treaties, Regulations like GDPR/AI Act/DORA/MiCA, Directives, and **CJEU / CURIA Case Law** + N-Lex national gateways). |
| **`uk_law`** | `scripts/sources/search_uk_law.py` | **United Kingdom** | **`legislation.gov.uk` Atom/XML API** (UK Acts & SIs) + **UK National Archives `Find Case Law` LegalDocML API** (UKSC, EWCA, EWHC) + **Companies House**. |
| **`ip_patents`** | `scripts/sources/search_ip_patents.py` | **US & Global IP / Patents** | **USPTO Open Data / IBD API**, **PatentsView**, **PTAB** proceedings, and WIPO/EPO patent family pointers. |

### Preset Source Bundles (`--sources <bundle>`)
- **`core`** *(Default)*: `sec_edgar,us_caselaw,us_regulations,eur_lex,uk_law`
- **`all`**: `sec_edgar,us_caselaw,us_regulations,eur_lex,uk_law,ip_patents`
- **`us`**: `sec_edgar,us_caselaw,us_regulations`
- **`eu_uk`**: `eur_lex,uk_law`
- **`transactional`** *(M&A, Corporate, Commercial Clauses)*: `sec_edgar,us_caselaw,uk_law,eur_lex`
- **`litigation`** *(Case Law, Briefs, Dockets, Precedent)*: `us_caselaw,us_regulations,uk_law,eur_lex`
- **`regulatory`** *(Compliance, Horizon Scanning, GRC)*: `us_regulations,eur_lex,uk_law,sec_edgar`

---

## 3. Step-by-Step Execution Workflow

Follow these steps in order whenever this skill is invoked:

### Step 1: Determine Search Scope (Query & Target Sources)
1. Extract the **search keyword, legal doctrine, statute, regulation, or topic** from the user's request.
2. Identify which **sources** the user wants to query:
   - If the user specifies particular sources (e.g., *"Search SEC EDGAR and Delaware case law for Material Adverse Effect"* → `--sources sec_edgar,us_caselaw --court delch`, or *"Search EUR-Lex and UK law for AI liability"* → `--sources eur_lex,uk_law`), map their selection to the matching `--sources` flags.
   - If the user says *"search all sources"* → use `--sources all`.
   - If the user does not specify a subset → default to `--sources core` (or the closest practice-area bundle: `transactional`, `litigation`, or `regulatory`).
3. Load `references/open_legal_sources_registry.md` via `load_skill_resource` if you need detailed parameter flags (`--court`, `--edgar-forms`, `--cfr-title`).

### Step 2: Execute the SuiJuris Search Orchestrator Script
Run the orchestrator script using `run_command` (with `PYTHONDONTWRITEBYTECODE=1 python3 -B` so no `.pyc` cache writes occur outside the workspace):

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B /Users/ramnathn/ge_spark_workspace/skills/suijuris-search/scripts/suijuris_search_runner.py \
  --query "<USER_KEYWORD_OR_TOPIC>" \
  --sources "<SELECTED_SOURCES_OR_BUNDLE>" \
  --limit-per-source 5 \
  --format markdown \
  --output suijuris_raw_dossier.md
```

*(You may also run individual source scripts in `scripts/sources/search_*.py` when drilling deeper into a specific source with custom filters such as `--edgar-forms "10-K,8-K,EX-10"`, `--court "delch"`, or `--cfr-title 17`.)*

**Handling Sandbox Network Blocks:**
- If `run_command` indicates that outbound network access is blocked by the sandbox (or if the script output shows `status: fallback_index` due to sandboxed network restrictions), you may either:
  1. Request network access via `ask_permission(action="network", target="*", justification="Query official open legal APIs (SEC EDGAR, CourtListener, eCFR, Federal Register, EUR-Lex, legislation.gov.uk) for suijuris-search")` and re-run the script to pull live API records, **AND/OR**
  2. Enrich the script's structured deep-link index with your built-in grounded legal knowledge and web search to ensure every section contains complete, verifiable case citations, statutory sections, CELEX identifiers, and verbatim legal standards.

### Step 3: Load the Report Template & Synthesize the Detailed Legal Report
1. Load `assets/report_template.md` via `load_skill_resource(skill_name="suijuris-search", file_path="assets/report_template.md")`.
2. Produce a **comprehensive, executive-grade SuiJuris Multi-Jurisdictional Legal Intelligence Report** (saved as a Markdown file in the workspace and/or rendered as an interactive HTML/PDF report if requested by the user) containing:
   - **Section 1 — Executive Summary & Plain-English Synthesis**: Clear, plain-English explanation of the legal concept, regulatory mandate, or market standard alongside precise legal terminology.
   - **Section 2 — Cross-Jurisdictional Primary Authority Matrix**: A master Markdown table listing every retrieved statute, regulation, judicial opinion, SEC filing/contract exhibit, EU directive/regulation, and UK authority with official citations, dates, controlling rules, and direct verification links.
   - **Section 3 — Deep-Dive Analysis by Source & Jurisdiction**:
     - *US Statutory & Regulatory Framework* (`us_regulations`: USC, eCFR, Federal Register rules/NPRMs).
     - *US Judicial Precedent & Litigation Landscape* (`us_caselaw`: SCOTUS, Federal Circuit, Delaware Court of Chancery holdings, tests, and burdens of proof).
     - *Corporate Filings & "What's Market" Contract Benchmarks* (`sec_edgar`: 10-K/8-K disclosures and Exhibit 10.x / 2.1 executed agreement clauses and carve-outs).
     - *European Union Legal & Regulatory Framework* (`eur_lex`: CELEX Regulations, Directives, CJEU case law, and Member State enforcement).
     - *United Kingdom Legal & Regulatory Framework* (`uk_law`: UK Public General Acts, Statutory Instruments, and English Commercial/Chancery Court precedent).
     - *IP & Patent Landscape* (`ip_patents`, when included).
   - **Section 4 — Comparative Risk & Practical Drafting / Compliance Recommendations**: Side-by-side comparison across US, EU, and UK law with concrete contract drafting or compliance actions.
   - **Section 5 — Verification Log & Direct Source Links**: Complete audit trail of queried open legal endpoints and clickable primary source URLs.
