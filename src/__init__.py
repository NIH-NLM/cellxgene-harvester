"""
cellxgene-harvester
===================

Harvest, filter, and count normal cells from CellxGene Census
using UBERON ontology-based tissue filtering.

Pipeline modules:
    logger                       - Structured logging for all pipeline steps
    resolve_uberon               - Resolve tissue labels to UBERON ontology terms
    fetch_collections            - Fetch public collections from CellxGene API
    generate_metadata            - Generate base metadata CSV
    append_details               - Append dataset details (titles, cell counts, URLs)
    filter_datasets              - Filter by UBERON labels and quality criteria
    count_normal_cells           - Count normal adult cells via Census (sequential)
    count_normal_cells_single    - Count normal cells for one dataset (Nextflow scatter)
    final_cleanup                - Remove datasets with 0 normal cells

Utilities:
    check_uberon                 - Interactive UBERON term lookup via OLS4 API
    check_census_schema          - Inspect CellxGene Census column schemas and values
"""

__version__ = "1.0.0"
__author__  = "Anne Deslattes Mays"
__license__ = "MIT"
