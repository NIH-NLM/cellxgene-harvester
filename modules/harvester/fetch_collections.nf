/*
 * Module: fetch_collections
 *
 * Fetches all public collections from the CellxGene API.
 * This step runs once and is cached by Nextflow.
 *
 * Output:
 *   collections_metadata.json - raw collection metadata
 */

process fetch_collections_process {

    tag "fetch_collections"
    label 'small'

    publishDir "${params.outdir}/catalog", mode: 'copy'

    output:
    path "collections_metadata.json"

    script:
    """
    python ${projectDir}/bin/1_fetch_collections.py \
        --output collections_metadata.json
    """
}
