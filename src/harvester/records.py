#!/usr/bin/env python3
"""
Build the JSON record of one dataset from one row of all_datasets_complete.csv.

Step 4 writes the record. Step 5 fills in the empty filtered_ values.

Usage:
    record = new_record(row, organ, filter_choices)
"""

from harvester.io_utils import FACETS, SCHEMA_VERSION, facet_keys

# The only place a " | " joined cell from the CSV is read.
PIPE = " | "

DATASET_TEXT_COLUMNS = (
    "dataset_id", "dataset_version_id", "collection_id", "collection_version_id",
    "collection_name", "dataset_title", "first_author", "journal",
    "doi", "collection_url", "explorer_url", "h5ad_url", "organism", "visibility",
)



def split_cell(text):
    """Turn "a | b" into ["a", "b"]. Empty text gives an empty list."""
    return text.split(PIPE) if text.strip() else []


def to_bool(text):
    """Turn "TRUE", "True" or "true" into True, "FALSE" and so on into False.
    Empty text gives None."""
    if not text.strip():
        return None
    return text.strip().lower() == "true"


def to_int(text):
    """Turn "2022" or "2022.0" into 2022. Empty text gives None."""
    return int(float(text)) if text.strip() else None


def dataset_block(row):
    """The facts about the dataset and its paper."""
    block = {name: row[name] for name in DATASET_TEXT_COLUMNS}
    block["year"] = to_int(row["year"])
    block["is_preprint"] = to_bool(row["is_preprint"])
    return block


def curation_block(row):
    """The values that are set or edited by hand after the first pass.

    A later run of Step 4 keeps the values that are already in the file.
    """
    return {
        "reference": row["reference"],
        "author_cell_type": row["author_cell_type"],
        "embedding": row["embedding"],
    }


def empty_facet(facet):
    """The six keys of one facet with nothing counted yet."""
    keys = facet_keys(facet)
    return {key: [] for key in keys}


def new_record(row, organ, filter_choices):
    """Return the record of one dataset as step 4 writes it.

    Tissue and disease have their source_ values from the CSV. Everything
    filtered_ is empty, and the other facets are empty, until step 5 counts
    the cells in Census.
    """
    record = {
        "schema_version": SCHEMA_VERSION,
        "dataset": dataset_block(row),
        "curation": curation_block(row),
        "organ": organ,
        "filter_choices": filter_choices,
        "source_cell_count": to_int(row["total_cell_count"]),
        "filtered_cell_count": None,
        "source_donor_count": None,
        "filtered_donor_count": None,
        "filtered_h5ad_url": None,
    }
    for facet in FACETS:
        record.update(empty_facet(facet))

    # From the CSV only the ids can be used: its labels are not listed in the order of
    # its ids. A label and a count are filled in Step 5, from the cells.
    for facet, column in (("tissue", "tissue_ontology_term_id"),
                          ("assay", "assay_ontology_term_id"),
                          ("disease", "disease_ontology_term_id")):
        record[f"source_{facet}"] = [
            {"ontology_id": name, "label": None, "source_count": None}
            for name in split_cell(row.get(column, ""))]
    return record
