#!/usr/bin/env python3
"""
Quick CLI check for UBERON tissue hierarchy via OLS4 API.

Usage:
    python bin/check_uberon.py "kidney"
    python bin/check_uberon.py "UBERON:0002113"
    python bin/check_uberon.py "lung" --levels 2
"""

import sys
import re
import argparse
import requests

OLS_BASE    = "https://www.ebi.ac.uk/ols4/api"
UBERON_IRI  = "http://purl.obolibrary.org/obo/{term_id}"


def search_uberon(label: str) -> list:
    """Search OLS for a UBERON term by label."""
    url = f"{OLS_BASE}/search"
    params = {
        "q":        label,
        "ontology": "uberon",
        "type":     "class",
        "rows":     10,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    docs = r.json().get("response", {}).get("docs", [])
    return [
        {"obo_id": d.get("obo_id"), "label": d.get("label"), "iri": d.get("iri")}
        for d in docs if d.get("obo_id", "").startswith("UBERON")
    ]


def get_terms(uberon_id: str, relation: str = "hierarchicalParents") -> list:
    """
    Get related terms for a UBERON ID.

    relation options:
        hierarchicalParents  - immediate parents only
        ancestors            - all ancestors up to root
        hierarchicalChildren - immediate children
        hierarchicalDescendants - all descendants
    """
    term_id  = uberon_id.replace(":", "_")
    iri      = UBERON_IRI.format(term_id=term_id)
    iri_enc  = requests.utils.quote(requests.utils.quote(iri, safe=""))

    url = f"{OLS_BASE}/ontologies/uberon/terms/{iri_enc}/{relation}"
    r   = requests.get(url, params={"size": 200}, timeout=10)

    if r.status_code == 404:
        return []
    r.raise_for_status()

    embedded = r.json().get("_embedded", {}).get("terms", [])
    return [
        {"obo_id": t.get("obo_id"), "label": t.get("label")}
        for t in embedded
    ]


def print_terms(terms: list, indent: int = 2) -> None:
    pad = " " * indent
    for t in terms:
        print(f"{pad}{t['obo_id']:20s}  {t['label']}")


def main():
    parser = argparse.ArgumentParser(
        description="Look up UBERON tissue hierarchy via OLS4 API"
    )
    parser.add_argument("query",
        help='Tissue label (e.g. "kidney") or UBERON ID (e.g. "UBERON:0002113")')
    parser.add_argument("--relation", default="hierarchicalParents",
        choices=["hierarchicalParents", "ancestors",
                 "hierarchicalChildren", "hierarchicalDescendants"],
        help="Relationship to traverse (default: hierarchicalParents)")
    parser.add_argument("--all", action="store_true",
        help="Show parents AND children AND ancestors in one shot")
    args = parser.parse_args()

    query = args.query.strip()

    # Resolve label → UBERON ID if needed
    if re.match(r"UBERON:\d+", query, re.IGNORECASE):
        uberon_id = query.upper()
        label     = query
    else:
        print(f"Searching OLS for: '{query}' ...")
        results = search_uberon(query)
        if not results:
            print(f"No UBERON terms found for '{query}'")
            sys.exit(1)

        print(f"\nTop matches:")
        for i, r in enumerate(results[:5], 1):
            print(f"  {i}. {r['obo_id']:20s}  {r['label']}")

        choice = input("\nUse which? [1]: ").strip() or "1"
        selected  = results[int(choice) - 1]
        uberon_id = selected["obo_id"]
        label     = selected["label"]
        print()

    print(f"Term  : {uberon_id}  ({label})")
    print("=" * 60)

    if args.all:
        for rel in ["hierarchicalParents", "ancestors",
                    "hierarchicalChildren", "hierarchicalDescendants"]:
            terms = get_terms(uberon_id, rel)
            print(f"\n{rel} ({len(terms)}):")
            print_terms(terms)
    else:
        terms = get_terms(uberon_id, args.relation)
        print(f"\n{args.relation} ({len(terms)}):")
        print_terms(terms)


if __name__ == "__main__":
    main()
