# cellxgene harvester

There are 4 steps in this process

1.  First we get all the collections in cellxgene - at the time of this writing there were 377

```bash
python3 bin/fetch_collections.py
```

This data now is located at `data/collections.json`

If you would like to inspect it and puruse it you can run

```bash
jq -r data/colletions.json > data/collections_pp.json
```

2. Next we want to split the collections - this will allow us then to retrieve for each of the collections the datasets.

```bash
bash bin/splitCollections.sh
```

this will put each of the collections into separate json files.   You can ask questions of these files -- such what are the keys etc or look at them with a pretty print format.

To look at `keys` you can run

```bash
jq 'keys' data/collection*json
```

To look at each json in a `pretty print` manner you can run

```bash
jq -r data/collection_00109df5-7810-4542-8db5-2288c46e0424.json > data/collection_00109df5-7810-4542-8db5-2288c46e0424_pretty.json
```

3. Next we want to process each of the collections

what that means is that we will run this script

```bash
bash process_all_collections.sh
```

what that does is:

* Pretty-print the collection

* Extract the datasets array

and finally

* Split the datasets

4. Next we want to extract the collection_uuid, collection_version_id, dataset_uuid, dataset_version_id,and other metadata about the file that we will use to decide if we will loadit into our Cell Knowledge base or not

```bash
python3 bin/generate_csv_from_collections.py
```

This outputs a file `all_datasets.csv`

This doesn't yet give us our h5ad file we will use as input to the quality control and other routines we will run to prepare it for loading into our knowledge base.

5. Run the routine to grab the h5ad file for the combination of collection_uuid, collection_version_id, dataset_uuid, dataset_version_id

Using another api we can grab the h5ad file that fits this combination and it is unique

```bash
python3 bin/append_h5ad_urls.py
```

This routine takes awhile and generates the `all_datasets_h5ad.csv`


