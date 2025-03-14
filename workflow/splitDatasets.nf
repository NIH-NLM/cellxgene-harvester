process splitDatasets {
    tag 'split_datasets'
    
    publishDir "${launchDir}/${params.datadir}/${params.datasets_split}", mode: 'copy'
    
    input:
        path dataset_json
        
    output:
        path "dataset*.json", emit: dataset_jsons

    script:
    """
    bash "${launchDir}/bin/splitDatasets.sh"
    """
}

