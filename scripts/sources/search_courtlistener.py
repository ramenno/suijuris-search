#!/usr/bin/env python3
"""
Free Law Project — CourtListener & RECAP Search Adapter (`search_courtlistener.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Directly queries the Free Law Project's CourtListener REST API v4 / v3:
1. Search API (`/api/rest/v4/search/` & `/api/rest/v3/search/`):
   - `type=o` : 10M+ U.S. Federal & 50-State Judicial Opinions (SCOTUS, Circuit Courts, District Courts,
                Delaware Court of Chancery `court=delch`, and Harvard Caselaw Access Project [CAP] reporters)
   - `type=r` : RECAP PACER Federal Docket & Pleading Archive (Complaints, Motions, Briefs, Orders)
   - `type=oa`: Oral Argument Audio & Transcripts
   - `type=p` : Judges & Judicial Biographical Directory
2. Citation Lookup & Open Citator Verification API (`/api/rest/v4/citation-lookup/`):
   - Deterministically verifies legal citations (e.g., `410 U.S. 113`, `347 U.S. 483`) against the
     CourtListener Open Citation Graph to prevent hallucinated authorities ("Open Shepardizing / KeyCite").
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import curated_legal_corpus  # noqa: E402

COURTLISTENER_V4_SEARCH_URL = "https://www.courtlistener.com/api/rest/v4/search/"
COURTLISTENER_V3_SEARCH_URL = "https://www.courtlistener.com/api/rest/v3/search/"
COURTLISTENER_CITATION_LOOKUP_URL = "https://www.courtlistener.com/api/rest/v4/citation-lookup/"

SEARCH_TYPE_LABELS = {
    "o": "Judicial Opinions (Federal, 50-State & Harvard CAP)",
    "r": "RECAP PACER Federal Dockets, Pleadings & Briefs",
    "oa": "Oral Argument Recordings & Transcripts",
    "p": "Judges & Judicial Directory",
}


def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", clean).strip()


def build_curated_courtlistener_fallback(
    query: str, search_type: str, court: Optional[str], limit: int, note: str
) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="courtlistener", query=query, court=court, limit=limit, note=note
    )


def verify_citations_courtlistener(text_or_citation: str, timeout: int = 12) -> Dict[str, Any]:
    """
    Calls CourtListener's Citation Lookup API (`/api/rest/v4/citation-lookup/`) to verify
    whether legal citations in a text string exist in the primary case law corpus.
    """
    headers = {
        "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
        "Accept": "application/json",
    }
    api_token = os.environ.get("COURTLISTENER_API_TOKEN")
    if api_token:
        headers["Authorization"] = f"Token {api_token}"

    data_bytes = urllib.parse.urlencode({"text": text_or_citation}).encode("utf-8")
    req = urllib.request.Request(
        COURTLISTENER_CITATION_LOOKUP_URL, data=data_bytes, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            return {
                "status": "live_api",
                "endpoint": COURTLISTENER_CITATION_LOOKUP_URL,
                "verified_citations": payload,
            }
    except Exception as exc:
        return {
            "status": "fallback_index",
            "endpoint": COURTLISTENER_CITATION_LOOKUP_URL,
            "error_note": f"{type(exc).__name__}: {exc}",
            "verified_citations": [],
        }


def search_courtlistener(
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
                case_name = item.get("caseName") or item.get("case_name") or "CourtListener Judicial Record"
                citations = item.get("citation") or []
                if isinstance(citations, list):
                    cit_str = ", ".join(citations) if citations else item.get("docketNumber", "Slip Op.")
                else:
                    cit_str = str(citations)

                date_filed = item.get("dateFiled") or item.get("date_filed") or ""
                court_name = item.get("court") or item.get("court_id") or "U.S. Court"
                abs_url = item.get("absolute_url") or ""
                full_url = (
                    f"https://www.courtlistener.com{abs_url}"
                    if abs_url.startswith("/")
                    else (abs_url or f"https://www.courtlistener.com/?q={urllib.parse.quote_plus(query)}")
                )
                snippet = strip_html(item.get("snippet") or item.get("syllabus") or "")
                cite_count = item.get("citeCount", 0)

                results.append(
                    {
                        "source_id": "courtlistener",
                        "source_name": "CourtListener (Free Law Project)",
                        "jurisdiction": "United States (Federal & State Courts)",
                        "doc_type": SEARCH_TYPE_LABELS.get(search_type, "Judicial Opinion"),
                        "title": f"{case_name} ({cit_str})",
                        "citation": f"{case_name}, {cit_str} ({court_name} {date_filed})",
                        "date": date_filed,
                        "authority_court_or_agency": court_name,
                        "url": full_url,
                        "api_endpoint": url,
                        "summary_snippet": snippet or f"Judicial record in {case_name} filed {date_filed}.",
                        "legal_significance": (
                            f"Cited by {cite_count} subsequent opinions in the CourtListener Open Citation Graph "
                            f"(Total CourtListener matches: {total_count})."
                        ),
                        "retrieval_mode": "live_api",
                    }
                )

            if not results:
                results = build_curated_courtlistener_fallback(
                    query, search_type, court, limit, "Zero direct hits returned; providing CourtListener corpus matches."
                )

    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live network request unavailable or blocked ({type(exc).__name__}: {exc})"
        results = build_curated_courtlistener_fallback(query, search_type, court, limit, error_note)

    return {
        "source_id": "courtlistener",
        "source_title": "CourtListener (Free Law Project — 10M+ US Opinions, Harvard CAP, Delaware Chancery & RECAP Dockets)",
        "jurisdiction": "United States",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search CourtListener (Free Law Project) for US Case Law, RECAP PACER Dockets, Oral Arguments, or Citation Verification."
    )
    parser.add_argument("--query", "-q", required=True, help="Case name, citation, legal doctrine, or keyword")
    parser.add_argument(
        "--type",
        choices=["o", "r", "oa", "p"],
        default="o",
        help="CourtListener search type: 'o'=Opinions (default), 'r'=RECAP PACER Dockets/Briefs, 'oa'=Oral Arguments, 'p'=Judges",
    )
    parser.add_argument(
        "--court",
        default=None,
        help="Optional CourtListener court code (e.g., 'scotus', 'ca2', 'ca9', 'delch', 'del', 'cadc')",
    )
    parser.add_argument(
        "--verify-citations",
        action="store_true",
        help="Run CourtListener Citation Lookup API (/api/rest/v4/citation-lookup/) on --query text",
    )
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return (default: 5)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()

    if args.verify_citations:
        res = verify_citations_courtlistener(args.query)
        print(json.dumps(res, indent=2))
        return

    data = search_courtlistener(
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
