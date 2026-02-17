#!/usr/bin/env python3
"""
Step 0: Resolve UBERON tissue terms via OLS4 API

Given a tissue label or UBERON ID, fetches the term itself plus all
hierarchical descendants, saves both JSON and CSV for use in downstream
filtering steps (4 and 5).

Usage:
    python bin/0_resolve_uberon.py "kidney"
    python bin/0_resolve_uberon.py "UBERON:0002113"
    python bin/0_resolve_uberon.py "lung" --output-prefix data/uberon_lung
    python bin/0_resolve_uberon.py "pancreas | islet of Langerhans" --multi

Output:
    data/uberon_kidney.json   - full term list with metadata
    data/uberon_kidney.csv    - flat table: obo_id, label, level
"""

import os
import re
import sys
import json
import argparse
import requests
import pandas as pd
from harvester_logger import setup_logger, log_command, log_counts, log_finish

OLS_BASE   = "https://www.ebi.ac.uk/ols4/api"
UBERON_IRI = "http://purl.obolibrary.org/obo/{term_id}"
DATA_DIR   = "data"


def search_uberon(label: str, logger) -> list:
    """Search OLS4 for a UBERON term by label, return top matches."""
    url    = f"{OLS_BASE}/search"
    params = {"q": label, "ontology": "uberon", "type": "class", "rows": 10}

    logger.info(f"  Searching OLS4 for: '{label}'")
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()

    docs = r.json().get("response", {}).get("docs", [])
    return [
        {"obo_id": d.get("obo_id"), "label": d.get("label"), "iri": d.get("iri")}
        for d in docs if d.get("obo_id", "").startswith("UBERON")
    ]


def get_descendants(uberon_id: str, logger) -> list:
    """Get all hierarchical descendants of a UBERON term."""
    term_id = uberon_id.replace(":", "_")
    iri     = UBERON_IRI.format(term_id=term_id)
    iri_enc = requests.utils.quote(requests.utils.quote(iri, safe=""))

    url  = f"{OLS_BASE}/ontologies/uberon/terms/{iri_enc}/hierarchicalDescendants"
    page = 0
    all_terms = []

    while True:
        r = requests.get(url, params={"size": 200, "page": page}, timeout=15)
        if r.status_code == 404:
            break
        r.raise_for_status()

        data     = r.json()
        embedded = data.get("_embedded", {}).get("terms", [])
        all_terms.extend([
            {"obo_id": t.get("obo_id"), "label": t.get("label"), "level": "descendant"}
            for t in embedded if t.get("obo_id", "").startswith("UBERON")
        ])

        # Check for next page
        links = data.get("_links", {})
        if "next" not in links:
            break
        page += 1

    logger.info(f"  Found {len(all_terms):,} descendants for {uberon_id}")
    return all_terms


def resolve_term(query: str, logger) -> tuple:
    """
    Resolve a label or UBERON ID to (uberon_id, label).
    Auto-selects exact label match, otherwise prompts user.
    """
    if re.match(r"UBERON:\d+", query.strip(), re.IGNORECASE):
        uberon_id = query.strip().upper()
        return uberon_id, uberon_id

    results = search_uberon(query, logger)
    if not results:
        logger.error(f"  No UBERON terms found for '{query}'")
        sys.exit(1)

    # Auto-select exact label match
    exact = [r for r in results if r["label"].lower() == query.lower()]
    if exact:
        logger.info(f"  Exact match: {exact[0]['obo_id']}  {exact[0]['label']}")
        return exact[0]["obo_id"], exact[0]["label"]

    # Show options and prompt
    logger.info(f"  Top matches:")
    for i, r in enumerate(results[:5], 1):
        logger.info(f"    {i}. {r['obo_id']:20s}  {r['label']}")

    choice = input("\n  Use which? [1]: ").strip() or "1"
    selected = results[int(choice) - 1]
    logger.info(f"  Selected: {selected['obo_id']}  {selected['label']}")
    return selected["obo_id"], selected["label"]


def resolve_uberon(queries: list, output_prefix: str, logger):
    """
    Resolve one or more tissue queries, combine all terms,
    save JSON and CSV.
    """
    all_terms    = []
    root_terms   = []

    for query in queries:
        query = query.strip()
        logger.info(f"\nResolving: '{query}'")

        uberon_id, label = resolve_term(query, logger)

        # Add the root term itself
        root = {"obo_id": uberon_id, "label": label, "level": "root"}
        root_terms.append(root)
        all_terms.append(root)
        logger.info(f"  Root term: {uberon_id}  {label}")

        # Get all descendants
        descendants = get_descendants(uberon_id, logger)
        all_terms.extend(descendants)

        log_counts(logger, f"terms resolved for '{query}'",
                   before=1, after=1 + len(descendants), unit="terms")

    # Deduplicate by obo_id
    before_dedup = len(all_terms)
    seen     = set()
    deduped  = []
    for t in all_terms:
        if t["obo_id"] not in seen:
            seen.add(t["obo_id"])
            deduped.append(t)

    log_counts(logger, "deduplication", before=before_dedup, after=len(deduped), unit="terms")

    # Build output
    obo_ids = [t["obo_id"] for t in deduped]

    output = {
        "queries":    queries,
        "root_terms": root_terms,
        "obo_ids":    obo_ids,
        "terms":      deduped,
        "total":      len(deduped),
    }

    # Save JSON
    json_path = f"{output_prefix}.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nSaved JSON: {json_path}")

    # Save CSV
    csv_path = f"{output_prefix}.csv"
    df = pd.DataFrame(deduped)
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved CSV : {csv_path}")
    logger.info(f"Total terms: {len(deduped):,}  (root + descendants)")

    return json_path, csv_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resolve UBERON tissue hierarchy and save JSON + CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single tissue
  python bin/0_resolve_uberon.py "kidney"

  # By UBERON ID
  python bin/0_resolve_uberon.py "UBERON:0002113"

  # Multiple tissues (combined into one file)
  python bin/0_resolve_uberon.py "pancreas" "islet of Langerhans" --multi

  # Custom output prefix
  python bin/0_resolve_uberon.py "lung" --output-prefix data/uberon_lung
        """
    )
    parser.add_argument("queries", nargs="+",
        help="Tissue label(s) or UBERON ID(s) to resolve")
    parser.add_argument("--output-prefix", default=None,
        help="Output file prefix (default: data/uberon_{first_query})")
    parser.add_argument("--multi", action="store_true",
        help="Combine multiple queries into a single output file")

    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    # Determine output prefix
    if args.output_prefix:
        output_prefix = args.output_prefix
    else:
        slug = re.sub(r"[^a-z0-9]+", "_", args.queries[0].lower()).strip("_")
        output_prefix = os.path.join(DATA_DIR, f"uberon_{slug}")

    log_file = f"{output_prefix}.log"
    logger   = setup_logger("0_resolve_uberon", output_csv=log_file)
    log_command(logger)

    if args.multi or len(args.queries) > 1:
        # Combine all queries into one output
        resolve_uberon(args.queries, output_prefix, logger)
    else:
        # Single query
        resolve_uberon(args.queries, output_prefix, logger)

    log_finish(logger, output_prefix + ".csv")
