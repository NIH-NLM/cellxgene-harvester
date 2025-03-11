process fetchCollections {
    tag 'fetchCollections'

    publishDir "${launchDir}/${params.datadir}", mode: 'copy'

    input:
        val collections_filename
	
    output:
        path $collections_filename, emit: collections_json

    script:
    """
    echo "Fetching collections from CellxGene API (Test Mode: $test_mode)"

    python "${launchDir}/bin/fetch_collections.py" $collections_filename
    """
}
