process mergeResults {
    input:
        path scores

    output:
        path "${launchDir}/results/output.csv"
        path "${launchDir}/results/cluster_silhouette_plot.png"

    script:
    """
    mkdir -p "${launchDir}/results"

    # Move the results
    mv ${scores} "${launchDir}/results/output.csv"

    # Generate plots using Python
    python "${launchDir}/bin/generate_plots.py" "${launchDir}/results/output.csv" "${launchDir}/results/cluster_silhouette_plot.png"
    """
}

