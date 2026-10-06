#!/usr/bin/env python3
"""
Step 0d: Resolve assay (technique) terms via OLS4 API

Given an assay label or an EFO ID, fetches the term itself plus all
hierarchical descendants, saves both JSON and CSV for use in Step 5
(count-normal-cells --exclude-assay).

The file is used as a NEGATIVE selection: the cells whose
assay_ontology_term_id is in the file are left out of the filtered counts, for
example to leave out spatial techniques. Text matching on titles does not find
a technique reliably (see the README). The assay ontology id of each cell does.

Usage:
1. Python module execution:
python -m harvester.resolve_assay "spatial transcriptomics"

2. CLI command (after pip install -e .):
cellxgene-harvester resolve-assay "spatial transcriptomics"
cellxgene-harvester resolve-assay "spatial transcriptomics" MERFISH --output-prefix 2026-08-03-run/assay_spatial

Output:
    <run folder>/assay_spatial_transcriptomics.json   - full term list with metadata
    <run folder>/assay_spatial_transcriptomics.csv    - flat table: obo_id, label, level
"""

import os
import re
import sys
import json
import requests
import pandas as pd
from harvester.io_utils import write_dataframe_csv
from harvester.run_dir import run_dir
from harvester.logger import setup_logger, log_command, log_counts, log_finish

OLS_BASE = "https://www.ebi.ac.uk/ols4/api"
EFO_IRI  = "http://www.ebi.ac.uk/efo/{term_id}"


def search_assay(label: str, logger) -> list:
    """Search OLS4 for an EFO assay term by label, return top matches."""
    url    = f"{OLS_BASE}/search"
    params = {"q": label, "ontology": "efo", "type": "class", "rows": 10}

    logger.info(f"  Searching OLS4 for: '{label}'")
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()

    docs = r.json().get("response", {}).get("docs", [])
    return [
        {"obo_id": d.get("obo_id"), "label": d.get("label"), "iri": d.get("iri")}
        for d in docs if d.get("obo_id", "").startswith("EFO")
    ]


def get_descendants(term_id: str, logger) -> list:
    """Get all hierarchical descendants of an EFO term."""
    iri     = EFO_IRI.format(term_id=term_id.replace(":", "_"))
    iri_enc = requests.utils.quote(requests.utils.quote(iri, safe=""))

    url       = f"{OLS_BASE}/ontologies/efo/terms/{iri_enc}/hierarchicalDescendants"
    page      = 0
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
            for t in embedded if t.get("obo_id", "").startswith("EFO")
        ])

        # Check for next page
        links = data.get("_links", {})
        if "next" not in links:
            break
        page += 1

    logger.info(f"  Found {len(all_terms)} descendants for {term_id}")
    return all_terms


def resolve_term(query: str, logger) -> tuple:
    """
    Resolve a label or EFO ID to (efo_id, label).
    Auto-selects exact label match, otherwise prompts user.
    """
    if re.match(r"EFO:\d+", query.strip(), re.IGNORECASE):
        efo_id = query.strip().upper()
        return efo_id, efo_id

    results = search_assay(query, logger)
    if not results:
        logger.error(f"  No EFO terms found for '{query}'")
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


def resolve_assay(queries: list, output_prefix: str, logger):
    """
    Resolve one or more assay queries, combine all terms,
    save JSON and CSV.

    JSON structure mirrors uberon JSON for consistent downstream loading:
        {
          "queries":    [...],
          "root_terms": [{obo_id, label, level}, ...],
          "obo_ids":    [...],          # all IDs including descendants
          "terms":      [{obo_id, label, level}, ...],
          "total":      N
        }
    """
    all_terms  = []
    root_terms = []

    for query in queries:
        query = query.strip()
        logger.info(f"\nResolving: '{query}'")

        efo_id, label = resolve_term(query, logger)

        # Add the root term itself
        root = {"obo_id": efo_id, "label": label, "level": "root"}
        root_terms.append(root)
        all_terms.append(root)
        logger.info(f"  Root term: {efo_id}  {label}")

        # Get all descendants
        descendants = get_descendants(efo_id, logger)
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
    write_dataframe_csv(pd.DataFrame(deduped), csv_path)
    logger.info(f"Saved CSV : {csv_path}")
    logger.info(f"Total terms: {len(deduped)}  (root + descendants)")

    return json_path, csv_path


# =============================================================================
# run_resolve_assay
# =============================================================================
def run_resolve_assay(queries: list, output_prefix: str = None):
    """Main entry point called by CLI"""
    os.makedirs(run_dir(), exist_ok=True)

    if output_prefix:
        out_prefix = output_prefix
    else:
        slug = re.sub(r"[^a-z0-9]+", "_", queries[0].lower()).strip("_")
        out_prefix = os.path.join(run_dir(), f"assay_{slug}")

    log_file = f"{out_prefix}.log"
    logger = setup_logger("0d_resolve_assay", output_csv=log_file)
    log_command(logger)

    resolve_assay(queries, out_prefix, logger)

    log_finish(logger, out_prefix + ".csv")
