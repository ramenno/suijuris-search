# SuiJuris Open Legal Search (`suijuris-search`)

[![Agent Skills Specification](https://img.shields.io/badge/Agent%20Skills-Compliant-blue.svg)](https://agentskills.io/specification)
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20External%20Pip-success.svg)](https://docs.python.org/3/library/)
[![Licence](https://img.shields.io/badge/Licence-Apache%202.0-blue.svg)](LICENSE)

**SuiJuris Open Legal Search** is an autonomous legal intelligence and research skill compliant with the [Agent Skills (`agentskills.io`)](https://agentskills.io/) specification. It searches across **free, open, primary legal, regulatory, statutory, judicial case law, corporate filing, and intellectual property databases** across the United States, United Kingdom, European Union, and Continental European jurisdictions.

Users and autonomous AI agents can query any legal keyword, doctrine, contract clause, statute, regulation, or commercial topic. SuiJuris executes modular adapters concurrently and synthesises citation-grounded **Legal Intelligence Dossiers** pairing formal legal citations with plain-English analysis.

---

## Key Highlights

- **Zero External Dependencies**: Operates strictly on Python 3.9+ standard library modules (`urllib`, `json`, `concurrent.futures`, `re`, `argparse`). No `pip install` required.
- **11 Primary Legal Sources**: Covers US federal and state case law, SEC corporate filings, federal regulations, US Code and tax law, EU CELLAR/EUR-Lex SPARQL, UK legislation and judicial opinions, UK Companies House, German federal law, Nordic statutory portals, Continental European courts, and USPTO patent/PTAB records.
- **Concurrent Multi-Source Execution**: Non-blocking asynchronous query runner querying multiple jurisdictions simultaneously with custom thread pools.
- **Air-Gap & Sandbox Resilience**: Built-in curated legal corpus (`curated_legal_corpus.py`) providing pinpoint citations, verbatim quotes, and deep verification links even when outbound network access is restricted or throttled.
- **Practice-Area Preset Bundles**: Instant multi-source configurations for transactional M&A, commercial litigation, regulatory compliance, US-only, and EU/UK research.
- **Executive Report Synthesis**: Standardised 5-section legal report template (`assets/report_template.md`) matching top-tier legal practice standards.

---

## Directory Structure

```text
suijuris-search/
├── SKILL.md                                     # Agent Skills manifest & orchestration instructions
├── README.md                                    # Project documentation & quickstart guide
├── LICENSE                                      # Apache-2.0 open-source licence
├── .gitignore                                   # Standard Python, macOS, and IDE exclusions
├── assets/
│   └── report_template.md                       # 5-section executive legal report template
├── references/
│   └── open_legal_sources_registry.md           # API endpoints, query params, and rate limit matrix
└── scripts/
    ├── suijuris_search_runner.py                # Multi-source concurrent CLI orchestrator
    └── sources/                                 # Modular per-source legal adapters
        ├── curated_legal_corpus.py              # In-memory primary legal corpus & sandbox fallback
        ├── search_courtlistener.py              # US Federal/State Case Law, Delaware Chancery & Dockets
        ├── search_us_caselaw.py                 # Case Law search alias & CourtListener wrapper
        ├── search_sec_edgar.py                  # SEC EDGAR filings & Exhibit 10.x Material Contracts
        ├── search_us_regulations.py             # Federal Register API v1 & eCFR Titles 1–50
        ├── search_us_code_tax.py                # US Code (GovInfo USLM) & IRS Title 26 Tax Law
        ├── search_eur_lex.py                    # EU CELLAR SPARQL (Directives, Regulations, CJEU)
        ├── search_uk_law.py                     # UK Legislation (legislation.gov.uk) & Find Case Law
        ├── search_uk_companies_house.py         # UK Companies House filings, PSCs & charges
        ├── search_de_law.py                     # Germany Gesetze-im-Internet & Federal Courts (BGH)
        ├── search_nordics_law.py                # Sweden Riksdagen, Norway Lovdata, Denmark & Finland
        ├── search_eu_national_law.py            # France (Légifrance), Netherlands & Spain (BOE)
        └── search_ip_patents.py                 # USPTO Open Data, PatentsView & PTAB Decisions
```

---

## Supported Legal Data Sources

| Source ID | Adapter Script | Jurisdiction & Scope | Primary Government / Judicial APIs |
| :--- | :--- | :--- | :--- |
| **`courtlistener`** | `scripts/sources/search_courtlistener.py` | **US Federal & 50-State Courts, Dockets & Citator** | Free Law Project **CourtListener REST API v4/v3** (`/search/` for Opinions `type=o`, RECAP PACER Dockets `type=r`, Oral Arguments `type=oa`, Judges `type=p`, and `/citation-lookup/` citator verification). |
| **`sec_edgar`** | `scripts/sources/search_sec_edgar.py` | **US Corporate & Securities** | SEC EDGAR Full-Text Search (`efts.sec.gov`) & Submissions API (`10-K`, `10-Q`, `8-K`, `S-1`, `DEF 14A`, `20-F`, and **Exhibit 10.x / 2.1 executed material contracts**). |
| **`us_caselaw`** | `scripts/sources/search_us_caselaw.py` | **US Federal & 50-State Courts** | Direct alias to CourtListener / Harvard CAP search (`court=scotus`, `court=delch`, `court=ca2`, etc.). |
| **`us_regulations`** | `scripts/sources/search_us_regulations.py` | **US Federal Rules & CFR** | **Federal Register API v1** (Final/Proposed Rules, Presidential Documents) + **eCFR Search API v1** (Titles 1–50 CFR, including Title 17 SEC & Title 16 FTC). |
| **`us_code_tax`** | `scripts/sources/search_us_code_tax.py` | **US Statutory & IRS Tax Law** | **GovInfo Search API** (`USCODE` & `STATUTE` USLM XML), **Congress.gov**, and **IRS Title 26 Internal Revenue Code / Revenue Rulings / PLRs**. |
| **`eur_lex`** | `scripts/sources/search_eur_lex.py` | **European Union & CJEU** | **EU Publications Office CELLAR SPARQL Endpoint** (Treaties, Regulations like GDPR/AI Act/DORA/MiCA, Directives, and **CJEU / CURIA Case Law**). |
| **`uk_law`** | `scripts/sources/search_uk_law.py` | **United Kingdom Statutes & Courts** | **`legislation.gov.uk` Atom/XML API** (UK Public General Acts & SIs) + **UK National Archives `Find Case Law` LegalDocML API** (UKSC, EWCA, EWHC). |
| **`uk_companies_house`** | `scripts/sources/search_uk_companies_house.py` | **United Kingdom Corporate Registry** | **UK Companies House REST API** (`api.company-information.service.gov.uk` — Corporate filings, Articles of Association, PSC registers, s. 859A charges, and ECCTA 2023 records). |
| **`de_law`** | `scripts/sources/search_de_law.py` | **Germany Statutes & Federal Courts** | **OpenLegalData DE API** (`/api/laws/` & `/api/cases/`) + **BMJ `Gesetze-im-Internet` / `Rechtsprechung-im-Internet`** (BGB, HGB, AktG, GmbHG, InsO, BGH, BVerfG). |
| **`nordics_law`** | `scripts/sources/search_nordics_law.py` | **Nordics (SE, NO, DK, FI)** | **Sweden Riksdagen Open Data API** (`data.riksdagen.se` — SFS statutes & *förarbeten* preparatory works), **Norway Lovdata API**, **Denmark Retsinformation**, and **Finland Finlex**. |
| **`eu_national_law`** | `scripts/sources/search_eu_national_law.py` | **France, Netherlands & Spain** | **Netherlands `Rechtspraak.nl` Open XML API** (Hoge Raad & ECLI judgments), **France `Légifrance` & `Judilibre` (PISTE API)**, and **Spain `BOE` Datos Abiertos API**. |
| **`ip_patents`** | `scripts/sources/search_ip_patents.py` | **US & Global IP / Patents** | **USPTO Open Data / IBD API**, **USPTO PTAB API v2** (IPR/PGR decisions), **PatentsView API**, and WIPO/EPO patent family pointers. |

---

## Preset Source Bundles

Rather than specifying individual source identifiers, you can query curated bundles tailored to specific legal practice areas:

| Bundle Name | Flag | Included Sources | Recommended Use Case |
| :--- | :--- | :--- | :--- |
| **Core** *(Default)* | `--sources core` | `courtlistener`, `sec_edgar`, `us_regulations`, `eur_lex`, `uk_law` | General multi-jurisdictional research across primary US, EU, and UK databases. |
| **All** | `--sources all` | All 11 sources | Exhaustive worldwide legal intelligence sweep across all supported repositories. |
| **United States** | `--sources us` | `courtlistener`, `sec_edgar`, `us_regulations`, `us_code_tax`, `ip_patents` | Comprehensive US federal, state, regulatory, statutory, and IP research. |
| **Europe & UK** | `--sources eu_uk` | `eur_lex`, `uk_law`, `uk_companies_house`, `de_law`, `nordics_law`, `eu_national_law` | Pan-European comparative law, EU directives, and UK common/statutory law. |
| **Transactional** | `--sources transactional` | `sec_edgar`, `courtlistener`, `us_code_tax`, `uk_law`, `uk_companies_house`, `de_law`, `eur_lex` | M&A deal terms, "what's market" contract clauses (Exhibit 10.x), Delaware precedent, corporate filings, and company registries. |
| **Litigation** | `--sources litigation` | `courtlistener`, `us_regulations`, `uk_law`, `eur_lex`, `de_law`, `eu_national_law` | Judicial precedent, dispute resolution, appellate decisions, court dockets, and evidentiary standards. |
| **Regulatory** | `--sources regulatory` | `us_regulations`, `us_code_tax`, `eur_lex`, `uk_law`, `de_law`, `nordics_law`, `sec_edgar` | Cross-border compliance, GRC, horizon scanning, antitrust, AI safety, and financial regulations (DORA, MiCA, SEC). |

---

## Command-Line Usage

### 1. Concurrent Multi-Source Orchestrator

The main orchestrator concurrently queries the chosen source adapters and formats the results into a Markdown dossier or JSON payload:

```bash
# Basic search using the default 'core' bundle (Markdown output)
python3 scripts/suijuris_search_runner.py --query "material adverse change"

# M&A transactional search saved directly to a file
python3 scripts/suijuris_search_runner.py \
  --query "fiduciary out termination fee" \
  --sources transactional \
  --limit-per-source 5 \
  --format markdown \
  --output transactional_dossier.md

# Regulatory compliance search across US and EU
python3 scripts/suijuris_search_runner.py \
  --query "artificial intelligence high risk conformity" \
  --sources regulatory \
  --format json \
  --output regulatory_findings.json

# Custom combination of specific sources
python3 scripts/suijuris_search_runner.py \
  --query "piercing the corporate veil" \
  --sources "courtlistener,uk_law,uk_companies_house" \
  --limit-per-source 3

# Targeted search with court filtering (e.g. Delaware Court of Chancery)
python3 scripts/suijuris_search_runner.py \
  --query "ordinary course covenant" \
  --sources courtlistener \
  --court delch

# List all available source adapters and preset bundles
python3 scripts/suijuris_search_runner.py --list-sources
```

### 2. Standalone Source Adapters

Each adapter script under `scripts/sources/` can also be executed individually for granular, source-specific investigations:

```bash
# Query US SEC EDGAR specifically for executed Exhibit 10 material contracts
python3 scripts/sources/search_sec_edgar.py --query "indemnification cap" --forms "10-K,8-K,EX-10" --limit 5

# Query CourtListener for Delaware Chancery decisions
python3 scripts/sources/search_us_caselaw.py --query "Caremark duty of loyalty" --court delch --limit 5

# Query US Federal Register and eCFR (Title 17 SEC)
python3 scripts/sources/search_us_regulations.py --query "climate disclosures" --cfr-title 17 --limit 5

# Query European Union CELLAR SPARQL for EU Regulations
python3 scripts/sources/search_eur_lex.py --query "digital operational resilience act" --limit 5

# Query UK Legislation and National Archives Find Case Law
python3 scripts/sources/search_uk_law.py --query "directors general duties" --limit 5

# Query UK Companies House registry
python3 scripts/sources/search_uk_companies_house.py --query "Revolut Ltd" --limit 3

# Query USPTO Patent Public Search and PTAB Decisions
python3 scripts/sources/search_ip_patents.py --query "machine learning transformer" --limit 5
```

---

## Offline & Sandbox Resilience (`curated_legal_corpus.py`)

When executed inside isolated execution environments, sandboxed runner containers, or air-gapped systems where outbound internet connectivity is restricted, SuiJuris automatically switches to its **in-memory verified legal authority corpus**:

1. **Curated Precedent Database**: Contains indexed, pinpoint-cited records of landmark decisions (*Akorn v. Fresenius*, *AB Stable v. MAPS Hotels*, *Caremark*, *Revlon*, *Chevron / Loper Bright*), key statutes (DGCL, UK Companies Act 2006, BGB, US Code), major regulations (EU AI Act, GDPR, eCFR Title 17), and market contract filings.
2. **Deep-Link Verification Index**: Automatically constructs direct, clickable query URLs targeting official government and court registries (CourtListener, EUR-Lex, SEC EDGAR, legislation.gov.uk) so practitioners can verify citations with a single click.

---

## Legal Intelligence Report Synthesis

The skill includes a production-grade report template at [`assets/report_template.md`](assets/report_template.md). Autonomous agents utilising this skill synthesise output into a 5-section executive report:

1. **Executive Summary & Plain-English Synthesis**: Clear, accessible business explanations paired with rigorous legal terminology.
2. **Cross-Jurisdictional Primary Authority Matrix**: Tabular synthesis of controlling statutes, regulations, court decisions, and filing identifiers.
3. **Deep-Dive Analysis by Source & Jurisdiction**: Detailed breakdowns covering U.S. statutory/regulatory posture, judicial precedent and litigation standards, corporate filings and "what's market" contract benchmarks, EU directives/regulations, and UK/Continental common and civil law authorities.
4. **Comparative Risk & Practical Drafting Recommendations**: Side-by-side jurisdictional risk matrix with practical contract drafting and compliance action items.
5. **Verification Log & Raw Source Citations**: Auditable trail of exact endpoints, timestamps, and direct primary source links.

---

## Agent Skills Specification

This repository conforms strictly to the **Agent Skills specification** ([`agentskills.io`](https://agentskills.io/specification)):
- Manifest metadata defined in [`SKILL.md`](SKILL.md).
- Strict directory layout separating executable logic (`scripts/`), reference documentation (`references/`), and report assets (`assets/`).
- Standardised argument passing and machine-readable output formats (`json`, `markdown`).

---

## Licence

Distributed under the [Apache License, Version 2.0](LICENSE).
