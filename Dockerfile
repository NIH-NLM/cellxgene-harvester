# cellxgene-harvester
# Harvests, filters, and counts normal cells from CellxGene Census
#
# Build:
#   docker build -t ghcr.io/nih-nlm/cellxgene-harvester:1.0.0 .
#
# Run:
#   docker run --rm ghcr.io/nih-nlm/cellxgene-harvester:1.0.0 \
#     python /opt/cellxgene-harvester/src/0_resolve_uberon.py "kidney"

FROM continuumio/miniconda3:24.1.2-0

LABEL org.opencontainers.image.source="https://github.com/NIH-NLM/cellxgene-harvester"
LABEL org.opencontainers.image.description="CellxGene data harvester with UBERON ontology filtering"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /opt/cellxgene-harvester

# Copy environment first for layer caching
COPY environment.yml .

# Create conda environment
RUN conda env create -f environment.yml \
    && conda clean -afy

# Make all RUN commands use the conda env
SHELL ["conda", "run", "-n", "cellxgene", "/bin/bash", "-c"]

# Copy source scripts
COPY src/ ./src/

# Add src/ to PATH so scripts are callable directly
ENV PATH="/opt/cellxgene-harvester/src:${PATH}"
ENV PYTHONPATH="/opt/cellxgene-harvester/src:${PYTHONPATH}"

# Default entrypoint - run with conda env active
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "cellxgene", "python"]
CMD ["--help"]
