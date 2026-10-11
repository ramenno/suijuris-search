#!/usr/bin/env python3
"""
SEC EDGAR Open Search Adapter (`search_sec_edgar.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import curated_legal_corpus  # noqa: E402

DEFAULT_USER_AGENT = os.environ.get(
    "SEC_EDGAR_USER_AGENT",
    "SuiJurisLegalSearchSkill/1.0 (EnterpriseLegalResearch; contact@suijuris-example.org)",
)
EFTS_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"


def build_curated_edgar_fallback(
    query: str, forms: Optional[str], limit: int, note: str
) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="sec_edgar", query=query, limit=limit, note=note
    )


def search_sec_edgar(
    query: str,
    forms: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 5,
    timeout: int = 12,
) -> Dict[str, Any]:
    params: Dict[str, str] = {"q": query}
    if forms:
        params["forms"] = forms
    if start_date or end_date:
        params["dateRange"] = "custom"
        if start_date:
            params["startdt"] = start_date
        if end_date:
            params["enddt"] = end_date

    url = f"{EFTS_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
        },
    )

    results: List[Dict[str, Any]] = []
    status = "live_api"
    error_note = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            hits = payload.get("hits", {}).get("hits", [])
            total_hits = payload.get("hits", {}).get("total", {}).get("value", len(hits))

            for hit in hits[:limit]:
                src = hit.get("_source", {})
                ciks = src.get("ciks", [])
                cik = ciks[0] if ciks else ""
                display_names = src.get("display_names", [])
                entity_name = display_names[0] if display_names else "SEC Registrant"
                form = src.get("form", src.get("root_form", "Filing"))
                file_date = src.get("file_date", "")
                adsh = src.get("adsh", "").replace("-", "")
                doc_id = hit.get("_id", "")
                file_name = doc_id.split(":")[-1] if ":" in doc_id else ""

                if cik and adsh and file_name:
                    cik_int = str(int(cik)) if cik.isdigit() else cik
                    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{adsh}/{file_name}"
                else:
                    filing_url = f"https://www.sec.gov/edgar/search/#/q={urllib.parse.quote_plus(query)}"

                results.append(
                    {
                        "source_id": "sec_edgar",
                        "source_name": "U.S. SEC EDGAR",
                        "jurisdiction": "United States (Federal Securities & Corporate)",
                        "doc_type": f"Form {form}",
                        "title": f"{entity_name} — Form {form} ({file_date})",
                        "citation": f"SEC CIK {cik}, Accession No. {src.get('adsh', 'N/A')} (Form {form}, filed {file_date})",
                        "date": file_date,
                        "authority_court_or_agency": "U.S. Securities and Exchange Commission (SEC)",
                        "url": filing_url,
                        "api_endpoint": url,
                        "summary_snippet": (
                            f"SEC Form {form} filed by {entity_name} on {file_date} "
                            f"(Period ending {src.get('period_ending', 'N/A')})."
                        ),
                        "legal_significance": (
                            f"Primary public company regulatory filing / exhibit matching '{query}' (Total EDGAR matches: {total_hits})."
                        ),
                        "retrieval_mode": "live_api",
                    }
                )

            if not results:
                results = build_curated_edgar_fallback(query, forms, limit, "Zero direct hits returned.")
    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live network request unavailable or blocked ({type(exc).__name__}: {exc})"
        results = build_curated_edgar_fallback(query, forms, limit, error_note)

    return {
        "source_id": "sec_edgar",
        "source_title": "U.S. SEC EDGAR (Corporate Filings & Exhibit 10.x Material Contracts)",
        "jurisdiction": "United States",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search U.S. SEC EDGAR filings and Exhibit 10.x contracts.")
    parser.add_argument("--query", "-q", required=True, help="Search keyword, clause, or legal topic")
    parser.add_argument("--forms", default=None, help="Comma-separated SEC form types")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()

    data = search_sec_edgar(query=args.query, forms=args.forms, limit=args.limit)
    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        for idx, r in enumerate(data["results"], 1):
            print(f"{idx}. **{r['title']}** (`{r['citation']}`)")


if __name__ == "__main__":
    main()
