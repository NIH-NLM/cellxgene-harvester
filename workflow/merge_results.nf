process mergeResults {
    input:
    path silhouette_scores_files

    output:
    path "output.csv"

    script:
    """
    cat \$(ls silhouette_scores.json) > merged_silhouette_scores.json
    mv merged_silhouette_scores.json "${launchDir}/results/output.csv"
    """
}

