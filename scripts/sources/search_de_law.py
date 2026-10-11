#!/usr/bin/env python3
"""
Germany Primary Law & Federal Courts Search Adapter (`search_de_law.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries OpenLegalData DE REST API (`https://de.openlegaldata.io/api/cases/` & `/api/laws/`)
and references official Federal Ministry of Justice (BMJ) portals (`gesetze-im-internet.de`
and `rechtsprechung-im-internet.de`) covering German federal codes (BGB, HGB, AktG, GmbHG, InsO, BDSG)
and federal supreme court decisions (BGH, BVerfG, BFH, BAG, BVerwG).
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import curated_legal_corpus  # noqa: E402

OLD_CASES_API_URL = "https://de.openlegaldata.io/api/cases/search/"
OLD_LAWS_API_URL = "https://de.openlegaldata.io/api/laws/search/"


def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", clean).strip()


def build_curated_de_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="de_law", query=query, limit=limit, note=note
    )


def search_de_law(query: str, limit: int = 5, timeout: int = 12) -> Dict[str, Any]:
    headers = {
        "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
        "Accept": "application/json",
    }
    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    status = "live_api"

    # 1. Search German Statutory Codes (OpenLegalData Laws API)
    law_limit = max(1, (limit + 1) // 2)
    law_url = f"{OLD_LAWS_API_URL}?{urllib.parse.urlencode({'text': query, 'page_size': str(law_limit)})}"
    try:
        req = urllib.request.Request(law_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for item in payload.get("results", [])[:law_limit]:
                title = item.get("title", "Bundesgesetz")
                book_code = item.get("book_code") or item.get("slug") or "BGB/HGB"
                section = item.get("section") or ""
                text_snip = strip_html(item.get("text") or "")
                results.append(
                    {
                        "source_id": "de_law",
                        "source_name": "Gesetze im Internet / OpenLegalData DE",
                        "jurisdiction": "Germany (Federal Statutory Law)",
                        "doc_type": "German Federal Statute (Bundesrecht)",
                        "title": f"{book_code.upper()} {section} — {title}".strip(),
                        "citation": f"{section} {book_code.upper()}".strip(),
                        "date": item.get("updated_date", ""),
                        "authority_court_or_agency": "Deutscher Bundestag / Bundesministerium der Justiz (BMJ)",
                        "url": f"https://www.gesetze-im-internet.de/",
                        "api_endpoint": OLD_LAWS_API_URL,
                        "summary_snippet": text_snip[:450] if text_snip else f"{title} ({book_code}).",
                        "legal_significance": "Codified German federal statutory provision (§ 5 UrhG official work).",
                        "retrieval_mode": "live_api",
                    }
                )
    except Exception as exc:
        errors.append(f"OpenLegalData Laws API: {type(exc).__name__}: {exc}")

    # 2. Search German Court Decisions (BGH, BVerfG, OLG, LG)
    case_limit = max(1, limit - len(results))
    case_url = f"{OLD_CASES_API_URL}?{urllib.parse.urlencode({'text': query, 'page_size': str(case_limit)})}"
    try:
        req = urllib.request.Request(case_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for item in payload.get("results", [])[:case_limit]:
                file_num = item.get("file_number", "Az.")
                court_name = item.get("court_name") or (item.get("court") or {}).get("name", "Deutsches Gericht")
                date_str = item.get("date", "")
                ecli = item.get("ecli", "")
                slug = item.get("slug", "")
                text_snip = strip_html(item.get("text") or item.get("abstract") or "")

                results.append(
                    {
                        "source_id": "de_law",
                        "source_name": "Rechtsprechung im Internet / OpenLegalData DE",
                        "jurisdiction": "Germany (Federal & State Courts)",
                        "doc_type": "German Judicial Decision (Urteil / Beschluss)",
                        "title": f"{court_name} — Az. {file_num}",
                        "citation": f"{court_name}, {date_str} — {file_num} ({ecli})".strip(" ()"),
                        "date": date_str,
                        "authority_court_or_agency": court_name,
                        "url": f"https://de.openlegaldata.io/case/{slug}/" if slug else "https://www.rechtsprechung-im-internet.de/",
                        "api_endpoint": OLD_CASES_API_URL,
                        "summary_snippet": text_snip[:450] if text_snip else f"Decision {file_num} by {court_name}.",
                        "legal_significance": "German judicial precedent from federal or appellate courts.",
                        "retrieval_mode": "live_api",
                    }
                )
    except Exception as exc:
        errors.append(f"OpenLegalData Cases API: {type(exc).__name__}: {exc}")

    if not results:
        status = "fallback_index"
        results = build_curated_de_fallback(query, limit, "; ".join(errors) or "No direct matches")

    return {
        "source_id": "de_law",
        "source_title": "Germany Primary Law (Gesetze-im-Internet BGB/HGB/AktG, BGH/BVerfG & OpenLegalData DE)",
        "jurisdiction": "Germany",
        "query": query,
        "status": status,
        "error_note": "; ".join(errors) if errors else None,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search German federal statutes (BGB/HGB/AktG) and BGH/BVerfG court decisions.")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()
    print(json.dumps(search_de_law(query=args.query, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
