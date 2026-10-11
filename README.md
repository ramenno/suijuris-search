# SuiJuris Open Legal Search (`suijuris-search`)

Multi-source legal, regulatory, case law, and corporate filing search across free US, EU, and UK primary databases.

Compliant with the [Agent Skills (`agentskills.io`)](https://agentskills.io/) specification.

## Overview

**SuiJuris Open Legal Search** enables autonomous research across open and free primary legal databases:
- **US SEC EDGAR**: Full-text company filings (10-K, 10-Q, 8-K) and Exhibit 10 material contracts.
- **US Case Law (CourtListener / RECAP)**: Over 10M opinions across federal circuits, district courts, state supreme courts, and Delaware Chancery.
- **US Federal Regulations (Federal Register & eCFR)**: Published rules, proposed rules, public notices, and current Code of Federal Regulations.
- **UK Legislation & Case Law**: Legislation.gov.uk (Acts of Parliament & Statutory Instruments) and Find Case Law (National Archives judgments).
- **EU Law (EUR-Lex CELLAR)**: SPARQL endpoint querying treaties, directives, regulations, and Court of Justice of the EU (CJEU) case law.
- **IP & Patents (USPTO / PatentsView)**: US patents, claims, specifications, and assignments.

Zero external Python package dependencies required — runs entirely on the Python 3.9+ standard library.

For comprehensive documentation, see [SKILL.md](SKILL.md) and the [Open Legal Sources Registry](references/open_legal_sources_registry.md).

## Licence

[Apache-2.0](LICENSE)
