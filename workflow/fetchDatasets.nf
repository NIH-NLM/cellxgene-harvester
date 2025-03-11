process fetchDatasets {
    tag 'fetch_datasets'

    publishDir "${launchDir}/results/", mode: 'copy'

    input:
        path datasets_json
        val test_mode

    output:
        path "${launchDir}/data/dataset_jsons/", emit: dataset_jsons

    script:
    """
    echo "Fetching datasets from CellxGene API (Test Mode: $test_mode)"

    python "${launchDir}/bin/fetch_cellxgene.py fetch_datasets $datasets_json $test_mode"
    """
}
