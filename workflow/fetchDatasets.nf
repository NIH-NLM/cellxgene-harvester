process fetchDatasets {
    tag 'fetch_datasets'

    publishDir "${launchDir}/${params.datadir}/datasets", mode: 'copy'

    input:
        path datasets_info_json
        val test_mode

    output:
        path "datasets", emit: datasets_dir

    script:
    """
    echo "Fetching datasets from CellxGene API (Test Mode: $test_mode)"
    
    python "${launchDir}/bin/fetch_cellxgene.py" fetch_datasets "$datasets_info_json" "$test_mode"
    """
}
