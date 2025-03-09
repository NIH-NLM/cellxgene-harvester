process computeSilhouette {
    input:
    path datasets_json_file

    output:
    path "silhouette_scores.json", emit: silhouette_scores

    publishDir "${launchDir}/results", mode: 'copy'  // Saves output in `results/`

    script:
    """
    python "${launchDir}/bin/compute_silhouette.py" "$datasets_json_file" "silhouette_scores.json"
    """
}

