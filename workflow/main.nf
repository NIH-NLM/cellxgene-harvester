// Define base directories
params.datadir              = "data"
params.outdir               = "results"
params.collections_filename = "collections_info.json"
params.test_mode            = false

// Ensure output directories exist
// Ensure output directories exist inside the workflow, not inside a process
process makeDirs {
    tag 'create_directories'
    
    output:
        path params.datadir, emit: datadir
        path params.outdir, emit: outdir

    script:
    """
    mkdir -p data
    mkdir -p results
    """
}

// Import Workflow Modules
include { fetchCollections  } from './fetchCollections.nf'
include { parseCollections  } from './parseCollections.nf'
include { fetchDatasets     } from './fetchDatasets.nf'
include { computeSilhouette } from './computeSilhouette.nf'
include { generatePlots     } from './generatePlots.nf'

// Define Workflow Execution Order
workflow {
    // Step 1: Ensure directories exist
    makeDirs()

    // Step 2: Fetch Collections (Runs Once)
    collections_json = fetchCollections(params.collections_filename)

    // Step 3: Parse Collections to Extract Dataset IDs (Runs Once)
    datasets_info_json = parseCollections(collections_json, params.test_mode)

    // Step 4: Fetch Datasets (Runs in Parallel for Each Dataset)
    dataset_jsons = fetchDatasets(datasets_info_json, params.test_mode)

    // Step 5: Compute Silhouette Scores (Runs in Parallel for Each Dataset)
    scores_csv = computeSilhouette(dataset_jsons)

    // Step 6: Generate Final Plots (Runs Once)
    generatePlots(scores_csv)
}
