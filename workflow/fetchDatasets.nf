process fetchDatasets {
    tag 'fetchDatasets'

    publishDir "${params.datadir}", mode: 'copy'

    input:
        path datasets_json
        val test_mode

    output:
        path "${params.datadir}/dataset_info.json", emit: dataset_jsons

    script:
    """
    echo "Fetching datasets from CellxGene API (Test Mode: $test_mode)"

    python "${launchDir}/bin/fetch_cellxgene.py fetch_datasets $datasets_json $test_mode"
    """
}
