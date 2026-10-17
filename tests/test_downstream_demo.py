"""Numerical contracts and real Workbench downstream integration."""
import csv
import json
from pathlib import Path
import shutil
import sys

import nibabel as nib
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from catalog import source_file
from examples.downstream_demo import (extract_regions, run_demo,
                                      synthetic_measurement, verify_extraction)


@pytest.fixture
def toy_atlas():
    # Sparse label IDs, unequal region sizes and deliberately huge excluded values.
    labels = np.array([0, 2, 2, 9, 9, 9, 15])
    table = {0: {'name': 'background'}, 2: {'name': 'region A'},
             9: {'name': 'region B'}, 15: {'name': 'corpuscallosum'},
             23: {'name': 'empty region'}}
    values = np.array([999., 1., 3., -2., 4., 10., 9999.])
    return labels, table, values


def test_vertex_means_exclusions_names_and_empty_regions(toy_atlas):
    labels, table, values = toy_atlas
    rows = extract_regions(labels, table, values, {'corpuscallosum'})
    assert [r['region_id'] for r in rows] == [2, 9, 23]
    assert [r['region_name'] for r in rows] == ['region A', 'region B', 'empty region']
    assert [r['vertex_count'] for r in rows] == [2, 3, 0]
    assert rows[0]['mean_value'] == 2
    assert rows[1]['mean_value'] == 4
    assert np.isnan(rows[2]['mean_value'])
    assert all(verify_extraction(labels, table, values, rows, {'corpuscallosum'}).values())
    rows[0]['mean_value'] += 1
    with pytest.raises(AssertionError):
        verify_extraction(labels, table, values, rows, {'corpuscallosum'})


@pytest.mark.parametrize('bad_values', [np.zeros(6), np.zeros((7, 1)), np.full(7, np.nan)])
def test_bad_measurements_rejected(toy_atlas, bad_values):
    labels, table, _ = toy_atlas
    with pytest.raises(ValueError):
        extract_regions(labels, table, bad_values)


def test_unknown_exclusion_rejected(toy_atlas):
    labels, table, values = toy_atlas
    with pytest.raises(ValueError, match='Excluded names not found'):
        extract_regions(labels, table, values, {'misspelled noncortical label'})


def test_simulation_reproducible_and_independent_of_labels():
    coords = np.arange(60).reshape(20, 3)
    np.testing.assert_array_equal(synthetic_measurement(coords), synthetic_measurement(coords))
    assert not np.array_equal(synthetic_measurement(coords), synthetic_measurement(coords, seed=7))


@pytest.mark.workbench
def test_real_conversion_and_aligned_measurement_reuse(tmp_path):
    if not shutil.which('/usr/bin/wb_command'):
        pytest.skip('/usr/bin/wb_command required for real downstream integration')
    if not source_file('desikan2006', 'L').is_file():
        pytest.skip('Optional TemplateFlow Desikan input not downloaded')
    output = tmp_path/'synthetic'
    summary = run_demo(output)
    assert summary['regional_rows'] == 34
    assert summary['excluded_names'] == ['corpuscallosum']
    assert all(summary['checks'].values())
    metric = nib.load(output/'synthetic_measurement.shape.gii')
    assert metric.agg_data().shape == (32492,)
    assert 'SYNTHETIC' in metric.meta['Description']
    assert 'SYNTHETIC' in (output/'downstream_figure.html').read_text()
    with (output/'regional_values.tsv').open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert set(rows[0]) == {'region_id', 'region_name', 'vertex_count', 'mean_value'}
    assert 'bankssts' in {r['region_name'] for r in rows}
    assert 'corpuscallosum' not in {r['region_name'] for r in rows}
    # The supplied-map path exercises the same extraction using a custom source.
    reused = tmp_path/'supplied'
    supplied = run_demo(reused, atlas='custom', source=source_file('desikan2006', 'L'),
                        measurement_path=output/'synthetic_measurement.shape.gii')
    assert supplied['seed'] is None
    assert (reused/'regional_values.tsv').read_bytes() == (output/'regional_values.tsv').read_bytes()
    assert json.loads((reused/'checks.json').read_text())['checks']['independent_numpy_means_match']
    with pytest.raises(ValueError, match='existing results'):
        run_demo(output)


@pytest.mark.workbench
def test_schaefer_downstream_from_public_download_profile(tmp_path):
    if not shutil.which('/usr/bin/wb_command'):
        pytest.skip('/usr/bin/wb_command required for Schaefer downstream integration')
    summary = run_demo(tmp_path/'schaefer', atlas='schaefer100-7net')
    assert summary['regional_rows'] == 50
    assert all(summary['checks'].values())
