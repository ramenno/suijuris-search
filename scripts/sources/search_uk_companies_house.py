#!/usr/bin/env python3
"""
UK Companies House Corporate Registry Search Adapter (`search_uk_companies_house.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries the UK Companies House REST API (`api.company-information.service.gov.uk/search/companies`)
and Public Register for UK corporate registrations, Articles of Association, directors,
Persons with Significant Control (PSC), charges/mortgages, and insolvency filings.
"""

import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import curated_legal_corpus  # noqa: E402

COMPANIES_HOUSE_API_URL = "https://api.company-information.service.gov.uk/search/companies"


def build_curated_ch_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="uk_companies_house", query=query, limit=limit, note=note
    )


def search_uk_companies_house(query: str, limit: int = 5, timeout: int = 12) -> Dict[str, Any]:
    params = {"q": query, "items_per_page": str(limit)}
    url = f"{COMPANIES_HOUSE_API_URL}?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
        "Accept": "application/json",
    }
    api_key = os.environ.get("COMPANIES_HOUSE_API_KEY")
    if api_key:
        b64_auth = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {b64_auth}"

    req = urllib.request.Request(url, headers=headers)
    results: List[Dict[str, Any]] = []
    status = "live_api"
    error_note = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for item in payload.get("items", [])[:limit]:
                title = item.get("title", "UK Registered Company")
                comp_num = item.get("company_number", "N/A")
                comp_status = item.get("company_status", "active")
                comp_type = item.get("company_type", "ltd")
                date_inc = item.get("date_of_creation", "")
                addr = item.get("address_snippet", "")
                desc = item.get("description", "")

                results.append(
                    {
                        "source_id": "uk_companies_house",
                        "source_name": "UK Companies House Registry",
                        "jurisdiction": "United Kingdom (England & Wales, Scotland, NI)",
                        "doc_type": f"UK Corporate Registration ({comp_type.upper()})",
                        "title": f"{title} (Company No. {comp_num})",
                        "citation": f"UK Companies House Reg. No. {comp_num} (Status: {comp_status.upper()})",
                        "date": date_inc,
                        "authority_court_or_agency": "Registrar of Companies for England and Wales (Companies House)",
                        "url": f"https://find-and-update.company-information.service.gov.uk/company/{comp_num}",
                        "api_endpoint": url,
                        "summary_snippet": f"{desc}. Registered Office: {addr}. Incorporated: {date_inc}.",
                        "legal_significance": (
                            "Official UK statutory corporate register (Companies Act 2006 & ECCTA 2023) covering "
                            "Articles of Association, PSCs, and registered charges."
                        ),
                        "retrieval_mode": "live_api",
                    }
                )
            if not results:
                results = build_curated_ch_fallback(query, limit, "Zero direct company matches.")
    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live API requires COMPANIES_HOUSE_API_KEY or network ({type(exc).__name__}: {exc})"
        results = build_curated_ch_fallback(query, limit, error_note)

    return {
        "source_id": "uk_companies_house",
        "source_title": "UK Companies House Corporate Registry (Filings, PSCs, Charges & ECCTA 2023)",
        "jurisdiction": "United Kingdom",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search UK Companies House corporate registry.")
    parser.add_argument("--query", "-q", required=True, help="Company name, officer, or corporate topic")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()
    print(json.dumps(search_uk_companies_house(query=args.query, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
