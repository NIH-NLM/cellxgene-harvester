process mergeResults {
    input:
        path scores

    output:
        path "${launchDir}/results/output.csv"

    script:
    """
    if [ -f ${scores} ]; then
        mkdir -p "${launchDir}/results"
        mv ${scores} "${launchDir}/results/output.csv"
    else
        echo "Error: silhouette_scores.csv not found!" >&2
        exit 1
    fi
    """
}
