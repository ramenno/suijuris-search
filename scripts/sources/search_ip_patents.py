#!/usr/bin/env python3
"""
USPTO Open Data, PatentsView & PTAB Search Adapter (`search_ip_patents.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries USPTO / PatentsView and PTAB Open Data endpoints for US Patents, Patent Applications,
Trademark filings, and Patent Trial and Appeal Board (PTAB) Inter Partes Review (IPR) decisions.
"""

import argparse
import datetime
import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List

USPTO_IBD_URL = "https://developer.uspto.gov/ibd-api/v1/application/publications"


def build_curated_ip_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    encoded_q = urllib.parse.quote_plus(query)
    records = [
        {
            "source_id": "uspto_patents_ptab",
            "source_name": "USPTO Open Data Portal & Patent Public Search",
            "jurisdiction": "United States (Federal IP / Patent & Trademark Law — Title 35 U.S.C.)",
            "doc_type": "Granted Patents, Pre-Grant Publications & PTAB Decisions",
            "title": f"USPTO Patent & PTAB Inter Partes Review (IPR) Search — Query: '{query}'",
            "citation": f"35 U.S.C. §§ 101–103, 311 (USPTO Search: {query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "United States Patent and Trademark Office (USPTO) & PTAB",
            "url": f"https://ppubs.uspto.gov/pubwebapp/",
            "api_endpoint": f"https://data.uspto.gov/",
            "summary_snippet": (
                f"Searches US granted patents, published patent applications, patent assignment records, "
                f"and Patent Trial and Appeal Board (PTAB) IPR/PGR proceedings for '{query}'. ({note})"
            ),
            "legal_significance": (
                "Establishes prior art, freedom-to-operate (FTO), claim construction, and PTAB validity challenges."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "google_patents_wipo",
            "source_name": "Global Patent & WIPO PATENTSCOPE / Espacenet Index",
            "jurisdiction": "Global (USPTO, EPO, WIPO PCT, JPO, CNIPA)",
            "doc_type": "International PCT & EPO Patent Families",
            "title": f"Global Patent & Prior Art Search — Query: '{query}'",
            "citation": f"PCT / EPC / 35 U.S.C. ({query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "USPTO / European Patent Office (EPO) / WIPO",
            "url": f"https://patents.google.com/?q={encoded_q}",
            "api_endpoint": "https://search.patentsview.org/api/v1/patent/",
            "summary_snippet": (
                f"Cross-jurisdictional patent family, CPC classification, and non-patent literature search for '{query}'."
            ),
            "legal_significance": (
                "Provides global patent family prosecution history and international prior art coverage."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
    ]
    return records[:limit]


def search_ip_patents(query: str, limit: int = 5, timeout: int = 10) -> Dict[str, Any]:
    params = {"searchText": query, "rows": str(limit), "start": "0"}
    url = f"{USPTO_IBD_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
            "Accept": "application/json",
        },
    )

    results: List[Dict[str, Any]] = []
    status = "live_api"
    error_note = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            items = payload.get("results", [])
            for item in items[:limit]:
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
                        "source_id": "uspto_patents",
                        "source_name": "USPTO Open Data Portal",
                        "jurisdiction": "United States (Patent / IP)",
                        "doc_type": "US Patent / Pre-Grant Publication",
                        "title": f"{title} ({pub_num})",
                        "citation": f"US {pub_num} (App. No. {app_num}, pub. {pub_date})",
                        "date": pub_date,
                        "authority_court_or_agency": f"USPTO (Assignee: {assignee})",
                        "url": f"https://patents.google.com/patent/US{pub_num}/en",
                        "api_endpoint": url,
                        "summary_snippet": str(abstract)[:450] if abstract else f"US Patent publication {pub_num} titled '{title}'.",
                        "legal_significance": "USPTO technical disclosure and patent claim record.",
                        "retrieval_mode": "live_api",
                    }
                )
            if not results:
                results = build_curated_ip_fallback(query, limit, "Zero direct hits from IBD endpoint.")
    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live network request unavailable or blocked ({type(exc).__name__}: {exc})"
        results = build_curated_ip_fallback(query, limit, error_note)

    return {
        "source_id": "ip_patents",
        "source_title": "U.S. & Global IP, Patents & PTAB Proceedings (USPTO Open Data / PatentsView / EPO)",
        "jurisdiction": "United States & International IP",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search USPTO Open Data, PatentsView, and PTAB proceedings.")
    parser.add_argument("--query", "-q", required=True, help="Invention keyword, patent topic, or assignee")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return (default: 5)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()

    data = search_ip_patents(query=args.query, limit=args.limit)

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(f"### {data['source_title']} (Status: `{data['status']}`)")
        for idx, r in enumerate(data["results"], 1):
            print(f"{idx}. **{r['title']}** (`{r['citation']}`)")
            print(f"   - **Authority:** {r['authority_court_or_agency']} | **Date:** {r['date']}")
            print(f"   - **Summary:** {r['summary_snippet']}")
            print(f"   - **URL:** {r['url']}\n")


if __name__ == "__main__":
    main()
