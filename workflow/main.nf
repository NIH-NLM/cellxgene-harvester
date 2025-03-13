params.datadir           = "data"
params.outdir            = "results"
params.test_mode         = false
params.collection_info   = "collections_info.json"
params.collections_split = "collections"
params.datasets_split    = "datasets"
params.final_report_pdf  = "final_report.pdf"
params.final_report_html = "final_report.html"

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

    // Step 7: Generate Plots for each cluster for each dataset
    final_plots = generatePlots(scores_csv).flatten()

    // Step 8: Merge Results for final report
    final_report = mergeResults(final_plots).flatten())

    final_report.view()
}

