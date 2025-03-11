process computeSilhouette {
    tag 'computeSilhouette'

    publishDir "${launchDir}/results/", mode: 'copy'

    input:
        path dataset_jsons

    output:
        path "${launchDir}/data/silhouette_scores.csv", emit: scores_csv

    script:
    """
    echo "Computing Silhouette Scores for datasets"

    python "${launchDir}/bin/compute_silhouette.py $dataset_jsons"
    """
}
