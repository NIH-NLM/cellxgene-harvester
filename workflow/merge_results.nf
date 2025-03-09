process mergeResults {
    input:
        path scores

    output:
        path "${launchDir}/results/output.csv"

    script:
    """
    cat silhouette_scores_*.csv > "${launchDir}/results/output.csv"
    """
}

