#!/usr/bin/env python3
"""
Step 0c: Resolve disease terms via OLS4 API

Given a disease label or ontology ID, fetches the term itself plus all
hierarchical descendants, saves JSON and CSV for use in downstream
filtering steps.

Supports PATO (phenotypic qualities, e.g. 'normal') and MONDO (disease
ontology, e.g. 'chronic kidney disease').  The primary use case is
resolving 'normal' to PATO:0000461 for filtering CellxGene data.

Usage:
1. Python module execution:
python -m harvester.resolve_disease normal \
        --output-prefix data/disease_normal

2. CLI command (after pip install -e .):
cellxgene-harvester resolve-disease normal
cellxgene-harvester resolve-disease normal --output-prefix data/disease_normal

Output:
    data/disease_normal.json   - full term list with metadata
    data/disease_normal.csv    - flat table: obo_id, label, level
"""

import os
import re
import sys
import json
import requests
import pandas as pd
from harvester.logger import setup_logger, log_command, log_counts, log_finish

OLS_BASE = "https://www.ebi.ac.uk/ols4/api"
DATA_DIR = "data"

# Ontologies searched in priority order when a bare label is given.
# PATO covers phenotypic qualities (normal, abnormal, …).
# MONDO covers disease entities (chronic kidney disease, diabetes, …).
_ONTOLOGY_PRIORITY = ["pato", "mondo"]

# ID prefix → ontology name for disambiguation
_PREFIX_ONTOLOGY = {
    "PATO":  "pato",
    "MONDO": "mondo",
    "HP":    "hp",
    "EFO":   "efo",
}


def _ontology_for_id(term_id: str) -> str:
    prefix = term_id.split(":")[0].upper()
    return _PREFIX_ONTOLOGY.get(prefix, prefix.lower())


def search_disease(label: str, logger) -> list:
    """Search OLS4 for a disease/phenotype term by label across PATO + MONDO."""
    url     = f"{OLS_BASE}/search"
    matches = []

    for ontology in _ONTOLOGY_PRIORITY:
        params = {"q": label, "ontology": ontology, "type": "class",
                  "exact": "true", "rows": 10}
        logger.info(f"  Searching OLS4 ({ontology}) for: '{label}'")
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        for d in docs:
            obo_id = d.get("obo_id", "")
            if any(obo_id.startswith(p) for p in _PREFIX_ONTOLOGY):
                matches.append({
                    "obo_id":   obo_id,
                    "label":    d.get("label"),
                    "iri":      d.get("iri"),
                    "ontology": ontology,
                })

        if matches:
            break  # stop at first ontology that returns results

    if not matches:
        # Fallback: non-exact search
        for ontology in _ONTOLOGY_PRIORITY:
            params = {"q": label, "ontology": ontology, "type": "class", "rows": 10}
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            docs = r.json().get("response", {}).get("docs", [])
            for d in docs:
                obo_id = d.get("obo_id", "")
                if any(obo_id.startswith(p) for p in _PREFIX_ONTOLOGY):
                    matches.append({
                        "obo_id":   obo_id,
                        "label":    d.get("label"),
                        "iri":      d.get("iri"),
                        "ontology": ontology,
                    })
            if matches:
                break

    return matches


def get_descendants(term_id: str, logger) -> list:
    """Get all hierarchical descendants of a disease/phenotype term via OLS4."""
    ontology = _ontology_for_id(term_id)
    term_key = term_id.replace(":", "_")
    iri      = f"http://purl.obolibrary.org/obo/{term_key}"
    iri_enc  = requests.utils.quote(requests.utils.quote(iri, safe=""))

    url       = f"{OLS_BASE}/ontologies/{ontology}/terms/{iri_enc}/hierarchicalDescendants"
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
            for t in embedded
            if t.get("obo_id") and any(t["obo_id"].startswith(p) for p in _PREFIX_ONTOLOGY)
        ])

        if "next" not in data.get("_links", {}):
            break
        page += 1

    logger.info(f"  Found {len(all_terms):,} descendants for {term_id}")
    return all_terms


def resolve_term(query: str, logger) -> tuple:
    """
    Resolve a label or ontology ID to (term_id, label).
    Auto-selects exact label match, otherwise prompts user.
    """
    # Already an ID (PATO:xxxxxxx, MONDO:xxxxxxx, etc.)
    if re.match(r"[A-Z]+:\d+", query.strip(), re.IGNORECASE):
        term_id = query.strip().upper()
        return term_id, term_id

    results = search_disease(query, logger)
    if not results:
        logger.error(f"  No disease/phenotype terms found for '{query}'")
        sys.exit(1)

    # Auto-select exact label match (case-insensitive)
    exact = [r for r in results if r["label"].lower() == query.lower()]
    if exact:
        logger.info(f"  Exact match : {exact[0]['obo_id']}  {exact[0]['label']}")
        return exact[0]["obo_id"], exact[0]["label"]

    # Show options and prompt
    logger.info(f"  Top matches:")
    for i, r in enumerate(results[:5], 1):
        logger.info(f"    {i}. {r['obo_id']:25s}  {r['label']}")

    choice   = input("\n  Use which? [1]: ").strip() or "1"
    selected = results[int(choice) - 1]
    logger.info(f"  Selected: {selected['obo_id']}  {selected['label']}")
    return selected["obo_id"], selected["label"]


def resolve_disease(queries: list, output_prefix: str, logger):
    """
    Resolve one or more disease/phenotype queries, combine all terms,
    save JSON and CSV.

    JSON structure mirrors uberon JSON for consistent downstream loading:
        {
          "queries":    [...],
          "root_terms": [{obo_id, label}, ...],
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

        term_id, label = resolve_term(query, logger)

        root = {"obo_id": term_id, "label": label, "level": "root"}
        root_terms.append(root)
        all_terms.append(root)
        logger.info(f"  Root term: {term_id}  {label}")

        descendants = get_descendants(term_id, logger)
        all_terms.extend(descendants)

        log_counts(logger, f"terms resolved for '{query}'",
                   before=1, after=1 + len(descendants), unit="terms")

    # Deduplicate by obo_id
    before_dedup = len(all_terms)
    seen, deduped = set(), []
    for t in all_terms:
        if t["obo_id"] not in seen:
            seen.add(t["obo_id"])
            deduped.append(t)

    log_counts(logger, "deduplication",
               before=before_dedup, after=len(deduped), unit="terms")

    obo_ids = [t["obo_id"] for t in deduped]

    output = {
        "queries":    queries,
        "root_terms": root_terms,
        "obo_ids":    obo_ids,
        "terms":      deduped,
        "total":      len(deduped),
    }

    json_path = f"{output_prefix}.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nSaved JSON: {json_path}")

    csv_path = f"{output_prefix}.csv"
    pd.DataFrame(deduped).to_csv(csv_path, index=False)
    logger.info(f"Saved CSV : {csv_path}")
    logger.info(f"Total terms: {len(deduped):,}  (root + descendants)")

    return json_path, csv_path


# =============================================================================
# run_resolve_disease
# =============================================================================

def run_resolve_disease(queries: list, output_prefix: str = None):
    """Main entry point called by CLI."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if output_prefix:
        out_prefix = output_prefix
    else:
        slug       = re.sub(r"[^a-z0-9]+", "_", queries[0].lower()).strip("_")
        out_prefix = os.path.join(DATA_DIR, f"disease_{slug}")

    log_file = f"{out_prefix}.log"
    logger   = setup_logger("0c_resolve_disease", output_csv=log_file)
    log_command(logger)

    resolve_disease(queries, out_prefix, logger)
    log_finish(logger, out_prefix + ".csv")
