#!/usr/bin/env python3
"""
SuiJuris Multi-Source Open Legal Search Orchestrator (`suijuris_search_runner.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Concurrently queries all or a user-selected subset of free/open primary legal, regulatory,
statutory, case law, and corporate filing databases across the US, EU, and UK:
  - `sec_edgar`       : U.S. SEC EDGAR Filings (10-K, 10-Q, 8-K, S-1) & Exhibit 10.x Material Contracts
  - `us_caselaw`      : Free Law Project CourtListener (10M+ US Federal/State Opinions, Delaware Chancery, RECAP Dockets)
  - `us_regulations`  : U.S. Federal Register API v1, eCFR API v1 (Titles 1-50 CFR), and U.S. Code / IRS Title 26
  - `eur_lex`         : European Union EUR-Lex / CELLAR SPARQL (EU Regulations, Directives, CJEU Case Law & National Portals)
  - `uk_law`          : UK Legislation (`legislation.gov.uk`), UK National Archives `Find Case Law`, & Companies House
  - `ip_patents`      : USPTO Open Data, PatentsView, PTAB Decisions & Global Patent Index

Produces structured JSON or a comprehensive, citation-grounded Markdown Legal Intelligence Dossier.
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional

# Ensure sibling `sources/` directory is importable regardless of current working directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES_DIR = os.path.join(SCRIPT_DIR, "sources")
if SOURCES_DIR not in sys.path:
    sys.path.insert(0, SOURCES_DIR)

import search_courtlistener  # noqa: E402
import search_de_law  # noqa: E402
import search_eu_national_law  # noqa: E402
import search_eur_lex  # noqa: E402
import search_ip_patents  # noqa: E402
import search_nordics_law  # noqa: E402
import search_sec_edgar  # noqa: E402
import search_uk_companies_house  # noqa: E402
import search_uk_law  # noqa: E402
import search_us_caselaw  # noqa: E402
import search_us_code_tax  # noqa: E402
import search_us_regulations  # noqa: E402

AVAILABLE_SOURCES: Dict[str, Dict[str, Any]] = {
    "courtlistener": {
        "label": "CourtListener (Free Law Project — 10M+ US Opinions, Harvard CAP, Delaware Chancery & RECAP Dockets)",
        "jurisdiction": "US Federal & 50-State Courts",
        "fn": search_courtlistener.search_courtlistener,
    },
    "sec_edgar": {
        "label": "U.S. SEC EDGAR (Filings & Exhibit 10.x Material Contracts)",
        "jurisdiction": "US Corporate / Securities",
        "fn": search_sec_edgar.search_sec_edgar,
    },
    "us_caselaw": {
        "label": "U.S. Case Law & Precedent Alias (CourtListener / CAP)",
        "jurisdiction": "US Federal & 50-State Courts",
        "fn": search_courtlistener.search_courtlistener,
    },
    "us_regulations": {
        "label": "U.S. Federal Register & eCFR (Titles 1–50 C.F.R.)",
        "jurisdiction": "US Federal Administrative & Regulatory",
        "fn": search_us_regulations.search_us_regulations,
    },
    "us_code_tax": {
        "label": "U.S. Code (GovInfo USLM), Congress.gov & IRS Tax Law (Title 26 USC)",
        "jurisdiction": "US Federal Statutory & Tax",
        "fn": search_us_code_tax.search_us_code_tax,
    },
    "eur_lex": {
        "label": "European Union EUR-Lex, CELLAR SPARQL & CJEU Case Law",
        "jurisdiction": "European Union & EU Member States",
        "fn": search_eur_lex.search_eur_lex,
    },
    "uk_law": {
        "label": "UK Legislation (legislation.gov.uk) & Find Case Law (National Archives)",
        "jurisdiction": "United Kingdom (Statutes & Courts)",
        "fn": search_uk_law.search_uk_law,
    },
    "uk_companies_house": {
        "label": "UK Companies House Corporate Registry (Filings, PSCs, Charges & ECCTA 2023)",
        "jurisdiction": "United Kingdom (Corporate Registry)",
        "fn": search_uk_companies_house.search_uk_companies_house,
    },
    "de_law": {
        "label": "Germany Primary Law (Gesetze-im-Internet BGB/HGB/AktG, BGH/BVerfG & OpenLegalData DE)",
        "jurisdiction": "Germany",
        "fn": search_de_law.search_de_law,
    },
    "nordics_law": {
        "label": "Nordics Primary Law (Sweden Riksdagen SFS & Förarbeten, Norway Lovdata, Denmark, Finland)",
        "jurisdiction": "Nordic Region (SE, NO, DK, FI)",
        "fn": search_nordics_law.search_nordics_law,
    },
    "eu_national_law": {
        "label": "France (Légifrance/Judilibre), Netherlands (Rechtspraak/KOOP) & Spain (BOE/CENDOJ)",
        "jurisdiction": "Continental Europe (FR, NL, ES)",
        "fn": search_eu_national_law.search_eu_national_law,
    },
    "ip_patents": {
        "label": "USPTO Open Data, PTAB Decisions API v2 & PatentsView",
        "jurisdiction": "US & Global IP / Patents",
        "fn": search_ip_patents.search_ip_patents,
    },
}

PRESET_BUNDLES: Dict[str, List[str]] = {
    "all": [
        "courtlistener",
        "sec_edgar",
        "us_regulations",
        "us_code_tax",
        "eur_lex",
        "uk_law",
        "uk_companies_house",
        "de_law",
        "nordics_law",
        "eu_national_law",
        "ip_patents",
    ],
    "core": ["courtlistener", "sec_edgar", "us_regulations", "eur_lex", "uk_law"],
    "us": ["courtlistener", "sec_edgar", "us_regulations", "us_code_tax", "ip_patents"],
    "eu_uk": ["eur_lex", "uk_law", "uk_companies_house", "de_law", "nordics_law", "eu_national_law"],
    "transactional": ["sec_edgar", "courtlistener", "us_code_tax", "uk_law", "uk_companies_house", "de_law", "eur_lex"],
    "litigation": ["courtlistener", "us_regulations", "uk_law", "eur_lex", "de_law", "eu_national_law"],
    "regulatory": ["us_regulations", "us_code_tax", "eur_lex", "uk_law", "de_law", "nordics_law", "sec_edgar"],
}


def resolve_selected_sources(sources_arg: str) -> List[str]:
    tokens = [t.strip().lower() for t in sources_arg.split(",") if t.strip()]
    if not tokens:
        return PRESET_BUNDLES["core"]

    resolved: List[str] = []
    for tok in tokens:
        if tok in PRESET_BUNDLES:
            for s in PRESET_BUNDLES[tok]:
                if s not in resolved:
                    resolved.append(s)
        elif tok in AVAILABLE_SOURCES:
            if tok not in resolved:
                resolved.append(tok)
        else:
            raise ValueError(
                f"Unknown source or bundle '{tok}'. Valid sources: {list(AVAILABLE_SOURCES.keys())}; "
                f"valid bundles: {list(PRESET_BUNDLES.keys())}"
            )
    return resolved


def run_federated_search(
    query: str,
    selected_sources: List[str],
    limit_per_source: int = 5,
    court: Optional[str] = None,
    edgar_forms: Optional[str] = None,
    cfr_title: Optional[int] = None,
) -> Dict[str, Any]:
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    source_outputs: Dict[str, Dict[str, Any]] = {}

    def _invoke(src_key: str) -> Dict[str, Any]:
        fn: Callable[..., Dict[str, Any]] = AVAILABLE_SOURCES[src_key]["fn"]
        if src_key == "sec_edgar":
            return fn(query=query, forms=edgar_forms, limit=limit_per_source)
        if src_key == "us_caselaw":
            return fn(query=query, court=court, limit=limit_per_source)
        if src_key == "us_regulations":
            return fn(query=query, cfr_title=cfr_title, limit=limit_per_source)
        return fn(query=query, limit=limit_per_source)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, len(selected_sources))) as pool:
        future_map = {pool.submit(_invoke, s): s for s in selected_sources}
        for fut in concurrent.futures.as_completed(future_map):
            src_key = future_map[fut]
            try:
                source_outputs[src_key] = fut.result()
            except Exception as exc:
                source_outputs[src_key] = {
                    "source_id": src_key,
                    "source_title": AVAILABLE_SOURCES[src_key]["label"],
                    "jurisdiction": AVAILABLE_SOURCES[src_key]["jurisdiction"],
                    "query": query,
                    "status": "error",
                    "error_note": str(exc),
                    "count": 0,
                    "results": [],
                }

    ordered_results = [source_outputs[s] for s in selected_sources if s in source_outputs]
    total_records = sum(s.get("count", 0) for s in ordered_results)
    live_sources = sum(1 for s in ordered_results if s.get("status") == "live_api")

    return {
        "skill": "suijuris-search",
        "query": query,
        "executed_at": timestamp,
        "selected_sources": selected_sources,
        "total_sources_queried": len(selected_sources),
        "live_api_sources_count": live_sources,
        "total_records_retrieved": total_records,
        "sources": ordered_results,
    }


def render_markdown_dossier(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    q = payload["query"]
    lines.append(f"# SuiJuris Open Legal Intelligence Dossier: `{q}`")
    lines.append("")
    lines.append(f"- **Search Query / Legal Topic:** `{q}`")
    lines.append(f"- **Executed Timestamp:** {payload['executed_at']}")
    lines.append(
        f"- **Sources Queried ({payload['total_sources_queried']}):** "
        + ", ".join(f"`{s}`" for s in payload["selected_sources"])
    )
    lines.append(f"- **Total Primary Authority & Filing Records:** {payload['total_records_retrieved']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Cross-Jurisdictional Authority Matrix")
    lines.append("")
    lines.append("| # | Source Database | Jurisdiction | Document / Authority Title | Official Citation / ID | Date | Direct Link |")
    lines.append("| :- | :--- | :--- | :--- | :--- | :--- | :--- |")

    row_idx = 1
    for src in payload["sources"]:
        for rec in src.get("results", []):
            title_clean = str(rec.get("title", "")).replace("|", "\\|")
            cite_clean = str(rec.get("citation", "")).replace("|", "\\|")
            jur_clean = str(rec.get("jurisdiction", "")).replace("|", "\\|")
            src_name = str(rec.get("source_name", src.get("source_title", ""))).replace("|", "\\|")
            date_str = str(rec.get("date", "N/A"))
            url = rec.get("url", "#")
            lines.append(
                f"| {row_idx} | **{src_name}** | {jur_clean} | {title_clean} | `{cite_clean}` | {date_str} | [View Source]({url}) |"
            )
            row_idx += 1

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Source-by-Source Primary Law & Regulatory Findings")
    lines.append("")

    for src in payload["sources"]:
        lines.append(f"### {src['source_title']}")
        lines.append(
            f"- **Jurisdiction:** {src.get('jurisdiction')} | "
            f"**Retrieval Mode:** `{src.get('status')}` | "
            f"**Records Returned:** {src.get('count', 0)}"
        )
        if src.get("error_note"):
            lines.append(f"- **Adapter Note:** _{src['error_note']}_")
        lines.append("")

        for idx, rec in enumerate(src.get("results", []), 1):
            lines.append(f"#### {idx}. {rec.get('title')}")
            lines.append(f"- **Citation / Identifier:** `{rec.get('citation')}`")
            lines.append(f"- **Issuing Court / Agency:** {rec.get('authority_court_or_agency')} ({rec.get('date')})")
            lines.append(f"- **Document Type:** {rec.get('doc_type')}")
            lines.append(f"- **Excerpt / Scope Summary:** {rec.get('summary_snippet')}")
            lines.append(f"- **Legal Significance:** {rec.get('legal_significance')}")
            lines.append(f"- **Primary Source URL:** {rec.get('url')}")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SuiJuris Open Legal Search Orchestrator — Search across free US, EU, and UK primary legal databases."
    )
    parser.add_argument("--query", "-q", required=False, default=None, help="Keyword, legal doctrine, statute, or corporate topic")
    parser.add_argument(
        "--sources",
        "-s",
        default="core",
        help=(
            "Comma-separated source IDs or preset bundle. "
            "Bundles: 'all', 'core' (default), 'us', 'eu_uk', 'transactional', 'litigation', 'regulatory'. "
            "Individual IDs: 'courtlistener', 'sec_edgar', 'us_caselaw', 'us_regulations', 'eur_lex', 'uk_law', 'ip_patents'."
        ),
    )
    parser.add_argument("--limit-per-source", "-n", type=int, default=4, help="Max results per source (default: 4)")
    parser.add_argument("--court", default=None, help="Optional CourtListener court code (e.g., 'scotus', 'delch')")
    parser.add_argument("--edgar-forms", default=None, help="Optional SEC EDGAR form filter (e.g., '10-K,8-K,EX-10')")
    parser.add_argument("--cfr-title", type=int, default=None, help="Optional US eCFR Title filter (e.g., 17, 26)")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Output format")
    parser.add_argument("--output", "-o", default=None, help="Optional file path to write output")
    parser.add_argument("--list-sources", action="store_true", help="List all supported open legal data sources and exit")
    args = parser.parse_args()

    if args.list_sources:
        print(json.dumps({"sources": {k: v["label"] for k, v in AVAILABLE_SOURCES.items()}, "bundles": PRESET_BUNDLES}, indent=2))
        return

    if not args.query:
        parser.error("the following arguments are required: --query/-q (unless --list-sources is specified)")

    if not args.query:
        parser.error("the following arguments are required: --query/-q (unless --list-sources is specified)")

    selected = resolve_selected_sources(args.sources)
    payload = run_federated_search(
        query=args.query,
        selected_sources=selected,
        limit_per_source=args.limit_per_source,
        court=args.court,
        edgar_forms=args.edgar_forms,
        cfr_title=args.cfr_title,
    )

    output_text = json.dumps(payload, indent=2) if args.format == "json" else render_markdown_dossier(payload)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"Wrote SuiJuris search dossier ({len(output_text)} chars) to {args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
