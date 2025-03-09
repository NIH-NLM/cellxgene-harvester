import json
import sys
import os
import scanpy as sc
import numpy as np
import pandas as pd
import sklearn.metrics as skm
import matplotlib.pyplot as plt
import seaborn as sns

def compute_silhouette_per_cluster(datasets_json_file, output_json, output_dir):
    """
    Computes silhouette scores per dataset & cluster (author_cell_type),
    organizes results per collection, and generates per-collection summary.
    """
    if not os.path.exists(datasets_json_file) or os.stat(datasets_json_file).st_size == 0:
        print(f"❌ ERROR: Input file '{datasets_json_file}' does not exist or is empty!", file=sys.stderr)
        sys.exit(1)

    with open(datasets_json_file, "r", encoding="utf-8") as f:
        datasets_data = json.load(f)

    collection_silhouette_scores = {}

    for dataset in datasets_data:
        collection_id = dataset["collection_id"]
        dataset_id = dataset["dataset_id"]
        dataset_url = dataset["dataset_url"]
        collection_name = dataset.get("collection_name", "UNKNOWN")
        publication_info = dataset.get("publication", "UNKNOWN")

        try:
            # Load dataset
            adata = sc.read_h5ad(dataset_url)  

            # Compute PCA
            sc.tl.pca(adata, svd_solver='arpack')
            pca = adata.obsm['X_pca']

            # Compute silhouette scores per cluster
            cluster_labels = adata.obs['author_cell_type']
            scores = skm.silhouette_samples(pca, cluster_labels)

            # Store results per cluster
            cluster_silhouettes = pd.DataFrame({"cluster": cluster_labels, "silhouette_score": scores})
            cluster_mean = cluster_silhouettes.groupby("cluster")["silhouette_score"].mean().reset_index()

            # Store data per collection
            if collection_id not in collection_silhouette_scores:
                collection_silhouette_scores[collection_id] = {
                    "collection_name": collection_name,
                    "publication": publication_info,
                    "datasets": {}
                }

            collection_silhouette_scores[collection_id]["datasets"][dataset_id] = {
                "dataset_url": dataset_url,
                "clusters": cluster_mean.to_dict(orient="records")
            }

        except Exception as e:
            print(f"❌ ERROR: Failed processing dataset {dataset_id}: {str(e)}", file=sys.stderr)

    # Save per-collection JSONs
    os.makedirs(output_dir, exist_ok=True)
    for collection_id, data in collection_silhouette_scores.items():
        collection_file = os.path.join(output_dir, f"{collection_id}.json")
        with open(collection_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    # Save master JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(collection_silhouette_scores, f, indent=4)

if __name__ == "__main__":
    datasets_json_file = sys.argv[1]
    output_json = sys.argv[2]
    output_dir = sys.argv[3]  # Directory to save per-collection JSONs
    compute_silhouette_per_cluster(datasets_json_file, output_json, output_dir)

