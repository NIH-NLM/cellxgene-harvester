nextflow.enable.dsl = 2

// Include separate workflow steps
include { fetchDatasets } from './fetch_cellxgene.nf'
include { parseCollections } from './parse_collections.nf'
include { computeSilhouette } from './compute_silhouette.nf'

workflow {
    // Fetch dataset (in test mode, only fetches smallest dataset)
    datasets_json_file = fetchDatasets(params.test_mode)

    // Extract dataset metadata
    parsed_datasets = parseCollections(datasets_json_file)

    // Compute silhouette scores (output has two named outputs)
    results = computeSilhouette(parsed_datasets)

    // Access each output separately using emit names
    results.silhouette_scores.view { file -> 
        println "✅ Silhouette scores saved at: ${launchDir}/results/silhouette_scores.json"
    }

    results.collection_scores.view { dir -> 
        println "📂 Per-collection scores saved in directory: ${launchDir}/results/collections/"
    }
}

