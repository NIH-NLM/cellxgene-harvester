#!/usr/bin/env python3
"""
Step 0b: Resolve HsapDv development stage terms for a minimum age threshold

Downloads the HsapDv OBO, parses every post-natal term, extracts its minimum
age in years, and writes a JSON containing only the term IDs whose age is
>= --min-age.

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
    data/hsapdv_adult_15.json   - obo_ids for all HsapDv terms with age >= 15
    data/hsapdv_adult_15.csv    - flat table: obo_id, label, min_age_years
"""

import os
import re
import sys
import json
import urllib.request
import pandas as pd
from harvester.logger import setup_logger, log_command, log_counts, log_finish

HSAPDV_OBO_URL = "http://purl.obolibrary.org/obo/hsapdv.obo"
DATA_DIR       = "data"

# ---------------------------------------------------------------------------
# Age extraction from OBO def: fields
#
# HsapDv uses these patterns in def: text:
#
#   Decade terms:
#     "Human life stage that starts around 60 years old..."  -> 60
#
#   Year-exact terms:
#     "...29 year old individual."                           -> 29
#
#   Sub-year postnatal (months):
#     "...from 0 to 28 days..."                             -> 0.0  (days/365)
#
#   Prenatal / embryonic / Carnegie:
#     -> None  (excluded regardless of threshold)
# ---------------------------------------------------------------------------

_RE_STARTS_AROUND  = re.compile(r'starts\s+around\s+(\d+(?:\.\d+)?)\s+year', re.I)
_RE_YEAR_OLD       = re.compile(r'(\d+)\s+year[- ]old', re.I)
_RE_MONTH_RANGE    = re.compile(r'from\s+(\d+)\s+to\s+\d+\s+month', re.I)
_RE_DAY_RANGE      = re.compile(r'from\s+(\d+)\s+to\s+\d+\s+day', re.I)

_PRENATAL_MARKERS  = [
    'post-fertilization', 'post fertilization', 'carnegie',
    'embryonic', 'prenatal', 'trimester', 'gestational', 'organogenesis',
]


def _extract_min_age(name: str, def_text: str):
    """Return minimum age in years from a def: field, or None if prenatal/unknown."""
    combined = (name + ' ' + def_text).lower()

    if any(m in combined for m in _PRENATAL_MARKERS):
        return None

    m = _RE_STARTS_AROUND.search(def_text)
    if m:
        return float(m.group(1))

    m = _RE_YEAR_OLD.search(def_text)
    if m:
        return float(m.group(1))

    m = _RE_MONTH_RANGE.search(def_text)
    if m:
        return float(m.group(1)) / 12.0

    m = _RE_DAY_RANGE.search(def_text)
    if m:
        return float(m.group(1)) / 365.25

    return None


def _parse_obo(obo_text: str) -> list:
    """Parse OBO text into a list of term dicts."""
    terms, current = [], None
    for raw_line in obo_text.splitlines():
        line = raw_line.strip()
        if line == '[Term]':
            if current:
                terms.append(current)
            current = {'id': None, 'name': '', 'def': '', 'is_obsolete': False}
        elif line == '[Typedef]':
            if current:
                terms.append(current)
            current = None
        elif current is None:
            continue
        elif line.startswith('id: '):
            current['id'] = line[4:].strip()
        elif line.startswith('name: '):
            current['name'] = line[6:].strip()
        elif line.startswith('def: '):
            m = re.match(r'^def:\s+"(.*?)"\s*\[', line, re.S)
            current['def'] = m.group(1) if m else line[5:].strip()
        elif line == 'is_obsolete: true':
            current['is_obsolete'] = True
    if current:
        terms.append(current)
    return terms


def resolve_hsapdv(min_age: float, output_prefix: str, obo_url: str, logger):
    """
    Download HsapDv OBO, collect all terms with age >= min_age, write JSON/CSV.

    JSON structure matches resolve_uberon / resolve_disease:
        {
          "queries":    ["min_age=15"],
          "root_terms": [{obo_id, label}, ...],   # youngest qualifying term(s)
          "obo_ids":    [...],
          "terms":      [{obo_id, label, min_age_years}, ...],
          "total":      N
        }
    """
    logger.info(f"Downloading HsapDv OBO from: {obo_url}")
    try:
        with urllib.request.urlopen(obo_url, timeout=60) as resp:
            obo_text = resp.read().decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to download HsapDv OBO: {e}")
        sys.exit(1)
    logger.info(f"Downloaded {len(obo_text):,} bytes")

    raw_terms = _parse_obo(obo_text)
    logger.info(f"Parsed {len(raw_terms):,} OBO terms")

    included = []
    n_below_threshold = 0
    n_prenatal        = 0
    n_obsolete        = 0

    for t in raw_terms:
        term_id = t['id']
        if not term_id or not term_id.startswith('HsapDv:'):
            continue
        if t['is_obsolete']:
            n_obsolete += 1
            continue

        age = _extract_min_age(t['name'], t['def'])

        if age is None:
            n_prenatal += 1
        elif age >= min_age:
            included.append({
                'obo_id':        term_id,
                'label':         t['name'],
                'min_age_years': age,
            })
        else:
            n_below_threshold += 1

    logger.info(f"\n  age >= {min_age} yr → included : {len(included):,}")
    logger.info(f"  age <  {min_age} yr → excluded : {n_below_threshold:,}")
    logger.info(f"  prenatal/embryonic  → excluded : {n_prenatal:,}")
    logger.info(f"  obsolete            → skipped  : {n_obsolete:,}")

    # Spot-checks
    logger.info("\n  Spot-checks:")
    name_map = {e['label'].lower(): e for e in included}
    checks = [
        ('seventh decade stage', True),   # 60 yr → included at min_age=15
        ('eighth decade stage',  True),   # 70 yr → included at min_age=15
        ('29-year-old stage',    True),   # 29 yr → included
        ('14-year-old stage',    False),  # 14 yr → excluded at min_age=15
    ]
    all_ok = True
    for label, expect_in in checks:
        in_result = label in name_map
        ok = in_result == expect_in
        all_ok = all_ok and ok
        age_str = f"  age={name_map[label]['min_age_years']}" if in_result else ""
        logger.info(f"    {'OK  ' if ok else 'FAIL'} {label!r:35s} "
                    f"{'included' if in_result else 'excluded'}{age_str}")
    if not all_ok:
        logger.warning("  WARNING: one or more spot-checks failed — review OBO parsing")

    # root_terms = youngest included term(s) (purely informational)
    min_included = min((e['min_age_years'] for e in included), default=None)
    root_terms   = [
        {'obo_id': e['obo_id'], 'label': e['label']}
        for e in included if e['min_age_years'] == min_included
    ] if min_included is not None else []

    obo_ids = [e['obo_id'] for e in included]

    output = {
        'queries':    [f'min_age={min_age}'],
        'root_terms': root_terms,
        'obo_ids':    obo_ids,
        'terms':      included,
        'total':      len(included),
    }

    json_path = f"{output_prefix}.json"
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nSaved JSON: {json_path}")

    csv_path = f"{output_prefix}.csv"
    pd.DataFrame(included).to_csv(csv_path, index=False)
    logger.info(f"Saved CSV : {csv_path}")
    logger.info(f"Total included terms: {len(included):,}  (age >= {min_age} yr)")

    return json_path, csv_path


# =============================================================================
# run_resolve_hsapdv
# =============================================================================

def run_resolve_hsapdv(min_age: float, output_prefix: str = None,
                       obo_url: str = HSAPDV_OBO_URL):
    """Main entry point called by CLI."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if output_prefix:
        out_prefix = output_prefix
    else:
        age_str    = str(int(min_age)) if min_age == int(min_age) else str(min_age)
        out_prefix = os.path.join(DATA_DIR, f"hsapdv_adult_{age_str}")

    log_file = f"{out_prefix}.log"
    logger   = setup_logger("0b_resolve_hsapdv", output_csv=log_file)
    log_command(logger)
    logger.info(f"Min age : {min_age}")
    logger.info(f"OBO URL : {obo_url}")
    logger.info(f"Output  : {out_prefix}\n")

    resolve_hsapdv(min_age, out_prefix, obo_url, logger)
    log_finish(logger, out_prefix + ".csv")
