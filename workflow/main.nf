params.datadir           = "data"
params.outdir            = "results"
params.collections_split = "collections"
params.datasets_split    = "datasets"
params.test_mode         = false
params.collection_info   = "${params.datadir}/collections_info.json"

// Import Workflow Modules
include { makeDirs          } from './makeDirs.nf'
include { fetchCollections  } from './fetchCollections.nf'
include { splitCollections  } from './splitCollections.nf'
include { fetchDatasets     } from './fetchDatasets.nf'
include { splitDatasets     } from './splitDatasets.nf'
include { computeSilhouette } from './computeSilhouette.nf'
include { generatePlots     } from './generatePlots.nf'

// Define input channels
Channel.fromPath("${params.datadir}/${params.collection_info}") \
    .set { collections_json }

workflow {
    // Step 1: Ensure directories exist
    makeDirs()

    // Step 2: Fetch Collections (Runs Once)
    collections_json = fetchCollections("${params.collection_info}")

    // Step 3: Split Collections into separate JSON files (Fan-out)
    collection_jsons = splitCollections(collections_json).flatten()

    // Step 4: Fetch Datasets for each Collection (Fan-out)
    dataset_jsons = fetchDatasets(collection_jsons, "${params.test_mode}").flatten()

    // Step 5: Split Datasets into individual JSONs (Fan-out)
    split_datasets_jsons = splitDatasets(dataset_jsons).flatten()

    // Step 6: Compute Silhouette Scores (Runs in Parallel for Each Dataset)
    scores_csv = computeSilhouette(split_datasets_jsons).flatten()

    // Step 7: Merge Results
    merged_results = mergeResults(scores_csv).flatten()

    // Step 8: Generate Final Plots
    generatePlots(merged_results)
}
