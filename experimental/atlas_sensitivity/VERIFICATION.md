# Local milestone verification — 17 October 2026

Historical state at the initial milestone: branch `feature/atlas-sensitivity`,
uncommitted and not pushed. The local generated provenance records that existing
commit plus dirty-worktree state and SHA-256 of the analysis/CLI code. Those
artifacts describe their original run, not the later publication commit.
External files and generated outputs are excluded from Git.

Commands run from the repository root:

```bash
./.venv/bin/python experimental/atlas_sensitivity/demo.py
./.venv/bin/python -m pytest -q tests/test_atlas_sensitivity.py -rs
./.venv/bin/python experimental/atlas_sensitivity/demo.py --download \
  --output experimental/atlas_sensitivity/output/real-left-final
ATLAS_RESCUE_WB=/usr/bin/wb_command ./.venv/bin/python -m pytest -q -rs
git diff --check
```

Individual public files were initially obtained with Python `urllib.request`
from the URLs subsequently pinned in `data_manifest.json`. The final `--download`
invocation verified all eight already-present files against those hashes. It can
fetch those exact files in a fresh data directory; no automatic UI fetch occurs.
Additional author 10k files were inspected but not used for the analysis.

The first CLI attempt rejected the author's unusual GIFTI intent NORMAL (11).
Inspection established the author-provided gradient definition and metadata;
the continuous loader now accepts and records this intent without treating the
values as z-statistics or modifying the source. The subsequent CLI run and final
run completed successfully. No synthetic map replaced either real map.

Final real-data results (left hemisphere, template-area-weighted regional means):

| Bilateral configuration | Retained regional units | Pearson r | Spearman rho | Retained area fraction |
|---|---:|---:|---:|---:|
| Schaefer100-7net | 50 | 0.250584 | 0.252917 | 1.000000 |
| Schaefer200-7net | 100 | 0.247200 | 0.273843 | 1.000000 |
| Schaefer400-7net | 200 | 0.189291 | 0.197064 | 1.000000 |

These are descriptive estimates over different regional units. No statistical
significance, robustness validation, anatomical accuracy or biological
confirmation is inferred. Area coverage is numerical coverage under the declared
mask; the 420 finite MRI zeros retained within it have unresolved sentinel
semantics in the author `.curv` metadata.

- Full existing-environment suite: **38 passed**, no skips or failures (8.82 s).
- Experimental analysis/UI suite: **12 passed** (3.55 s).
- Common mask: **149,876** of 163,842 vertices; identical for both maps and all
  three atlases. No real input nonfinite values or invalid area weights; no empty
  real regions. Test fixtures explicitly verify empty-region and nonfinite handling.
- All 350 original region ID/name pairs were checked against annotation tables.
- A separate raw-array check (no analysis-module calls) reconstructed the mask,
  used explicit annotation membership and Python `math.fsum` for both weighted
  numerators/denominators, and verified **700 saved means**. Maximum absolute
  difference: **3.3306690738754696e-16**. The check is recorded locally as
  `output/real-left-final/independent_checks.json`.
- Reference spheres: exactly matching faces and nearest-vertex indices; maximum
  vertex separation **0.008032683675449409 mm**. This checks reference ordering,
  not biological registration accuracy.
- Streamlit AppTest checked the real experimental analysis, missing-data blocking
  without any download, and return to the existing conversion workflow.

Final outputs: `experimental/atlas_sensitivity/output/real-left-final/` contains
three regional TSVs, summary TSV, common mask, interactive HTML report, provenance
JSON, output README and the supplementary independent-check JSON. Versions and
input/code hashes are in provenance. No hosted CI run is claimed for this branch.

Source documentation, units, missing-data uncertainties, download routes and
citations are in README.md next to this file. See INVENTORY.md for the initial
workspace inventory. Existing atlas data, converter code and `.venv` were not
modified. The Streamlit change is a separate experimental workflow choice.

## Feature-branch publication review

The prepublication review reran the full existing-environment suite: **38 passed,
no skips or failures**. `git diff --check` passed. Documentation and generated
explanations explicitly identify Hist_G1, Micro_G1, the left fsaverage hemisphere,
and group-template-area-weighted regional means. The unresolved MRI-zero
semantics remain documented; numerical coverage is not complete biological coverage.

Git ignore checks confirmed exclusions for external experimental maps, original
atlas/reference data, generated HTML/TSV/array/provenance outputs, `.venv`, `.env`,
cache files and Streamlit secrets. Only source, tests, documentation and small
source-URL/hash manifests are intended for this feature branch. The shared
telemetry-disabled Streamlit configuration is intentionally tracked; it contains
no environment credentials. No data license is replaced by the code's MIT license.
