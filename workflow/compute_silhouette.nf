nextflow.enable.dsl = 2

include { fetchCollections } from './pull_cellxgene.nf'
include { processDataset } from './compute_silhouette.nf'
include { mergeResults } from './merge_results.nf'

workflow {
    // Step 1: Fetch all collections (Fan-Out at Collection Level)
    collections = fetchCollections(params.test_mode)

    // Step 2: Extract datasets from collections & Create a Nextflow Channel
    dataset_channel = Channel
        .from(collections)
        .map { it.datasets }
        .flatten()

    // Step 3: Fan-Out datasets into processDataset (Parallel Execution)
    results = processDataset(dataset_channel)  // Pass dataset channel into the process

    // Step 4: Merge results (Fan-In)
    mergeResults(results)
}

