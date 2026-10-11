#!/usr/bin/env python3
"""
United Kingdom Legislation & Case Law Search Adapter (`search_uk_law.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries two official UK Open Government / Open Justice Atom/XML APIs:
1. UK Legislation API (`https://www.legislation.gov.uk/all/data.feed?text=...`) — UK Public General Acts,
   Statutory Instruments (SIs), and Assimilated EU Law under Open Government Licence v3.0.
2. UK National Archives "Find Case Law" API (`https://caselaw.nationalarchives.gov.uk/atom.xml?query=...`) —
   UK Supreme Court, Privy Council, Court of Appeal, and High Court judgments in LegalDocML / Akoma Ntoso.
"""

import argparse
import datetime
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

UK_LEGISLATION_ATOM_URL = "https://www.legislation.gov.uk/all/data.feed"
UK_CASELAW_ATOM_URL = "https://caselaw.nationalarchives.gov.uk/atom.xml"

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "ukm": "http://www.legislation.gov.uk/namespaces/metadata"}


def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", clean).strip()


def build_curated_uk_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    encoded_q = urllib.parse.quote_plus(query)
    records = [
        {
            "source_id": "uk_legislation",
            "source_name": "UK Legislation Official Portal (legislation.gov.uk)",
            "jurisdiction": "United Kingdom (England & Wales, Scotland, Northern Ireland)",
            "doc_type": "UK Public General Acts & Statutory Instruments (SIs)",
            "title": f"UK Primary & Secondary Legislation Search — Query: '{query}'",
            "citation": f"UK Acts & Statutory Instruments (Search: {query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "UK Parliament / The National Archives (OGL v3.0)",
            "url": f"https://www.legislation.gov.uk/all?text={encoded_q}",
            "api_endpoint": f"{UK_LEGISLATION_ATOM_URL}?text={encoded_q}",
            "summary_snippet": (
                f"Searches all revised and enacted UK Public General Acts (e.g., Companies Act 2006, Data Protection Act 2018, "
                f"Financial Services and Markets Act 2023, Bribery Act 2010, Insolvency Act 1986) and Statutory Instruments for '{query}'. ({note})"
            ),
            "legal_significance": (
                "Primary UK statutory authority with point-in-time historical versions and Akoma Ntoso XML structure."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "uk_find_caselaw",
            "source_name": "The National Archives — Find Case Law & BAILII",
            "jurisdiction": "United Kingdom (UKSC, EWCA, EWHC, Upper Tribunals)",
            "doc_type": "UK Court & Tribunal Judgments (Neutral Citations)",
            "title": f"UK Find Case Law Judicial Precedent Search — Query: '{query}'",
            "citation": f"[YYYY] UKSC / EWCA Civ / EWHC Comm (Search: {query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "UK Supreme Court, Court of Appeal, High Court (Commercial, Chancery, King's Bench)",
            "url": f"https://caselaw.nationalarchives.gov.uk/judgments/search?query={encoded_q}",
            "api_endpoint": f"{UK_CASELAW_ATOM_URL}?query={encoded_q}",
            "summary_snippet": (
                f"Searches English and UK appellate and High Court judgments (LegalDocML / Akoma Ntoso) matching '{query}'."
            ),
            "legal_significance": (
                "Binding English common-law judicial precedent governing international commercial contracts, finance, and tort law."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "uk_companies_house_fca",
            "source_name": "UK Companies House Registry & FCA Handbook",
            "jurisdiction": "United Kingdom (Corporate & Financial Regulatory)",
            "doc_type": "Corporate Filings, Articles of Association & FCA Rules",
            "title": f"UK Corporate & Regulatory Search — Query: '{query}'",
            "citation": "Companies Act 2006 / FCA Handbook",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "Companies House & Financial Conduct Authority (FCA)",
            "url": f"https://find-and-update.company-information.service.gov.uk/search?q={encoded_q}",
            "api_endpoint": "https://api.company-information.service.gov.uk/search",
            "summary_snippet": (
                f"Searches UK corporate registrations, PSC registers, charges, insolvency filings, and FCA regulatory rules for '{query}'."
            ),
            "legal_significance": (
                "Essential for UK M&A due diligence, corporate verification, and financial services compliance."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
    ]
    return records[:limit]


def parse_atom_feed(xml_bytes: bytes, source_id: str, source_name: str, authority_default: str, limit: int) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    root = ET.fromstring(xml_bytes)
    entries = root.findall("atom:entry", ATOM_NS)
    for entry in entries[:limit]:
        title_el = entry.find("atom:title", ATOM_NS)
        id_el = entry.find("atom:id", ATOM_NS)
        updated_el = entry.find("atom:updated", ATOM_NS)
        summary_el = entry.find("atom:summary", ATOM_NS)
        content_el = entry.find("atom:content", ATOM_NS)

        title = title_el.text.strip() if (title_el is not None and title_el.text) else "UK Legal Instrument"
        link_url = id_el.text.strip() if (id_el is not None and id_el.text) else ""
        for link in entry.findall("atom:link", ATOM_NS):
            rel = link.attrib.get("rel", "alternate")
            href = link.attrib.get("href", "")
            if rel == "alternate" and href:
                link_url = href
                break

        updated = updated_el.text[:10] if (updated_el is not None and updated_el.text) else ""
        summary = ""
        if summary_el is not None and summary_el.text:
            summary = strip_html(summary_el.text)
        elif content_el is not None and content_el.text:
            summary = strip_html(content_el.text)

        items.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "jurisdiction": "United Kingdom",
                "doc_type": "UK Statute / SI" if source_id == "uk_legislation" else "UK Court Judgment",
                "title": title,
                "citation": title,
                "date": updated,
                "authority_court_or_agency": authority_default,
                "url": link_url,
                "api_endpoint": UK_LEGISLATION_ATOM_URL if source_id == "uk_legislation" else UK_CASELAW_ATOM_URL,
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
                    resp.read(),
                    "uk_legislation",
                    "legislation.gov.uk (UK National Archives)",
                    "UK Parliament",
                    leg_limit,
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
                    resp.read(),
                    "uk_find_caselaw",
                    "UK Find Case Law (The National Archives)",
                    "UK Courts & Tribunals",
                    case_limit,
                )
            )
    except Exception as exc:
        errors.append(f"Find Case Law: {type(exc).__name__}: {exc}")

    if not results:
        status = "fallback_index"
        results = build_curated_uk_fallback(query, limit, "; ".join(errors) or "No direct Atom feed matches")

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
    parser = argparse.ArgumentParser(
        description="Search UK Acts, Statutory Instruments (legislation.gov.uk), and UK Court Judgments (Find Case Law)."
    )
    parser.add_argument("--query", "-q", required=True, help="UK statute, legal doctrine, case name, or keyword")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return (default: 5)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()

    data = search_uk_law(query=args.query, limit=args.limit)

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
