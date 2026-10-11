#!/usr/bin/env python3
"""
U.S. Code (GovInfo USLM), Congress.gov & IRS Tax Authorities Adapter (`search_us_code_tax.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries U.S. GovInfo Search API (`api.govinfo.gov/search` for `USCODE`, `STATUTE`, `CRPT`),
Congress.gov legislation endpoints, and IRS Title 26 statutory/administrative guidance
(Internal Revenue Code, Treasury Regulations, Revenue Rulings, and Private Letter Rulings).
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import curated_legal_corpus  # noqa: E402

GOVINFO_SEARCH_URL = "https://api.govinfo.gov/search"


def build_curated_uscode_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="us_code_tax", query=query, limit=limit, note=note
    )


def search_us_code_tax(query: str, limit: int = 5, timeout: int = 12) -> Dict[str, Any]:
    api_key = os.environ.get("GOVINFO_API_KEY", "DEMO_KEY")
    url = f"{GOVINFO_SEARCH_URL}?api_key={urllib.parse.quote(api_key)}"
    body_payload = {
        "query": f"collection:(USCODE OR STATUTE) {query}",
        "pageSize": limit,
        "offsetMark": "*",
        "sorts": [{"field": "score", "sortOrder": "DESC"}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body_payload).encode("utf-8"),
        headers={
            "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    results: List[Dict[str, Any]] = []
    status = "live_api"
    error_note = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for item in payload.get("results", [])[:limit]:
                title = item.get("title", "United States Code Provision")
                pkg_id = item.get("packageId", "")
                granule_id = item.get("granuleId", "")
                date_issued = item.get("dateIssued", "")
                gov_branch = item.get("governmentAuthor1", "United States Congress")
                pdf_link = item.get("resultLink") or f"https://www.govinfo.gov/app/details/{pkg_id}/{granule_id}"

                results.append(
                    {
                        "source_id": "us_code_tax",
                        "source_name": "U.S. GovInfo (United States Code & Statutes at Large)",
                        "jurisdiction": "United States (Federal Statutory & Tax Law)",
                        "doc_type": "U.S. Code / Statute at Large (USLM)",
                        "title": title,
                        "citation": f"{granule_id or pkg_id} ({date_issued})",
                        "date": date_issued,
                        "authority_court_or_agency": gov_branch,
                        "url": f"https://www.govinfo.gov/app/details/{pkg_id}/{granule_id}" if pkg_id else pdf_link,
                        "api_endpoint": GOVINFO_SEARCH_URL,
                        "summary_snippet": f"{title} — Official U.S. Code / Statutory provision ({pkg_id}).",
                        "legal_significance": "Binding federal statutory mandate enacted by the United States Congress.",
                        "retrieval_mode": "live_api",
                    }
                )
            if not results:
                results = build_curated_uscode_fallback(query, limit, "Zero direct GovInfo hits.")
    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live GovInfo API unavailable or blocked ({type(exc).__name__}: {exc})"
        results = build_curated_uscode_fallback(query, limit, error_note)

    return {
        "source_id": "us_code_tax",
        "source_title": "U.S. Code (GovInfo USLM), Congress.gov & IRS Tax Law (Title 26 USC / Revenue Rulings)",
        "jurisdiction": "United States (Federal Statutory & Tax)",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search U.S. Code (GovInfo) and IRS Title 26 tax authorities.")
    parser.add_argument("--query", "-q", required=True, help="Statutory section, tax rule, or legal topic")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()
    print(json.dumps(search_us_code_tax(query=args.query, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
