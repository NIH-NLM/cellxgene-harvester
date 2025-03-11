// Define base directories
params.collections_filename = "collections_info.json"
params.datadir              = "data"
params.final_report_pdf     = "final_report.pdf"
params.final_report_html    = "final_report.html"
params.outdir               = "results"
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
include { computeSilhouette } from './computeSilhouette.nf'
include { fetchCollections  } from './fetchCollections.nf'
include { fetchDatasets     } from './fetchDatasets.nf'
include { generatePlots     } from './generatePlots.nf'
include { mergeResults      } from './mergeResults.nf'

// Define Workflow Execution Order
workflow {
    // Step 0: Ensure directories exist
    makeDirs()

    // Step 1: Fetch collections (single process)
    collections_json = fetchCollections(params.collections_filename)

    // Step 2: Split collections into individual JSONs (fan-out)
    collection_jsons = collections_json.splitJson(path: '.')

    // Step 3: Split each collection into individual datasets (fan-out)
    dataset_info_jsons = collection_jsons.splitJson(path: 'datasets')

    // Step 4: Fetch datasets in parallel (fan-out on dataset level)
    dataset_jsons = fetchDatasets(dataset_info_jsons, test_mode)

    // Step 5: Compute silhouette scores in parallel for each dataset
    scores_csvs = computeSilhouette(dataset_jsons)

    // Step 6: Generate per-dataset plots in parallel
    dataset_plots = generatePlots(scores_csvs)

    // Step 7: Merge final dataset-level results into a report (AFTER all datasets are done)
    final_report = mergeResults(dataset_plots, params.final_report_pdf, params.final_report_html)
}
