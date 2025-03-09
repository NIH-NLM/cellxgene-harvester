nextflow.enable.dsl = 2

include { fetchCollections } from './pull_cellxgene.nf'
include { processDataset } from './compute_silhouette.nf'
include { mergeResults } from './merge_results.nf'

workflow {
    // Step 1: Fetch collections and dataset metadata
    collections = fetchCollections(params.test_mode)

    // Step 2: Extract datasets (Fan-Out at Dataset Level)
    dataset_channel = collections
        .mapMany { collection -> 
            collection.datasets.collect { dataset ->
                dataset + [
                    'collection_id': collection.collection_id,
                    'collection_version_id': collection.collection_version_id,
                    'collection_url': collection.collection_url
                ]
            }
        }

    // Step 3: Convert dataset objects to JSON strings
    dataset_json_channel = dataset_channel
        .map { dataset -> groovy.json.JsonOutput.toJson(dataset) }

    // Step 4: Fan-Out datasets into processDataset (Parallel Execution)
    results = processDataset(dataset_json_channel)

    // Step 5: Merge results (Fan-In)
    mergeResults(results)
}

