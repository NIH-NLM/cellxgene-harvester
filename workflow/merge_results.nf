process mergeResults {
    input:
    path silhouette_scores_csv_files

    output:
    path "output.csv"

    script:
    """
    cat silhouette_scores_*.csv > output.csv
    mv output.csv "${launchDir}/results/output.csv"
    """
}

