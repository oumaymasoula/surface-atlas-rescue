"""Convert an atlas, then summarize a SYNTHETIC map (no participant data).

Run from the project directory:
./.venv/bin/python examples/downstream_demo.py --wb /usr/bin/wb_command
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import nibabel as nib
import numpy as np
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from catalog import entries, source_file
from converter import (check_hemisphere, convert, display_mesh_paths, load_source,
                       sha256, validate_label_image)

SEED = 20261016
LIMITATIONS = ('This demonstrates software functionality, not biological validity, '
               'anatomical accuracy or research demand. Matching vertex counts alone '
               'do not prove spatial alignment or vertex ordering.')
DISCLAIMER = 'SYNTHETIC simulated data, arbitrary units; no participant MRI. ' + LIMITATIONS


def synthetic_measurement(coords, seed=SEED):
    """A coordinate gradient plus seeded noise, unrelated to atlas labels."""
    coords = np.asarray(coords, dtype=np.float64)
    if coords.ndim != 2 or coords.shape[1] != 3 or not np.isfinite(coords).all():
        raise ValueError('Expected finite mesh coordinates with shape (vertices, 3).')
    scaled = (coords - coords.mean(axis=0)) / np.maximum(np.ptp(coords, axis=0), 1e-12)
    values = 2 + scaled @ np.array([0.8, -0.5, 1.2])
    values += np.random.default_rng(seed).normal(0, 0.15, len(coords))
    return values.astype(np.float32)


def extract_regions(labels, table, measurement, excluded_names=()):
    """Ordinary vertex means, NOT area weighted; empty parcels have NaN means.

    Background ID 0 is always excluded. The caller must identify any other
    noncortical labels in a custom dictionary. Nonfinite measurements are rejected.
    """
    labels, measurement = np.asarray(labels), np.asarray(measurement, dtype=np.float64)
    if labels.ndim != 1 or measurement.ndim != 1 or labels.shape != measurement.shape:
        raise ValueError('Measurement and atlas must be 1D with matching vertex counts; '
                         'matching counts alone do not prove spatial alignment.')
    if not np.issubdtype(labels.dtype, np.integer) or np.any(labels < 0):
        raise ValueError('Atlas IDs must be nonnegative integers.')
    if not np.isfinite(measurement).all():
        raise ValueError('Measurement contains NaN/Inf; define a missing-data policy first.')
    if not set(map(int, np.unique(labels))).issubset(table):
        raise ValueError('Atlas contains IDs absent from its dictionary.')
    excluded_names = set(excluded_names)
    unknown = excluded_names - {v['name'] for v in table.values()}
    if unknown:
        raise ValueError(f'Excluded names not found in atlas: {sorted(unknown)}')
    # Aggregate with indexed sums. Verification below uses a separate boolean-mask mean.
    keys = np.array(sorted(table), dtype=np.int64)
    index = np.searchsorted(keys, labels)
    counts = np.bincount(index, minlength=len(keys))
    sums = np.bincount(index, weights=measurement, minlength=len(keys))
    return [dict(region_id=int(key), region_name=table[int(key)]['name'],
                 vertex_count=int(counts[i]),
                 mean_value=float(sums[i] / counts[i]) if counts[i] else float('nan'))
            for i, key in enumerate(keys)
            if key != 0 and table[int(key)]['name'] not in excluded_names]


def verify_extraction(labels, table, measurement, rows, excluded_names):
    """Independent direct NumPy means and an intentional wrong-length input."""
    expected = {key: item['name'] for key, item in table.items()
                if key != 0 and item['name'] not in excluded_names}
    actual = {row['region_id']: row['region_name'] for row in rows}
    if actual != expected or len(rows) != len(expected):
        raise AssertionError('Expected region names/IDs did not survive extraction.')
    for row in rows:
        selected = np.asarray(measurement)[labels == row['region_id']]
        direct = np.mean(selected, dtype=np.float64) if selected.size else np.nan
        np.testing.assert_allclose(row['mean_value'], direct, rtol=1e-12, atol=1e-12)
        if row['vertex_count'] != selected.size:
            raise AssertionError('Regional vertex count differs from direct calculation.')
    try:
        extract_regions(labels, table, measurement[:-1], excluded_names)
    except ValueError as exc:
        if 'matching vertex counts' not in str(exc):
            raise
    else:
        raise AssertionError('Mismatched measurement length was accepted.')
    return dict(vertex_counts_agree=True, expected_region_names_survive=True,
                independent_numpy_means_match=True, mismatched_length_rejected=True)


def save_figure(path, coords, faces, measurement, rows, synthetic, hemi):
    kind = 'SYNTHETIC simulated measurement' if synthetic else 'User-supplied aligned measurement'
    fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'scene'}, {'type': 'xy'}]],
                        column_widths=[0.52, 0.48],
                        subplot_titles=(f'{kind}: fsLR32k {hemi}', 'Regional ordinary vertex means'))
    fig.add_trace(go.Mesh3d(x=coords[:, 0], y=coords[:, 1], z=coords[:, 2],
                           i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
                           intensity=measurement, intensitymode='vertex', colorscale='Viridis',
                           colorbar=dict(title='Value', x=0.46, len=0.65),
                           hovertemplate='Value: %{intensity:.4f}<extra></extra>'), row=1, col=1)
    fig.add_trace(go.Bar(x=[r['mean_value'] for r in rows],
                         y=[r['region_name'] for r in rows], orientation='h',
                         hovertemplate='%{y}: %{x:.5f}<extra></extra>'), row=1, col=2)
    fig.update_layout(title=f'{kind} — downstream software demonstration',
                      height=max(850, 20 * len(rows) + 180), showlegend=False,
                      margin=dict(l=20, r=20, t=100, b=90),
                      scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
                                 aspectmode='data'))
    fig.update_xaxes(title_text='Mean value (not area weighted)', row=1, col=2)
    fig.update_yaxes(autorange='reversed', automargin=True, row=1, col=2)
    fig.add_annotation(text='No anatomical accuracy or research demand established; counts do not prove alignment.',
                       x=0.5, y=-0.08, xref='paper', yref='paper', showarrow=False)
    fig.write_html(path, include_plotlyjs=True, full_html=True)


def run_demo(output, atlas='desikan2006', hemi='L', data_dir=ROOT/'reference-data',
             wb='/usr/bin/wb_command', source=None, measurement_path=None, excluded_names=()):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose a new or empty output directory; existing results are not overwritten.')
    if atlas == 'custom' and source is None:
        raise ValueError('--atlas custom requires --source with an existing fsaverage5 atlas.')
    if atlas != 'custom' and source is not None:
        raise ValueError('Use --atlas custom when providing --source.')
    source = Path(source).resolve() if source else source_file(atlas, hemi)
    source_labels, source_table = validate_label_image(load_source(source))
    excluded_names = set(excluded_names)
    # Also recognize the exact Desikan name in custom dictionaries.
    if atlas == 'desikan2006' or any(v['name'] == 'corpuscallosum' for v in source_table.values()):
        excluded_names.add('corpuscallosum')
    if any(v['name'] == 'Medial_wall' for v in source_table.values()):
        excluded_names.add('Medial_wall')
    mesh_path = display_mesh_paths(data_dir, hemi)[1]
    coords, faces = nib.load(mesh_path).agg_data()
    synthetic = measurement_path is None
    if synthetic:
        measurement = synthetic_measurement(coords)
    else:
        check_hemisphere(measurement_path, hemi)
        image = nib.load(measurement_path)
        if not isinstance(image, nib.gifti.GiftiImage) or len(image.darrays) != 1:
            raise ValueError('Provide a single-array continuous GIFTI measurement map.')
        if image.darrays[0].intent not in (nib.nifti1.intent_codes['NIFTI_INTENT_SHAPE'],
                                          nib.nifti1.intent_codes['NIFTI_INTENT_NONE']):
            raise ValueError('Expected a continuous SHAPE or NONE measurement, not labels.')
        measurement = np.asarray(image.darrays[0].data)
    if measurement.shape != (len(coords),):
        raise ValueError('Measurement must match the fsLR32k reference mesh vertex counts.')
    # Existing application converter; no change to its mapping or masking method.
    report = convert(source, output/'converted', hemi, data_dir, wb)
    labels, table = validate_label_image(nib.load(output/'converted'/report['target']['filename']), 32492)
    if {k: v['name'] for k, v in source_table.items()} != {k: v['name'] for k, v in table.items()}:
        raise AssertionError('Source region names changed during conversion.')
    rows = extract_regions(labels, table, measurement, excluded_names)
    checks = verify_extraction(labels, table, measurement, rows, excluded_names)
    checks['source_names_preserved_by_conversion'] = True
    if atlas == 'desikan2006':
        if len(rows) != 34 or any(r['region_name'] == 'corpuscallosum' for r in rows):
            raise AssertionError('Expected 34 cortical Desikan regions, excluding corpuscallosum.')
        checks['desikan_34_cortical_regions_only'] = True
    with (output/'regional_values.tsv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['region_id', 'region_name', 'vertex_count', 'mean_value'], delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
    if synthetic:
        metric = nib.gifti.GiftiImage(darrays=[nib.gifti.GiftiDataArray(measurement, intent='NIFTI_INTENT_SHAPE')])
        metric.meta['Description'] = DISCLAIMER
        metric.meta['Seed'] = str(SEED)
        nib.save(metric, output/'synthetic_measurement.shape.gii')
    save_figure(output/'downstream_figure.html', coords, faces, measurement, rows, synthetic, hemi)
    summary = dict(data_kind='SYNTHETIC simulated data' if synthetic else 'User-supplied measurement; no inference of validity',
                   seed=SEED if synthetic else None, hemisphere=hemi, atlas=atlas,
                   measurement_vertices=len(measurement), regional_rows=len(rows),
                   excluded_names=sorted(excluded_names), background_excluded=True,
                   averaging='Ordinary vertex mean; not area weighted. Empty regions retain NaN.',
                   source=str(source), source_sha256=sha256(source),
                   mesh=str(mesh_path.resolve()), mesh_sha256=sha256(mesh_path),
                   measurement_file=str(Path(measurement_path).resolve()) if not synthetic else 'synthetic_measurement.shape.gii',
                   measurement_sha256=sha256(measurement_path if not synthetic else output/'synthetic_measurement.shape.gii'),
                   versions={'numpy': np.__version__, 'nibabel': nib.__version__, 'plotly': plotly.__version__},
                   checks=checks, limitations=DISCLAIMER if synthetic else LIMITATIONS)
    (output/'checks.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output/'README.md').write_text(f'''# Downstream example outputs

{summary['data_kind']}. {'Fixed seed: ' + str(SEED) + '.' if synthetic else 'Measurement supplied by the user.'}
No participant results or biological conclusions are generated by the synthetic example.

- `converted/`: outputs from the existing app converter: labelled fsLR32k GIFTI,
  labels.tsv, Workbench read/export checks, JSON and HTML conversion reports.
- `{'synthetic_measurement.shape.gii' if synthetic else summary['measurement_file']}`:
  {'simulated continuous map generated here from matching reference-mesh coordinates plus seeded noise, in arbitrary units' if synthetic else 'external continuous map supplied by the user, not generated by the app'}.
- `regional_values.tsv`: downstream regional means. Background ID 0 and names
  {sorted(excluded_names)} excluded. Ordinary vertex means, NOT area weighted.
  Empty dictionary regions retain vertex_count 0 and mean_value NaN.
- `downstream_figure.html`: self-contained interactive measurement surface and regional summary;
  open in a browser (no server or network required). The surface uses the inflated display mesh.
- `checks.json`: downstream numerical checks, file hashes, versions and provenance.

{summary['limitations']}
Real measurements must already use the matching hemisphere, template registration,
mesh topology and vertex ordering. This example does not align measurement maps.
Software checks passed for {len(rows)} regional rows. Anatomical accuracy requires
independent validation; research demand requires actual users doing their work.
''')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atlas', choices=[e['id'] for e in entries()] + ['custom'], default='desikan2006')
    parser.add_argument('--hemi', choices=['L', 'R'], default='L')
    parser.add_argument('--wb', default='/usr/bin/wb_command')
    parser.add_argument('--data-dir', type=Path, default=ROOT/'reference-data')
    parser.add_argument('--output', type=Path, default=ROOT/'examples/output/desikan-L-synthetic')
    parser.add_argument('--source', type=Path, help='Custom fsaverage5 .annot or .label.gii; use --atlas custom')
    parser.add_argument('--measurement', type=Path, help='Already aligned single-array fsLR32k continuous GIFTI; omit for SYNTHETIC data')
    parser.add_argument('--exclude-name', action='append', default=[], help='Exact noncortical dictionary name; repeat as needed')
    args = parser.parse_args()
    summary = run_demo(args.output, args.atlas, args.hemi, args.data_dir, args.wb,
                       args.source, args.measurement, args.exclude_name)
    print(summary['data_kind'])
    print(f"All {len(summary['checks'])} checks passed; {summary['regional_rows']} regional rows.")
    print(f'Outputs: {args.output.resolve()}')


if __name__ == '__main__':
    main()
