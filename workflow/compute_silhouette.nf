process computeSilhouette {
    input:
    path datasets_json_file

    output:
    path "silhouette_scores.json"

    script:
    """
    python "${launchDir}/bin/compute_silhouette.py" "$datasets_json_file" "silhouette_scores.json"

    if [ ! -s silhouette_scores.json ]; then
        echo "❌ ERROR: No silhouette_scores.json found!" >&2
        exit 1
    fi
    """
}

