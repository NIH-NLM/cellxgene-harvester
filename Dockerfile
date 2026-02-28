FROM mambaorg/micromamba:1.5.6

LABEL maintainer="nih-nlm"

USER root:root

RUN apt-get update && \
    apt-get install -y git procps && \
    apt-get clean

WORKDIR /app

# Copy repository files
COPY --chown=mambauser:mambauser . /app/cellxgene-harvester

USER mambauser:mambauser

ENV MAMBA_ROOT_PREFIX=/opt/conda \
    PATH=/opt/conda/bin:$PATH \
    DEBIAN_FRONTEND=noninteractive

# Install Python
RUN micromamba install -y -n base -c conda-forge python=3.11 pip && \
    micromamba clean --all --yes

# Pre-install heavy dependencies separately for layer caching.
# cellxgene-census and tiledbsoma are large; pinning them here means
# rebuilds due to source code changes skip this slow layer.
WORKDIR /app/cellxgene-harvester
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir \
        "pandas>=1.5" \
        "requests>=2.28" \
        "typer[all]>=0.9" \
        "cellxgene-census>=1.15" \
        "tiledbsoma>=1.12" && \
    python -m pip install --no-cache-dir .

ENV PYTHONPATH="/app/cellxgene-harvester/src"

# Default entrypoint is the cellxgene-harvester CLI.
# Nextflow modules override this with explicit command arguments.
ENTRYPOINT ["cellxgene-harvester"]
CMD ["--help"]
