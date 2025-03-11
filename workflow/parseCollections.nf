process parseCollections {
    tag 'parse_collections'

    publishDir "${launchDir}/results/", mode: 'copy'

    input:
        path collections_json
        val test_mode

    output:
        path "${launchDir}/data/datasets_info.json", emit: datasets_json

    script:
    """
    echo "Parsing collections to extract dataset IDs (Test Mode: $test_mode)"

    python "${launchDir}/bin/parse_collections.py" $collections_json $test_mode
    """
}

