nextflow.enable.dsl = 2

include { fetchCollections } from './pull_cellxgene.nf'
include { processDataset } from './compute_silhouette.nf'
include { mergeResults } from './merge_results.nf'

workflow {
    // Step 1: Fetch all collections (Fan-Out at Collection Level)
    collections = fetchCollections(params.test_mode)

    // Step 2: Extract datasets & Fan-Out at Dataset Level
    datasets = collections.flatten().datasets.flatten() 

    results = processDataset(datasets) // Explicitly pass datasets to processDataset

    // Step 3: Merge results (Fan-In)
    mergeResults(results)
}

