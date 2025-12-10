process fetchDatasets {
    tag 'fetch_datasets'

    publishDir "${launchDir}/${params.datadir}/${params.datasets_split}", mode: 'copy'

    input:
        path collections_json
	val test_mode

    output:
        path "dataset*.json", emit: dataset_jsons

    script:
    """
    echo "Fetching datasets from CellxGene API (Test Mode: $test_mode)"
    
    python "${launchDir}/bin/fetch_datasets.py" "$collections_json" "$test_mode"
    """
}
