/**
 * count_normal_cells_single.nf
 *
 * Step 5 (scatter): Count normal adult cells for one dataset via CellxGene Census.
 *
 * Called once per dataset row in the harvester CSV.  Results are collected by
 * the calling workflow and concatenated into the final counts CSV.
 *
 * Filter chain applied inside Census (uniform .isin(obo_ids) pattern):
 *   1. tissue_ontology_term_id  .isin(uberon_ids)      — server-side in Census query
 *   2. disease_ontology_term_id .isin(disease_ids)     — server-side in Census query
 *   3. development_stage_ontology_term_id .isin(hsapdv_ids)  — client-side after Census fetch
 *
 * All three filters use the same JSON structure (queries, root_terms, obo_ids, terms)
 * produced by the three resolve steps (0a/0b/0c).  No text matching, no numeric
 * age comparison — only set intersection with obo_ids.
 *
 * @param meta          Map with keys: dataset_id, first_author, year, journal
 * @param uberon_json   uberon_<organ>.json from resolve_uberon (Step 0a)
 * @param disease_json  disease_<state>.json from resolve_disease (Step 0b)
 * @param hsapdv_json   hsapdv_adult_<N>.json from resolve_hsapdv (Step 0c)
 *
 * @output counts_csv  <dataset_id>_normal_count.csv — single-row result:
 *                     dataset_id, normal_cell_count, total_count, adult_count,
 *                     plus tissue/assay/cell_type/disease/sex ontology summaries
 */
process COUNT_NORMAL_CELLS_SINGLE {

    label 'process_medium'

    container 'ghcr.io/nih-nlm/cellxgene-harvester:latest'

    // Census queries can fail transiently; retry twice before marking failed
    errorStrategy 'retry'
    maxRetries 2

    input:
    tuple val(meta), path(uberon_json), path(disease_json), path(hsapdv_json)

    output:
    path "${meta.dataset_id}_normal_count.csv", emit: counts_csv

    script:
    """
    python -m harvester.count_normal_cells_single \
        --dataset-id   "${meta.dataset_id}" \
        --uberon       ${uberon_json} \
        --disease      ${disease_json} \
        --hsapdv       ${hsapdv_json} \
        --first-author "${meta.first_author}" \
        --year         "${meta.year}" \
        --journal      "${meta.journal}" \
        --output       ${meta.dataset_id}_normal_count.csv
    """
}
