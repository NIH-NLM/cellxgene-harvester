/**
 * fetch_collections.nf
 *
 * Step 1: Fetch all public collections from the CellxGene Curation API.
 *
 * Downloads collection metadata (IDs, names, publication info, and the
 * datasets[] array with tissue and disease ontology term IDs) and saves
 * it as a single JSON file.
 *
 * This step is slow on first run (~1-2 min) but the output is stable
 * across runs unless a new CellxGene release occurs.  Cache with -resume.
 *
 * @output collections_json  collections_metadata.json — all public collections
 */
process FETCH_COLLECTIONS {

    label 'process_low'

    container 'ghcr.io/nih-nlm/cellxgene-harvester:latest'

    output:
    path "collections_metadata.json", emit: collections_json

    script:
    """
    # CLI writes to data/collections_metadata.json; move to work dir root
    mkdir -p data
    cellxgene-harvester fetch-collections
    mv data/collections_metadata.json .
    """
}
