/**
 * generate_metadata.nf
 *
 * Step 2: Generate the base metadata CSV from collections_metadata.json.
 *
 * Flattens the collections → datasets hierarchy into one row per dataset,
 * extracting publication metadata (first_author, journal, year, doi) and
 * both the label AND ontology_term_id for tissue and disease directly from
 * the CellxGene API response — no additional API calls required.
 *
 * Key columns added in this step:
 *   tissue                   — human-readable label(s), " | " joined
 *   tissue_ontology_term_id  — UBERON IDs, " | " joined (used by Step 4)
 *   disease                  — human-readable label(s)
 *   disease_ontology_term_id — PATO/MONDO IDs, " | " joined (used by Step 4)
 *
 * @param collections_json  collections_metadata.json from fetch_collections
 *
 * @output datasets_csv  all_datasets.csv — one row per dataset
 */
process GENERATE_METADATA {

    label 'process_low'

    container 'ghcr.io/nih-nlm/cellxgene-harvester:latest'

    input:
    path collections_json

    output:
    path "all_datasets.csv", emit: datasets_csv

    script:
    """
    mkdir -p data
    cp ${collections_json} data/collections_metadata.json
    cellxgene-harvester generate-metadata
    mv data/all_datasets.csv .
    """
}
