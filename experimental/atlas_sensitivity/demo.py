"""Real author-distributed BigBrain/MRI gradient comparison; no map transformations."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request

import nibabel as nib
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from atlas_sensitivity import analyze_maps, continuous_values, interactive_report, write_tsv

HERE = Path(__file__).resolve().parent
X_FILE = 'tpl-fsaverage_hemi-L_den-164k_desc-Hist_G1.shape.gii'
Y_FILE = 'tpl-fsaverage_hemi-L_den-164k_desc-Micro_G1.curv'
AREA_FILE = 'fsaverage.L.midthickness_va_avg.164k_fsavg_L.shape.gii'
AUTHOR_SPHERE = 'tpl-fsaverage_hemi-L_den-164k_desc-sphere.surf.gii'
CBIG_SPHERE = 'fsaverage_std_sphere.L.164k_fsavg_L.surf.gii'
X_NAME = 'BigBrain Hist_G1 (dimensionless gradient)'
Y_NAME = 'MRI Micro_G1 (dimensionless qT1-derived gradient)'
SOURCES = {
    'author_repository': 'https://github.com/caseypaquola/BigBrainWarp/tree/68b068fbb93df49eb1339bf7a038876b4412577c',
    'common_surface_documentation': 'https://bigbrainwarp.readthedocs.io/en/latest/pages/tutorial_gradients.html',
    'map_definitions': 'https://bigbrainwarp.readthedocs.io/en/latest/pages/toolbox_contents.html',
    'bigbrainwarp_citation': 'https://doi.org/10.7554/eLife.70119',
    'bigbrain_citation': 'https://doi.org/10.1126/science.1235381',
    'mri_dataset_citation': 'https://doi.org/10.1038/s41597-022-01682-y',
    'schaefer_citation': 'https://doi.org/10.1093/cercor/bhx179',
    'area_documentation': 'https://github.com/ThomasYeoLab/CBIG/blob/634f676630929a71297852d01dd92a287103e861/data/templates/surface/standard_mesh_atlases_20170508/00_README.txt',
}
LIMITATIONS = ('Experimental descriptive estimates only. Different parcellations summarize different regional units. '
               'No ordinary correlation p-values, statistical significance, validated robustness, anatomical accuracy '
               'or biological confirmation. Spatial autocorrelation and source-population differences are not modeled. '
               'Gradient signs and values are used as distributed; they are not direct cellular density or raw T1 measurements. '
               'MRI-zero semantics remain unresolved: finite zeros are retained. Reported coverage is numerical under '
               'the declared mask, not evidence of complete biological coverage or valid sampling at every vertex.')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_data(data_dir, download=False):
    """Explicit downloads only; fail closed on changed files or missing inputs."""
    data_dir = Path(data_dir)
    records = json.loads((HERE/'data_manifest.json').read_text())
    for item in records:
        path = data_dir/item['filename']
        if not path.is_file():
            if not download:
                raise FileNotFoundError(f'{path} is missing. Explicitly run the CLI with --download after reviewing README source terms.')
            data_dir.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name+'.download')
            try:
                with urllib.request.urlopen(item['url'], timeout=90) as response:
                    temporary.write_bytes(response.read())
                if digest(temporary) != item['sha256']:
                    raise ValueError(f'Download checksum mismatch: {path.name}; do not disable verification.')
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        if digest(path) != item['sha256']:
            raise ValueError(f'Checksum mismatch: {path.name}; existing data were not overwritten.')
    return records


def load_real_inputs(data_dir):
    data_dir = Path(data_dir)
    records = prepare_data(data_dir)
    author, cbig = nib.load(data_dir/AUTHOR_SPHERE), nib.load(data_dir/CBIG_SPHERE)
    coords, faces = author.agg_data()
    ref_coords, ref_faces = cbig.agg_data()
    if not np.array_equal(faces, ref_faces):
        raise ValueError('Author and atlas reference sphere topology differs.')
    distances, indices = cKDTree(ref_coords).query(coords)
    if not np.array_equal(indices, np.arange(len(coords))) or distances.max() > 0.01:
        raise ValueError('Author sphere vertex ordering does not correspond to atlas reference sphere.')
    if author.darrays[0].meta.get('AnatomicalStructurePrimary') != 'CortexLeft':
        raise ValueError('Expected author left-hemisphere sphere metadata.')
    hist_image = nib.load(data_dir/X_FILE)
    # The author GIFTI has AnatomicalStructurePrimary=Invalid. Use its recorded
    # transformation target, the documented filenames, and checked sphere instead.
    hist_metadata = dict(hist_image.meta)
    if 'tpl-fsaverage_hemi-L_den-164k_desc-sphere.surf.gii' not in hist_metadata.get('Provenance', ''):
        raise ValueError('Histological map lacks expected author fsaverage-L target provenance.')
    x, y = continuous_values(data_dir/X_FILE), continuous_values(data_dir/Y_FILE)
    if x.shape != (len(coords),) or y.shape != x.shape or len(x) != 163842:
        raise ValueError('Expected matching author fsaverage 164k left-hemisphere arrays.')
    atlases = {}
    for count in (100, 200, 400):
        path = data_dir/f'lh.Schaefer2018_{count}Parcels_7Networks_order.annot'
        labels, color_table, names = nib.freesurfer.read_annot(path, orig_ids=False)
        names = {index: name.decode('utf-8') for index, name in enumerate(names)}
        if len(names) != count//2+1 or names[0] != 'Background+FreeSurfer_Defined_Medial_Wall':
            raise ValueError(f'Unexpected source dictionary for Schaefer {count}.')
        if not all(name.startswith('7Networks_LH_') for key, name in names.items() if key):
            raise ValueError('Atlas source names do not identify left 7-network Schaefer parcels.')
        if color_table.shape[0] != len(names):
            raise ValueError('Annotation IDs, color-table rows and names disagree.')
        atlases[f'Schaefer{count}-7net'] = dict(labels=labels, names=names,
                                               expected_names=names.copy())
    # All three author atlas backgrounds should identify the same medial wall.
    cortex = next(iter(atlases.values()))['labels'] > 0
    if not all(np.array_equal(atlas['labels'] > 0, cortex) for atlas in atlases.values()):
        raise ValueError('Author atlas cortical support differs; review before analysis.')
    weights = continuous_values(data_dir/AREA_FILE)
    evidence = dict(space='FreeSurfer fsaverage', density='164k (163842 vertices per hemisphere)',
                    hemisphere='L', matching_counts_are_not_alignment_proof=True,
                    identical_sphere_faces=True, nearest_sphere_vertex_indices_identical=True,
                    max_sphere_distance_mm=float(distances.max()), sphere_tolerance_mm=0.01,
                    documentation=SOURCES, histology_gifti_metadata=hist_metadata,
                    histology_intent=int(hist_image.darrays[0].intent),
                    histology_intent_note='Author intent NORMAL (11) retained as input metadata; source documentation defines a gradient, not a z-score.',
                    mri_curv_metadata='No rich metadata; named author fsaverage-L-164k distribution plus common-surface tutorial.',
                    cortical_background_identical_across_atlases=True,
                    validity='Common intersection: author atlas nonbackground cortex, finite x/y, finite positive area. '
                             'Zeros remain numerical values; source curv has no documented extra missing-value sentinel. '
                             'No MRI zero-based exclusion, smoothing, reorientation or transformation performed here.',
                    weighting='HCP group-average midthickness vertex areas distributed with the CBIG fsaverage reference; '
                              'mm^2 area weights, not individual-participant areas. Regional correlations weight regions equally.')
    return x, y, atlases, cortex, weights, records, evidence


def run(data_dir=HERE/'data', output=HERE/'output/real-left'):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose a new or empty output directory; results are not overwritten.')
    x, y, atlases, cortex, weights, records, evidence = load_real_inputs(data_dir)
    tables, summary, common, diagnostics = analyze_maps(x, y, atlases, cortex, weights)
    output.mkdir(parents=True, exist_ok=True)
    for config, rows in tables.items():
        write_tsv(output/f'{config}_regional_values.tsv', rows)
    write_tsv(output/'summary.tsv', summary)
    np.save(output/'common_valid_mask.npy', common)
    interactive_report(tables, summary, X_NAME, Y_NAME).write_html(output/'report.html', include_plotlyjs=True)
    git = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    dirty = subprocess.run(['git', '-C', str(ROOT), 'status', '--porcelain'], capture_output=True, text=True)
    provenance = dict(data_kind='REAL public author-distributed maps; no synthetic replacement',
                      time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      inputs=records, correspondence=evidence, diagnostics=diagnostics,
                      settings=dict(configurations=list(atlases), area_weighted=True, coverage_threshold=None,
                                    common_mask_file='common_valid_mask.npy', common_mask_file_sha256=digest(output/'common_valid_mask.npy'),
                                    zero_values_retained=True, hemisphere='L', map_transforms_performed=False,
                                    correlations='Pearson and tie-aware Spearman descriptive estimates; no p-values'),
                      versions={key: importlib.metadata.version(key) for key in ['numpy','scipy','nibabel','plotly']},
                      python=platform.python_version(), git_commit=git.stdout.strip(), dirty_worktree=bool(dirty.stdout.strip()),
                      code_hashes={name:digest(ROOT/name) for name in ['atlas_sensitivity.py','experimental/atlas_sensitivity/demo.py']},
                      limitations=LIMITATIONS)
    (output/'provenance.json').write_text(json.dumps(provenance, indent=2, allow_nan=False)+'\n')
    (output/'README.md').write_text('# Experimental real-map comparison\n\n'+LIMITATIONS+'\n\n'
        'Source maps: BigBrainWarp Hist_G1 and qT1-derived Micro_G1, author fsaverage 164k left hemisphere. '
        'Both are dimensionless gradients. See provenance.json and the experiment README for source processing and evidence. '
        'Schaefer 100/200/400 are bilateral configuration sizes: this left-hemisphere run has 50/100/200 regional units.\n\n'
        'Regional TSVs retain every source region, including no-valid-data rows with NaN means. Coverage denominators '
        'are full source-region vertices and finite positive reference areas. Summary correlations use regions with at least '
        'one common valid vertex, without a tuned coverage cutoff. common_valid_mask.npy is identical across all configurations. '
        'summary.tsv contains descriptive correlations and coverage; report.html has three interactive scatterplots and a '
        'comparison panel. Weights are group-average midthickness area, not participant-specific physical areas. '
        'Nonfinite values and invalid areas are excluded globally. Finite zeros are retained and counted; author .curv '
        'does not document an additional sentinel convention. No p-values, gradient sign flips or new map transformations.\n')
    return tables, summary, diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=HERE/'data')
    parser.add_argument('--output', type=Path, default=HERE/'output/real-left')
    parser.add_argument('--download', action='store_true', help='Explicitly fetch hash-pinned external files; review README terms first')
    args = parser.parse_args()
    if args.download:
        prepare_data(args.data_dir, download=True)
    _, summary, diagnostics = run(args.data_dir, args.output)
    print('REAL MAPS — experimental descriptive comparison; no p-values')
    for row in summary:
        print(f"{row['configuration']}: n={row['retained_regions']}, Pearson={row['pearson_r']:.6f}, "
              f"Spearman={row['spearman_rho']:.6f}, area coverage={row['weight_coverage']:.6f}")
    print('Checks:', json.dumps(diagnostics))
    print('Outputs:', args.output.resolve())


if __name__ == '__main__':
    main()
