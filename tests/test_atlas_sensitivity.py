"""Data-free mathematical checks plus an optional real-data milestone check."""
from pathlib import Path
import sys

import nibabel as nib
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from atlas_sensitivity import (analyze_maps, continuous_values, descriptive_correlations,
                               validate_atlas, interactive_report)


@pytest.fixture
def small_inputs():
    x = np.array([0., 1., 2., np.nan, 4., 5., 6., 7.])
    y = np.array([1., 2., 4., 3., np.inf, 6., 7., 8.])
    weights = np.array([1., 2., 3., 4., 5., 6., 0., 8.])
    names = {0: 'background', 9: 'A', 2: 'B', 7: 'C', 4: 'D', 20: 'empty'}
    labels = np.array([0, 9, 9, 2, 2, 7, 7, 4])
    atlases = {f'config{n}': dict(labels=labels.copy(), names=names.copy(), expected_names=names.copy())
               for n in range(3)}
    atlases['config1']['labels'][-1] = 0  # excluded from EVERY configuration
    return x, y, atlases, np.ones(8, dtype=bool), weights


def test_common_mask_weighted_means_coverage_and_empty_regions(small_inputs):
    x, y, atlases, cortex, weights = small_inputs
    tables, summary, mask, checks = analyze_maps(x, y, atlases, cortex, weights)
    np.testing.assert_array_equal(mask, [False, True, True, False, False, True, False, False])
    a = {row['region_id']: row for row in tables['config0']}
    assert a[9]['region_name'] == 'A'  # sparse IDs and shuffled dictionary order
    assert a[9]['mean_x'] == pytest.approx(1.6)
    assert a[9]['mean_y'] == pytest.approx(3.2)
    assert a[7]['vertex_coverage'] == 0.5
    assert a[4]['weight_coverage'] == 0
    assert a[20]['status'] == a[2]['status'] == 'no_valid_data'
    assert np.isnan(a[20]['mean_x'])
    assert a[20]['total_vertices'] == 0
    assert checks['nonfinite_x'] == checks['nonfinite_y'] == checks['invalid_weights'] == 1
    assert len({row['common_mask_sha256'] for row in summary}) == 1
    assert all(sum(row['valid_vertices'] for row in rows) == mask.sum() for rows in tables.values())
    assert checks['independent_weighted_means_checked']
    for config, rows in tables.items():
        for row in rows:
            indices = [i for i in range(len(x)) if mask[i] and atlases[config]['labels'][i] == row['region_id']]
            if indices:
                direct = sum(weights[i]*x[i] for i in indices)/sum(weights[i] for i in indices)
                assert row['mean_x'] == pytest.approx(direct)


def test_ordinary_means_are_explicit_and_zeros_remain_valid(small_inputs):
    x, y, atlases, cortex, _ = small_inputs
    for atlas in atlases.values():
        atlas['labels'][0] = 9
    tables, summary, common, diagnostics = analyze_maps(x, y, atlases, cortex)
    row = next(row for row in tables['config0'] if row['region_id'] == 9)
    assert row['mean_x'] == 1
    assert common[0] and diagnostics['zero_x_in_common'] == 1
    assert summary[0]['averaging'] == 'ordinary_vertex_mean_not_area_weighted'


def test_id_name_mismatch_and_undefined_ids_rejected(small_inputs):
    x, y, atlases, cortex, weights = small_inputs
    atlases['config0']['names'][9] = 'wrong region name'
    with pytest.raises(ValueError, match='ID-to-name'):
        analyze_maps(x, y, atlases, cortex, weights)
    with pytest.raises(ValueError, match='absent'):
        validate_atlas(np.array([0, 30]), {0: 'background', 2: 'region'}, 2)


@pytest.mark.parametrize('change', ['length', 'categorical_float', 'mask_type', 'no_finite_data'])
def test_invalid_inputs_fail_without_silent_repair(small_inputs, change):
    x, y, atlases, cortex, weights = small_inputs
    if change == 'length':
        y = y[:-1]
    elif change == 'categorical_float':
        atlases['config0']['labels'] = atlases['config0']['labels'].astype(float)
    elif change == 'mask_type':
        cortex = cortex.astype(int)
    else:
        x[:] = np.nan
    with pytest.raises(ValueError):
        analyze_maps(x, y, atlases, cortex, weights)


def test_pearson_and_tied_spearman_without_p_values():
    x = [1., 1., 2., 3.]
    y = [1., 2., 2., 4.]
    pearson, spearman, status = descriptive_correlations(x, y)
    assert pearson == pytest.approx(np.corrcoef(x, y)[0, 1])
    # Explicit average ranks, calculated independently of scipy.rankdata.
    assert spearman == pytest.approx(np.corrcoef([1.5, 1.5, 3, 4], [1, 2.5, 2.5, 4])[0, 1])
    assert status == 'descriptive_only'
    assert np.isnan(descriptive_correlations([1, 1, 1], [1, 2, 3])[0])


def test_continuous_loader_rejects_label_intent(tmp_path):
    image = nib.gifti.GiftiImage(darrays=[nib.gifti.GiftiDataArray(np.array([0, 1], dtype=np.int32), intent='NIFTI_INTENT_LABEL')])
    path = tmp_path/'not_continuous.label.gii'
    nib.save(image, path)
    with pytest.raises(ValueError, match='intent'):
        continuous_values(path)


def test_real_author_maps_if_downloaded(tmp_path):
    from experimental.atlas_sensitivity.demo import HERE, prepare_data, run
    try:
        prepare_data(HERE/'data')
    except FileNotFoundError:
        pytest.skip('Optional real BigBrainWarp data unavailable; run experimental/atlas_sensitivity/demo.py --download')
    tables, summary, diagnostics = run(HERE/'data', tmp_path/'real')
    assert [row['retained_regions'] for row in summary] == [50, 100, 200]
    assert all(row['averaging'] == 'surface_area_weighted' for row in summary)
    assert all('p_value' not in row for row in summary)
    assert len({row['common_mask_sha256'] for row in summary}) == 1
    assert diagnostics['independent_weighted_means_checked']
    fig = interactive_report(tables, summary, 'Hist_G1', 'Micro_G1')
    assert len(fig.data) == 5  # three scatterplots, two correlation comparison series
    assert (tmp_path/'real/provenance.json').is_file()


def test_experimental_ui_missing_data_never_downloads(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    import urllib.request
    def forbid(*args, **kwargs):
        raise AssertionError('UI must never download data')
    monkeypatch.setattr(urllib.request, 'urlopen', forbid)
    app = AppTest.from_file(str(ROOT/'app.py')).run()
    app.radio(key='workflow').set_value('Atlas sensitivity (experimental)').run()
    app.text_input(key='sensitivity_data').set_value(str(tmp_path/'missing')).run()
    assert not app.exception
    assert app.button(key='run_sensitivity').disabled
    assert app.warning
    assert any('--download' in code.value for code in app.code)


def test_real_experimental_ui_if_data_available():
    from streamlit.testing.v1 import AppTest
    from experimental.atlas_sensitivity.demo import HERE, prepare_data
    try:
        prepare_data(HERE/'data')
    except FileNotFoundError:
        pytest.skip('Optional real experimental data unavailable')
    app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=60).run()
    app.radio(key='workflow').set_value('Atlas sensitivity (experimental)').run()
    assert not app.button(key='run_sensitivity').disabled
    app.button(key='run_sensitivity').click().run(timeout=60)
    assert not app.exception and not app.error
    assert app.success
    assert [row['retained_regions'] for row in app.session_state['sensitivity_result'][1]] == [50, 100, 200]
    app.radio(key='workflow').set_value('Atlas conversion').run()
    assert app.selectbox(key='atlas').value == 'schaefer100-7net'
