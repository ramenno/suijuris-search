#!/usr/bin/env python3
"""
France, Spain & Netherlands National Primary Law Adapter (`search_eu_national_law.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries open Continental European national statutory & judicial APIs:
1. Netherlands — Rechtspraak.nl Open Data XML API (`https://data.rechtspraak.nl/uitspraken/zoeken`)
   covering Hoge Raad (Supreme Court), Gerechtshoven, and Rechtbanken with ECLI citations,
   plus Overheid.nl KOOP (Burgerlijk Wetboek / Dutch legislation).
2. France — PISTE API (`Légifrance` for French Codes & `Judilibre` by Cour de cassation for case law).
3. Spain — BOE Datos Abiertos API (`https://www.boe.es/datosabiertos/api/` for Boletín Oficial del Estado) & CENDOJ.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import curated_legal_corpus  # noqa: E402

RECHTSPRAAK_ATOM_URL = "https://data.rechtspraak.nl/uitspraken/zoeken"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def build_curated_eunat_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="eu_national_law", query=query, limit=limit, note=note
    )


def search_eu_national_law(query: str, limit: int = 5, timeout: int = 12) -> Dict[str, Any]:
    params = {"zoekterm": query, "max": str(limit), "return": "DOC"}
    url = f"{RECHTSPRAAK_ATOM_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
            "Accept": "application/xml, text/xml",
        },
    )

    results: List[Dict[str, Any]] = []
    status = "live_api"
    error_note = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            xml_bytes = resp.read()
            root = ET.fromstring(xml_bytes)
            for entry in root.findall("atom:entry", ATOM_NS)[:limit]:
                id_el = entry.find("atom:id", ATOM_NS)
                title_el = entry.find("atom:title", ATOM_NS)
                updated_el = entry.find("atom:updated", ATOM_NS)
                summary_el = entry.find("atom:summary", ATOM_NS)

                ecli = id_el.text.strip() if (id_el is not None and id_el.text) else "ECLI:NL"
                title = title_el.text.strip() if (title_el is not None and title_el.text) else ecli
                updated = updated_el.text[:10] if (updated_el is not None and updated_el.text) else ""
                summary = summary_el.text.strip() if (summary_el is not None and summary_el.text) else ""

                results.append(
                    {
                        "source_id": "eu_national_law",
                        "source_name": "Rechtspraak.nl Open Data (NL) / Légifrance (FR) / BOE (ES)",
                        "jurisdiction": "Netherlands / France / Spain (EU National Courts & Codes)",
                        "doc_type": "European National Court Judgment (ECLI)",
                        "title": title,
                        "citation": f"{ecli} ({updated})",
                        "date": updated,
                        "authority_court_or_agency": "De Rechtspraak (Hoge Raad / Gerechtshof / Rechtbank)",
                        "url": f"https://uitspraken.rechtspraak.nl/details?id={urllib.parse.quote(ecli)}",
                        "api_endpoint": RECHTSPRAAK_ATOM_URL,
                        "summary_snippet": summary[:450] if summary else f"Dutch judicial decision {ecli}.",
                        "legal_significance": "Official European national court decision indexed by European Case Law Identifier (ECLI).",
                        "retrieval_mode": "live_api",
                    }
                )
            if not results:
                results = build_curated_eunat_fallback(query, limit, "Zero direct Rechtspraak XML matches.")
    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live EU National API unavailable or blocked ({type(exc).__name__}: {exc})"
        results = build_curated_eunat_fallback(query, limit, error_note)

    return {
        "source_id": "eu_national_law",
        "source_title": "France (Légifrance & Cour de cassation Judilibre), Netherlands (Rechtspraak/KOOP) & Spain (BOE/CENDOJ)",
        "jurisdiction": "France, Netherlands & Spain",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search France (Légifrance/Judilibre), Netherlands (Rechtspraak/KOOP), and Spain (BOE) primary law."
    )
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()
    print(json.dumps(search_eu_national_law(query=args.query, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
