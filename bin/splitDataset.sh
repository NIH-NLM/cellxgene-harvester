#!/bin/bash
jq -c '.[]' dataset_info.json | while read -r dataset; do
    dataset_version_id=$(echo "$dataset" | jq -r '.dataset_version_id')
    echo "$dataset" > "dataset_${dataset_version_id}.json"
done
