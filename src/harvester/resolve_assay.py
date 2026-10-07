#!/usr/bin/env python3
"""
Step 0d: Resolve assay (technique) terms via OLS4 API

You give the assays you WANT, each by its EFO label or EFO ID. Each assay is
resolved on its own: there is no root term and no descendants. The assays that
resolve are written to a JSON and a CSV file. An assay that does not resolve is
listed under "unresolved" in the JSON and in the log, and is skipped.

The file is used in Step 5 (count-normal-cells --assay): only the cells whose
assay_ontology_term_id is in the file are counted on the filtered side. Every
other assay, for example every spatial technique, is left out by not being in
the file. A label that does not resolve is also left out, so read the
"unresolved" list.

Text matching on titles does not find a technique reliably (see the README).
The assay ontology id of each cell does.

Usage:
1. Python module execution:
python -m harvester.resolve_assay "10x 3' v3" "Smart-seq2" EFO:0009900

2. CLI command (after pip install -e .):
cellxgene-harvester resolve-assay "10x 3' v3" "Smart-seq2" EFO:0009900 --output-prefix 2026-08-03-run/assay_published

Output:
    <run folder>/assay_10x_3_v3.json   - the resolved assays and the unresolved labels
    <run folder>/assay_10x_3_v3.csv    - flat table: obo_id, label, query
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


def search_assay(label: str, logger) -> list:
    """Search OLS4 for an EFO assay term by label, return top matches."""
    url    = f"{OLS_BASE}/search"
    params = {"q": label, "ontology": "efo", "type": "class", "rows": 20}

    logger.info(f"  Searching OLS4 for: '{label}'")
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()

    docs = r.json().get("response", {}).get("docs", [])
    return [
        {"obo_id": d.get("obo_id"), "label": d.get("label")}
        for d in docs if (d.get("obo_id") or "").startswith("EFO")
    ]


def get_term(efo_id: str, logger) -> dict:
    """Look up one EFO term by its id. Return None if there is no such term."""
    logger.info(f"  Looking up OLS4 for: {efo_id}")
    r = requests.get(f"{OLS_BASE}/ontologies/efo/terms",
                     params={"short_form": efo_id.replace(":", "_")}, timeout=15)
    r.raise_for_status()
    terms = r.json().get("_embedded", {}).get("terms", [])
    if not terms:
        return None
    return {"obo_id": terms[0].get("obo_id"), "label": terms[0].get("label")}


def resolve_term(query: str, logger) -> dict:
    """
    Resolve a label or an EFO ID to {"obo_id", "label"}, or None.
    A label must match one EFO term exactly (ignoring case). Nothing is asked
    and nothing is chosen for you: a label with no exact match is not resolved.
    """
    if re.fullmatch(r"EFO:\d+", query.strip(), re.IGNORECASE):
        return get_term(query.strip().upper(), logger)

    exact = [t for t in search_assay(query, logger)
             if (t["label"] or "").lower() == query.lower()]
    return exact[0] if exact else None


def resolve_assay(queries: list, output_prefix: str, logger):
    """
    Resolve each assay on its own, write the resolved assays and the
    unresolved labels to JSON, and the resolved assays to CSV.

    JSON structure:
        {
          "queries":    [...],
          "assays":     [{query, obo_id, label}, ...],
          "unresolved": [...],
          "obo_ids":    [...],          # the resolved ids, each once
          "total":      N
        }
    """
    assays     = []
    unresolved = []
    seen       = set()

    for query in queries:
        query = query.strip()
        logger.info(f"\nResolving: '{query}'")
        term = resolve_term(query, logger)
        if term is None:
            logger.warning(f"  NOT RESOLVED: '{query}' (no exact EFO label or id) - skipped")
            unresolved.append(query)
            continue
        if term["obo_id"] in seen:
            logger.info(f"  {term['obo_id']} {term['label']} is already in the list - kept once")
            continue
        seen.add(term["obo_id"])
        assays.append({"query": query, "obo_id": term["obo_id"], "label": term["label"]})
        logger.info(f"  Resolved: {term['obo_id']}  {term['label']}")

    log_counts(logger, "assays resolved", before=len(queries), after=len(assays), unit="assays")
    if unresolved:
        logger.warning(f"\n  WARNING: {len(unresolved)} not resolved and left out: {unresolved}")
    if not assays:
        logger.error("ERROR: no assay resolved, so there is no file to write")
        sys.exit(1)

    output = {
        "queries":    queries,
        "assays":     assays,
        "unresolved": unresolved,
        "obo_ids":    [a["obo_id"] for a in assays],
        "total":      len(assays),
    }

    # Save JSON
    json_path = f"{output_prefix}.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nSaved JSON: {json_path}")

    # Save CSV
    csv_path = f"{output_prefix}.csv"
    write_dataframe_csv(pd.DataFrame(assays, columns=["obo_id", "label", "query"]), csv_path)
    logger.info(f"Saved CSV : {csv_path}")
    logger.info(f"Total assays: {len(assays)}")

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
