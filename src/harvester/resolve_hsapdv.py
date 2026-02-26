#!/usr/bin/env python3
"""
Step 0c: Resolve HsapDv development stage terms for a minimum age threshold

Queries the OLS4 API for all HsapDv terms, reads the authoritative
"start, years post birth" annotation field, and writes a JSON containing
only the term IDs whose start age is >= --min-age.

The output JSON has the same structure as resolve_uberon and resolve_disease
(queries, root_terms, obo_ids, terms, total), so all three cell-level filters
in the pipeline are a uniform .isin(obo_ids) check on the ontology_term_id
column. No age comparison logic lives in the filter code.

Usage:
1. Python module execution:
python -m harvester.resolve_hsapdv --min-age 15

2. CLI command (after pip install -e .):
cellxgene-harvester resolve-hsapdv --min-age 15
cellxgene-harvester resolve-hsapdv --min-age 15 --output-prefix data/hsapdv_adult_15

Output:
    data/hsapdv_adult_15.json   - obo_ids for all HsapDv terms with start age >= 15
    data/hsapdv_adult_15.csv    - flat table: obo_id, label, start_years_post_birth
"""

import os
import sys
import json
import requests
import pandas as pd
from harvester.logger import setup_logger, log_command, log_counts, log_finish

OLS_BASE = "https://www.ebi.ac.uk/ols4/api"
DATA_DIR = "data"

# Kept for CLI signature compatibility with cli.py (obo_url parameter); not used.
HSAPDV_OBO_URL = None


def fetch_all_hsapdv_terms(logger) -> list:
    """
    Fetch all HsapDv terms from OLS4 API, paginating through all results.

    Reads the "start, years post birth" annotation field which is the
    authoritative source for age in HsapDv — e.g. seventh decade stage
    has annotation {"start, years post birth": ["60.0"]} so it correctly
    resolves to start_age=60, which passes any min_age <= 60.

    Returns list of dicts: {obo_id, label, start_years_post_birth}
    start_years_post_birth is None for prenatal/non-age terms.
    """
    url  = f"{OLS_BASE}/ontologies/hsapdv/terms"
    page = 0
    size = 200
    all_terms = []

    logger.info("Fetching HsapDv terms from OLS4 API...")

    while True:
        r = requests.get(url, params={"size": size, "page": page}, timeout=30)
        if r.status_code == 404:
            break
        r.raise_for_status()

        data     = r.json()
        embedded = data.get("_embedded", {}).get("terms", [])
        if not embedded:
            break

        for t in embedded:
            obo_id = t.get("obo_id", "")
            if not obo_id.startswith("HsapDv:"):
                continue
            if t.get("is_obsolete", False):
                continue

            label      = t.get("label", "")
            annotation = t.get("annotation", {}) or {}

            # "start, years post birth" is the canonical age field in OLS4 HsapDv terms.
            # Example: seventh decade stage → ["60.0"], newborn stage → ["0.0"]
            start_vals = annotation.get("start, years post birth", [])
            start_age  = None
            if start_vals:
                try:
                    start_age = float(start_vals[0])
                except (ValueError, TypeError):
                    pass

            all_terms.append({
                "obo_id":                 obo_id,
                "label":                  label,
                "start_years_post_birth": start_age,
            })

        logger.info(f"  Page {page}: {len(embedded)} terms "
                    f"(running total: {len(all_terms):,})")

        if "next" not in data.get("_links", {}):
            break
        page += 1

    logger.info(f"Fetched {len(all_terms):,} HsapDv terms total\n")
    return all_terms


def resolve_hsapdv(min_age: float, output_prefix: str, logger):
    """
    Fetch all HsapDv terms via OLS4, select those with
    start_years_post_birth >= min_age, write JSON and CSV.

    JSON structure matches resolve_uberon / resolve_disease:
        {
          "queries":    ["min_age=15"],
          "root_terms": [{obo_id, label}, ...],
          "obo_ids":    [...],
          "terms":      [{obo_id, label, start_years_post_birth}, ...],
          "total":      N
        }
    """
    all_terms = fetch_all_hsapdv_terms(logger)

    included = []
    n_below  = 0
    n_no_age = 0

    for t in all_terms:
        age = t["start_years_post_birth"]
        if age is None:
            n_no_age += 1
        elif age >= min_age:
            included.append(t)
        else:
            n_below += 1

    logger.info(f"  start age >= {min_age} yr → included : {len(included):,}")
    logger.info(f"  start age <  {min_age} yr → excluded : {n_below:,}")
    logger.info(f"  no age annotation        → excluded : {n_no_age:,}")

    # Spot-checks using known terms
    logger.info("\n  Spot-checks:")
    name_map = {e["label"].lower(): e for e in included}
    checks = [
        ("seventh decade stage", True),   # start=60 → included (60 >= 15)
        ("eighth decade stage",  True),   # start=70 → included (70 >= 15)
        ("29-year-old stage",    True),   # start=29 → included (29 >= 15)
        ("15-year-old stage",    True),   # start=15 → included (15 >= 15)
        ("14-year-old stage",    False),  # start=14 → excluded (14 < 15)
        ("newborn stage",        False),  # start=0  → excluded (0 < 15)
    ]
    all_ok = True
    for label, expect_in in checks:
        in_result = label in name_map
        ok        = in_result == expect_in
        all_ok    = all_ok and ok
        age_str   = f"  start={name_map[label]['start_years_post_birth']}" if in_result else ""
        logger.info(f"    {'OK  ' if ok else 'FAIL'} {label!r:35s} "
                    f"{'included' if in_result else 'excluded'}{age_str}")
    if not all_ok:
        logger.warning("\n  WARNING: one or more spot-checks failed — "
                       "check OLS4 annotations for these terms")

    # root_terms = term(s) with the lowest start age among included (informational)
    min_included = min((e["start_years_post_birth"] for e in included), default=None)
    root_terms   = [
        {"obo_id": e["obo_id"], "label": e["label"]}
        for e in included if e["start_years_post_birth"] == min_included
    ] if min_included is not None else []

    obo_ids = [e["obo_id"] for e in included]

    output = {
        "queries":    [f"min_age={min_age}"],
        "root_terms": root_terms,
        "obo_ids":    obo_ids,
        "terms":      included,
        "total":      len(included),
    }

    json_path = f"{output_prefix}.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nSaved JSON: {json_path}")

    csv_path = f"{output_prefix}.csv"
    pd.DataFrame(included).to_csv(csv_path, index=False)
    logger.info(f"Saved CSV : {csv_path}")
    logger.info(f"Total included terms: {len(included):,}  (start age >= {min_age} yr)")

    return json_path, csv_path


# =============================================================================
# run_resolve_hsapdv
# =============================================================================

def run_resolve_hsapdv(min_age: float, output_prefix: str = None,
                       obo_url: str = None):
    """Main entry point called by CLI."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if output_prefix:
        out_prefix = output_prefix
    else:
        age_str    = str(int(min_age)) if min_age == int(min_age) else str(min_age)
        out_prefix = os.path.join(DATA_DIR, f"hsapdv_adult_{age_str}")

    log_file = f"{out_prefix}.log"
    logger   = setup_logger("0c_resolve_hsapdv", output_csv=log_file)
    log_command(logger)
    logger.info(f"Min age : {min_age}")
    logger.info(f"Output  : {out_prefix}\n")

    resolve_hsapdv(min_age, out_prefix, logger)
    log_finish(logger, out_prefix + ".csv")
