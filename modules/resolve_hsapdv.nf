/**
 * resolve_hsapdv.nf
 *
 * Step 0c: Resolve HsapDv development stage terms for a minimum age threshold.
 *
 * Run ONCE per age threshold before the main pipeline.  Queries the OLS4 API
 * for all HsapDv terms and selects those whose start age >= min_age.
 *
 * The age threshold is encoded in the JSON at resolve time: downstream filters
 * in Step 5 (count_normal_cells_single) and sc-nsforest-qc-nf (filter_adata)
 * use the same .isin(obo_ids) pattern as tissue and disease — no numeric
 * comparison lives in the filter code.
 *
 * @param min_age  Minimum donor age in years (e.g. 15)
 *
 * @output hsapdv_json  hsapdv_adult_<min_age>.json — obo_ids for all HsapDv
 *                      terms whose start age >= min_age
 */
process RESOLVE_HSAPDV {

    label 'process_low'

    container 'ghcr.io/nih-nlm/cellxgene-harvester:latest'

    input:
    val min_age

    output:
    path "hsapdv_adult_${min_age}.json", emit: hsapdv_json

    script:
    """
    cellxgene-harvester resolve-hsapdv \
        --min-age ${min_age} \
        --output-prefix hsapdv_adult_${min_age}
    """
}
