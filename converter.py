"""A narrow, label-preserving fsaverage5 -> fsLR32k converter.

Registration is supplied by neuromaps-distributed reference spheres; names and
colours never drive the mapping. No anatomical accuracy is inferred here.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
from neuromaps.images import annot_to_gifti

LABEL_INTENT = nib.nifti1.intent_codes['NIFTI_INTENT_LABEL']


def declared_filename_hemi(filename):
    name = Path(filename).name
    left = name.startswith('lh.') or bool(re.search(r'(?:^|_)hemi-L(?:_|\.)',name))
    right = name.startswith('rh.') or bool(re.search(r'(?:^|_)hemi-R(?:_|\.)',name))
    if left and right:
        raise ValueError('Filename contains conflicting hemisphere labels.')
    return 'L' if left else 'R' if right else None


def check_hemisphere(filename, hemi):
    detected = declared_filename_hemi(filename)
    if detected and detected != hemi:
        raise ValueError(f'Hemisphere mismatch: filename indicates {detected}, but {hemi} was selected.')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def label_dictionary(img):
    return {int(x.key): {'name': x.label, 'rgba': [x.red, x.green, x.blue, x.alpha]}
            for x in img.labeltable.labels}


def validate_label_image(img, expected_vertices=10242):
    if not isinstance(img, nib.gifti.GiftiImage) or len(img.darrays) != 1:
        raise ValueError('Provide one GIFTI label map, with exactly one data array.')
    arr = np.asarray(img.darrays[0].data)
    if arr.ndim != 1 or len(arr) != expected_vertices:
        raise ValueError(f'Expected {expected_vertices} vertices in fsaverage5; got {arr.shape}. '
                         'Vertex count alone cannot establish reference space.')
    if img.darrays[0].intent != LABEL_INTENT:
        raise ValueError('Input must have LABEL intent. Continuous metrics are not supported.')
    if not np.issubdtype(arr.dtype, np.integer) or np.any(arr < 0):
        raise ValueError('Region IDs must be nonnegative integers; background must be 0.')
    table = label_dictionary(img)
    if len(table) != len(img.labeltable.labels):
        raise ValueError('Duplicate keys in label table.')
    absent = sorted(set(map(int, np.unique(arr))) - set(table))
    if absent:
        raise ValueError(f'Missing original label dictionary entries: {absent}. Cannot guess names.')
    if 0 not in table:
        raise ValueError('An explicit background entry with ID 0 is required.')
    if any(k != 0 and v['name'] == '???' for k,v in table.items()):
        raise ValueError('The Workbench unassigned name ??? is reserved for background ID 0.')
    for key, item in table.items():
        if not item['name']:
            raise ValueError(f'Empty label name for ID {key}.')
        rgba = item['rgba']
        if any(c is None or not np.isfinite(c) or not 0 <= c <= 1 for c in rgba):
            raise ValueError(f'ID {key} has missing or invalid RGBA colour metadata.')
    if not np.any(arr != 0):
        raise ValueError('Input contains only background.')
    return arr, table


def load_source(path):
    path = Path(path)
    if path.suffix == '.annot':
        # FreeSurfer annot stores RGB-packed codes; neuromaps normalizes them
        # to parcel indices and sets recognized background to 0.
        img, = annot_to_gifti(str(path))
    elif str(path).endswith('.label.gii'):
        img = nib.load(path)
    else:
        raise ValueError('Supported inputs: FreeSurfer .annot or GIFTI .label.gii.')
    validate_label_image(img)
    return img


def required_reference_paths(data_dir, hemi):
    if hemi not in ('L', 'R'):
        raise ValueError('Hemisphere must be L or R.')
    root = Path(data_dir).resolve() / 'atlases'
    src, trg = root / 'fsaverage', root / 'fsLR'
    paths = {
        'source_sphere': src / f'tpl-fsaverage_den-10k_hemi-{hemi}_sphere.surf.gii',
        'source_area': src / f'tpl-fsaverage_den-10k_hemi-{hemi}_desc-vaavg_midthickness.shape.gii',
        'source_mask': src / f'tpl-fsaverage_den-10k_hemi-{hemi}_desc-nomedialwall_dparc.label.gii',
        'target_sphere': trg / f'tpl-fsLR_space-fsaverage_den-32k_hemi-{hemi}_sphere.surf.gii',
        'target_area': trg / f'tpl-fsLR_den-32k_hemi-{hemi}_desc-vaavg_midthickness.shape.gii',
        'target_mask': trg / f'tpl-fsLR_den-32k_hemi-{hemi}_desc-nomedialwall_dparc.label.gii',
    }
    return paths


def reference_paths(data_dir, hemi):
    paths = required_reference_paths(data_dir, hemi)
    missing = [str(x) for x in paths.values() if not x.is_file()]
    if missing:
        raise FileNotFoundError('Missing reference files. Run prepare_demo.py first.\n' + '\n'.join(missing))
    for key, count in [('source_sphere', 10242), ('target_sphere', 32492)]:
        sphere = nib.load(paths[key])
        if sphere.darrays[0].data.shape != (count, 3):
            raise ValueError(f'Unexpected reference mesh shape for {key}.')
    return paths


def wb_run(executable, args):
    try:
        env = os.environ.copy()
        env['OMP_NUM_THREADS'] = '2'
        result = subprocess.run([str(executable), *map(str, args)], env=env,
                                capture_output=True, text=True, check=True, timeout=180)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError('Workbench failed: ' + exc.stderr[-3000:]) from exc
    return result.stdout.strip()


def check_workbench(wb):
    executable = shutil.which(str(wb))
    if not executable:
        raise FileNotFoundError(f'Workbench executable not found or not executable: {wb}')
    # Keep interface setup checks bounded even for a broken launcher.
    result = subprocess.run([executable, '-version'], capture_output=True,
                            text=True, check=True, timeout=10)
    return executable, result.stdout.strip()


def display_mesh_paths(data_dir, hemi):
    root = Path(data_dir).resolve() / 'atlases'
    return (root / 'fsaverage' / f'tpl-fsaverage_den-10k_hemi-{hemi}_inflated.surf.gii',
            root / 'fsLR' / f'tpl-fsLR_den-32k_hemi-{hemi}_inflated.surf.gii')


def setup_issues(data_dir, hemi, wb, source, uploaded=False):
    """Return actionable setup blockers without creating or changing files."""
    issues = []
    try:
        check_workbench(wb)
    except (OSError, subprocess.SubprocessError) as exc:
        issues.append(f'Workbench could not run -version: {exc}. On Ubuntu run '
                      'sudo apt install connectome-workbench, then which wb_command and '
                      'wb_command -version. Set the resulting path in Advanced runtime settings. '
                      'If a launcher fails, retain its shared libraries and check its terminal error.')
    for path in required_reference_paths(data_dir, hemi).values():
        if not path.is_file():
            issues.append(f'Missing reference file: {path}. Restore the bundled file or run '
                          './.venv/bin/python prepare_demo.py from the project directory; '
                          'check Reference-data directory in Advanced runtime settings.')
    for path in display_mesh_paths(data_dir, hemi):
        if not path.is_file():
            issues.append(f'Missing display mesh: {path}. Restore the bundled file or run '
                          './.venv/bin/python prepare_demo.py; check Reference-data directory.')
    if source is None and not uploaded:
        issues.append('Select an existing fsaverage5 .annot or .label.gii file in Upload my atlas.')
    elif source is not None and not Path(source).is_file():
        issues.append(f'Missing input atlas: {source}. Restore this file from the project bundle '
                      'or download it with prepare_demo.py (TemplateFlow atlases require --include-templateflow and terms review); see README.')
    return issues


def convert(source, output_dir, hemi, data_dir, wb='wb_command'):
    check_hemisphere(source, hemi)
    executable, wb_version = check_workbench(wb)
    source, output_dir = Path(source).resolve(), Path(output_dir).resolve()
    # Output paths must not overwrite user-supplied source files or past runs.
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('Choose a new or empty output directory; previous files will not be overwritten.')
    img = load_source(source)
    source_values, source_table = validate_label_image(img)
    refs = reference_paths(data_dir, hemi)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f'hemi-{hemi}_space-fsLR_den-32k'
    out_file = output_dir / f'{stem}_atlas.label.gii'
    with tempfile.TemporaryDirectory(prefix='atlas_rescue_') as tmp:
        tmp = Path(tmp)
        src_gii, resampled, masked = [tmp / x for x in ['source.label.gii', 'resampled.label.gii', 'masked.label.gii']]
        working = copy.deepcopy(img)
        # Workbench locates its unassigned label by the reserved name ???.
        # Keep it at the explicit background ID instead of introducing ID 51,
        # for example. Restore the original background name in the final file.
        for entry in working.labeltable.labels:
            if entry.key == 0:
                entry.label = '???'
        nib.save(working, src_gii)
        wb_run(executable, ['-label-resample', src_gii, refs['source_sphere'], refs['target_sphere'],
                           'ADAP_BARY_AREA', resampled, '-area-metrics', refs['source_area'],
                           refs['target_area'], '-current-roi', refs['source_mask']])
        # This is a LABEL mask, rather than the metric-mask in neuromaps 0.0.7.
        wb_run(executable, ['-label-mask', resampled, refs['target_mask'], masked])
        result = nib.load(masked)
        for entry in result.labeltable.labels:
            if entry.key == 0:
                entry.label = source_table[0]['name']
        target_values, target_table = validate_label_image(result, 32492)
        if set(target_table) != set(source_table):
            raise RuntimeError('Conversion changed label dictionary keys.')
        for key, entry in source_table.items():
            if entry['name'] != target_table[key]['name'] or not np.allclose(
                    entry['rgba'], target_table[key]['rgba'], atol=1e-6, rtol=0):
                raise RuntimeError(f'Name/colour dictionary changed for ID {key}.')
        if not set(np.unique(target_values)).issubset(set(np.unique(source_values)) | {0}):
            raise RuntimeError('Unexpected parcel IDs appeared.')
        target_mask = nib.load(refs['target_mask']).agg_data()
        if np.any(target_values[target_mask <= 0] != 0):
            raise RuntimeError('Non-background labels appear outside target cortical mask.')
        nib.save(result, out_file)
        # Validate by consuming the actual saved file with Workbench.
        wb_run(executable, ['-label-export-table', out_file, output_dir / 'workbench_labels.txt'])
        exported = (output_dir / 'workbench_labels.txt').read_text()
        # Workbench can omit the transparent unassigned/background entry from
        # its text export. Background metadata was already checked in GIFTI.
        if not exported.strip() or any(entry['name'] not in exported.splitlines()
                                       for key,entry in source_table.items() if key != 0):
            raise RuntimeError('Workbench exported an empty or incomplete name table.')
        info = wb_run(executable, ['-file-information', out_file])
        (output_dir / 'workbench_file_information.txt').write_text(info)

    source_ids = set(map(int, np.unique(source_values))) - {0}
    target_ids = set(map(int, np.unique(target_values))) - {0}
    disappeared = sorted(source_ids - target_ids)
    rows = []
    for key, entry in sorted(source_table.items()):
        rows.append({'index': key, 'name': entry['name'],
                     **dict(zip(['red','green','blue','alpha'], entry['rgba'])),
                     'source_vertices': int(np.count_nonzero(source_values == key)),
                     'target_vertices': int(np.count_nonzero(target_values == key))})
    with (output_dir / 'labels.tsv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter='\t')
        writer.writeheader(); writer.writerows(rows)
    report = {
        'status': 'passed_with_warnings' if disappeared else 'passed',
        'source': {'filename': source.name, 'sha256': sha256(source),
                   'declared_space': 'fsaverage5', 'vertices': len(source_values), 'hemisphere': hemi},
        'target': {'space': 'fsLR', 'density': '32k', 'vertices': len(target_values),
                   'filename': out_file.name, 'sha256': sha256(out_file)},
        'source_parcels_present': len(source_ids), 'target_parcels_present': len(target_ids),
        'parcels_without_target_vertices': disappeared,
        'checks': {'label_intent': True, 'dictionary_keys_preserved': True,
                   'names_preserved': True, 'rgba_preserved_within_1e-6': True,
                   'no_new_region_ids': True, 'target_medial_wall_masked': True,
                   'workbench_label_export_succeeded': True, 'workbench_file_read_succeeded': True},
        'method': 'Workbench ADAP_BARY_AREA label resampling with vertex-area metrics and cortical masks',
        'background_handling': 'ID 0 temporarily named ??? for Workbench; original name restored after label-mask.',
        'versions': {k: importlib.metadata.version(k) for k in ['neuromaps','nibabel','numpy']},
        'workbench_version': wb_version,
        'reference_files': {k: {'filename': v.name, 'sha256': sha256(v)} for k,v in refs.items()},
        'limitations': ['Source space and hemisphere are user declarations, not proven by vertex count.',
                        'Checks establish metadata and file compatibility, not anatomical accuracy.',
                        'Vertex counts are sampling counts, not physical area estimates.',
                        'FreeSurfer annot IDs are normalized by neuromaps; packed RGB codes are not preserved as IDs.',
                        'One hemisphere per job; no automatic CIFTI merge or missing-name reconstruction.']}
    (output_dir / 'conversion_report.json').write_text(json.dumps(report, indent=2))
    (output_dir / 'report.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Conversion report</title>'
        '<h1>Surface atlas conversion checks</h1><p>File compatibility checks; not anatomical validation.</p>'
        '<pre>' + __import__('html').escape(json.dumps(report, indent=2)) + '</pre>')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source'); parser.add_argument('output_dir')
    parser.add_argument('--hemi', required=True, choices=['L','R'])
    parser.add_argument('--data-dir', default='reference-data')
    parser.add_argument('--wb', default='wb_command')
    args = parser.parse_args()
    print(json.dumps(convert(args.source,args.output_dir,args.hemi,args.data_dir,args.wb),indent=2))
