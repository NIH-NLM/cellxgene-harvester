/*
 * Module: append_details
 *
 * Appends dataset details (titles, cell counts, h5ad URLs) via CellxGene API.
 * This is the slow step (~10-20 min). Cached by Nextflow after first run.
 *
 * Input:
 *   metadata_csv - output from generate_metadata_process
 *
 * Output:
 *   all_datasets_complete.csv - master catalog with all dataset details
 */

process append_details_process {

    tag "append_details"
    label 'medium'

    publishDir "${params.outdir}/catalog", mode: 'copy'

    input:
    path metadata_csv

    output:
    path "all_datasets_complete.csv"

    script:
    """
    python ${projectDir}/bin/3_append_dataset_details.py \
        --input  ${metadata_csv} \
        --output all_datasets_complete.csv
    """
}
