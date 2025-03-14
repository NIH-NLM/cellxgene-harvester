#!/bin/bash

input_json="$1"

if [ ! -f "$input_json" ]; then
    echo "ERROR: File not found: $input_json"
    exit 1
fi

jq -c '.[]' "$input_json" | while read -r dataset; do
    dataset_version_id=$(echo "$dataset" | jq -r '.dataset_version_id')
    echo "$dataset" > "dataset_${dataset_version_id}.json"
done

echo "Datasets split successfully!"
