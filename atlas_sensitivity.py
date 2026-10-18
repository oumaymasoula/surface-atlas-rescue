"""Experimental descriptive map comparison; independent of atlas conversion.

Never infers registration from array length. Callers must establish input space,
vertex ordering, hemisphere and meaningful validity conventions from provenance.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import nibabel as nib
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import rankdata


def continuous_values(path):
    path = Path(path)
    if path.suffix == '.curv':
        values = nib.freesurfer.read_morph_data(path)
    else:
        image = nib.load(path)
        if not isinstance(image, nib.gifti.GiftiImage) or len(image.darrays) != 1:
            raise ValueError('Continuous input must contain exactly one GIFTI array or be a FreeSurfer .curv.')
        if image.darrays[0].intent not in (0, nib.nifti1.intent_codes['NIFTI_INTENT_SHAPE'],
                                         nib.nifti1.intent_codes['NIFTI_INTENT_NORMAL']):
            raise ValueError('Continuous input has unsupported intent (categorical LABEL is not continuous).')
        values = image.darrays[0].data
    # Author BigBrainWarp Hist_G1 declares NORMAL (11); its documented meaning
    # remains a gradient, not a claim of a normal-distribution statistic.
    return continuous_array(values)


def continuous_array(values):
    values = np.asarray(values)
    if values.ndim != 1 or not np.issubdtype(values.dtype, np.number) or np.iscomplexobj(values):
        raise ValueError('Continuous values must be a one-dimensional real numeric array.')
    return values.astype(np.float64)


def validate_atlas(labels, names, size, expected_names=None):
    labels = np.asarray(labels)
    if labels.shape != (size,) or not np.issubdtype(labels.dtype, np.integer) or np.any(labels < 0):
        raise ValueError('Atlas must be one nonnegative integer label per measurement vertex.')
    if 0 not in names or any(not isinstance(k, (int, np.integer)) or k < 0 for k in names):
        raise ValueError('Atlas dictionary must use nonnegative integer IDs including background 0.')
    if any(not isinstance(name, str) or not name.strip() for name in names.values()):
        raise ValueError('Every ID needs a nonempty name.')
    if len(set(names.values())) != len(names):
        raise ValueError('Region names must be unique for unambiguous ID-to-name correspondence.')
    if not set(np.unique(labels)).issubset(names):
        raise ValueError('Atlas contains IDs absent from the name dictionary.')
    if expected_names is not None and names != expected_names:
        raise ValueError('ID-to-name correspondence differs from the expected source dictionary.')
    if not np.any(labels > 0):
        raise ValueError('Atlas contains only background.')
    return labels


def descriptive_correlations(x, y):
    """Pearson and tie-aware Spearman estimates only; never computes p-values."""
    x, y = np.asarray(x), np.asarray(y)
    if len(x) < 3:
        return float('nan'), float('nan'), 'fewer_than_three_regions'
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return float('nan'), float('nan'), 'constant_regional_map'
    return (float(np.corrcoef(x, y)[0, 1]),
            float(np.corrcoef(rankdata(x), rankdata(y))[0, 1]), 'descriptive_only')


def analyze_maps(x, y, atlases, cortex_mask, weights=None):
    """Use the identical vertex mask for both maps and every parcellation.

    Nonfinite measurements and nonpositive/nonfinite area weights are excluded
    globally and counted. Numerical zeros in maps remain valid. Dictionary-only
    parcels remain in tables with zero coverage and NaN means. No coverage cutoff
    or correlation-based selection is applied. Regions are equally weighted for
    correlations after within-region area weighting (if supplied).
    """
    x, y = continuous_array(x), continuous_array(y)
    if x.shape != y.shape:
        raise ValueError('Measurement lengths differ; counts alone cannot prove alignment.')
    cortex_mask = np.asarray(cortex_mask)
    if cortex_mask.shape != x.shape or cortex_mask.dtype != np.bool_:
        raise ValueError('Cortex mask must be a boolean array matching the measurements.')
    if not atlases:
        raise ValueError('At least one categorical atlas is required.')
    weighting = 'surface_area_weighted' if weights is not None else 'ordinary_vertex_mean_not_area_weighted'
    w = np.ones(x.shape) if weights is None else continuous_array(weights)
    if w.shape != x.shape:
        raise ValueError('Area weights and measurement lengths differ.')
    area_valid = np.isfinite(w) & (w > 0)
    common = cortex_mask & np.isfinite(x) & np.isfinite(y) & area_valid
    checked = {}
    for config, atlas in atlases.items():
        labels = validate_atlas(atlas['labels'], atlas['names'], len(x), atlas.get('expected_names'))
        checked[config] = labels
        common &= labels != 0
    if not common.any():
        raise ValueError('No common valid cortical vertices remain.')
    mask_hash = hashlib.sha256(common.astype(np.uint8).tobytes()).hexdigest()
    tables, summary = {}, []
    for config, atlas in atlases.items():
        labels, names = checked[config], atlas['names']
        rows = []
        for key, name in sorted(names.items()):
            if key == 0:
                continue
            full = labels == key
            valid = full & common
            total_vertices, valid_vertices = int(full.sum()), int(valid.sum())
            total_weight = float(w[full & area_valid].sum())
            retained_weight = float(w[valid].sum())
            rows.append(dict(region_id=int(key), region_name=name,
                             total_vertices=total_vertices, valid_vertices=valid_vertices,
                             zero_x_vertices=int(((x == 0) & valid).sum()),
                             zero_y_vertices=int(((y == 0) & valid).sum()),
                             vertex_coverage=valid_vertices/total_vertices if total_vertices else 0.,
                             total_weight=total_weight, retained_weight=retained_weight,
                             weight_coverage=retained_weight/total_weight if total_weight else 0.,
                             mean_x=float(np.dot(w[valid], x[valid])/retained_weight) if valid_vertices else float('nan'),
                             mean_y=float(np.dot(w[valid], y[valid])/retained_weight) if valid_vertices else float('nan'),
                             status='retained' if valid_vertices else 'no_valid_data'))
        # Independent summation: np.average with explicit membership indices.
        for row in rows:
            idx = np.flatnonzero((labels == row['region_id']) & common)
            if idx.size:
                np.testing.assert_allclose([row['mean_x'], row['mean_y']],
                                          [np.average(x[idx], weights=w[idx]), np.average(y[idx], weights=w[idx])],
                                          rtol=1e-12, atol=1e-12)
        retained = [row for row in rows if row['valid_vertices']]
        r, rho, status = descriptive_correlations([row['mean_x'] for row in retained],
                                                  [row['mean_y'] for row in retained])
        tables[config] = rows
        total = sum(row['total_vertices'] for row in rows)
        area = sum(row['total_weight'] for row in rows)
        summary.append(dict(configuration=config, regions=len(rows), retained_regions=len(retained),
                            empty_regions=len(rows)-len(retained), common_vertices=int(common.sum()),
                            vertex_coverage=int(common.sum())/total,
                            weight_coverage=sum(row['retained_weight'] for row in rows)/area if area else 0.,
                            min_regional_weight_coverage=min(row['weight_coverage'] for row in rows),
                            pearson_r=r, spearman_rho=rho, estimate_status=status,
                            averaging=weighting, common_mask_sha256=mask_hash))
    diagnostics = dict(total_vertices=len(x), cortex_vertices=int(cortex_mask.sum()),
                       nonfinite_x=int((~np.isfinite(x)).sum()), nonfinite_y=int((~np.isfinite(y)).sum()),
                       invalid_weights=int((~area_valid).sum()), common_vertices=int(common.sum()),
                       zero_x_in_common=int(((x == 0) & common).sum()), zero_y_in_common=int(((y == 0) & common).sum()),
                       common_mask_sha256=mask_hash, averaging=weighting,
                       independent_weighted_means_checked=True)
    return tables, summary, common, diagnostics


def write_tsv(path, rows):
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)


def interactive_report(tables, summary, x_name, y_name):
    fig = make_subplots(rows=2, cols=2, subplot_titles=[*tables.keys(), 'Correlation estimates across different regional units'])
    for index, (config, rows) in enumerate(tables.items()):
        r, c = index//2+1, index%2+1
        retained = [row for row in rows if row['valid_vertices']]
        fig.add_trace(go.Scatter(x=[row['mean_x'] for row in retained], y=[row['mean_y'] for row in retained],
                                 mode='markers', text=[row['region_name'] for row in retained],
                                 customdata=[[row['region_id'], row['weight_coverage']] for row in retained],
                                 hovertemplate='%{text}<br>ID %{customdata[0]}<br>retained weight %{customdata[1]:.3f}<br>x %{x:.5f}<br>y %{y:.5f}<extra></extra>',
                                 name=config), row=r, col=c)
        fig.update_xaxes(title_text=x_name, row=r, col=c)
        fig.update_yaxes(title_text=y_name, row=r, col=c)
    for key, name in [('pearson_r', 'Pearson'), ('spearman_rho', 'Spearman')]:
        fig.add_trace(go.Scatter(x=[row['configuration'] for row in summary], y=[row[key] for row in summary],
                                 mode='lines+markers', name=name), row=2, col=2)
    fig.update_yaxes(title_text='Descriptive estimate (no p-values)', range=[-1, 1], row=2, col=2)
    fig.update_layout(title='EXPERIMENTAL atlas sensitivity — different parcellations summarize different regional units',
                      height=1000, width=1300, margin=dict(t=110, b=90))
    fig.add_annotation(text='No statistical significance, validated robustness, anatomical accuracy or biological confirmation established.',
                       x=0.5, y=-0.12, xref='paper', yref='paper', showarrow=False)
    return fig
