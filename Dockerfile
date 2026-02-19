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

# Install Python with channels specified
RUN micromamba install -y -n base -c conda-forge python=3.11 pip && \
    micromamba clean --all --yes

# Install all packages via pip
WORKDIR /app/cellxgene-harvester
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir \
        pandas \
        requests \
        "typer[all]" \
        cellxgene-census \
        tiledbsoma && \
    python -m pip install --no-cache-dir .

ENV PYTHONPATH="/app/cellxgene-harvester/src"

ENTRYPOINT ["cellxgene-harvester"]
CMD ["--help"]
