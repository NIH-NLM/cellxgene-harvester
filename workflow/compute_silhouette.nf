process computeSilhouette {
    input:
        val dataset_json_str

    output:
        path "silhouette_scores.json"

    script:
    """
    python "${launchDir}/bin/compute_silhouette.py" '${dataset_json_str}' "silhouette_scores.json"
    """
}

