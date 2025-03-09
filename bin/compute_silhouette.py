import json
import pandas as pd
import scanpy as sc
import pooch
import sklearn.metrics as skm
import os
import sys

CACHE_DIR = os.path.expanduser("~/.cellxgene_cache")

def compute_silhouette(dataset_json_str, output_csv):
    """
    Computes silhouette scores per cluster for a single dataset.
    """
    try:
        # Ensure the input JSON is not empty
        if not dataset_json_str or dataset_json_str.strip() == "":
            raise ValueError("Received empty dataset JSON string")

        dataset = json.loads(dataset_json_str)  # Convert JSON string to dict

        # Ensure dataset has valid fields
        dataset_id = dataset.get('dataset_id', 'unknown_id')
        dataset_url = dataset.get('dataset_url', '').strip()

        if not dataset_url:
            raise ValueError(f"Dataset {dataset_id} is missing a valid URL")

        print(f"Processing dataset: {dataset_id}")

        dataset_path = pooch.retrieve(
            url=dataset_url,
            fname=f"{dataset_id}.h5ad",
            path=CACHE_DIR,
            known_hash=None
        )

        adata = sc.read_h5ad(dataset_path)

        sc.tl.pca(adata, svd_solver="arpack")
        pca = adata.obsm['X_pca']
        labels = adata.obs['author_cell_type']

        unique_clusters = labels.unique()
        cluster_scores = []
        for cluster in unique_clusters:
            cluster_indices = labels == cluster
            if sum(cluster_indices) > 1:
                score = skm.silhouette_score(pca[cluster_indices], labels[cluster_indices], metric='cosine')
                cluster_scores.append({"dataset_id": dataset_id, "cluster": cluster, "silhouette_score": score})

        df = pd.DataFrame(cluster_scores)
        df.to_csv(output_csv, index=False)

    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}. Input JSON: {dataset_json_str}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Error processing dataset {dataset_id}: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    dataset_json_str = sys.argv[1]  # Read dataset JSON from Nextflow
    output_csv = sys.argv[2]
    compute_silhouette(dataset_json_str, output_csv)

