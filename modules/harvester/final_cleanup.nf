/*
 * Module: final_cleanup
 *
 * Removes datasets with 0 normal cells from the final output.
 *
 * Input:
 *   counts_csv  - merged CSV from count_normal_cells_process
 *   organ_slug  - used for output filename
 *
 * Output:
 *   *_final.csv - clean final dataset list with normal cell counts
 */

process final_cleanup_process {

    tag "${organ_slug}"
    label 'small'

    publishDir "${params.outdir}", mode: 'copy'

    input:
    path counts_csv
    val  organ_slug

    output:
    path "${organ_slug}_final.csv"

    script:
    """
    python ${projectDir}/bin/6_final_cleanup.py \
        --input  ${counts_csv} \
        --output ${organ_slug}_final.csv
    """
}
