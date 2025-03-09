process computeSilhouette {
    input:
    path datasets_json_file

    output:
    path "silhouette_scores.json"

    script:
    """
    echo "🔍 DEBUG: Received file - $datasets_json_file"
    ls -lh $datasets_json_file  # Check file size
    cat $datasets_json_file | head -n 20  # Print first 20 lines to verify content

    python "${launchDir}/bin/compute_silhouette.py" "$datasets_json_file" "silhouette_scores.json"
    """
}

