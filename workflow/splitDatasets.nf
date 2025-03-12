process splitDatasets {
    tag 'split_datasets'
    
    input:
        path dataset_json
        
    output:
        path "dataset_*.json", emit: dataset_jsons

    script:
    """
    bash ${launchDir}/bin/splitDatasets.sh 
    """
}

