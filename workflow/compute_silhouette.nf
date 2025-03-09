process computeSilhouette {
    input:
    path datasets_json_file

    output:
    path "silhouette_scores.json", emit: silhouette_scores
    path "collections/", emit: collection_scores

    publishDir "${launchDir}/results", mode: 'copy'

    script:
    """
    python "${launchDir}/bin/compute_silhouette.py" "$datasets_json_file" "silhouette_scores.json" "collections/"
    """
}

