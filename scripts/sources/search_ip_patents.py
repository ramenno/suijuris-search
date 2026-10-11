#!/usr/bin/env python3
"""
USPTO Open Data, PatentsView & PTAB Proceedings Search Adapter (`search_ip_patents.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries three official IP/Patent endpoints:
1. USPTO Open Data Portal / IBD API (`developer.uspto.gov/ibd-api/v1/application/publications`)
2. USPTO Patent Trial and Appeal Board (PTAB) API v2 (`developer.uspto.gov/ptab-api/decisions`)
   covering Inter Partes Review (IPR), Post-Grant Review (PGR), and Ex Parte appeal decisions
3. PatentsView REST API (`search.patentsview.org/api/v1/patent/`)
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

USPTO_IBD_URL = "https://developer.uspto.gov/ibd-api/v1/application/publications"
USPTO_PTAB_URL = "https://developer.uspto.gov/ptab-api/decisions"


def build_curated_ip_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="ip_patents", query=query, limit=limit, note=note
    )


def search_ip_patents(query: str, limit: int = 5, timeout: int = 10) -> Dict[str, Any]:
    headers = {
        "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
        "Accept": "application/json",
    }
    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    status = "live_api"

    # 1. USPTO IBD Patent Publications
    ibd_limit = max(1, (limit + 1) // 2)
    ibd_url = f"{USPTO_IBD_URL}?{urllib.parse.urlencode({'searchText': query, 'rows': str(ibd_limit), 'start': '0'})}"
    try:
        req = urllib.request.Request(ibd_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for item in payload.get("results", [])[:ibd_limit]:
                title = item.get("inventionTitle", "US Patent Publication")
                pub_num = item.get("publicationDocumentIdentifier", "USPTO Pub.")
                app_num = item.get("applicationNumberText", "")
                pub_date = item.get("publicationDate", "")
                assignee = item.get("assigneeEntityName", "Applicant")
                abstract = item.get("abstractText", "")
                if isinstance(abstract, list):
                    abstract = " ".join(abstract)

                results.append(
                    {
                        "source_id": "ip_patents",
                        "source_name": "USPTO Open Data Portal",
                        "jurisdiction": "United States (Patent / IP)",
                        "doc_type": "US Patent / Pre-Grant Publication",
                        "title": f"{title} ({pub_num})",
                        "citation": f"US {pub_num} (App. No. {app_num}, pub. {pub_date})",
                        "date": pub_date,
                        "authority_court_or_agency": f"USPTO (Assignee: {assignee})",
                        "url": f"https://patents.google.com/patent/US{pub_num}/en",
                        "api_endpoint": ibd_url,
                        "summary_snippet": str(abstract)[:450] if abstract else f"US Patent publication {pub_num}.",
                        "legal_significance": "USPTO technical disclosure and patent claim record.",
                        "retrieval_mode": "live_api",
                    }
                )
    except Exception as exc:
        errors.append(f"USPTO IBD API: {type(exc).__name__}: {exc}")

    # 2. USPTO PTAB Decisions API v2 (IPR / PGR / Appeal Decisions)
    ptab_limit = max(1, limit - len(results))
    ptab_url = f"{USPTO_PTAB_URL}?{urllib.parse.urlencode({'proceedingNumber': query, 'rows': str(ptab_limit)})}"
    try:
        req = urllib.request.Request(ptab_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for item in payload.get("results", [])[:ptab_limit]:
                proc_num = item.get("proceedingNumber", "IPR")
                dec_type = item.get("subdecisionTypeCategory", "PTAB Decision")
                dec_date = item.get("decisionDate", "")
                patent_num = item.get("respondentPatentNumber", "")
                patent_owner = item.get("respondentPartyName", "Patent Owner")
                petitioner = item.get("appellantPartyName", "Petitioner")

                results.append(
                    {
                        "source_id": "ip_patents",
                        "source_name": "USPTO Patent Trial and Appeal Board (PTAB API v2)",
                        "jurisdiction": "United States (PTAB — 35 U.S.C. §§ 311–319)",
                        "doc_type": f"PTAB {dec_type}",
                        "title": f"{petitioner} v. {patent_owner} (Proceeding {proc_num})",
                        "citation": f"PTAB {proc_num} (U.S. Patent {patent_num}, {dec_date})",
                        "date": dec_date,
                        "authority_court_or_agency": "USPTO Patent Trial and Appeal Board (PTAB)",
                        "url": "https://developer.uspto.gov/ptab-web/",
                        "api_endpoint": ptab_url,
                        "summary_snippet": f"PTAB {dec_type} in {proc_num} challenging U.S. Patent {patent_num}.",
                        "legal_significance": "Adjudicates patentability and validity under 35 U.S.C. §§ 102/103.",
                        "retrieval_mode": "live_api",
                    }
                )
    except Exception as exc:
        errors.append(f"USPTO PTAB API: {type(exc).__name__}: {exc}")

    if not results:
        status = "fallback_index"
        results = build_curated_ip_fallback(query, limit, "; ".join(errors) or "No direct hits")

    return {
        "source_id": "ip_patents",
        "source_title": "U.S. & Global IP, Patents & PTAB Proceedings (USPTO Open Data / PTAB API v2 / PatentsView)",
        "jurisdiction": "United States & International IP",
        "query": query,
        "status": status,
        "error_note": "; ".join(errors) if errors else None,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search USPTO Open Data, PatentsView, and PTAB proceedings.")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()
    print(json.dumps(search_ip_patents(query=args.query, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
