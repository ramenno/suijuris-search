#!/usr/bin/env python3
"""
US Federal Register, eCFR & Statutory/Tax Search Adapter (`search_us_regulations.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries two official, unauthenticated US Government REST APIs:
1. Federal Register API v1 (`https://www.federalregister.gov/api/v1/documents.json`) — Final Rules, Proposed Rules (NPRMs), Presidential Documents, and Agency Notices (SEC, FTC, DOJ, Treasury/IRS, CISA, FDA, EPA).
2. Electronic Code of Federal Regulations (eCFR) Search API v1 (`https://www.ecfr.gov/api/search/v1/results`) — Point-in-time codified federal regulations across all 50 CFR Titles (including Title 17 Securities & Title 26 IRS/Tax).
"""

import argparse
import datetime
import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

FEDREG_API_URL = "https://www.federalregister.gov/api/v1/documents.json"
ECFR_SEARCH_URL = "https://www.ecfr.gov/api/search/v1/results"


def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", clean).strip()


def build_curated_us_reg_fallback(
    query: str, title_filter: Optional[int], limit: int, note: str
) -> List[Dict[str, Any]]:
    encoded_q = urllib.parse.quote_plus(query)
    records = [
        {
            "source_id": "us_federal_register",
            "source_name": "U.S. Federal Register (NARA / GPO Official API v1)",
            "jurisdiction": "United States (Federal Administrative & Regulatory Law)",
            "doc_type": "Final Rules, Proposed Rules (NPRMs) & Presidential Executive Orders",
            "title": f"Federal Register Rulemaking & Agency Actions — Query: '{query}'",
            "citation": f"Federal Register (FR) — Search: {query}",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "U.S. Federal Agencies (SEC, FTC, DOJ, Treasury/IRS, CISA,HHS/FDA)",
            "url": f"https://www.federalregister.gov/documents/search?conditions%5Bterm%5D={encoded_q}",
            "api_endpoint": f"{FEDREG_API_URL}?conditions[term]={encoded_q}",
            "summary_snippet": (
                f"Official daily journal of the US Government covering final rules, proposed rulemaking (NPRMs), "
                f"and public notices matching '{query}'. ({note})"
            ),
            "legal_significance": (
                "Captures binding agency regulatory mandates, effective dates, preambles, and open notice-and-comment periods."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "us_ecfr",
            "source_name": "Electronic Code of Federal Regulations (eCFR API v1)",
            "jurisdiction": "United States (Codified Federal Regulations — Titles 1–50)",
            "doc_type": f"Codified CFR Provisions (Title Filter: {title_filter or 'All 50 Titles'})",
            "title": f"U.S. Code of Federal Regulations (eCFR) — Query: '{query}'",
            "citation": f"{title_filter or '1–50'} C.F.R. (Search: {query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "Office of the Federal Register (NARA) / GPO",
            "url": f"https://www.ecfr.gov/search?search%5Bquery%5D={encoded_q}",
            "api_endpoint": f"{ECFR_SEARCH_URL}?query={encoded_q}",
            "summary_snippet": (
                f"Point-in-time codified text of the Code of Federal Regulations (including Title 12 Banking, "
                f"Title 16 FTC, Title 17 SEC, Title 21 FDA, Title 26 IRS/Treasury Tax, Title 45 HIPAA) for '{query}'."
            ),
            "legal_significance": (
                "Provides currently operative regulatory sections with historical amendment diffs."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "us_code_govinfo",
            "source_name": "United States Code (U.S.C.) & Internal Revenue Code (Title 26)",
            "jurisdiction": "United States (Federal Statutory Law)",
            "doc_type": "Federal Statutes (USLM XML / House OLRC)",
            "title": f"United States Code (Titles 1–54 U.S.C.) — Query: '{query}'",
            "citation": f"U.S.C. Statutory Search ({query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "United States Congress (Office of the Law Revision Counsel / GovInfo)",
            "url": f"https://www.govinfo.gov/app/search/%7B%22query%22%3A%22collection%3A(USCODE)%20{encoded_q}%22%7D",
            "api_endpoint": "https://api.govinfo.gov/collections/USCODE/",
            "summary_snippet": (
                f"Searches the official United States Code (U.S.C.), including Title 11 (Bankruptcy), Title 15 (Commerce/Antitrust/Securities), "
                f"Title 17 (Copyright), Title 26 (Internal Revenue Code), and Title 35 (Patents) for '{query}'."
            ),
            "legal_significance": (
                "Primary federal statutory authority enacted by the U.S. Congress."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
    ]
    return records[:limit]


def search_us_regulations(
    query: str,
    cfr_title: Optional[int] = None,
    limit: int = 5,
    timeout: int = 12,
) -> Dict[str, Any]:
    headers = {
        "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
        "Accept": "application/json",
    }
    results: List[Dict[str, Any]] = []
    status = "live_api"
    errors: List[str] = []

    # 1. Query Federal Register API v1
    fr_limit = max(1, (limit + 1) // 2)
    fr_params = {
        "conditions[term]": query,
        "per_page": str(fr_limit),
        "order": "relevance",
    }
    fr_url = f"{FEDREG_API_URL}?{urllib.parse.urlencode(fr_params)}"
    try:
        req = urllib.request.Request(fr_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for doc in payload.get("results", [])[:fr_limit]:
                title = doc.get("title", "Federal Register Document")
                citation = doc.get("citation") or doc.get("document_number") or "FR Doc."
                pub_date = doc.get("publication_date", "")
                doc_type = doc.get("type", "Rule/Notice")
                agencies = [a.get("name", "") for a in doc.get("agencies", []) if a.get("name")]
                agency_str = ", ".join(agencies) if agencies else "U.S. Federal Agency"
                html_url = doc.get("html_url") or doc.get("pdf_url") or ""
                abstract = doc.get("abstract") or doc.get("excerpts") or ""
                if isinstance(abstract, list):
                    abstract = " ... ".join(abstract)
                abstract = strip_html(str(abstract))

                results.append(
                    {
                        "source_id": "us_federal_register",
                        "source_name": "U.S. Federal Register",
                        "jurisdiction": "United States (Federal Regulatory)",
                        "doc_type": f"Federal Register {doc_type}",
                        "title": title,
                        "citation": f"{citation} ({pub_date})",
                        "date": pub_date,
                        "authority_court_or_agency": agency_str,
                        "url": html_url,
                        "api_endpoint": fr_url,
                        "summary_snippet": abstract[:450] if abstract else f"{doc_type} published by {agency_str} on {pub_date}.",
                        "legal_significance": f"Official Federal Register {doc_type} (Doc No. {doc.get('document_number', 'N/A')}).",
                        "retrieval_mode": "live_api",
                    }
                )
    except Exception as exc:
        errors.append(f"FederalRegister API: {type(exc).__name__}: {exc}")

    # 2. Query eCFR API v1
    ecfr_limit = max(1, limit - len(results))
    ecfr_params: Dict[str, str] = {
        "query": query,
        "per_page": str(ecfr_limit),
        "page": "1",
    }
    ecfr_url = f"{ECFR_SEARCH_URL}?{urllib.parse.urlencode(ecfr_params)}"
    try:
        req = urllib.request.Request(ecfr_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for item in payload.get("results", [])[:ecfr_limit]:
                headings = item.get("headings", {})
                title_num = headings.get("title", cfr_title or "")
                part_num = headings.get("part", "")
                section_num = headings.get("section", "")
                subject = item.get("hierarchy_heading") or headings.get("subject") or "eCFR Section"
                cfr_cite = f"{title_num} C.F.R. § {section_num}" if section_num else f"{title_num} C.F.R. Part {part_num}"
                snippet = strip_html(item.get("full_text_excerpt") or "")
                starts_on = item.get("starts_on") or datetime.date.today().isoformat()
                item_url = f"https://www.ecfr.gov/current/title-{title_num}/part-{part_num}" if title_num and part_num else (
                    f"https://www.ecfr.gov/search?search%5Bquery%5D={urllib.parse.quote_plus(query)}"
                )

                results.append(
                    {
                        "source_id": "us_ecfr",
                        "source_name": "U.S. Electronic Code of Federal Regulations (eCFR)",
                        "jurisdiction": "United States (Federal Regulations)",
                        "doc_type": "Codified Regulation (C.F.R.)",
                        "title": f"{cfr_cite} — {subject}",
                        "citation": cfr_cite,
                        "date": starts_on,
                        "authority_court_or_agency": f"Title {title_num} C.F.R.",
                        "url": item_url,
                        "api_endpoint": ecfr_url,
                        "summary_snippet": snippet[:450] if snippet else f"Codified federal regulation at {cfr_cite}.",
                        "legal_significance": "Currently operative provision of the Code of Federal Regulations.",
                        "retrieval_mode": "live_api",
                    }
                )
    except Exception as exc:
        errors.append(f"eCFR API: {type(exc).__name__}: {exc}")

    if not results:
        status = "fallback_index"
        results = build_curated_us_reg_fallback(query, cfr_title, limit, "; ".join(errors) or "No direct API hits")

    return {
        "source_id": "us_regulations",
        "source_title": "U.S. Federal Register, Code of Federal Regulations (eCFR) & U.S. Code / Tax",
        "jurisdiction": "United States",
        "query": query,
        "status": status,
        "error_note": "; ".join(errors) if errors else None,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search U.S. Federal Register rules/notices and eCFR codified regulations."
    )
    parser.add_argument("--query", "-q", required=True, help="Regulatory topic, statute, agency rule, or CFR citation")
    parser.add_argument("--cfr-title", type=int, default=None, help="Optional CFR Title filter (e.g., 17 for SEC, 26 for IRS)")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return (default: 5)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()

    data = search_us_regulations(query=args.query, cfr_title=args.cfr_title, limit=args.limit)

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(f"### {data['source_title']} (Status: `{data['status']}`)")
        for idx, r in enumerate(data["results"], 1):
            print(f"{idx}. **{r['title']}** (`{r['citation']}`)")
            print(f"   - **Agency/Source:** {r['authority_court_or_agency']} | **Date:** {r['date']}")
            print(f"   - **Summary:** {r['summary_snippet']}")
            print(f"   - **URL:** {r['url']}\n")


if __name__ == "__main__":
    main()
