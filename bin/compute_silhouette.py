import os
import json
import sys
import scanpy as sc
import pooch  # Efficient file downloading

def download_h5ad(url, dataset_id, test_mode):
    """
    Downloads an H5AD file using pooch and returns the local file path.
    - Only downloads if test_mode is enabled.
    """
    cache_dir = "datasets"
    os.makedirs(cache_dir, exist_ok=True)

    file_path = os.path.join(cache_dir, f"{dataset_id}.h5ad")

    if test_mode.lower() == "true":
        if not os.path.exists(file_path):
            print(f"⬇️ Downloading TEST dataset {dataset_id} from {url}...")
            try:
                file_path = pooch.retrieve(url, known_hash=None, fname=f"{dataset_id}.h5ad", path=cache_dir)
            except Exception as e:
                print(f"❌ ERROR: Failed to download {url}: {e}", file=sys.stderr)
                return None

    return file_path if os.path.exists(file_path) else None

def compute_silhouette(datasets_info_file, output_file, output_dir, test_mode):
    """
    Computes silhouette scores for each dataset.
    """
    print(f"🔍 Reading dataset info from '{datasets_info_file}'...")
    
    with open(datasets_info_file, "r") as f:
        datasets = json.load(f)

    results = []
    
    for dataset in datasets:
        dataset_id = dataset["dataset_id"]
        dataset_url = dataset["dataset_url"]

        # ✅ Download dataset ONLY in test mode
        dataset_path = download_h5ad(dataset_url, dataset_id, test_mode)
        if not dataset_path:
            print(f"❌ ERROR: Skipping dataset {dataset_id} - No local file available.")
            continue

        try:
            print(f"📂 Loading dataset {dataset_id} from {dataset_path}...")
            adata = sc.read_h5ad(dataset_path)

            # Compute silhouette score (dummy value for now)
            silhouette_score = 0.75  # Replace with real computation
            
            results.append({"dataset_id": dataset_id, "silhouette_score": silhouette_score})
        
        except Exception as e:
            print(f"❌ ERROR: Failed processing dataset {dataset_id}: {e}", file=sys.stderr)

    # Save results
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)
    
    print(f"✅ Silhouette scores saved at: {output_file}")

if __name__ == "__main__":
    datasets_info_json = sys.argv[1]
    output_json = sys.argv[2]
    output_dir = sys.argv[3]  # Collection results directory
    test_mode_flag = sys.argv[4]  # Pass test mode flag from Nextflow
    
    compute_silhouette(datasets_info_json, output_json, output_dir, test_mode_flag)

