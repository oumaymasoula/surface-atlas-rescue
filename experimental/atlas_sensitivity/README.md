# Atlas sensitivity — separate experimental prototype

Compare a fixed pair of **real, author-distributed cortical gradients** across
Schaefer 100, 200 and 400, all using 7 networks. This experiment uses the original
**FreeSurfer fsaverage 164k left hemisphere** (163,842 vertices), not the
application's fsaverage5-to-fsLR conversion route. Neither continuous map nor
categorical atlas is transformed by this prototype. The existing converter is
unchanged. A left-only run has **50, 100 and 200 regional units**, respectively;
100/200/400 name the full bilateral atlas configurations.

This is a descriptive experiment, **not validated robustness, anatomical
accuracy or biological confirmation**. No ordinary correlation p-values or
statistical-significance statements are produced.

## Data, processing, units and correspondence

The chosen fields are `Hist_G1` and `Micro_G1`, the **first** gradients as
provided in [BigBrainWarp](https://github.com/caseypaquola/BigBrainWarp/tree/68b068fbb93df49eb1339bf7a038876b4412577c).
They were chosen before calculating correlations; no gradient sign flipping,
mask optimization, alternative gradient search or atlas selection was performed.
They are not replaced with a raw biological measure or simulated values.

| Field | Origin and author processing | Units / validity |
|---|---|---|
| `tpl-fsaverage_hemi-L_den-164k_desc-Hist_G1.shape.gii` | BigBrain histological staining profiles → patch-wise microstructure profile covariance, normalized-angle similarity and diffusion embedding; author MSM-based transformation to fsaverage | Dimensionless embedding coordinates; finite zeros are numerical values |
| `tpl-fsaverage_hemi-L_den-164k_desc-Micro_G1.curv` | Group MRI quantitative-T1-derived microstructural gradient from MICs (50 adults), described in the author common-surface tutorial; profiles/patch-wise covariance and embedding on fsaverage | Dimensionless embedding coordinates, **not milliseconds**, T1w/T2w ratio or a direct myelin assay; no rich `.curv` metadata or documented additional sentinel mask |
| `lh.Schaefer2018_{100,200,400}Parcels_7Networks_order.annot` | Original CBIG FreeSurfer5.3/**fsaverage** annotations, downloaded from pinned commit `634f676630929a71297852d01dd92a287103e861` | Categorical index → original name, background 0 is explicitly named `Background+FreeSurfer_Defined_Medial_Wall` |
| `fsaverage.L.midthickness_va_avg.164k_fsavg_L.shape.gii` | HCP group-average midthickness vertex areas distributed with CBIG's standard mesh references | Template area weights (mm²); not individual BigBrain/MICs participant areas |

The author [tutorial](https://bigbrainwarp.readthedocs.io/en/latest/pages/tutorial_gradients.html)
explicitly places the histological and MRI gradients on common fsaverage space.
Its gradient procedure uses downsampled patches and expands gradients back onto
the surface; **163,842 entries do not mean 163,842 independent observations**.
The author [contents and naming conventions](https://bigbrainwarp.readthedocs.io/en/latest/pages/toolbox_contents.html)
specify template and L/R hemispheres. The author warns that histological gradient
ordering differs from some earlier work; `Hist_G1` here is the provided first
axis, not a renamed sensory-fugal axis chosen to improve correspondence.

Actual files add these checks beyond vertex counts:

- Hist_G1's embedded `Provenance` names the author fsaverage-L-164k sphere as its
  transformation target. Its `AnatomicalStructurePrimary` is **Invalid**, and its
  intent is **NORMAL (11)**. Neither is silently treated as authoritative anatomy
  or a z-score. These limitations and the full original metadata are recorded.
- The author sphere declares `CortexLeft`. It has exactly the same face array as
  the CBIG fsaverage sphere. A nearest-neighbor comparison of every sphere vertex
  gives **identical vertex indices**, with maximum Euclidean separation
  **0.008032684 mm** on radius-100 spheres. The predeclared tolerance is 0.01 mm.
  This establishes ordering of the documented reference meshes; it does not
  independently validate the histological registration or a metadata-free MRI field.
- Every atlas has the expected left-hemisphere 7-network names and cardinality;
  original annotation indices, names and colour-table rows remain paired.
- All three author atlas cortical/background supports are identical.

The MRI `.curv` does not encode a registration chain. Its provenance rests on the
named author distribution and explicit common-surface documentation, not on
array length. We inspected author 10k versions but did not use them: the MRI
10k `.curv` lacks a documented resampling chain. Original 164k files avoid adding
an undocumented transformation. No inference of alignment is made for arbitrary
user-supplied files; this first UI prototype only accepts the hash-pinned pair.

## Fixed mask and estimates

The common mask is the intersection of the author atlas cortical supports,
finite values in **both** maps, and finite positive template area weights. It is
computed once and used unchanged for every atlas. Source background 0 (including
the FreeSurfer-defined medial wall) is excluded. No atlas-specific finite-data
mask or preferred-correlation selection is used.

Finite map zeros are retained. There are **420 MRI zeros** inside the common
cortex in this release. The author `.curv` does not document a separate sentinel
convention, so this prototype does not invent one. These zeros are counted in
both per-region outputs and diagnostics. **100% reported retained coverage means
numerical coverage under this declared mask, not proof that every zero reflects
a biological measurement.** Confirm any additional missing-data conventions with
source maintainers before scientific interpretation. No one has been contacted.

Within a region, means are `sum(area * value) / sum(area)` over common vertices.
Weights are the HCP group-average areas described in the
[standard-mesh README](https://github.com/ThomasYeoLab/CBIG/blob/634f676630929a71297852d01dd92a287103e861/data/templates/surface/standard_mesh_atlases_20170508/00_README.txt).
The independent module supports ordinary vertex means when area weights are not
supplied; those are explicitly labelled `ordinary_vertex_mean_not_area_weighted`.
The real demonstration always supplies the matching area metric.

TSVs retain dictionary regions with no common valid data: count 0, NaN means,
`no_valid_data` status and zero coverage. Coverage denominators are full source
region vertices and finite positive source region areas, before common masking.
The current data have no empty regions. No minimum-coverage cutoff is tuned or
applied: a region with any common valid data enters the descriptive comparison.
Nonfinite values are counted and excluded globally, never imputed or separately
filtered by atlas. A completely empty common mask is rejected.

Pearson is computed between regional means; Spearman is Pearson on tie-aware
average ranks. **Regional units have equal weight in correlations**, even though
within-region means use area weights. Constant maps or fewer than three retained
regions produce NaN estimates with an explicit status. No p-values are computed.
Different parcellations summarize different regional units; changes in these
estimates are not evidence of significance or a validated robustness assessment.

## Reproduce with the existing environment

From the repository root (containing `app.py`):

```bash
# Explicit download only, after reviewing sources and their terms.
./.venv/bin/python experimental/atlas_sensitivity/demo.py --download \
  --output experimental/atlas_sensitivity/output/real-left

# Subsequent runs are offline; choose a new output directory.
./.venv/bin/python experimental/atlas_sensitivity/demo.py \
  --output experimental/atlas_sensitivity/output/real-left-repeat

./.venv/bin/python -m pytest -q tests/test_atlas_sensitivity.py -rs
ATLAS_RESCUE_WB=/usr/bin/wb_command ./.venv/bin/python -m pytest -q -rs
```

The experiment uses installed NumPy, SciPy, NiBabel and Plotly; SciPy is now an
explicit requirement. It needs no Workbench executable. Existing converter
integration tests still use Workbench. No `.venv` recreation is needed.

`data_manifest.json` pins source URLs and SHA-256 for all eight used files.
Existing files must match hashes and are never overwritten on mismatch. The
BigBrainWarp public-share URL redirects from its documented archive route; its
WebDAV file endpoints permit fetching only the needed maps/reference instead of
a multi-gigabyte archive. A changed/unavailable share is a reproducibility blocker,
not a reason to disable hashes or substitute synthetic data.

Outputs in the chosen directory:

- Three `Schaefer*-7net_regional_values.tsv` files with IDs/names, means,
  total/valid counts, zero counts, retained weights and both coverage measures.
- `summary.tsv`: estimates, retained/empty regions, coverage and common mask hash.
- `common_valid_mask.npy`: the exact reusable boolean mask.
- `report.html`: a self-contained interactive report with three scatterplots and
  a comparison panel. No external plotting service or analytics is used.
- `provenance.json`: source URLs/hashes, metadata/correspondence evidence, settings,
  code hashes, git state and software versions. A dirty worktree is recorded as such.
- `README.md`: output explanation and interpretation limits.

The numerical unit tests independently calculate means from explicit membership
indices, test sparse/shuffled IDs and changed ID-to-name mappings, nonfinite
measurements, masks, empty parcels, ties and the labelled unweighted fallback.
An optional local real-data integration test checks the exact verified inputs
and creates a fresh report. It skips explicitly when those downloads are absent;
it does not fetch files or substitute synthetic data.

## Experimental Streamlit mode

Only after the real CLI milestone worked, a separate workflow choice was added:

```bash
./.venv/bin/python -m streamlit run app.py
```

Select **Atlas sensitivity (experimental)** in the sidebar. The existing
conversion workflow remains the default. The experimental mode uses the same
analysis module and hash-pinned local data, checks availability, and runs only
when requested. It never downloads maps. It presents the summary, interactive
plots, diagnostics and a ZIP containing the report, tables and provenance.
Temporary UI outputs stay in the session and can be downloaded. There is no
arbitrary-map upload/alignment feature in this milestone.

## Limitations, citations and licensing

This is one public histology-derived map (BigBrain is one postmortem brain) and
one group MRI-derived map, not paired participant observations. Gradient signs,
source preprocessing, patch-level downsampling, regional boundaries and group
area weights affect interpretation. Neither differences across atlas estimates
nor agreement with numerical checks validates anatomy, biology, research demand
or general reproducibility. No spatial-autocorrelation-aware inferential procedure
is implemented. No resampling, extra smoothing, sign alignment or measure
substitution is performed here.

Cite the actual sources:

- Paquola et al. (2021), *The BigBrainWarp toolbox for integration of BigBrain 3D
  histology with multimodal neuroimaging*, [eLife 70119](https://doi.org/10.7554/eLife.70119).
- Amunts et al. (2013), *BigBrain: an ultrahigh-resolution 3D human brain model*,
  [Science](https://doi.org/10.1126/science.1235381).
- Royer et al. (2022), *An Open MRI Dataset For Multiscale Neuroscience*,
  [Scientific Data](https://doi.org/10.1038/s41597-022-01682-y). BigBrainWarp's
  tutorial is the specific provenance for its distributed Micro_G1 gradient.
- Schaefer et al. (2018), [Cerebral Cortex](https://doi.org/10.1093/cercor/bhx179);
  retain the existing CBIG notice in `demo/CBIG_LICENSE.txt`.
- HCP/CBIG reference areas: Coalson, Glasser, Harms and Van Essen,
  `standard_mesh_atlases_20170508/00_README.txt` (22 September 2016), linked above.

External maps, meshes, annotation files and all generated derivatives are ignored
by Git and remain local. The BigBrainWarp code repository has its own GPL notices;
no BigBrainWarp source code was copied here. This project's MIT license does not
relicense its external maps or establish redistribution rights for every derived
file. See [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md). Review upstream
terms before reuse/redistribution; local availability is not permission to publish.
