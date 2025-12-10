params.datadir           = "data"
params.outdir            = "results"
params.test_mode         = false
params.collection_info   = "collections_info.json"
params.collections_split = "collections"
params.datasets_split    = "datasets"
params.final_report_pdf  = "final_report.pdf"
params.final_report_html = "final_report.html"

// add all the process steps
include { computeSilhouette } from './computeSilhouette.nf'
include { fetchCollections }  from './fetchCollections.nf'
include { fetchDatasets }     from './fetchDatasets.nf'
include { generatePlots }     from './generatePlots.nf'
include { mergeResults }      from './mergeResults.nf'
include { splitCollections }  from './splitCollections.nf'
include { splitDatasets }     from './splitDatasets.nf'

// Define Workflow Execution Order

workflow {

    // **Step 1: Fetch collections (single file)**
    collection_json = fetchCollections(params.collection_info)

    // **Step 2: Split collections into multiple JSONs**
    splitCollections(collection_json)
    collections_json = Channel.fromPath("${params.datadir}/${params.collections_split}/collection_*.json")

    // **Step 3: Fetch dataset metadata for each collection**
    fetchDatasets(collections_json, params.test_mode)
    datasets_json = Channel.fromPath("${params.datadir}/${params.datasets_split}/dataset_*.json")
  
    // **Step 4: Split datasets into individual dataset versions**
    splitDatasets(datasets_json)
    dataset_versions_json = Channel.fromPath("${params.datadir}/${params.datasets_split}/dataset_version_*.json")

    // **Step 5: Compute silhouette scores for each dataset version**
    scores_csvs = computeSilhouette(dataset_versions_json)

    // **Step 6: Generate plots**
    plots = generatePlots(scores_csvs)

    // **Step 7: Merge results into a final report**
    mergeResults(plots, params.final_report_pdf, params.final_report_html)
}
