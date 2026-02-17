# cellxgene-harvester

[![Build and Publish Docker image to GHCR](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml)
[![Build and Deploy Sphinx Documentation](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml)

Harvest, filter, and count normal cells from the [CellxGene Census](https://chanzuckerberg.github.io/cellxgene-census/) using UBERON ontology-based tissue filtering.

> Architecture and engineering by Anne Deslattes Mays (NIH-NLM) with human-prompted AI-assisted development using [Claude](https://claude.ai) (Anthropic).

---

## Installation

```bash
git clone https://github.com/NIH-NLM/cellxgene-harvester
cd cellxgene-harvester
mamba env create -f environment.yml
mamba activate cellxgene
```

---

## Usage

```bash
# Single tissue
nextflow run main.nf \
  --tissue "kidney" \
  --organism "Homo sapiens" \
  --outdir results/kidney

# Multiple tissues combined
nextflow run main.nf \
  --tissue "respiratory system,nose" \
  --organism "Homo sapiens" \
  --outdir results/respiratory
```

See the full API and CLI reference in the documentation.

---

## Profiles

| Profile | Description |
|---------|-------------|
| `local` | Conda environment, no container |
| `docker` | Docker container from GHCR |
| `singularity` | Singularity for HPC |
| `lifebit` | Lifebit CloudOS on AWS |
| `test` | CI/CD regression testing |

---

## Documentation

Full API and CLI documentation is auto-generated with [Sphinx](https://www.sphinx-doc.org/) using `autodoc` and deployed via [GitHub Pages](https://pages.github.com/):

https://nih-nlm.github.io/cellxgene-harvester/

---

## Testing

```bash
nextflow run test/test_harvester.nf -profile test
```

---

## License

MIT License © National Library of Medicine, NIH
