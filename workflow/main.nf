nextflow.enable.dsl = 2

include { fetchDatasets } from './pull_cellxgene.nf'
include { computeSilhouette } from './compute_silhouette.nf'
include { mergeResults } from './merge_results.nf'

workflow {
    datasets = fetchDatasets()
    scores = computeSilhouette(datasets)
    mergeResults(scores)
}
