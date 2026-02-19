#!/usr/bin/env python3
"""
cellxgene-harvester CLI

Unified command-line interface for all pipeline steps.

Usage:
    cellxgene-harvester resolve-uberon kidney
    cellxgene-harvester fetch-collections
    cellxgene-harvester generate-metadata
    cellxgene-harvester append-details
    cellxgene-harvester filter-datasets --input ... --output ...
    cellxgene-harvester count-normal-cells --input ... --uberon ...
    cellxgene-harvester final-cleanup --input ...
"""

import os
import typer
from pathlib import Path
from typing import List, Optional
from harvester.logger import setup_logger, log_command, log_finish

# Import the modules directly - no aliases
from harvester import (
    resolve_uberon,
    fetch_collections,
    generate_metadata,
    append_dataset_details,
    filter_datasets,
    count_normal_cells,
    final_cleanup
)


app = typer.Typer(
    name="cellxgene-harvester",
    help="Harvest, filter, and count normal cells from CellxGene Census using UBERON ontology"
)


@app.command(name="resolve-uberon")
def resolve_uberon_command(
    queries: List[str] = typer.Argument(..., help="Tissue label(s) or UBERON ID(s)"),
    output_prefix: Optional[str] = typer.Option(None, help="Output file prefix"),
    multi: bool = typer.Option(False, help="Combine multiple queries into single file")
):
    """Step 0: Resolve UBERON tissue terms via OLS4 API"""
    resolve_uberon.run_resolve_uberon(queries, output_prefix, multi)


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
    input: Path = typer.Option("data/all_datasets_complete.csv", help="Input CSV"),
    output: Path = typer.Option(..., help="Output CSV path"),
    uberon: Optional[Path] = typer.Option(None, help="UBERON JSON"),
    organism: Optional[str] = typer.Option(None, help="Filter by organism"),
    no_preprints: bool = typer.Option(False, help="Exclude preprints"),
    exclude_cancer: bool = typer.Option(False, help="Exclude cancer"),
    exclude_spatial: bool = typer.Option(False, help="Exclude spatial"),
    disease: Optional[str] = typer.Option(None, help="Filter by disease")
):
    """Step 4: Filter datasets using UBERON labels"""
    filter_datasets.run_filter_datasets(
        input_csv=str(input),
        output_csv=str(output),
        uberon_json=str(uberon) if uberon else None,
        organism=organism,
        no_preprints=no_preprints,
        exclude_cancer=exclude_cancer,
        exclude_spatial=exclude_spatial,
        disease=disease
    )


@app.command(name="count-normal-cells")
def count_normal_cells_command(
    input: Path = typer.Option(..., help="Input CSV"),
    uberon: Path = typer.Option(..., help="UBERON JSON"),
    min_age: int = typer.Option(15, help="Minimum age for adult filtering")
):
    """Step 5: Count normal cells from CellxGene Census"""
    count_normal_cells.run_count_normal_cells(
        input_csv=str(input),
        uberon_json=str(uberon),
        min_age=min_age
    )


@app.command(name="final-cleanup")
def final_cleanup_command(
    input: Path = typer.Argument(..., help="Input CSV with normal_cell_count")
):
    """Step 6: Remove datasets with 0 normal cells"""
    final_cleanup.run_final_cleanup(str(input))


def main():
    app()


if __name__ == "__main__":
    app()
