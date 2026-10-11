#!/usr/bin/env python3
"""
European Union EUR-Lex & CELLAR SPARQL Search Adapter (`search_eur_lex.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import curated_legal_corpus  # noqa: E402

CELLAR_SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"


def build_sparql_query(keyword: str, limit: int = 5) -> str:
    safe_kw = keyword.replace('"', '\\"').replace("'", "\\'")
    return f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?celex ?title ?date
WHERE {{
  ?work cdm:resource_legal_id_celex ?celex .
  ?exp cdm:expression_belongs_to_work ?work ;
       cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> ;
       cdm:expression_title ?title .
  OPTIONAL {{ ?work cdm:work_date_document ?date . }}
  FILTER(CONTAINS(LCASE(STR(?title)), LCASE("{safe_kw}")))
}}
ORDER BY DESC(?date)
LIMIT {limit}
""".strip()


def build_curated_eurlex_fallback(query: str, limit: int, note: str) -> List[Dict[str, Any]]:
    return curated_legal_corpus.query_curated_corpus(
        source_id="eur_lex", query=query, limit=limit, note=note
    )


def search_eur_lex(query: str, limit: int = 5, timeout: int = 14) -> Dict[str, Any]:
    sparql = build_sparql_query(query, limit=limit)
    params = {"query": sparql, "format": "application/sparql-results+json"}
    url = f"{CELLAR_SPARQL_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SuiJurisLegalSearchSkill/1.0 (+https://agentskills.io)",
            "Accept": "application/sparql-results+json",
        },
    )

    results: List[Dict[str, Any]] = []
    status = "live_api"
    error_note = None

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            bindings = payload.get("results", {}).get("bindings", [])
            for b in bindings[:limit]:
                celex = b.get("celex", {}).get("value", "N/A")
                title = b.get("title", {}).get("value", "EU Legal Act")
                doc_date = b.get("date", {}).get("value", "")
                eurlex_url = f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{urllib.parse.quote(celex)}"
                results.append(
                    {
                        "source_id": "eur_lex",
                        "source_name": "EUR-Lex (EU CELLAR SPARQL)",
                        "jurisdiction": "European Union",
                        "doc_type": "EU Legal Instrument / CJEU Case",
                        "title": title,
                        "citation": f"CELEX:{celex} ({doc_date})",
                        "date": doc_date,
                        "authority_court_or_agency": "European Union / CJEU",
                        "url": eurlex_url,
                        "api_endpoint": CELLAR_SPARQL_URL,
                        "summary_snippet": f"{title} [CELEX: {celex}, Date: {doc_date}].",
                        "legal_significance": "Official European Union legal act or CJEU decision.",
                        "retrieval_mode": "live_api",
                    }
                )
            if not results:
                results = build_curated_eurlex_fallback(query, limit, "Zero direct SPARQL hits.")
    except Exception as exc:
        status = "fallback_index"
        error_note = f"Live network request unavailable or blocked ({type(exc).__name__}: {exc})"
        results = build_curated_eurlex_fallback(query, limit, error_note)

    return {
        "source_id": "eur_lex",
        "source_title": "European Union Law & CJEU Case Law (EUR-Lex / CELLAR SPARQL & EU National Portals)",
        "jurisdiction": "European Union",
        "query": query,
        "status": status,
        "error_note": error_note,
        "count": len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Search EUR-Lex and CJEU case law.")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()
    print(json.dumps(search_eur_lex(query=args.query, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
