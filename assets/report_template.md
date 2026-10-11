# SuiJuris Legal Intelligence Report Template

Use this structure when synthesizing the final detailed report for the user after executing `scripts/suijuris_search_runner.py`. Every report must combine **rigorous legal precision** (exact statutory/case citations, CELEX numbers, CFR titles, SEC accession numbers, and court hierarchies) with **plain-English executive explanations** so both legal counsel and business/commercial stakeholders can act on the findings immediately.

---

```markdown
# SuiJuris Multi-Jurisdictional Legal Intelligence Report: [Topic / Keyword]

**Prepared Date:** YYYY-MM-DD  
**Search Scope & Sources Queried:** [List of Open Databases Queried, e.g., SEC EDGAR, CourtListener US Case Law, US eCFR / Federal Register, EUR-Lex CELLAR, UK Legislation & Find Case Law]  
**Jurisdictions Covered:** [e.g., United States (Federal & Delaware), European Union, United Kingdom]

---

## 1. Executive Summary & Plain-English Synthesis
- **Plain-English Bottom Line:** *(2–3 paragraphs explaining what the law, regulation, or market practice is in clear, non-jargon business language alongside precise legal terminology.)*
- **Key Cross-Jurisdictional Takeaways:**
  - **United States (Statutory, Regulatory & SEC Practice):** ...
  - **United States (Judicial Precedent & Delaware / Federal Case Law):** ...
  - **European Union (EUR-Lex Directives / Regulations & CJEU Case Law):** ...
  - **United Kingdom (UK Statutes, SIs & English Common Law):** ...

---

## 2. Cross-Jurisdictional Primary Authority Matrix
| # | Jurisdiction | Source Database | Authority / Document Title | Official Citation / Identifier | Date | Controlling Rule / Holding | Direct Link |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | ... | ... | ... | `...` | ... | ... | [Source](...) |

---

## 3. Deep-Dive Analysis by Source & Jurisdiction

### 3.1 U.S. Statutory & Regulatory Framework (`us_regulations` — USC, eCFR & Federal Register)
- **Controlling Statutes & Codified Regulations:** *(Cite exact USC and CFR sections, e.g., `17 C.F.R. § 229.106`, `15 U.S.C. § 18a`, `26 U.S.C. § 368`.)*
- **Recent Rulemaking & Enforcement Posture (Federal Register):** *(Detail recent Final Rules, NPRMs, effective dates, and agency guidance.)*
- **Plain-English Operational Impact:** ...

### 3.2 U.S. Judicial Precedent & Litigation Landscape (`us_caselaw` — CourtListener, Delaware Chancery & RECAP)
- **Leading Judicial Authorities:** *(Analyze leading SCOTUS, Federal Circuit, and Delaware Court of Chancery decisions with full citations, e.g., `Akorn, Inc. v. Fresenius Kabi AG, C.A. No. 2018-0300-JTL (Del. Ch. Oct. 1, 2018)`.)*
- **Judicial Standard & Evidentiary Burden:** *(Explain the multi-factor test, standard of review, or pleading standard.)*
- **Plain-English Litigation Takeaway:** ...

### 3.3 Corporate Filings & "What's Market" Contract Benchmarks (`sec_edgar` — 10-K/8-K & Exhibit 10.x/2.x)
- **Public Company Disclosure Trends:** *(How public companies disclose this issue in Item 1A Risk Factors, Item 7 MD&A, or Form 8-K.)*
- **Exhibit 10.x / 2.1 Material Contract Precedents:** *(How major law firms draft around this topic in publicly filed Merger Agreements, Credit Agreements, or MSAs, including standard carve-outs and risk allocation.)*

### 3.4 European Union Legal & Regulatory Framework (`eur_lex` — EUR-Lex, CELLAR & CJEU)
- **Applicable EU Regulations & Directives:** *(Cite CELEX numbers and Articles, e.g., `Regulation (EU) 2024/1689 (EU AI Act)`, `Regulation (EU) 2016/679 (GDPR)`.)*
- **CJEU / General Court Jurisprudence & Member State Transposition:** ...
- **Plain-English EU Compliance Impact:** ...

### 3.5 United Kingdom Legal & Regulatory Framework (`uk_law` — legislation.gov.uk & Find Case Law)
- **UK Primary Legislation & Statutory Instruments:** *(Cite UK Acts and SIs, e.g., `Companies Act 2006 c. 46`, `UK GDPR / Data Protection Act 2018`.)*
- **English Common Law & Commercial Court Precedent:** *(Cite leading UKSC, EWCA Civ, and EWHC Comm judgments with neutral citations.)*

---

## 4. Comparative Risk & Practical Drafting / Compliance Recommendations
| Dimension / Issue | U.S. Position (Federal / Delaware) | EU Position (EUR-Lex / Member States) | UK Position (English Law) | Recommended Drafting / Compliance Action |
| :--- | :--- | :--- | :--- | :--- |
| ... | ... | ... | ... | ... |

---

## 5. Verification Log & Raw Source Citations
*(Complete list of API queries executed, timestamps, and direct verification URLs.)*
```
