#!/usr/bin/env python3
"""
US Federal Register, eCFR & Statutory/Tax Search Adapter (`search_us_regulations.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).
"""

import argparse
import datetime
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
    return curated_legal_corpus.query_curated_corpus(
        source_id="us_regulations", query=query, limit=limit, note=note
    )


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

    fr_limit = max(1, (limit + 1) // 2)
    fr_params = {"conditions[term]": query, "per_page": str(fr_limit), "order": "relevance"}
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
                abstract = strip_html(str(doc.get("abstract") or ""))

                results.append(
                    {
                        "source_id": "us_regulations",
                        "source_name": "U.S. Federal Register",
                        "jurisdiction": "United States (Federal Regulatory)",
                        "doc_type": f"Federal Register {doc_type}",
                        "title": title,
                        "citation": f"{citation} ({pub_date})",
                        "date": pub_date,
                        "authority_court_or_agency": agency_str,
                        "url": html_url,
                        "api_endpoint": fr_url,
                        "summary_snippet": abstract[:450] if abstract else f"{doc_type} published by {agency_str}.",
                        "legal_significance": f"Official Federal Register {doc_type}.",
                        "retrieval_mode": "live_api",
                    }
                )
    except Exception as exc:
        errors.append(f"FederalRegister API: {type(exc).__name__}: {exc}")

    ecfr_limit = max(1, limit - len(results))
    ecfr_params: Dict[str, str] = {"query": query, "per_page": str(ecfr_limit), "page": "1"}
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
                item_url = (
                    f"https://www.ecfr.gov/current/title-{title_num}/part-{part_num}"
                    if title_num and part_num
                    else f"https://www.ecfr.gov/search?search%5Bquery%5D={urllib.parse.quote_plus(query)}"
                )

                results.append(
                    {
                        "source_id": "us_regulations",
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
        results = build_curated_us_reg_fallback(query, cfr_title, limit, "; ".join(errors) or "No direct hits")

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
    parser = argparse.ArgumentParser(description="Search U.S. Federal Register and eCFR regulations.")
    parser.add_argument("--query", "-q", required=True, help="Regulatory topic or keyword")
    parser.add_argument("--cfr-title", type=int, default=None, help="Optional CFR Title filter")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()

    data = search_us_regulations(query=args.query, cfr_title=args.cfr_title, limit=args.limit)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
