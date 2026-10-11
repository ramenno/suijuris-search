# SuiJuris Open Legal & Regulatory Data Sources Registry

This reference document details the open/free primary legal databases, official APIs, rate limits, and citation standards used by the `suijuris-search` skill (`scripts/suijuris_search_runner.py` and `scripts/sources/*.py`).

---

## 1. Source Adapter Matrix

| Source ID (`--sources`) | Script Path | Official Endpoint(s) | Authentication & Rate Limits | Primary Legal Coverage |
| :--- | :--- | :--- | :--- | :--- |
| **`courtlistener`** | `scripts/sources/search_courtlistener.py` | `https://www.courtlistener.com/api/rest/v4/search/`<br>`https://www.courtlistener.com/api/rest/v4/citation-lookup/` | **Free / Open Source** (Free Law Project); optional `COURTLISTENER_API_TOKEN` env var. Supports `--type o` (Opinions), `--type r` (RECAP Dockets), `--type oa` (Oral Arguments), `--type p` (Judges), and `--verify-citations`. | **10M+ US Federal & 50-State Judicial Opinions** (SCOTUS, Circuit Courts, District Courts, **Delaware Court of Chancery** `court=delch`, Harvard CAP) + **RECAP PACER Docket Archive** + **Open Citation Graph Verification**. |
| **`sec_edgar`** | `scripts/sources/search_sec_edgar.py` | `https://efts.sec.gov/LATEST/search-index`<br>`https://data.sec.gov/submissions/` | **Free / Public Domain**; requires descriptive `User-Agent` header (`SEC_EDGAR_USER_AGENT`), max 10 req/sec. | US public company filings (`10-K`, `10-Q`, `8-K`, `S-1`, `DEF 14A`, `20-F`) and **Item 601 Material Contracts (`EX-10.x`, `EX-2.1`)** for M&A and commercial clause benchmarking. |
| **`us_caselaw`** | `scripts/sources/search_us_caselaw.py` | `https://www.courtlistener.com/api/rest/v3/search/`<br>`https://www.courtlistener.com/api/rest/v4/search/` | **Free / Open Source** (Free Law Project); optional `COURTLISTENER_API_TOKEN` env var for elevated rate limits. | **10M+ US Federal & 50-State Judicial Opinions** (SCOTUS, Circuit Courts, District Courts, **Delaware Court of Chancery** `court=delch`, Harvard CAP historical reporters) + **RECAP PACER Docket Archive** (`type=r`). |
| **`us_regulations`** | `scripts/sources/search_us_regulations.py` | `https://www.federalregister.gov/api/v1/documents.json`<br>`https://www.ecfr.gov/api/search/v1/results` | **Free / US Public Domain** (`17 U.S.C. § 105`); unauthenticated REST JSON APIs. | **Federal Register** (Final Rules, Proposed Rules/NPRMs, Presidential Executive Orders, Agency Notices) and **Electronic Code of Federal Regulations (eCFR Titles 1–50)**, including SEC (Title 17), FTC (Title 16), FDA (Title 21), and IRS Tax (Title 26). |
| **`eur_lex`** | `scripts/sources/search_eur_lex.py` | `https://publications.europa.eu/webapi/rdf/sparql` | **Free / Open Reuse** (EU Commission Decision 2011/833/EU); unauthenticated W3C SPARQL JSON endpoint. | **EUR-Lex & CELLAR**: EU Treaties (Sector 1), EU Regulations, Directives & Decisions (Sector 3: GDPR, EU AI Act, DORA, MiCA, NIS2, DMA/DSA), and **CJEU / General Court Case Law** (Sector 6), plus N-Lex national gateways (FR Légifrance, DE Gesetze-im-Internet, NO Lovdata, ES BOE). |
| **`uk_law`** | `scripts/sources/search_uk_law.py` | `https://www.legislation.gov.uk/all/data.feed`<br>`https://caselaw.nationalarchives.gov.uk/atom.xml` | **Free** (Open Government Licence v3.0 & Open Justice Licence); unauthenticated Atom/LegalDocML XML feeds. | **UK Primary & Secondary Legislation** (UK Public General Acts, Statutory Instruments, Scottish Acts) and **UK Find Case Law** (UK Supreme Court, Privy Council, Court of Appeal, High Court Commercial/Chancery). |
| **`ip_patents`** | `scripts/sources/search_ip_patents.py` | `https://developer.uspto.gov/ibd-api/v1/application/publications`<br>`https://search.patentsview.org/api/v1/patent/` | **Free / Public Domain**; USPTO Open Data Portal & PatentsView REST endpoints. | US granted patents, pre-grant publications, assignee records, PTAB Inter Partes Review (IPR) proceedings, and global WIPO/EPO prior art pointers. |

---

## 2. Preset Source Bundles (`--sources <bundle>`)

Users can specify either individual comma-separated source IDs (e.g., `--sources sec_edgar,eur_lex`) or one of the following preset bundles:

- **`core`** *(Default)*: `sec_edgar,us_caselaw,us_regulations,eur_lex,uk_law`
- **`all`**: `sec_edgar,us_caselaw,us_regulations,eur_lex,uk_law,ip_patents`
- **`us`**: `sec_edgar,us_caselaw,us_regulations`
- **`eu_uk`**: `eur_lex,uk_law`
- **`transactional`** *(M&A, Corporate, Commercial Contracts)*: `sec_edgar,us_caselaw,uk_law,eur_lex`
- **`litigation`** *(Disputes, Briefs, Precedent)*: `us_caselaw,us_regulations,uk_law,eur_lex`
- **`regulatory`** *(Compliance, Horizon Scanning, GRC)*: `us_regulations,eur_lex,uk_law,sec_edgar`

---

## 3. Sandbox & Network Resilience Protocol

When running in a sandboxed environment where outbound internet access is blocked (`=== SANDBOX HINT ===`), the agent should:
1. Request network access via `ask_permission(action="network", target="*", justification="Query official open legal APIs (SEC EDGAR, CourtListener, Federal Register, eCFR, EUR-Lex, legislation.gov.uk) for suijuris-search")` so live API records are retrieved, **OR**
2. Combine the orchestrator script's structured deep-link index with built-in grounded web search to populate full verbatim holdings, statutory provisions, and regulatory citations.
