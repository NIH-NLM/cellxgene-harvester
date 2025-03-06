import json
import pandas as pd
import scanpy as sc
import numpy as np
import sklearn.metrics as skm

def compute_silhouette(input_file, output_file):
    with open(input_file, "r") as f:
        datasets = json.load(f)

    results = []
    
    for dataset in datasets:
        dataset_url = dataset['dataset_url']
        print(f"Fetching dataset: {dataset_url}")

        try:
            adata = sc.read(dataset_url)
            sc.tl.pca(adata, svd_solver="arpack")
            pca = adata.obsm["X_pca"]
            labels = adata.obs["author_cell_type"]

            silhouette_score = skm.silhouette_score(pca, labels, metric="cosine")

            dataset["silhouette_score"] = silhouette_score
            results.append(dataset)
        except Exception as e:
            print(f"Failed to process {dataset_url}: {e}")

    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input JSON file with dataset metadata")
    parser.add_argument("--output", required=True, help="Output CSV file with silhouette scores")

    args = parser.parse_args()
    compute_silhouette(args.input, args.output)
