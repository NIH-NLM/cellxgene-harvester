nextflow.enable.dsl = 2

include { fetchCollections } from './pull_cellxgene.nf'
include { processDataset } from './compute_silhouette.nf'
include { mergeResults } from './merge_results.nf'

workflow {
    // Step 1: Fetch all collections (Fan-Out at Collection Level)
    collections = fetchCollections(params.test_mode)

    // Step 2: Extract datasets from collections & Fan-Out at Dataset Level
    dataset_channel = Channel
        .from(collections)
        .map { collection -> collection.datasets }  // Extract dataset lists from each collection
        .flatten()  // Convert list of dataset lists into a single list of datasets

    // Step 3: Fan-Out datasets into processDataset (Parallel Execution)
    results = processDataset(dataset_channel)  // Each dataset runs as an independent Nextflow task

    // Step 4: Merge results (Fan-In)
    mergeResults(results)
}

