#!/usr/bin/env python3
"""
cellxgene-harvester CLI

Unified command-line interface for all pipeline steps.

Usage:
    cellxgene-harvester [--run-dir 2026-08-03-run] resolve-uberon kidney
    cellxgene-harvester resolve-disease normal
    cellxgene-harvester resolve-hsapdv --min-age 15
    cellxgene-harvester resolve-assay "spatial transcriptomics"
    cellxgene-harvester fetch-collections
    cellxgene-harvester generate-metadata
    cellxgene-harvester append-details
    cellxgene-harvester filter-datasets 2026-08-03-run/all_datasets_complete.csv --output FOLDER --uberon ... --disease ... --hsapdv ...
    cellxgene-harvester count-normal-cells FOLDER --uberon ... --disease ... --hsapdv ... [--exclude-assay ...] [--census-version ...]
    cellxgene-harvester final-cleanup FOLDER
    cellxgene-harvester export-datasets-csv FOLDER --output datasets.csv
"""

import os
import typer
from pathlib import Path
from typing import List, Optional
from harvester.logger import setup_logger, log_command, log_finish
from harvester.run_dir import ENV_NAME as RUN_DIR_ENV

# Import the modules directly - no aliases
from harvester import (
    resolve_uberon,
    resolve_disease,
    resolve_hsapdv,
    resolve_assay,
    fetch_collections,
    generate_metadata,
    append_dataset_details,
    filter_datasets,
    count_normal_cells,
    final_cleanup,
    export_datasets_csv,
)


app = typer.Typer(
    name="cellxgene-harvester",
    help="Harvest, filter, and count normal cells from CellxGene Census using ontology IDs"
)


@app.callback()
def options(
    run_folder: Optional[Path] = typer.Option(
        None, "--run-dir",
        help="Folder for the files of this run (default: <today>-run, for example 2026-08-03-run)"),
):
    """cellxgene-harvester: each run keeps its files in one folder named by its date."""
    if run_folder:
        os.environ[RUN_DIR_ENV] = str(run_folder)


@app.command(name="resolve-uberon")
def resolve_uberon_command(
    queries: List[str] = typer.Argument(..., help="Tissue label(s) or UBERON ID(s)"),
    output_prefix: Optional[str] = typer.Option(None, help="Output file prefix"),
    multi: bool = typer.Option(False, help="Combine multiple queries into single file")
):
    """Step 0a: Resolve UBERON tissue terms via OLS4 API"""
    resolve_uberon.run_resolve_uberon(queries, output_prefix, multi)


@app.command(name="resolve-disease")
def resolve_disease_command(
    queries: List[str] = typer.Argument(..., help="Disease label(s) or ontology ID(s) e.g. 'normal'"),
    output_prefix: Optional[str] = typer.Option(None, help="Output file prefix"),
):
    """Step 0b: Resolve disease terms (PATO/MONDO) via OLS4 API"""
    resolve_disease.run_resolve_disease(queries, output_prefix)


@app.command(name="resolve-hsapdv")
def resolve_hsapdv_command(
    min_age: float = typer.Option(..., help="Minimum age in years (e.g. 15)"),
    output_prefix: Optional[str] = typer.Option(None, help="Output file prefix"),
    obo_url: str = typer.Option(
        resolve_hsapdv.HSAPDV_OBO_URL,
        help="HsapDv OBO URL (default: OBO Foundry)"
    ),
):
    """Step 0c: Resolve HsapDv development stage terms for a minimum age threshold"""
    resolve_hsapdv.run_resolve_hsapdv(min_age, output_prefix, obo_url)


@app.command(name="resolve-assay")
def resolve_assay_command(
    queries: List[str] = typer.Argument(..., help="Assay (technique) label(s) or EFO ID(s), e.g. 'spatial transcriptomics'"),
    output_prefix: Optional[str] = typer.Option(None, help="Output file prefix"),
):
    """Step 0d: Resolve assay (technique) terms via OLS4 (EFO), for --exclude-assay in step 5"""
    resolve_assay.run_resolve_assay(queries, output_prefix)


@app.command(name="fetch-collections")
def fetch_collections_command():
    """Step 1: Fetch all collections from CellxGene API"""
    fetch_collections.run_fetch_collections()


@app.command(name="generate-metadata")
def generate_metadata_command():
    """Step 2: Generate metadata CSV from collections JSON"""
    generate_metadata.run_generate_metadata()


@app.command(name="append-details")
def append_details_command():
    """Step 3: Append dataset details (titles, cell counts, URLs)"""
    append_dataset_details.run_append_details()


@app.command(name="filter-datasets")
def filter_datasets_command(
    input: Path = typer.Argument(..., help="Input CSV (all_datasets_complete.csv from append-details)"),
    output: Path = typer.Option(..., help="Output folder, one JSON file per dataset is written here"),
    uberon: Optional[Path] = typer.Option(None, help="UBERON JSON from resolve-uberon"),
    disease: Optional[Path] = typer.Option(None, help="Disease JSON from resolve-disease"),
    hsapdv: Optional[Path] = typer.Option(None, help="HsapDv JSON from resolve-hsapdv (recorded only; age is filtered in step 5)"),
    organism: Optional[str] = typer.Option(None, help="Filter by organism label"),
    no_preprints: bool = typer.Option(False, help="Exclude preprints"),
):
    """Step 4: Filter datasets using UBERON and disease ontology IDs"""
    filter_datasets.run_filter_datasets(
        input_csv=str(input),
        output_dir=str(output),
        uberon_json=str(uberon) if uberon else None,
        disease_json=str(disease) if disease else None,
        hsapdv_json=str(hsapdv) if hsapdv else None,
        organism=organism,
        no_preprints=no_preprints,
    )


@app.command(name="count-normal-cells")
def count_normal_cells_command(
    input:   Path = typer.Argument(..., help="Folder of JSON files from filter-datasets"),
    uberon:  Path = typer.Option(...,   help="UBERON JSON from resolve-uberon"),
    disease: Path = typer.Option(...,   help="Disease JSON from resolve-disease"),
    hsapdv:  Path = typer.Option(...,   help="HsapDv JSON from resolve-hsapdv --min-age N"),
    exclude_assay: Optional[Path] = typer.Option(None, "--exclude-assay", help="Assay JSON from resolve-assay: its cells are left out of the filtered counts (negative selection)"),
    census_version: str = typer.Option("latest", "--census-version", help="Census release to read (default: latest)"),
):
    """Step 5: Count source and filtered cells via CellxGene Census"""
    count_normal_cells.run_count_normal_cells(
        folder=str(input),
        uberon_json=str(uberon),
        disease_json=str(disease),
        hsapdv_json=str(hsapdv),
        exclude_assay_json=str(exclude_assay) if exclude_assay else None,
        census_version=census_version,
    )


@app.command(name="final-cleanup")
def final_cleanup_command(
    input: Path = typer.Argument(..., help="Folder of JSON files from count-normal-cells")
):
    """Step 6: Delete the files of datasets with 0 filtered cells"""
    final_cleanup.run_final_cleanup(str(input))


@app.command(name="export-datasets-csv")
def export_datasets_csv_command(
    input:  Path = typer.Argument(..., help="Folder of JSON files from final-cleanup"),
    output: Path = typer.Option(..., help="CSV file for sc-nsforest-qc-nf (--datasets_csv)"),
):
    """Step 7: Write the datasets CSV that sc-nsforest-qc-nf reads"""
    export_datasets_csv.run_export_datasets_csv(folder=str(input), output_csv=str(output))


def main():
    app()


if __name__ == "__main__":
    app()
