/*
 * Module: count_normal_cells
 *
 * Counts normal adult cells for a single dataset via CellxGene Census API.
 * Runs in parallel - one process per dataset_id (scatter pattern).
 *
 * Filters applied server-side in Census query:
 *   - UBERON tissue_ontology_term_id
 *   - is_primary_data == True
 *   - disease == 'normal'
 *
 * Filters applied client-side:
 *   - age >= min_age
 *
 * Input:
 *   dataset_row  - tuple [dataset_id, first_author, year, journal, total_cell_count]
 *   uberon_json  - UBERON terms JSON from resolve_uberon_process
 *   min_age      - minimum age for adult filtering
 *
 * Output:
 *   *_normal_count.csv - single-row CSV with normal cell count + metadata
 */

process count_normal_cells_process {

    tag "${dataset_id}"
    label 'medium'

    // Retry on S3/network failures
    errorStrategy { task.exitStatus in [1, 137, 139] ? 'retry' : 'finish' }
    maxRetries 3

    input:
    tuple val(dataset_id),
          val(first_author),
          val(year),
          val(journal),
          val(total_cell_count)
    path  uberon_json
    val   min_age

    output:
    path "${dataset_id}_normal_count.csv"

    script:
    """
    python ${projectDir}/bin/5_count_normal_cells_single.py \
        --dataset-id   "${dataset_id}" \
        --uberon       ${uberon_json} \
        --min-age      ${min_age} \
        --first-author "${first_author}" \
        --year         "${year}" \
        --journal      "${journal}" \
        --output       ${dataset_id}_normal_count.csv
    """
}
