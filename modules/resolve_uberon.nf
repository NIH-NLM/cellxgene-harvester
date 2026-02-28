/**
 * resolve_uberon.nf
 *
 * Step 0a: Resolve a tissue label (or UBERON ID) to a full UBERON ontology JSON
 * containing the root term plus all hierarchical descendants.
 *
 * Run ONCE per organ before the main pipeline.  The output JSON is a
 * prerequisite for filter_datasets (Step 4) and count_normal_cells_single (Step 5).
 *
 * @param organ  Tissue label or UBERON ID (e.g. "kidney", "UBERON:0002113")
 *
 * @output uberon_json  uberon_<organ>.json — obo_ids list used by all downstream filters
 */
process RESOLVE_UBERON {

    label 'process_low'

    container 'ghcr.io/nih-nlm/cellxgene-harvester:latest'

    input:
    val organ

    output:
    path "uberon_${organ}.json", emit: uberon_json

    script:
    """
    cellxgene-harvester resolve-uberon ${organ} \
        --output-prefix uberon_${organ}
    """
}
