// Define base directories
params.datadir = "${launchDir}/data"
params.outdir = "${launchDir}/results"

// Ensure output directories exist
process makeDirs {
    output:
        path params.datadir, emit: datadir
        path params.outdir, emit: outdir

    script:
    """
    mkdir -p ${params.datadir}
    mkdir -p ${params.outdir}
    """
}

// Import Workflow Modules
include { fetchCollections  } from './workflow/fetchCellxgene.nf'
include { parseCollections  } from './workflow/parseCollections.nf'
include { fetchDatasets     } from './workflow/fetchDatasets.nf'
include { computeSilhouette } from './workflow/computeSilhouette.nf'
include { generatePlots     } from './workflow/generatePlots.nf'

// Define Workflow Execution Order
workflow {
    // Step 1: Ensure directories exist
    makeDirs()

    // Step 2: Fetch Collections (Runs Once)
    collections_json = fetchCollections(test_mode)

    // Step 3: Parse Collections to Extract Dataset IDs (Runs Once)
    datasets_info_json = parseCollections(collections_json, test_mode)

    // Step 4: Fetch Datasets (Runs in Parallel for Each Dataset)
    dataset_jsons = fetchDatasets(datasets_info_json, test_mode)

    // Step 5: Compute Silhouette Scores (Runs in Parallel for Each Dataset)
    scores_csv = computeSilhouette(dataset_jsons)

    // Step 6: Generate Final Plots (Runs Once)
    generatePlots(scores_csv)
}
