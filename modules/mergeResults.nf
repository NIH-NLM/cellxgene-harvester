process mergeResults {
    tag 'merge_results'

    publishDir "${params.outdir}/final_report", mode: 'copy'

    input:
        path dataset_plots
	val  final_report_pdf
	val  final_report_html

    output:
        path final_report_pdf, emit: final_pdf
        path final_report.html, emit: final_html

    script:
    """
    echo "Merging dataset plots into a final report"

    python "${launchDir}/bin/merge_results.py" --pdf "$final_report_pdf"  --html "$final_report_html"
    """
}
