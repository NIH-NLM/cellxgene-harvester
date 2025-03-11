process parseCollections {
    tag 'parseCollections'

    publishDir "${params.outdir}", mode: 'copy'

    input:
        path collections_json
        val test_mode

    output:
        path "${params.outdir}/datasets_info.json", emit: datasets_json

    script:
    """
    echo "Parsing collections to extract dataset IDs (Test Mode: $test_mode)"

    python "${launchDir}/bin/parse_collections.py" $collections_json $test_mode
    """
}

