nextflow.enable.dsl = 2

include { fetchCellxgene } from './fetch_cellxgene.nf'
include { parseCollections } from './parse_collections.nf'
include { computeSilhouette } from './compute_silhouette.nf'

workflow {
    collections_json_file = fetchCellxgene()
    datasets_json_file = parseCollections(collections_json_file)
    tuple(silhouette_scores, collection_scores) = computeSilhouette(datasets_json_file)

    silhouette_scores.view { result_file -> 
        println "✅ Silhouette scores saved at: ${launchDir}/results/silhouette_scores.json"
    }

    collection_scores.view { result_dir -> 
        println "📂 Per-collection scores saved in directory: ${launchDir}/results/collections/"
    }
}

