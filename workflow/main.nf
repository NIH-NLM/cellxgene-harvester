params.datadir = "data"
params.outdir = "results"
params.collection_info = "${params.datadir}/collections_info.json"

// Ensure output directories exist
process makeDirs {
    tag 'create_directories'
    
    output:
        path params.datadir, emit: datadir
        path params.outdir, emit: outdir

    script:
    """
    mkdir -p ${params.datadir}
    mkdir -p ${params.outdir}
    mkdir -p ${params.datadir}/collections_split
    mkdir -p ${params.datadir}/datasets_split
    """
}

// Import Workflow Modules
include { fetchCollections  } from './fetchCollections.nf'
include { splitCollections  } from './splitCollections.nf'
include { fetchDatasets     } from './fetchDatasets.nf'
include { splitDatasets     } from './splitDatasets.nf'
include { computeSilhouette } from './computeSilhouette.nf'
include { generatePlots     } from './generatePlots.nf'

// Define Workflow Execution Order
workflow {
    // Step 1: Ensure directories exist
    makeDirs()

    // Step 2: Fetch Collections (Runs Once)
    collections_json = fetchCollections()

    // Step 3: Split Collections into separate JSON files (Fan-out)
    collection_jsons = splitCollections(collections_json)

    // Step 4: Fetch Datasets for each Collection (Fan-out)
    dataset_jsons = fetchDatasets(collection_jsons, test_mode)

    // Step 5: Split Datasets into individual JSONs (Fan-out)
    split_datasets_jsons = splitDatasets(dataset_jsons)

    // Step 6: Compute Silhouette Scores (Runs in Parallel for Each Dataset)
    scores_csv = computeSilhouette(split_datasets_jsons)

    // Step 7: Generate Final Plots (Runs Once)
    generatePlots(scores_csv)
}

