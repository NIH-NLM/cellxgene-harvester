from setuptools import setup, find_packages

setup(
    name="scrnaseq_silhouette_score",
    version="1.0",
    author="Anne Deslattes Mays",
    author_email="adeslat@scitechcon.org",
    description="A Nextflow pipeline to analyze scRNA-seq datasets from CellxGene using silhouette scores.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/scrnaseq_silhouette_score",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "numpy",
        "pandas",
        "scanpy",
        "scikit-learn",
        "requests",
        "jupyterlab",
        "matplotlib",
        "seaborn",
        "sphinx",
        "sphinx-rtd-theme",
        "sphinx-autodoc-typehints"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "run_scrnaseq_pipeline=bin.compute_silhouette:main",
        ],
    },
)
