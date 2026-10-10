#!/usr/bin/env python3
"""
Step 0: Resolve UBERON tissue terms via OLS4 API

Given a tissue label or UBERON ID, fetches the term itself plus all
hierarchical descendants, saves both JSON and CSV for use in downstream
filtering steps (4 and 5).

--also-relation LABEL adds the terms that have that relation to the root, and
everything below them. The label is an exact relation label of the ontology, for
example "contributes to morphology of": the nose is not below the respiratory
system, but it contributes to its morphology, so it is added with its
descendants. The organ stays the one root term; the added terms are listed under
"related_terms" in the JSON. Without the option only the descendants are used.

Usage:
1. Python module execution:
python -m harvester.resolve_uberon "kidney"

2. CLI command (after pip install -e .):
cellxgene-harvester resolve-uberon kidney
cellxgene-harvester resolve-uberon kidney --output-prefix 2026-08-03-run/uberon_kidney
cellxgene-harvester resolve-uberon "respiratory system" --also-relation "contributes to morphology of"

Output:
    <run folder>/uberon_kidney.json   - full term list with metadata
    <run folder>/uberon_kidney.csv    - flat table: obo_id, label, level
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

OLS_BASE   = "https://www.ebi.ac.uk/ols4/api"
OLS_V2     = "https://www.ebi.ac.uk/ols4/api/v2/ontologies/uberon"
UBERON_IRI = "http://purl.obolibrary.org/obo/{term_id}"


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

    logger.info(f"  Found {len(all_terms)} descendants for {uberon_id}")
    return all_terms


def find_relation(label: str, logger) -> dict:
    """Return {"label", "iri"} of the relation with exactly this label (ignoring case).

    Raises ValueError if no relation, or more than one, has that label: nothing is
    guessed, so a wrong label is never read as a different relation.
    """
    logger.info(f"  Looking up the relation: '{label}'")
    r = requests.get(f"{OLS_V2}/properties", params={"search": label, "size": 50}, timeout=30)
    r.raise_for_status()
    found = {}
    for element in r.json().get("elements", []):
        names = element.get("label") or []
        names = [names] if isinstance(names, str) else names
        if label.strip().lower() in [n.lower() for n in names if isinstance(n, str)]:
            found[element["iri"]] = names[0]
    if len(found) != 1:
        raise ValueError(f"'{label}' is not the exact label of one relation of the ontology "
                         f"(found {len(found)}); give it as OLS shows it, for example "
                         f"'contributes to morphology of'")
    iri, name = next(iter(found.items()))
    return {"label": name, "iri": iri}


def get_related(uberon_id: str, relation: dict, logger) -> list:
    """Return the terms that have the relation to the term: {"obo_id", "label", "level"}.

    OLS4 lists the classes related to an IRI by any relation; only those related by
    this relation are kept, and only UBERON terms.
    """
    root_iri = UBERON_IRI.format(term_id=uberon_id.replace(":", "_"))
    terms, page = [], 0
    while True:
        r = requests.get(f"{OLS_V2}/classes",
                         params={"relatedTo": root_iri, "size": 100, "page": page}, timeout=60)
        r.raise_for_status()
        data = r.json()
        for element in data.get("elements", []):
            curie = element.get("curie") or ""
            has_relation = any(link.get("property") == relation["iri"] and link.get("value") == root_iri
                               for link in element.get("relatedTo", []))
            if has_relation and curie.startswith("UBERON"):
                name = element.get("label")
                terms.append({"obo_id": curie, "label": name[0] if isinstance(name, list) else name,
                              "level": "related"})
        page += 1
        if page >= data.get("totalPages", 0):
            break
    logger.info(f"  Found {len(terms)} terms that '{relation['label']}' {uberon_id}")
    return terms


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


def resolve_uberon(queries: list, output_prefix: str, logger, relations: list = None):
    """
    Resolve one or more tissue queries, combine all terms,
    save JSON and CSV. relations are exact relation labels: the terms that have
    one of them to a root are added, with their descendants.
    """
    all_terms     = []
    root_terms    = []
    related_terms = []
    try:
        relation_list = [find_relation(label, logger) for label in (relations or [])]
    except ValueError as e:
        logger.error(f"ERROR: {e}")
        sys.exit(1)

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

        # the terms that have a relation to the root, each with its descendants
        for relation in relation_list:
            for term in get_related(uberon_id, relation, logger):
                related_terms.append({"obo_id": term["obo_id"], "label": term["label"],
                                      "relation": relation["label"], "root": uberon_id})
                all_terms.append(term)
                all_terms.extend(get_descendants(term["obo_id"], logger))

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
    if relation_list:
        output["relations"]     = [r["label"] for r in relation_list]
        output["related_terms"] = related_terms

    # Save JSON
    json_path = f"{output_prefix}.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nSaved JSON: {json_path}")

    # Save CSV
    csv_path = f"{output_prefix}.csv"
    df = pd.DataFrame(deduped)
    write_dataframe_csv(df, csv_path)
    logger.info(f"Saved CSV : {csv_path}")
    logger.info(f"Total terms: {len(deduped)}  (root + descendants)")

    return json_path, csv_path

# =============================================================================
# run_resolve_uberon
# =============================================================================
def run_resolve_uberon(queries: list, output_prefix: str = None, multi: bool = False,
                       relations: list = None):
    """Main entry point called by CLI"""
    os.makedirs(run_dir(), exist_ok=True)
    
    if output_prefix:
        out_prefix = output_prefix
    else:
        slug = re.sub(r"[^a-z0-9]+", "_", queries[0].lower()).strip("_")
        out_prefix = os.path.join(run_dir(), f"uberon_{slug}")
    
    log_file = f"{out_prefix}.log"
    logger = setup_logger("0_resolve_uberon", output_csv=log_file)
    log_command(logger)
    
    resolve_uberon(queries, out_prefix, logger, relations)
    
    log_finish(logger, out_prefix + ".csv")

