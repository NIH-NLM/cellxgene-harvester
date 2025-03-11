process computeSilhouette {
    tag 'computeSilhouette'

    publishDir "${launchDir}/${params.outdir}", mode: 'copy'

    input:
        path dataset_jsons

    output:
        path "silhouette_scores.csv", emit: scores_csv

    script:
    """
    echo "Computing Silhouette Scores for datasets"

    python "${launchDir}/bin/compute_silhouette.py" "$dataset_jsons"
    """
}
