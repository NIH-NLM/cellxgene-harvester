/**
 * append_dataset_details.nf
 *
 * Step 3: Enrich each dataset row with title, cell count, and H5AD URL.
 *
 * Makes one CellxGene Curation API call per dataset to fetch:
 *   dataset_title     — human-readable title
 *   total_cell_count  — all cells before filtering
 *   h5ad_url          — direct download URL for the .h5ad file
 *   explorer_url      — CellxGene browser link
 *
 * This step is slow (~10-20 min for all datasets) due to rate limiting but
 * stable between CellxGene releases.  Cache aggressively with -resume.
 *
 * NOTE: H5AD files are NOT downloaded here.  URLs are recorded for Step 5
 * (count_normal_cells_single) which downloads each file on demand.
 *
 * @param datasets_csv  all_datasets.csv from generate_metadata
 *
 * @output complete_csv  all_datasets_complete.csv — enriched dataset table
 */
process APPEND_DATASET_DETAILS {

    label 'process_medium'

    container 'ghcr.io/nih-nlm/cellxgene-harvester:latest'

    input:
    path datasets_csv

    output:
    path "all_datasets_complete.csv", emit: complete_csv

    script:
    """
    mkdir -p data
    cp ${datasets_csv} data/all_datasets.csv
    cellxgene-harvester append-details
    mv data/all_datasets_complete.csv .
    """
}
