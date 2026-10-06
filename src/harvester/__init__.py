"""
cellxgene-harvester
===================

Harvest, filter, and count normal cells from CellxGene Census
using ontology-based filtering (UBERON, PATO/MONDO, HsapDv).

Pipeline modules:
    logger                       - Structured logging for all pipeline steps
    resolve_uberon               - Step 0a: Resolve tissue labels to UBERON ontology terms
    resolve_disease              - Step 0b: Resolve disease labels to PATO/MONDO ontology terms
    resolve_hsapdv               - Step 0c: Resolve HsapDv age terms for a minimum age threshold
    fetch_collections            - Step 1:  Fetch public collections from CellxGene API
    generate_metadata            - Step 2:  Generate base metadata CSV
    append_dataset_details       - Step 3:  Append dataset details (titles, cell counts, URLs)
    filter_datasets              - Step 4:  Filter datasets, write one JSON file for each one kept
    count_normal_cells           - Step 5:  Count source and filtered cells via Census (whole folder)
    count_normal_cells_single    - Step 5:  Count source and filtered cells for one dataset file
    final_cleanup                - Step 6:  Delete the files of datasets with 0 filtered cells
    export_datasets_csv          - Step 7:  Write the datasets CSV that sc-nsforest-qc-nf reads

Shared by Steps 4 to 6:
    io_utils                     - Check and write the JSON files
    ontology_files               - Read the resolve-uberon / -disease / -hsapdv files
    records                      - Build the JSON record of one dataset

Utilities:
    check_uberon                 - Interactive UBERON term lookup via OLS4 API
    check_census_schema          - Inspect CellxGene Census column schemas and values
"""

__version__ = "1.0.0"
__author__  = "Anne Deslattes Mays"
__license__ = "MIT"
