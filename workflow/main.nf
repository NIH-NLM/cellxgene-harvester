nextflow.enable.dsl = 2

include { fetchDatasets } from './pull_cellxgene.nf'
include { computeSilhouette } from './compute_silhouette.nf'
include { mergeResults } from './merge_results.nf'

workflow {
    // Ensure fetchDatasets receives the test mode flag
    datasets = fetchDatasets(params.test_mode)

    // Pass the datasets output to computeSilhouette
    scores = computeSilhouette(datasets)

    // Pass the computed scores to mergeResults
    mergeResults(scores)
}
