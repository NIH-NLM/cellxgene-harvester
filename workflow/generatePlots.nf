process generatePlots {
    tag 'generatePlots'

    publishDir "${launchDir}/results/", mode: 'copy'

    input:
        path scores_csv

    output:
        path "${launchDir}/results/final_plots.png", emit: final_plots

    script:
    """
    echo "Generating plots from silhouette scores"

    python "${launchDir}/bin/generate_plots.py $scores_csv"
    """
}
