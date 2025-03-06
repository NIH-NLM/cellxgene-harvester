process mergeResults {
    input:
        path scores

    output:
        path "results/output.csv"

    script:
    """
    mv silhouette_scores.csv results/output.csv
    """
}
