process splitCollections {
    tag 'split_collections'
    
    input:
        path collections_json
        
    output:
        path "collection_*.json", emit: collection_jsons

    script:
    """
    bash "${launchDir}/bin/splitCollections.sh"
    """
}

