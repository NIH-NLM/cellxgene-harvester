process generatePlots {
    tag 'generatePlots'

    publishDir "${launchDir}/${params.outdir}", mode: 'copy'

    input:
        path scores_csv

    output:
        path "${params.outdir}/final_plots.png", emit: final_plots

    script:
    """
    echo "Generating plots from silhouette scores"

    python "${launchDir}/bin/generate_plots.py" "$scores_csv"
    """
}
