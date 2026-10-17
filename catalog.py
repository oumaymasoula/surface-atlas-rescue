"""Small pinned catalog: three atlas families, not fourteen independent atlases."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent


def entries():
    return json.loads((ROOT/'atlas_catalog.json').read_text())['atlases']


def get_entry(key):
    return next(x for x in entries() if x['id']==key)


def source_file(key, hemi):
    return ROOT/get_entry(key)['files'][hemi]
