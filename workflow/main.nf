nextflow.enable.dsl = 2

// Include Nextflow processes
include { fetchCellxgene } from './fetch_cellxgene.nf'
include { parseCollections } from './parse_collections.nf'
include { computeSilhouette } from './compute_silhouette.nf'

workflow {
    // Step 1: Get the test mode flag from Nextflow parameters (default = false)
    test_mode_flag = params.test_mode ?: "false"

    // Step 2: Fetch collections data (outputs collections_info.json)
    collections_json_file = fetchCellxgene(test_mode_flag)

    // Step 3: Parse collections to extract dataset information
    datasets_json_file = parseCollections(collections_json_file)

    // Step 4: Compute silhouette scores per dataset (outputs silhouette_scores.json)
    silhouette_scores_file = computeSilhouette(datasets_json_file, test_mode_flag)

    // Step 5: Print output file for validation
    silhouette_scores_file.view()
}

