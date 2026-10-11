#!/usr/bin/env python3
"""
US Case Law & PACER Docket Search Adapter (`search_us_caselaw.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries Free Law Project's CourtListener REST API v4 (`courtlistener.com/api/rest/v4/search/`)
covering 10M+ US Federal & 50-State Court Opinions (including SCOTUS, Circuit Courts, and
Delaware Court of Chancery) and the RECAP PACER Docket Archive.
"""

import argparse
import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

COURTLISTENER_SEARCH_URL = "https://www.courtlistener.com/api/rest/v4/search/"
COURTLISTENER_V3_SEARCH_URL = "https://www.courtlistener.com/api/rest/v3/search/"


def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", clean).strip()


def build_curated_caselaw_fallback(
    query: str, search_type: str, court: Optional[str], limit: int, note: str
) -> List[Dict[str, Any]]:
    encoded_q = urllib.parse.quote_plus(query)
    court_param = f"&court={urllib.parse.quote_plus(court)}" if court else ""
    web_url = f"https://www.courtlistener.com/?q={encoded_q}&type={search_type}{court_param}"

    records = [
        {
            "source_id": "us_caselaw_courtlistener",
            "source_name": "Free Law Project — CourtListener & Harvard Caselaw Access Project (CAP)",
            "jurisdiction": "United States (Federal & 50-State Appellate / Supreme Courts)",
            "doc_type": "Published & Unpublished Judicial Opinions (type=o)",
            "title": f"CourtListener Federal & State Case Law Index — Query: '{query}'",
            "citation": f"CourtListener / CAP Precedent Search ({query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": court or "SCOTUS, U.S. Circuit Courts (1st–11th, D.C., Fed. Cir.), District Courts & 50 State Courts",
            "url": web_url,
            "api_endpoint": f"{COURTLISTENER_SEARCH_URL}?q={encoded_q}&type={search_type}",
            "summary_snippet": (
                f"Full-text judicial opinion and citation-graph search across 10M+ federal and state opinions "
                f"(including Harvard CAP historical reporters and daily slip opinions) for '{query}'. ({note})"
            ),
            "legal_significance": (
                "Primary binding and persuasive judicial precedent across US federal and state courts, "
                "including citing/cited-by treatment relationships for authority verification."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "us_caselaw_delaware_chancery",
            "source_name": "Delaware Court of Chancery & Delaware Supreme Court (via CourtListener)",
            "jurisdiction": "United States — State of Delaware (Corporate & M&A Law)",
            "doc_type": "Chancery & Supreme Court Memorandum Opinions",
            "title": f"Delaware Corporate & Fiduciary Precedent Filter — Query: '{query}'",
            "citation": "Del. Ch. / Del. Supr. (court=delch,del)",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "Delaware Court of Chancery & Supreme Court of Delaware",
            "url": f"https://www.courtlistener.com/?q={encoded_q}&type=o&court=delch%20del",
            "api_endpoint": f"{COURTLISTENER_SEARCH_URL}?q={encoded_q}&type=o&court=delch+del",
            "summary_snippet": (
                f"Targeted corporate law search across Delaware Court of Chancery and Delaware Supreme Court "
                f"opinions addressing '{query}' (e.g., MAE clauses, fiduciary duties, Revlon/MFW, sandbagging, busted deals)."
            ),
            "legal_significance": (
                "Controlling authority for US corporate governance, M&A disputes, and DGCL statutory interpretation."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "us_dockets_recap",
            "source_name": "Free Law Project — RECAP Archive (PACER Federal Dockets & Briefs)",
            "jurisdiction": "United States (Federal District & Bankruptcy Courts)",
            "doc_type": "PACER Dockets, Complaints, Motions & Briefs (type=r)",
            "title": f"RECAP Federal Litigation Docket & Pleading Search — Query: '{query}'",
            "citation": f"PACER / RECAP Docket Archive ({query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "U.S. Federal District & Bankruptcy Courts (PACER / RECAP)",
            "url": f"https://www.courtlistener.com/?q={encoded_q}&type=r",
            "api_endpoint": f"{COURTLISTENER_SEARCH_URL}?q={encoded_q}&type=r",
            "summary_snippet": (
                f"Searches millions of free PACER dockets, complaints, motions to dismiss, and summary judgment briefs "
                f"in the RECAP archive matching '{query}'."
            ),
            "legal_significance": (
                "Surfaces real-world litigation pleadings, motions, and active federal docket histories without PACER per-page fees."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
    ]
    return records[:limit]


def search_us_caselaw(
    query: str,
    search_type: str = "o",
    court: Optional[str] = None,
    limit: int = 5,
    timeout: int = 12,
) -> Dict[str, Any]:
    params: Dict[str, str] = {"q": query, "type": search_type}
    if court:
        params["court"] = court

    url = f"{COURTLISTENER_V3_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
        "Accept": "application/json",
    }
    api_token = os.environ.get("COURTLISTENER_API_TOKEN")
    if api_token:
        headers["Authorization"] = f"Token {api_token}"

    req = urllib.request.Request(url, headers=headers)
    results: List[Dict[str, Any]] = []
    status = "live_api"
    error_note = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            items = payload.get("results", [])
            total_count = payload.get("count", len(items))

            for item in items[:limit]:
                case_name = item.get("caseName") or item.get("case_name") or "Judicial Opinion"
                citations = item.get("citation") or []
                if isinstance(citations, list):
                    cit_str = ", ".join(citations) if citations else item.get("docketNumber", "Slip Op.")
                else:
                    cit_str = str(citations)

                date_filed = item.get("dateFiled") or item.get("date_filed") or ""
                court_name = item.get("court") or item.get("court_id") or "U.S. Court"
                abs_url = item.get("absolute_url") or ""
                full_url = f"https://www.courtlistener.com{abs_url}" if abs_url.startswith("/") else (
                    abs_url or f"https://www.courtlistener.com/?q={urllib.parse.quote_plus(query)}"
                )
                snippet = strip_html(item.get("snippet") or item.get("syllabus") or "")
                cite_count = item.get("citeCount", 0)

                results.append(
                    {
                        "source_id": "us_caselaw_courtlistener",
                        "source_name": "CourtListener / Free Law Project (US Case Law & RECAP)",
                        "jurisdiction": "United States (Federal & State Courts)",
                        "doc_type": "Judicial Opinion" if search_type == "o" else "PACER Docket / Filing",
                        "title": f"{case_name} ({cit_str})",
                        "citation": f"{case_name}, {cit_str} ({court_name} {date_filed})",
                        "date": date_filed,
                        "authority_court_or_agency": court_name,
                        "url": full_url,
                        "api_endpoint": url,
                        "summary_snippet": snippet or f"Judicial opinion in {case_name} decided {date_filed}.",
                        "legal_significance": (
                            f"Cited by {cite_count} subsequent opinions in the CourtListener Open Citation Graph "
                            f"(Total corpus matches: {total_count})."
                        ),
                        "retrieval_mode": "live_api",
                    }
                )

            if not results:
                results = build_curated_caselaw_fallback(
                    query, search_type, court, limit, "Zero direct hits returned; providing deep-search pointers."
                )

    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live network request unavailable or blocked ({type(exc).__name__}: {exc})"
        results = build_curated_caselaw_fallback(query, search_type, court, limit, error_note)

    return {
        "source_id": "us_caselaw",
        "source_title": "U.S. Federal & 50-State Case Law, Delaware Chancery & RECAP Dockets (CourtListener / CAP)",
        "jurisdiction": "United States",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search U.S. Federal & State Case Law and RECAP PACER Dockets via CourtListener."
    )
    parser.add_argument("--query", "-q", required=True, help="Case name, legal doctrine, statute, or keyword")
    parser.add_argument(
        "--type",
        choices=["o", "r"],
        default="o",
        help="Search type: 'o' for Judicial Opinions (default), 'r' for RECAP PACER Dockets/Briefs",
    )
    parser.add_argument(
        "--court",
        default=None,
        help="Optional court filter (e.g., 'scotus', 'ca2', 'ca9', 'delch', 'del')",
    )
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return (default: 5)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()

    data = search_us_caselaw(
        query=args.query,
        search_type=args.type,
        court=args.court,
        limit=args.limit,
    )

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(f"### {data['source_title']} (Status: `{data['status']}`)")
        for idx, r in enumerate(data["results"], 1):
            print(f"{idx}. **{r['title']}** — `{r['citation']}`")
            print(f"   - **Court:** {r['authority_court_or_agency']} | **Date:** {r['date']}")
            print(f"   - **Snippet:** {r['summary_snippet']}")
            print(f"   - **URL:** {r['url']}\n")


if __name__ == "__main__":
    main()
