#!/usr/bin/env python3
"""
European Union EUR-Lex & CELLAR SPARQL Search Adapter (`search_eur_lex.py`)
Part of the `suijuris-search` Agent Skill (https://agentskills.io/).

Queries the Publications Office of the European Union's official CELLAR SPARQL Endpoint
(`https://publications.europa.eu/webapi/rdf/sparql`) for EU Regulations, Directives, Decisions,
Treaties, Antitrust/Merger actions, and Court of Justice of the European Union (CJEU / CURIA) case law.
"""

import argparse
import datetime
import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

CELLAR_SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"


def build_sparql_query(keyword: str, limit: int = 5) -> str:
    safe_kw = keyword.replace('"', '\\"').replace("'", "\\'")
    return f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

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
    encoded_q = urllib.parse.quote_plus(query)
    eurlex_search_url = f"https://eur-lex.europa.eu/search.html?scope=EURLEX&text={encoded_q}&lang=en&type=quick"
    curia_search_url = f"https://curia.europa.eu/juris/liste.jsf?language=en&td=ALL"

    records = [
        {
            "source_id": "eu_eur_lex_legislation",
            "source_name": "EUR-Lex & EU Publications Office (CELLAR)",
            "jurisdiction": "European Union (27 Member States & EEA)",
            "doc_type": "EU Regulations, Directives & Decisions (Secondary Legislation)",
            "title": f"EUR-Lex Legislative & Regulatory Corpus — Query: '{query}'",
            "citation": f"Official Journal of the European Union (OJ L / CELEX Search: {query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "European Parliament, Council of the European Union & European Commission",
            "url": eurlex_search_url,
            "api_endpoint": CELLAR_SPARQL_URL,
            "summary_snippet": (
                f"Direct EUR-Lex & CELLAR semantic search across EU Regulations (e.g., GDPR 2016/679, EU AI Act 2024/1689, "
                f"DORA 2022/2554, MiCA 2023/1114, DMA/DSA), Directives (NIS2), and Commission Implementing Decisions for '{query}'. ({note})"
            ),
            "legal_significance": (
                "Directly applicable EU Regulations and Member-State-transposed Directives governing European operations."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "eu_cjeu_curia",
            "source_name": "Court of Justice of the European Union (CJEU / CURIA via EUR-Lex Sector 6)",
            "jurisdiction": "European Union (CJEU & General Court)",
            "doc_type": "CJEU Judgments & Advocate General Opinions (CELEX Sector 6)",
            "title": f"CJEU / General Court Case Law Filter — Query: '{query}'",
            "citation": f"ECLI:EU:C / ECLI:EU:T (CELEX 6* Search: {query})",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "Court of Justice of the European Union (Luxembourg)",
            "url": f"https://eur-lex.europa.eu/search.html?scope=EURLEX&text={encoded_q}&lang=en&type=quick&DTS_DOM=EU_CASE_LAW",
            "api_endpoint": curia_search_url,
            "summary_snippet": (
                f"Searches judgments and orders of the Court of Justice and General Court of the EU interpreting EU treaties, "
                f"fundamental rights, competition law (Arts. 101/102 TFEU), and data protection for '{query}'."
            ),
            "legal_significance": (
                "Supreme judicial interpretation of EU law binding on all national courts of EU Member States."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
        {
            "source_id": "eu_national_open_portals",
            "source_name": "European National Primary Law Portals (Légifrance FR, Gesetze-im-Internet DE, Lovdata NO, BOE ES)",
            "jurisdiction": "European National Jurisdictions (FR, DE, ES, NL, Nordics)",
            "doc_type": "National Codes, Transposing Acts & Supreme Court Rulings",
            "title": f"N-Lex & European National Statutory / Case Law Cross-Search — Query: '{query}'",
            "citation": f"EU N-Lex / ELI (European Legislation Identifier) — {query}",
            "date": datetime.date.today().isoformat(),
            "authority_court_or_agency": "Légifrance/Judilibre (FR), BMJ/BGH (DE), BOE (ES), Rechtspraak (NL), Lovdata (NO)",
            "url": f"https://n-lex.europa.eu/n-lex/",
            "api_endpoint": "https://eur-lex.europa.eu/collection/n-lex.html",
            "summary_snippet": (
                f"Cross-border gateway to national European statutory codes and national transposition measures for '{query}'."
            ),
            "legal_significance": (
                "Captures Member-State gold-plating, national civil/commercial codes (BGB, Code civil), and local enforcement penalties."
            ),
            "retrieval_mode": "offline_curated_index_with_deep_link",
        },
    ]
    return records[:limit]


def search_eur_lex(query: str, limit: int = 5, timeout: int = 14) -> Dict[str, Any]:
    sparql = build_sparql_query(query, limit=limit)
    params = {
        "query": sparql,
        "format": "application/sparql-results+json",
    }
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

                sector = celex[0] if celex else ""
                if sector == "3":
                    doc_type = "EU Secondary Legislation (Regulation / Directive / Decision)"
                    authority = "European Union (Parliament / Council / Commission)"
                elif sector == "6":
                    doc_type = "CJEU Case Law (Judgment / Opinion)"
                    authority = "Court of Justice of the European Union (CJEU)"
                elif sector == "1":
                    doc_type = "EU Primary Treaty Provision"
                    authority = "European Union Treaties (TEU / TFEU)"
                else:
                    doc_type = "EU Legal Act / Official Journal Document"
                    authority = "Publications Office of the European Union"

                results.append(
                    {
                        "source_id": "eu_eur_lex",
                        "source_name": "EUR-Lex (EU CELLAR SPARQL)",
                        "jurisdiction": "European Union",
                        "doc_type": doc_type,
                        "title": title,
                        "citation": f"CELEX:{celex} ({doc_date})",
                        "date": doc_date,
                        "authority_court_or_agency": authority,
                        "url": eurlex_url,
                        "api_endpoint": CELLAR_SPARQL_URL,
                        "summary_snippet": f"{title} [CELEX: {celex}, Document Date: {doc_date}].",
                        "legal_significance": f"Official European Union legal instrument or judicial decision ({doc_type}).",
                        "retrieval_mode": "live_api",
                    }
                )

            if not results:
                results = build_curated_eurlex_fallback(
                    query, limit, "SPARQL title filter returned 0 exact title matches; providing full-text EUR-Lex & CURIA search links."
                )

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
    parser = argparse.ArgumentParser(
        description="Search European Union legislation, directives, regulations, and CJEU case law via EUR-Lex CELLAR."
    )
    parser.add_argument("--query", "-q", required=True, help="EU regulation, directive, legal doctrine, or keyword")
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results to return (default: 5)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format")
    args = parser.parse_args()

    data = search_eur_lex(query=args.query, limit=args.limit)

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
