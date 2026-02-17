/*
 * Module: generate_metadata
 *
 * Generates base metadata CSV from collections JSON.
 *
 * Input:
 *   collections_json - output from fetch_collections_process
 *
 * Output:
 *   all_datasets.csv - base metadata for all datasets
 */

process generate_metadata_process {

    tag "generate_metadata"
    label 'small'

    publishDir "${params.outdir}/catalog", mode: 'copy'

    input:
    path collections_json

    output:
    path "all_datasets.csv"

    script:
    """
    python ${projectDir}/bin/2_generate_metadata_csv.py \
        --input ${collections_json} \
        --output all_datasets.csv
    """
}
