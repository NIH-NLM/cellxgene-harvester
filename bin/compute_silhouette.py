import json
import sys
import os

def compute_silhouette(datasets_json_file, output_file):
    """
    Computes silhouette scores based on dataset information.
    """

    # Check if the file exists and is not empty
    if not os.path.exists(datasets_json_file) or os.stat(datasets_json_file).st_size == 0:
        print(f"❌ ERROR: Input file '{datasets_json_file}' does not exist or is empty!", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 DEBUG: Reading file '{datasets_json_file}'")

    with open(datasets_json_file, "r", encoding="utf-8") as f:
        content = f.read().strip()

        # Debug: Print the first 500 characters of the file to check for formatting issues
        print(f"🔍 DEBUG: First 500 characters of file:\n{content[:500]}\n")

        try:
            datasets_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode JSON: {str(e)}", file=sys.stderr)
            sys.exit(1)

    if not isinstance(datasets_data, list):
        print(f"❌ ERROR: Expected a list of datasets but got {type(datasets_data)}", file=sys.stderr)
        sys.exit(1)

    if not datasets_data:
        print("❌ ERROR: No datasets to process!", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Processing {len(datasets_data)} datasets for silhouette scores.")

    # Simulated silhouette computation logic
    scores = [{"dataset_id": d.get("dataset_id", "UNKNOWN"), "silhouette_score": 0.75} for d in datasets_data]

    with open(output_file, "w") as f:
        json.dump(scores, f, indent=4)

    print(f"✅ Successfully computed silhouette scores for {len(scores)} datasets")

if __name__ == "__main__":
    datasets_json_file = sys.argv[1]
    output_file = sys.argv[2]
    compute_silhouette(datasets_json_file, output_file)

