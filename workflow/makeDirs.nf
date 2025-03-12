process makeDirs {
    tag 'make_directories'

    output:
        path "${params.datadir}", emit: datadir
        path "${params.outdir}", emit: outdir
        path "${params.collections_split}", emit: collections_dir
        path "${params.datasets_split}", emit: datasets_dir

    publishDir "${params.datadir}", mode: 'copy'
    publishDir "${params.outdir}", mode: 'copy'
    publishDir "${params.collections_split}", mode: 'copy'
    publishDir "${params.datasets_split}", mode: 'copy'

    script:
    """
    echo "Creating directories:"
    echo " - Data directory: ${params.datadir}"
    echo " - Results directory: ${params.outdir}"
    echo " - Collections split directory: ${params.collections_split}"
    echo " - Datasets split directory: ${params.datasets_split}"

    mkdir -p "${params.datadir}"
    mkdir -p "${params.outdir}"
    mkdir -p "${params.collections_split}"
    mkdir -p "${params.datasets_split}"
    """
}
