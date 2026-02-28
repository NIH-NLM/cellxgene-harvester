/**
 * filter_datasets.nf
 *
 * Step 4: Filter all_datasets_complete.csv to organ- and disease-relevant datasets
 * using exact ontology ID matching.
 *
 * Filters applied:
 *   tissue   — keep if ANY of the dataset's tissue_ontology_term_ids are in
 *              the UBERON obo_ids set (inclusive match; multi-tissue datasets
 *              are retained if they include the target tissue)
 *   disease  — keep if the target disease ID is AMONG the dataset's
 *              disease_ontology_term_ids (inclusive; datasets with mixed
 *              [normal, COVID-19] are retained — they contain normal cells)
 *   organism — optional label filter (default: "Homo sapiens")
 *
 * Age filtering (HsapDv) is NOT applied here.  development_stage is absent
 * at the dataset level in the CellxGene API; it is only available at the
 * cell level via Census in Step 5.
 *
 * @param complete_csv  all_datasets_complete.csv from append_dataset_details
 * @param uberon_json   uberon_<organ>.json from resolve_uberon (Step 0a)
 * @param disease_json  disease_<state>.json from resolve_disease (Step 0b)
 * @param organ         organ label used to name the output file
 * @param organism      organism label for filtering (default: "Homo sapiens")
 *
 * @output harvester_csv  homo_sapiens_<organ>_harvester.csv — filtered dataset list
 */
process FILTER_DATASETS {

    label 'process_low'

    container 'ghcr.io/nih-nlm/cellxgene-harvester:latest'

    input:
    path complete_csv
    path uberon_json
    path disease_json
    val  organ
    val  organism

    output:
    path "homo_sapiens_${organ}_harvester.csv", emit: harvester_csv

    script:
    def org_arg = organism ? "--organism '${organism}'" : "--organism 'Homo sapiens'"
    """
    cellxgene-harvester filter-datasets ${complete_csv} \
        --uberon  ${uberon_json} \
        --disease ${disease_json} \
        ${org_arg} \
        --output  homo_sapiens_${organ}_harvester.csv
    """
}
