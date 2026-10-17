# Try atlas conversion in a downstream workflow

This separate example asks a concrete software question: can the preserved atlas
names and categorical labels be used to summarize a continuous surface map?
It does not modify the app, the conversion algorithm, or the bundled atlases.

## Run the synthetic example

From the directory containing `app.py`, using the existing environment:

```bash
/usr/bin/wb_command -version
./.venv/bin/python prepare_demo.py
./.venv/bin/python examples/downstream_demo.py --wb /usr/bin/wb_command
./.venv/bin/python -m pytest -q
```

The default uses the local **left Schaefer-100/7-network atlas**, converts it through
`converter.convert`, and simulates a continuous map on the matching inflated
fsLR32k reference mesh (32,492 vertices). The map is a coordinate gradient plus
noise from NumPy's fixed seed **20261016**. It is **SYNTHETIC**, in arbitrary units:
not participant MRI, not a model of any biological process. It is constructed
without using region IDs. No new dependencies are required. GitHub excludes
atlas/reference data and generated outputs. See
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) before obtaining data.
The default requires only the standard `prepare_demo.py` download setup.
Desikan/Destrieux remain explicit choices; their optional
`prepare_demo.py --include-templateflow` route requires upstream terms review.

Default outputs are in `examples/output/schaefer-L-synthetic/`:

| Output | Produced by | Meaning |
|---|---|---|
| `converted/hemi-L_space-fsLR_den-32k_atlas.label.gii` | Existing app converter | Categorical converted atlas with original names/colours |
| `converted/labels.tsv` | Existing app converter | Full label dictionary and source/target assignment counts, including noncortical labels |
| `converted/conversion_report.json`, `converted/report.html` | Existing app converter | Conversion provenance, warnings, compatibility checks |
| `converted/workbench_labels.txt`, `converted/workbench_file_information.txt` | Existing app converter | Workbench export/read results |
| `synthetic_measurement.shape.gii` | Downstream example | Simulated continuous measurement in reference-mesh vertex order |
| `regional_values.tsv` | Downstream example | `region_id`, `region_name`, `vertex_count`, `mean_value` |
| `downstream_figure.html` | Downstream example | Self-contained interactive measurement surface and regional mean bars; open in a browser |
| `checks.json`, `README.md` | Downstream example | Numerical check results, provenance, exclusions and interpretation |

Background ID 0 is excluded, leaving 50 left-hemisphere Schaefer regions.
When Desikan is explicitly selected, **corpuscallosum** is also excluded,
leaving 34 cortical regions. Means are ordinary arithmetic vertex means, **not area
weighted**. The converter's use of area metrics for label resampling does not
make downstream means area weighted. Dictionary entries with no target vertices
are retained as count 0 and mean `NaN`; they must not be interpreted as zero
measurements. Nonfinite measurement data are rejected; this example does not
silently impute or omit missing observations. The surface panel shows the full
measurement, including vertices excluded from regional extraction.

Checks compare source and target dictionaries, measurement/mesh/atlas counts,
regional names, and aggregation against independent direct NumPy masked means.
A deliberately shortened measurement must raise an error. These checks execute
on every run, with outcomes saved in `checks.json`; tests also use a small atlas
with known means and extreme excluded values. Matching counts alone cannot
prove spatial alignment, hemisphere, topology or vertex ordering.

For another run, choose a new output directory; existing output is never overwritten:

```bash
./.venv/bin/python examples/downstream_demo.py --wb /usr/bin/wb_command \
  --hemi R --output examples/output/schaefer-R-synthetic
```

Other bundled catalog IDs are accepted via `--atlas` (see `--help`). Destrieux's
`Medial_wall` is also explicitly excluded when present. The default seed is fixed;
`checks.json` records dependency versions and input/mesh hashes for reproducibility.

## Repeat with a researcher's custom atlas and aligned map

1. Obtain the researcher's own **existing fsaverage5** atlas for one hemisphere:
   a `.annot` or `.label.gii` with 10,242 vertices, integer labels and original
   names/colours, explicit background 0. A native-subject annotation, MRI volume
   or picture is not supported. Confirm its space and hemisphere from provenance,
   not just its filename or vertex count.
2. Obtain a **continuous measurement already aligned to the matching fsLR32k
   template**, same hemisphere and exact vertex correspondence as the bundled
   target reference (see mesh path/hash and converter references in the reports).
   Use one GIFTI array, 32,492 values, SHAPE or NONE intent. The example does not
   project volumes, register native surfaces, resample measurements or repair
   vertex order. Inflation changes display coordinates, not vertex correspondence.
   Verify the registration pipeline and inspect alignment using appropriate
   anatomical landmarks/reference data before interpreting any regional result.
3. Inspect the custom dictionary for noncortical labels. Background 0 is always
   excluded; exact `corpuscallosum` and `Medial_wall` names are excluded when
   present. Supply any other noncortical names using repeated `--exclude-name`.
   Names must match exactly; an unknown exclusion fails rather than silently
   leaving unwanted vertices in the summary. Renamed Desikan corpus-callosum
   labels must be explicitly excluded by their actual names.
4. Run, replacing the example absolute paths with actual files:

```bash
./.venv/bin/python examples/downstream_demo.py \
  --wb /usr/bin/wb_command --atlas custom --hemi L \
  --source /absolute/path/lh.custom_fsaverage5.annot \
  --measurement /absolute/path/measurement_hemi-L_fsLR32k.shape.gii \
  --output examples/output/custom-L
```

For additional noncortical labels, append e.g. `--exclude-name 'my_non_cortical_label'`
using a name actually in the dictionary. Omit `--measurement` only if you want
another **synthetic** test, not results from the real map. User-supplied maps stay
external; the report records their absolute path and SHA-256, not a copy. No
simulated-measurement file is produced in supplied-map mode. Keep sensitive
outputs and identifying regional names/paths in an appropriate local location.

5. Inspect `converted/conversion_report.json` and any parcel disappearance
   warnings, the downstream exclusions, and `regional_values.tsv`. Compare at
   least a few regions with the researcher's existing workflow and resolve
   discrepancies in registration, masking, label IDs and averaging rules. A
   direct independent calculation for a region is:

```python
import nibabel as nib
import numpy as np

labels = nib.load('examples/output/custom-L/converted/hemi-L_space-fsLR_den-32k_atlas.label.gii').agg_data()
measurement = nib.load('/absolute/path/measurement_hemi-L_fsLR32k.shape.gii').agg_data()
region_id = 1  # replace with a retained region_id from regional_values.tsv
assert labels.shape == measurement.shape  # necessary, not proof of alignment
mean_value = np.mean(measurement[labels == region_id], dtype=np.float64)
```

If Workbench is missing/failing, confirm `/usr/bin/wb_command -version` first.
For missing reference meshes, restore the bundle or run
`./.venv/bin/python prepare_demo.py`. Wrong measurement lengths and nonfinite
values fail explicitly. Existing output directories require a new `--output`.
No inference about alignment is made from passing these checks.

## What usefulness can and cannot mean here

**Software functionality:** the synthetic run demonstrates that the existing
converter can produce a readable named categorical atlas, and that downstream
code can use it to compute reproducible regional means, write a table and draw
a figure. Numerical agreement verifies extraction arithmetic for these inputs.

**Anatomical accuracy:** neither simulated values nor metadata/count checks
establish that labels delineate the intended anatomy. That needs independent
registration/anatomical validation using appropriate reference data and expert
review. Do not interpret this synthetic example as participant results.

**Research demand:** synthetic data cannot establish demand. Ask real researchers
to repeat the task with their own appropriately aligned atlas and measurements.
Record whether they complete it, assistance/errors encountered, time and effort
relative to their current workflow, whether names/colours and outputs meet their
needs, and whether they choose to use it again. Report actual observations and
limitations; do not substitute generated data or invented participant outcomes
for user evidence. No user-study or demand result is claimed here.
