/*
 * Module: resolve_uberon
 *
 * Resolves tissue label(s) to UBERON ontology terms via OLS4 API.
 * Outputs JSON and CSV of all descendant terms for use in filtering.
 *
 * Input:
 *   tissue     - tissue label(s), comma-separated (e.g. "kidney" or "respiratory system,nose")
 *   organ_slug - filesystem-safe slug for output filenames
 *
 * Output:
 *   json - uberon_{organ_slug}.json (obo_ids list + term metadata)
 *   csv  - uberon_{organ_slug}.csv  (obo_id, label, level)
 */

process resolve_uberon_process {

    tag "${organ_slug}"
    label 'small'

    publishDir "${params.outdir}/uberon", mode: 'copy'

    input:
    val tissue
    val organ_slug

    output:
    path "uberon_${organ_slug}.json", emit: json
    path "uberon_${organ_slug}.csv",  emit: csv

    script:
    // Convert comma-separated tissues to space-separated quoted args
    def tissue_args = tissue
        .split(',')
        .collect { "\"${it.trim()}\"" }
        .join(' ')

    """
    python ${projectDir}/bin/0_resolve_uberon.py \
        ${tissue_args} \
        --output-prefix uberon_${organ_slug}
    """
}
