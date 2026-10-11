#!/usr/bin/env python3
"""
United Kingdom Legislation & Case Law Search Adapter (`search_uk_law.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import curated_legal_corpus  # noqa: E402

UK_LEGISLATION_ATOM_URL = "https://www.legislation.gov.uk/all/data.feed"
UK_CASELAW_ATOM_URL = "https://caselaw.nationalarchives.gov.uk/atom.xml"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", clean).strip()


def build_curated_uk_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="uk_law", query=query, limit=limit, note=note
    )


def parse_atom_feed(
    xml_bytes: bytes, source_id: str, source_name: str, authority_default: str, limit: int
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    root = ET.fromstring(xml_bytes)
    entries = root.findall("atom:entry", ATOM_NS)
    for entry in entries[:limit]:
        title_el = entry.find("atom:title", ATOM_NS)
        id_el = entry.find("atom:id", ATOM_NS)
        updated_el = entry.find("atom:updated", ATOM_NS)
        summary_el = entry.find("atom:summary", ATOM_NS)

        title = title_el.text.strip() if (title_el is not None and title_el.text) else "UK Legal Instrument"
        link_url = id_el.text.strip() if (id_el is not None and id_el.text) else ""
        for link in entry.findall("atom:link", ATOM_NS):
            if link.attrib.get("rel", "alternate") == "alternate" and link.attrib.get("href"):
                link_url = link.attrib["href"]
                break
        updated = updated_el.text[:10] if (updated_el is not None and updated_el.text) else ""
        summary = strip_html(summary_el.text) if (summary_el is not None and summary_el.text) else ""

        items.append(
            {
                "source_id": "uk_law",
                "source_name": source_name,
                "jurisdiction": "United Kingdom",
                "doc_type": "UK Statute / Court Judgment",
                "title": title,
                "citation": title,
                "date": updated,
                "authority_court_or_agency": authority_default,
                "url": link_url,
                "api_endpoint": UK_LEGISLATION_ATOM_URL,
                "summary_snippet": summary[:450] if summary else f"{title} ({updated}).",
                "legal_significance": f"Official UK primary law authority from {source_name}.",
                "retrieval_mode": "live_api",
            }
        )
    return items


def search_uk_law(query: str, limit: int = 5, timeout: int = 12) -> Dict[str, Any]:
    headers = {
        "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
        "Accept": "application/atom+xml, application/xml, text/xml",
    }
    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    status = "live_api"

    leg_limit = max(1, (limit + 1) // 2)
    leg_url = f"{UK_LEGISLATION_ATOM_URL}?{urllib.parse.urlencode({'text': query})}"
    try:
        req = urllib.request.Request(leg_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            results.extend(
                parse_atom_feed(
                    resp.read(), "uk_legislation", "legislation.gov.uk", "UK Parliament", leg_limit
                )
            )
    except Exception as exc:
        errors.append(f"legislation.gov.uk: {type(exc).__name__}: {exc}")

    case_limit = max(1, limit - len(results))
    case_url = f"{UK_CASELAW_ATOM_URL}?{urllib.parse.urlencode({'query': query})}"
    try:
        req = urllib.request.Request(case_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            results.extend(
                parse_atom_feed(
                    resp.read(), "uk_find_caselaw", "UK Find Case Law", "UK Courts & Tribunals", case_limit
                )
            )
    except Exception as exc:
        errors.append(f"Find Case Law: {type(exc).__name__}: {exc}")

    if not results:
        status = "fallback_index"
        results = build_curated_uk_fallback(query, limit, "; ".join(errors) or "No direct matches")

    return {
        "source_id": "uk_law",
        "source_title": "United Kingdom Legislation (legislation.gov.uk), Find Case Law & Companies House",
        "jurisdiction": "United Kingdom",
        "query": query,
        "status": status,
        "error_note": "; ".join(errors) if errors else None,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search UK legislation and case law.")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()
    print(json.dumps(search_uk_law(query=args.query, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
