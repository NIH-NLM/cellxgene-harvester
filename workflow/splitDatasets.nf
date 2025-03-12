process splitDatasets {
    tag 'split_datasets'
    
    publishDir "${params.datasets_split}", mode: 'copy'
    
    input:
        path dataset_json
        
    output:
        path "dataset_*.json", emit: dataset_jsons

    script:
    """
    bash "${launchDir}/bin/splitDatasets.sh"
    """
}

