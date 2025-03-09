nextflow.enable.dsl = 2

include { fetchCellxgene } from './fetch_cellxgene.nf'
include { computeSilhouette } from './compute_silhouette.nf'
include { mergeResults } from './merge_results.nf'

workflow {
    // Step 1: Fetch collections (outputs collections_info.json)
    collections_channel = fetchCellxgene()

    // Debug print collections_channel content
    collections_channel.view { collection_data -> 
        println "🔹 Collection Data: ${collection_data}"
    }

    // Step 2: Extract datasets from collections
    dataset_channel = collections_channel
        .map { collection_data -> 
            println "🔹 Extracting datasets from: ${collection_data}"  // Debug
            return collection_data.datasets
        }
        .flatten()

    // Step 3: Compute silhouette scores per dataset
    processed_datasets_channel = computeSilhouette(dataset_channel)

    // Step 4: Merge all processed dataset results
    mergeResults(processed_datasets_channel)
}
