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
    filter_datasets              - Step 4:  Filter by UBERON labels and quality criteria
    count_normal_cells           - Step 5:  Count normal adult cells via Census (sequential)
    count_normal_cells_single    - Step 5:  Count normal cells for one dataset (Nextflow scatter)
    final_cleanup                - Step 6:  Remove datasets with 0 normal cells

Utilities:
    check_uberon                 - Interactive UBERON term lookup via OLS4 API
    check_census_schema          - Inspect CellxGene Census column schemas and values
"""

__version__ = "1.0.0"
__author__  = "Anne Deslattes Mays"
__license__ = "MIT"
