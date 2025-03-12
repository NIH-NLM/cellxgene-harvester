#!/bin/bash
jq -c '.[]' collections_info.json | while read -r collection; do
    collection_id=$(echo "$collection" | jq -r '.collection_id')
    echo "$collection" > "collection_${collection_id}.json"
done
