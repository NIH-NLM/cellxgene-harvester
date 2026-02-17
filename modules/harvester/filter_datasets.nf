/*
 * Module: filter_datasets
 *
 * Filters the master catalog by UBERON tissue labels + quality criteria.
 * Uses UBERON term labels for text matching against the 'tissue' column.
 * Precise ontology ID filtering is applied in count_normal_cells via Census.
 *
 * Input:
 *   all_datasets_csv - output from append_details_process
 *   uberon_json      - output from resolve_uberon_process
 *   organism         - e.g. "Homo sapiens"
 *
 * Output:
 *   *_harvester.csv  - filtered dataset list ready for Census counting
 */

process filter_datasets_process {

    tag "${uberon_json.baseName}"
    label 'small'

    publishDir "${params.outdir}", mode: 'copy'

    input:
    path all_datasets_csv
    path uberon_json
    val  organism

    output:
    path "*_harvester.csv"

    script:
    def organ_slug  = uberon_json.baseName.replace('uberon_', '')
    def no_preprint = params.no_preprints    ? '--no-preprints'    : ''
    def no_cancer   = params.exclude_cancer  ? '--exclude-cancer'  : ''
    def no_spatial  = params.exclude_spatial ? '--exclude-spatial' : ''

    """
    python ${projectDir}/bin/4_filter_datasets.py \
        --input    ${all_datasets_csv} \
        --uberon   ${uberon_json} \
        --organism "${organism}" \
        ${no_preprint} \
        ${no_cancer} \
        ${no_spatial} \
        --output   ${organism.toLowerCase().replaceAll(/\s+/, '_')}_${organ_slug}_harvester.csv
    """
}
