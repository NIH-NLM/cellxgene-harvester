process fetchCollections {
    tag 'fetchCollections'

    publishDir "${launchDir}/${params.datadir}", mode: 'copy'

    input:
        val test_mode

    output:
        path "${params.collection_info}", emit: collections_json

    script:
    """
    echo "Fetching collections from CellxGene API (Test Mode: $test_mode)"

    python "${launchDir}/bin/fetch_collections.py" "${params.collection_info}" $test_mode
    """
}
