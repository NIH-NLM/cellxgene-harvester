params.datadir = "data"
params.outdir = "results"
params.test_mode = false
params.collection_info = "collections_info.json"

// Ensure output directories exist
include { makeDirs } from './makeDirs.nf'
include { fetchCollections } from './fetchCollections.nf'
include { splitCollections } from './splitCollections.nf'
include { fetchDatasets } from './fetchDatasets.nf'
include { splitDatasets } from './splitDatasets.nf'
include { computeSilhouette } from './computeSilhouette.nf'
include { mergeResults } from './mergeResults.nf'

// Define Workflow Execution Order
workflow {

    // Step 1: Create directories
    makeDirs()

    // Step 2: Fetch Collections
    collections_json = fetchCollections(params.collection_info)

    // Step 3: Split Collections (Creates separate JSON files per collection)
    collection_jsons = splitCollections(collections_json).flatten()

    // Step 4: Fetch Datasets for each Collection (Parallel)
    dataset_jsons = fetchDatasets(collection_jsons, params.test_mode).flatten()

    // Step 5: Split Datasets (Creates individual dataset JSONs)
    split_datasets_jsons = splitDatasets(dataset_jsons).flatten()

    // Step 6: Compute Silhouette Scores per dataset
    scores_csv = computeSilhouette(split_datasets_jsons).flatten()

    // Step 7: Merge Results for final report
    final_report = mergeResults(scores_csv)

    // Print outputs
    scores_csv.view()
    final_report.view()
}

