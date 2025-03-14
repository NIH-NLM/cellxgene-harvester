#!/bin/bash

input_json="$1"

if [ ! -f "$input_json" ]; then
    echo "ERROR: File not found: $input_json"
    exit 1
fi

jq -c '.[]' "$input_json" | while read -r collection; do
    collection_id=$(echo "$collection" | jq -r '.collection_id')
    echo "$collection" > "collection_${collection_id}.json"
done

echo "Collections split successfully!"

