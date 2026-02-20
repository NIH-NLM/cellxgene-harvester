#!/usr/bin/env python3
"""
Step 5 (single dataset): Count normal cells for one dataset via CellxGene Census.

Called by Nextflow count_normal_cells module - one process per dataset_id.
Results are collected and merged by Nextflow into the final CSV.

Filters applied server-side in Census query (memory efficient):
  - tissue_ontology_term_id IN uberon_ids
  - is_primary_data == True
  - disease == 'normal'

Filters applied client-side:
  - age >= min_age

Usage:
    python src/5_count_normal_cells_single.py \
        --dataset-id   "066943a2-fdac-4b29-b348-40cede398e4e" \
        --uberon       data/uberon_kidney.json \
        --min-age      15 \
        --first-author "Sikkema" \
        --year         "2023" \
        --journal      "Nat Med" \
        --output       066943a2_normal_count.csv
"""

import os
import sys
import json
import argparse
import re
import pandas as pd
from typing import Optional


def extract_age_from_stage(stage_label: str) -> Optional[int]:
    if not stage_label or not isinstance(stage_label, str):
        return None
    match = re.search(r'(\d+)[- ]?(?:year|yr)', stage_label.lower())
    return int(match.group(1)) if match else None


def filter_adult_cells(obs_df: pd.DataFrame, min_age: int) -> pd.DataFrame:
    if 'development_stage' not in obs_df.columns or min_age == 0:
        return obs_df

    EXCLUDE_TERMS = ['fetal', 'embryo', 'newborn', 'prenatal', 'lmp',
                     'post-fertilization', 'week post', 'Carnegie stage',
                     'trimester', 'gestational']

    adult_mask = []
    for stage_val in obs_df['development_stage'].astype(str):
        stage_lower = stage_val.lower()

        if not stage_val or stage_val in ('nan', 'None') or stage_val.strip() == '':
            adult_mask.append(False)
            continue

        if any(term in stage_lower for term in EXCLUDE_TERMS):
            adult_mask.append(False)
            continue

        if 'adult' in stage_lower:
            adult_mask.append(True)
            continue

        age = extract_age_from_stage(stage_val)
        if age is not None:
            adult_mask.append(age >= min_age)
        else:
            adult_mask.append(False)

    return obs_df[adult_mask]


def extract_metadata(obs_df: pd.DataFrame) -> dict:
    def most_common(col):
        if col in obs_df.columns and len(obs_df) > 0:
            vc = obs_df[col].value_counts()
            return str(vc.index[0]) if len(vc) > 0 else ''
        return ''

    def all_unique(col):
        if col in obs_df.columns and len(obs_df) > 0:
            uv = obs_df[col].dropna().unique()
            return ' | '.join(sorted(str(v) for v in uv))
        return ''

    # Tissue ontology summary
    tissue_summary = ''
    if 'tissue_ontology_term_id' in obs_df.columns:
        tissue_counts = obs_df['tissue_ontology_term_id'].value_counts()
        parts = [f"{tid}: {count:,}" for tid, count in tissue_counts.items() if count > 0]
        tissue_summary = "; ".join(parts)

    # Assay ontology summary
    assay_summary = ''
    if 'assay_ontology_term_id' in obs_df.columns:
        assay_counts = obs_df['assay_ontology_term_id'].value_counts()
        parts = [f"{aid}: {count:,}" for aid, count in assay_counts.items() if count > 0]
        assay_summary = "; ".join(parts)

    # Cell type ontology summary
    cell_type_summary = ''
    if 'cell_type_ontology_term_id' in obs_df.columns:
        ct_counts = obs_df['cell_type_ontology_term_id'].value_counts()
        parts = [f"{ct}: {count:,}" for ct, count in ct_counts.items() if count > 0]
        cell_type_summary = "; ".join(parts)

    # Disease ontology summary
    disease_summary = ''
    if 'disease_ontology_term_id' in obs_df.columns:
        dis_counts = obs_df['disease_ontology_term_id'].value_counts()
        parts = [f"{did}: {count:,}" for did, count in dis_counts.items() if count > 0]
        disease_summary = "; ".join(parts)

    # Sex ontology summary
    sex_summary = ''
    if 'sex_ontology_term_id' in obs_df.columns:
        sex_counts = obs_df['sex_ontology_term_id'].value_counts()
        parts = [f"{sid}: {count:,}" for sid, count in sex_counts.items() if count > 0]
        sex_summary = "; ".join(parts)

    dev_stage_summary = ''
    if 'development_stage' in obs_df.columns and len(obs_df) > 0:
        counts            = obs_df['development_stage'].value_counts()
        dev_stage_summary = "; ".join(f"{s}: {c:,}" for s, c in counts.items())

    donor_count = obs_df['donor_id'].nunique() if 'donor_id' in obs_df.columns else 0

    return {
        'tissue_ontology_term_id':            get_all_unique('tissue_ontology_term_id'),
        'assay_ontology_term_id':             get_all_unique('assay_ontology_term_id'),
        'cell_type_ontology_term_id':         get_all_unique('cell_type_ontology_term_id'),
        'disease_ontology_term_id':           get_all_unique('disease_ontology_term_id'),
        'development_stage_ontology_term_id': get_all_unique('development_stage_ontology_term_id'),
        'sex_ontology_term_id':               get_all_unique('sex_ontology_term_id'),
        'is_primary_data':                    most_common('is_primary_data'),
        'donor_id_count':                     donor_count,
        'tissue_ontology_summary':            tissue_summary,
        'assay_ontology_summary':             assay_summary,
        'cell_type_ontology_summary':         cell_type_summary,
        'disease_ontology_summary':           disease_summary,
        'development_stage_summary':          dev_stage_summary,
        'sex_ontology_summary':               sex_summary,
    }


def count_normal_cells_single(dataset_id, uberon_ids, min_age):
    """
    Query Census for one dataset, apply server-side filters, count normal adult cells.

    Args:
        dataset_id: CellxGene dataset UUID
        uberon_ids: set of UBERON obo_ids from resolve_uberon step
        min_age:    minimum age for adult cell filtering

    Returns:
        dict with normal_cell_count and metadata, or None on failure
    """
    import cellxgene_census

    # Build server-side filter - push everything possible into the query
    tissue_ids_str = ", ".join(f"'{t}'" for t in sorted(uberon_ids))
    obs_filter = (
        f"dataset_id == '{dataset_id}' "
        f"and tissue_ontology_term_id in [{tissue_ids_str}] "
        f"and is_primary_data == True "
        f"and disease == 'normal'"
    )

    print(f"  Querying Census (server-side filtered)...")

    with cellxgene_census.open_soma(census_version="latest") as census:
        adata = cellxgene_census.get_anndata(
            census=census,
            organism="Homo sapiens",
            obs_value_filter=obs_filter,
            obs_column_names=[
                "tissue",
                "tissue_ontology_term_id",
                "disease",
                "disease_ontology_term_id",
                "development_stage",
                "development_stage_ontology_term_id",
                "assay_ontology_term_id",
                "cell_type_ontology_term_id",
                "sex_ontology_term_id",
                "is_primary_data",
                "donor_id",
                "suspension_type"
            ]
        )

    if adata is None or adata.n_obs == 0:
        print(f"  Census returned 0 cells after server-side filters")
        return {
            'normal_cell_count': 0,
            'total_count':       0,
            'adult_count':       0,
            **extract_metadata(pd.DataFrame())
        }

    obs_df = adata.obs
    print(f"  Census returned {len(obs_df):,} cells (tissue + primary + normal filtered)")

    # Capture metadata before age filter
    metadata    = extract_metadata(obs_df)

    # Age filter (client-side - not supported in Census query)
    adult_df    = filter_adult_cells(obs_df, min_age)
    adult_count = len(adult_df)
    print(f"  After age filter (>= {min_age}): {adult_count:,} cells")

    return {
        'normal_cell_count': adult_count,
        'total_count':       len(obs_df),
        'adult_count':       adult_count,
        **metadata
    }


def write_result(result, dataset_id, first_author, year, journal, output_csv):
    """Write single-row result CSV."""
    row = {
        'dataset_id':       dataset_id,
        'first_author':     first_author,
        'year':             year,
        'journal':          journal,
        'normal_cell_count': result['normal_cell_count'],
        'total_count':      result['total_count'],
        'adult_count':      result['adult_count'],
        **{k: v for k, v in result.items()
           if k not in ('normal_cell_count', 'total_count', 'adult_count')}
    }
    pd.DataFrame([row]).to_csv(output_csv, index=False)
    print(f"  Saved: {output_csv}")


def write_empty_result(dataset_id, first_author, year, journal, output_csv, reason=""):
    """Write zero-count row so Nextflow collect still works."""
    row = {
        'dataset_id':        dataset_id,
        'first_author':      first_author,
        'year':              year,
        'journal':           journal,
        'normal_cell_count': 0,
        'total_count':       0,
        'adult_count':       0,
        'error':             reason,
    }
    pd.DataFrame([row]).to_csv(output_csv, index=False)
    print(f"  Saved empty result: {output_csv} ({reason})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count normal cells for a single dataset via CellxGene Census"
    )
    parser.add_argument('--dataset-id',   required=True)
    parser.add_argument('--uberon',       required=True,
                        help='UBERON JSON from 0_resolve_uberon.py')
    parser.add_argument('--min-age',      type=int, default=15)
    parser.add_argument('--first-author', default='')
    parser.add_argument('--year',         default='')
    parser.add_argument('--journal',      default='')
    parser.add_argument('--output',       required=True)

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Dataset : {args.dataset_id}")
    print(f"Author  : {args.first_author} ({args.year}) - {args.journal}")
    print(f"UBERON  : {args.uberon}")
    print(f"Min age : {args.min_age}")
    print(f"{'='*60}")

    # Load UBERON IDs
    with open(args.uberon) as f:
        uberon_data = json.load(f)
    uberon_ids = set(uberon_data["obo_ids"])
    print(f"  UBERON IDs loaded: {len(uberon_ids):,}")

    try:
        import cellxgene_census
    except ImportError:
        print("ERROR: cellxgene_census not installed")
        write_empty_result(args.dataset_id, args.first_author, args.year,
                           args.journal, args.output, "cellxgene_census not installed")
        sys.exit(1)

    try:
        result = count_normal_cells_single(args.dataset_id, uberon_ids, args.min_age)
        write_result(result, args.dataset_id, args.first_author,
                     args.year, args.journal, args.output)
        print(f"\nResult: {result['normal_cell_count']:,} normal cells")

    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        print(traceback.format_exc())
        write_empty_result(args.dataset_id, args.first_author, args.year,
                           args.journal, args.output, str(e))
        sys.exit(1)
