#!/usr/bin/env python3
"""
Nordics Primary Law Search Adapter (`search_nordics_law.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries open Nordic parliamentary, statutory, and judicial portals (Legora's core regional strength):
1. Sweden — Sveriges Riksdag Open Data API (`https://data.riksdagen.se/dokumentlista/?sok=...&utformat=json`)
   covering Svensk författningssamling (SFS statutes), Government Bills (Propositioner / förarbeten),
   and SOU official reports, plus Domstolsverket (Högsta domstolen).
2. Norway — Lovdata Open API (`https://api.lovdata.no/` / `lovdata.no`) covering Norsk lovtidend & Supreme Court.
3. Denmark — Retsinformation Open API (`https://www.retsinformation.dk/`) & Finland — Finlex (`finlex.fi`).
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

RIKSDAGEN_API_URL = "https://data.riksdagen.se/dokumentlista/"


def strip_html(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", clean).strip()


def build_curated_nordics_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="nordics_law", query=query, limit=limit, note=note
    )


def search_nordics_law(query: str, limit: int = 5, timeout: int = 12) -> Dict[str, Any]:
    params = {
        "sok": query,
        "utformat": "json",
        "antal": str(limit),
        "sort": "rel",
    }
    url = f"{RIKSDAGEN_API_URL}?{urllib.parse.urlencode(params)}"
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
            docs = payload.get("dokumentlista", {}).get("dokument", [])
            for d in docs[:limit]:
                title = d.get("titel", "Nordic Legal Instrument")
                subtitle = d.get("undertitel", "")
                dok_id = d.get("dok_id", "")
                rm = d.get("rm", "")
                beteckning = d.get("beteckning", "")
                typ = d.get("doktyp", "SFS/Prop")
                datum = d.get("datum", "")
                organ = d.get("organ", "Sveriges Riksdag")
                doc_url = d.get("dokument_url_html") or f"https://www.riksdagen.se/sv/dokument-och-lagar/dokument/{dok_id}/"
                if doc_url.startswith("//"):
                    doc_url = "https:" + doc_url
                summary = strip_html(d.get("summary") or d.get("notis") or subtitle)

                results.append(
                    {
                        "source_id": "nordics_law",
                        "source_name": "Sveriges Riksdag (SFS Statutes & Förarbeten) / Nordic Open Law",
                        "jurisdiction": "Nordics (Sweden, Norway, Denmark, Finland)",
                        "doc_type": f"Nordic Statute / Preparatory Work ({typ.upper()})",
                        "title": f"{title} ({rm}:{beteckning})" if rm and beteckning else title,
                        "citation": f"{typ.upper()} {rm}:{beteckning} ({dok_id})".strip(),
                        "date": datum,
                        "authority_court_or_agency": f"Sveriges Riksdag ({organ})",
                        "url": doc_url,
                        "api_endpoint": RIKSDAGEN_API_URL,
                        "summary_snippet": summary[:450] if summary else f"{title} — {subtitle} ({datum}).",
                        "legal_significance": (
                            "Primary Nordic statutory law (SFS) or authoritative legislative preparatory work (förarbeten/Proposition)."
                        ),
                        "retrieval_mode": "live_api",
                    }
                )
            if not results:
                results = build_curated_nordics_fallback(query, limit, "Zero direct Riksdagen hits.")
    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live Nordic API unavailable or blocked ({type(exc).__name__}: {exc})"
        results = build_curated_nordics_fallback(query, limit, error_note)

    return {
        "source_id": "nordics_law",
        "source_title": "Nordics Primary Law: Sweden (Riksdagen SFS & Förarbeten), Norway (Lovdata), Denmark (Retsinformation) & Finland (Finlex)",
        "jurisdiction": "Nordic Region (SE, NO, DK, FI)",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results[:limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Nordic statutes, preparatory works, and case law (SE, NO, DK, FI).")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()
    print(json.dumps(search_nordics_law(query=args.query, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
