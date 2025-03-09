nextflow.enable.dsl = 2

include { fetchCellxgene } from './fetch_cellxgene.nf'
include { parseCollections } from './parse_collections.nf'
include { computeSilhouette } from './compute_silhouette.nf'

workflow {
    collections_json_file = fetchCellxgene()
    datasets_json_file = parseCollections(collections_json_file)
    
    // Compute silhouette scores
    results = computeSilhouette(datasets_json_file)

    // Extract named outputs
    silhouette_scores = results.silhouette_scores
    collection_scores = results.collection_scores

    // Print output paths
    silhouette_scores.view { file -> 
        println "✅ Silhouette scores saved at: ${launchDir}/results/silhouette_scores.json"
    }

    collection_scores.view { dir -> 
        println "📂 Per-collection scores saved in: ${launchDir}/results/collections/"
    }
}

