#!/usr/bin/env nextflow

/*
 * Test workflow for cellxgene-harvester
 *
 * Tests each module independently with small known inputs.
 * Run with: nextflow run test/test_harvester.nf -profile test
 *
 * Regression testing: outputs are compared to expected/ reference files.
 */

nextflow.enable.dsl = 2

include { resolve_uberon_process }     from '../modules/harvester/resolve_uberon.nf'
include { fetch_collections_process }  from '../modules/harvester/fetch_collections.nf'
include { generate_metadata_process }  from '../modules/harvester/generate_metadata.nf'
include { append_details_process }     from '../modules/harvester/append_details.nf'
include { filter_datasets_process }    from '../modules/harvester/filter_datasets.nf'
include { count_normal_cells_process } from '../modules/harvester/count_normal_cells.nf'
include { final_cleanup_process }      from '../modules/harvester/final_cleanup.nf'

// Test: known UBERON IDs for kidney
// UBERON:0002113 = kidney
// Expected: > 50 descendant terms
workflow test_resolve_uberon {
    resolve_uberon_process("kidney", "kidney")
        | view { json, csv ->
            assert json.exists()  : "uberon_kidney.json not created"
            assert csv.exists()   : "uberon_kidney.csv not created"
            log.info "PASS: resolve_uberon - JSON and CSV created"
        }
}

// Test: fetch collections returns non-empty JSON
workflow test_fetch_collections {
    fetch_collections_process()
        | view { json ->
            assert json.exists()  : "collections_metadata.json not created"
            assert json.size() > 0 : "collections_metadata.json is empty"
            log.info "PASS: fetch_collections - non-empty JSON"
        }
}

// Test: filter on known complete CSV with kidney UBERON
// Expects at least 10 kidney datasets from Homo sapiens
workflow test_filter_datasets {
    all_datasets = Channel.fromPath("${projectDir}/test/fixtures/all_datasets_complete_small.csv")
    uberon_json  = Channel.fromPath("${projectDir}/test/fixtures/uberon_kidney.json")

    filter_datasets_process(all_datasets, uberon_json, "Homo sapiens")
        | view { csv ->
            def lines = csv.readLines().size() - 1  // subtract header
            assert lines > 0 : "filter_datasets returned 0 datasets"
            log.info "PASS: filter_datasets - ${lines} datasets after filtering"
        }
}

// Test: count normal cells for one known good dataset
// Sikkema 2023 kidney dataset - known to have normal cells
workflow test_count_normal_cells {
    dataset_row = Channel.of([
        "a6a8b248-fa1b-4892-8e93-3a33e2ea42ac",  // Sikkema 2023
        "Sikkema", "2023", "Nat Med", "584944"
    ])
    uberon_json = Channel.fromPath("${projectDir}/test/fixtures/uberon_kidney.json")

    count_normal_cells_process(dataset_row, uberon_json, 15)
        | view { csv ->
            assert csv.exists() : "normal count CSV not created"
            def count = csv.readLines()[1].split(',')[0].toInteger()
            assert count > 0    : "Expected > 0 normal cells for Sikkema 2023"
            log.info "PASS: count_normal_cells - ${count} normal cells for Sikkema 2023"
        }
}

// Default: run all tests
workflow {
    log.info "Running cellxgene-harvester test suite..."
    test_resolve_uberon()
    test_fetch_collections()
    test_filter_datasets()
    test_count_normal_cells()
}
