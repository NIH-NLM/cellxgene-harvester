/**
 * resolve_disease.nf
 *
 * Step 0b: Resolve a disease label (or PATO/MONDO ID) to an ontology JSON
 * containing the root term plus all hierarchical descendants.
 *
 * Run ONCE per disease state before the main pipeline.  For the standard
 * normal-cell workflow, resolve "normal" → PATO:0000461.
 *
 * The output JSON has the same structure as uberon JSON (queries, root_terms,
 * obo_ids, terms, total), so all downstream filters use the same
 * .isin(obo_ids) pattern regardless of ontology.
 *
 * @param disease_label  Disease label or ontology ID (e.g. "normal", "PATO:0000461")
 *
 * @output disease_json  disease_<disease_label>.json — obo_ids used by Steps 4 and 5
 */
process RESOLVE_DISEASE {

    label 'process_low'

    container 'ghcr.io/nih-nlm/cellxgene-harvester:latest'

    input:
    val disease_label

    output:
    path "disease_${disease_label}.json", emit: disease_json

    script:
    """
    cellxgene-harvester resolve-disease ${disease_label} \
        --output-prefix disease_${disease_label}
    """
}
