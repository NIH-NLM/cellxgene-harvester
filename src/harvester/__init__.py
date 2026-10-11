"""
cellxgene-harvester
===================

Harvest, filter, and count normal cells of the CellxGene datasets
using ontology-based filtering (UBERON, PATO/MONDO, HsapDv). The cells are read from the h5ad
file of each dataset; the CellxGene Census is another source (--source census).

Pipeline modules:
    logger                       - Structured logging for all pipeline steps
    resolve_uberon               - Step 0a: Resolve tissue labels to UBERON ontology terms
    resolve_disease              - Step 0b: Resolve disease labels to PATO/MONDO ontology terms
    resolve_hsapdv               - Step 0c: Resolve HsapDv age terms for a minimum age threshold
    fetch_collections            - Step 1:  Fetch public collections from CellxGene API
    generate_metadata            - Step 2:  Generate base metadata CSV
    append_dataset_details       - Step 3:  Append dataset details (titles, cell counts, URLs)
    filter_datasets              - Step 4:  Filter datasets, write one JSON file for each one kept
    count_normal_cells           - Step 5:  Count source and filtered cells from the h5ad files (whole folder)
    count_normal_cells_single    - Step 5:  Count source and filtered cells for one dataset file
    final_cleanup                - Step 6:  Delete the files of datasets with 0 filtered cells
    export_datasets_csv          - Step 7:  Write the datasets CSV that sc-nsforest-qc-nf reads
    build_gene_mapping           - Utility: Build the gene id to gene name table of a GENCODE release

Shared by the steps:
    io_utils                     - Check and write the JSON files; the schema version to GENCODE release table
    snapshot                     - The provenance file of the CellxGene API snapshot (Steps 1 to 3)
    ontology_files               - Read the resolve-uberon / -disease / -hsapdv files
    records                      - Build the JSON record of one dataset

Utilities:
    check_uberon                 - Interactive UBERON term lookup via OLS4 API
    check_census_schema          - Inspect CellxGene Census column schemas and values
"""

__version__ = "1.0.0"
__author__  = "Anne Deslattes Mays"
__license__ = "MIT"
