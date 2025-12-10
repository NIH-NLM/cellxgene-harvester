#!/bin/bash

set -e

DATA_DIR="${1:-data}"

echo "Processing collections in: $DATA_DIR"

for collection_file in "$DATA_DIR"/collection_*.json; do
    [ -e "$collection_file" ] || continue  # skip if no match

    collection_basename=$(basename "$collection_file" .json)
    collection_id=${collection_basename#collection_}
    outdir="$DATA_DIR/$collection_basename"

    echo "→ Processing $collection_id..."

    mkdir -p "$outdir"

    # 1. Pretty-print collection
    jq '.' "$collection_file" > "$outdir/collection_$collection_id.pretty.json"

    # 2. Extract datasets array
    datasets_file="$outdir/datasets_$collection_id.json"
    jq '.datasets' "$collection_file" > "$datasets_file"
    jq '.' "$datasets_file" > "$outdir/datasets_$collection_id.pretty.json"

    # 3. Split datasets
    jq -c '.[]' "$datasets_file" | while read -r dataset; do
        dataset_version_id=$(echo "$dataset" | jq -r '.dataset_version_id')
        echo "$dataset" > "$outdir/dataset_${dataset_version_id}.json"
        jq '.' "$outdir/dataset_${dataset_version_id}.json" > "$outdir/dataset_${dataset_version_id}.pretty.json"
    done

    echo "✓ $collection_id done."
done

echo "🎉 All collections processed successfully."
