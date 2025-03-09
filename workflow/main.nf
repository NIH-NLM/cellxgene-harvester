nextflow.enable.dsl = 2

include { fetchDatasets } from './fetch_cellxgene.nf'
include { parseCollections } from './parse_collections.nf'
include { computeSilhouette } from './compute_silhouette.nf'

workflow {
    // Pass test_mode to the fetch process
    datasets_json_file = fetchDatasets(params.test_mode)

    // Extract datasets from JSON
    parsed_datasets = parseCollections(datasets_json_file)

    // Compute silhouette scores
    silhouette_scores = computeSilhouette(parsed_datasets)

    // Print result
    silhouette_scores.view { file -> 
        println "✅ Silhouette scores saved at: ${launchDir}/results/silhouette_scores.json"
    }

    collection_scores.view { dir -> 
        println "📂 Per-collection scores saved in: ${launchDir}/results/collections/"
    }
}

