#!/usr/bin/env nextflow

/*
 * cellxgene-harvester
 *
 * Harvest, filter and count normal cells from CellxGene Census.
 *
 * Steps:
 *   0. resolve_uberon    - resolve tissue labels to UBERON ontology IDs
 *   1. fetch_collections - fetch all public collections from CellxGene API
 *   2. generate_metadata - generate base metadata CSV
 *   3. append_details    - append dataset details (titles, cell counts, h5ad URLs)
 *   4. filter_datasets   - filter by UBERON labels + organism + quality criteria
 *   5. count_normal_cells - count normal adult cells via Census API (scatter by dataset)
 *   6. final_cleanup     - remove datasets with 0 normal cells
 *
 * Usage:
 *   nextflow run main.nf \
 *     --tissue "kidney" \
 *     --organism "Homo sapiens" \
 *     --outdir results/kidney
 *
 *   # Multiple tissues combined
 *   nextflow run main.nf \
 *     --tissue "respiratory system,nose" \
 *     --organism "Homo sapiens" \
 *     --outdir results/respiratory
 */

nextflow.enable.dsl = 2

include { resolve_uberon_process }     from './modules/harvester/resolve_uberon.nf'
include { fetch_collections_process }  from './modules/harvester/fetch_collections.nf'
include { generate_metadata_process }  from './modules/harvester/generate_metadata.nf'
include { append_details_process }     from './modules/harvester/append_details.nf'
include { filter_datasets_process }    from './modules/harvester/filter_datasets.nf'
include { count_normal_cells_process } from './modules/harvester/count_normal_cells.nf'
include { final_cleanup_process }      from './modules/harvester/final_cleanup.nf'

workflow {

    // Validate required parameters
    if (!params.tissue) {
        log.error "ERROR: --tissue is required (e.g. 'kidney' or 'respiratory system,nose')"
        exit 1
    }

    if (!params.organism) {
        log.error "ERROR: --organism is required (e.g. 'Homo sapiens')"
        exit 1
    }

    // Derive organ slug for filenames (e.g. "respiratory system,nose" -> "respiratory_system_nose")
    def organ_slug = params.tissue
        .toLowerCase()
        .replaceAll(/[^a-z0-9]+/, '_')
        .replaceAll(/^_|_$/, '')

    // -------------------------------------------------------------------------
    // Step 0: Resolve UBERON tissue terms → uberon_{organ}.json + .csv
    // -------------------------------------------------------------------------
    uberon_ch = resolve_uberon_process(
        params.tissue,
        organ_slug
    )

    // -------------------------------------------------------------------------
    // Steps 1-3: Fetch + build master catalog (runs once, cached by Nextflow)
    // -------------------------------------------------------------------------
    collections_ch      = fetch_collections_process()
    metadata_ch         = generate_metadata_process(collections_ch)
    all_datasets_ch     = append_details_process(metadata_ch)

    // -------------------------------------------------------------------------
    // Step 4: Filter by UBERON labels + quality criteria
    // -------------------------------------------------------------------------
    harvester_ch = filter_datasets_process(
        all_datasets_ch,
        uberon_ch.json,
        params.organism
    )

    // -------------------------------------------------------------------------
    // Step 5: Scatter by dataset_id, count normal cells via Census
    // -------------------------------------------------------------------------
    // Split CSV into per-row channel for parallel processing
    dataset_rows_ch = harvester_ch
        .splitCsv(header: true, sep: ',')
        .map { row -> 
            [ row.dataset_id,
              row.first_author,
              row.year,
              row.journal,
              row.total_cell_count
            ]
        }

    normal_counts_ch = count_normal_cells_process(
        dataset_rows_ch,
        uberon_ch.json,
        params.min_age ?: 15
    )

    // Collect all per-dataset results and merge
    merged_ch = normal_counts_ch
        .collectFile(
            name: "${organ_slug}_with_normal_counts.csv",
            keepHeader: true,
            storeDir: "${params.outdir}"
        )

    // -------------------------------------------------------------------------
    // Step 6: Final cleanup - remove 0 normal cell datasets
    // -------------------------------------------------------------------------
    final_cleanup_process(merged_ch, organ_slug)

}
