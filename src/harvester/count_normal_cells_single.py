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
import pandas as pd
from typing import Optional


def load_disease_ids(disease_json: str) -> set:
    """Load disease obo_ids from a resolve_disease JSON file."""
    with open(disease_json) as f:
        data = json.load(f)
    obo_ids = set(data["obo_ids"])
    roots   = [t["label"] for t in data["root_terms"]]
    print(f"  Disease IDs loaded  : {len(obo_ids):,}  (roots: {', '.join(roots)})")
    return obo_ids


def load_hsapdv_ages(hsapdv_json: str) -> dict:
    """Load HsapDv ID -> min_age_years mapping from resolve_hsapdv JSON."""
    with open(hsapdv_json) as f:
        data = json.load(f)
    terms  = data["terms"]
    n_ages = sum(1 for v in terms.values() if v["min_age_years"] is not None)
    print(f"  HsapDv terms with age : {n_ages:,}")
    return {term_id: v["min_age_years"] for term_id, v in terms.items()}


def filter_adult_cells(obs_df: pd.DataFrame, min_age: int,
                       hsapdv_ages: dict) -> pd.DataFrame:
    """Filter cells using development_stage_ontology_term_id resolved via HsapDv ages JSON."""
    if min_age == 0:
        return obs_df

    id_col = "development_stage_ontology_term_id"
    if id_col not in obs_df.columns:
        print(f"  WARNING: {id_col} column missing - skipping age filter")
        return obs_df

    adult_mask     = []
    cells_adult    = 0
    cells_child    = 0
    cells_prenatal = 0
    cells_unknown  = 0

    for term_id in obs_df[id_col].astype(str):
        term_id = term_id.strip()
        if term_id in ("", "nan", "None", "unknown") or term_id not in hsapdv_ages:
            adult_mask.append(False)
            cells_unknown += 1
            continue
        age = hsapdv_ages[term_id]
        if age is None:
            adult_mask.append(False)
            cells_prenatal += 1
        elif age >= min_age:
            adult_mask.append(True)
            cells_adult += 1
        else:
            adult_mask.append(False)
            cells_child += 1

    adult_df = obs_df[adult_mask]
    print(f"  Age filter (>= {min_age} yr, via HsapDv ID): "
          f"{len(obs_df):,} -> {len(adult_df):,} cells")
    print(f"    Adult: {cells_adult:,}  Child: {cells_child:,}  "
          f"Prenatal: {cells_prenatal:,}  Unknown ID: {cells_unknown:,}")
    return adult_df


def extract_metadata(obs_df: pd.DataFrame) -> dict:
    def get_most_common(col):
        if col in obs_df.columns and len(obs_df) > 0:
            vc = obs_df[col].value_counts()
            return str(vc.index[0]) if len(vc) > 0 else ''
        return ''

    def get_all_unique(col):
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
        'is_primary_data':                    get_most_common('is_primary_data'),
        'donor_id_count':                     donor_count,
        'tissue_ontology_summary':            tissue_summary,
        'assay_ontology_summary':             assay_summary,
        'cell_type_ontology_summary':         cell_type_summary,
        'disease_ontology_summary':           disease_summary,
        'development_stage_summary':          dev_stage_summary,
        'sex_ontology_summary':               sex_summary,
    }


def count_normal_cells_single(dataset_id, uberon_ids, disease_ids, hsapdv_ages, min_age):
    """
    Query Census for one dataset, apply server-side filters, count normal adult cells.

    Args:
        dataset_id:   CellxGene dataset UUID
        uberon_ids:   set of UBERON obo_ids from resolve_uberon
        disease_ids:  set of disease obo_ids from resolve_disease
        hsapdv_ages:  dict of HsapDv ID -> min_age_years from resolve_hsapdv
        min_age:      minimum age for adult cell filtering
    """
    import cellxgene_census

    tissue_ids_str  = ", ".join(f"'{t}'" for t in sorted(uberon_ids))
    disease_ids_str = ", ".join(f"'{d}'" for d in sorted(disease_ids))
    obs_filter = (
        f"dataset_id == '{dataset_id}' "
        f"and tissue_ontology_term_id in [{tissue_ids_str}] "
        f"and is_primary_data == True "
        f"and disease_ontology_term_id in [{disease_ids_str}]"
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
    adult_df    = filter_adult_cells(obs_df, min_age, hsapdv_ages)
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
                        help='UBERON JSON from resolve_uberon')
    parser.add_argument('--disease',      required=True,
                        help='Disease JSON from resolve_disease')
    parser.add_argument('--hsapdv',       required=True,
                        help='HsapDv ages JSON from resolve_hsapdv')
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
    print(f"Disease : {args.disease}")
    print(f"HsapDv  : {args.hsapdv}")
    print(f"Min age : {args.min_age}")
    print(f"{'='*60}")

    # Load ontology IDs
    with open(args.uberon) as f:
        uberon_data = json.load(f)
    uberon_ids = set(uberon_data["obo_ids"])
    print(f"  UBERON IDs loaded: {len(uberon_ids):,}")

    disease_ids = load_disease_ids(args.disease)
    hsapdv_ages = load_hsapdv_ages(args.hsapdv)

    try:
        import cellxgene_census
    except ImportError:
        print("ERROR: cellxgene_census not installed")
        write_empty_result(args.dataset_id, args.first_author, args.year,
                           args.journal, args.output, "cellxgene_census not installed")
        sys.exit(1)

    try:
        result = count_normal_cells_single(args.dataset_id, uberon_ids,
                                           disease_ids, hsapdv_ages, args.min_age)
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
