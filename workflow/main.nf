nextflow.enable.dsl = 2

include { fetchCellxgene } from './fetch_cellxgene.nf'
include { parseCollections } from './parse_collections.nf'
include { computeSilhouette } from './compute_silhouette.nf'
include { mergeResults } from './merge_results.nf'

workflow {
    // Step 1: Fetch collections (outputs collections_info.json)
    collections_json_file = fetchCellxgene()

    // Step 2: Parse collections JSON file to extract datasets
    datasets_json_file = parseCollections(collections_json_file)

    // Step 3: Compute silhouette scores per dataset
    processed_datasets = computeSilhouette(datasets_json_file)

    // Step 4: Merge all processed dataset results
    mergeResults(processed_datasets)
}

