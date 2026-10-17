# Local prepublication verification — 16 October 2026

These are actual local checks, not a claim that GitHub Actions has run or that
anatomical accuracy, biological validity or demand has been established.

Environment: Linux, Python 3.12, existing `.venv`, `/usr/bin/wb_command`.

- `./.venv/bin/python -m pytest -q -m 'not workbench' -rs`:
  **18 passed, 4 deselected**. No Workbench or external data needed.
- `ATLAS_RESCUE_WB=/usr/bin/wb_command ./.venv/bin/python -m pytest -q -rs`:
  **22 passed, no skips or failures**. Real local Destrieux/Schaefer app
  conversions and Desikan/Schaefer downstream conversions were exercised.
  The Desikan test also reused the synthetic measurement through the custom
  source/supplied-measurement path. These are not participant results.
- `./.venv/bin/python prepare_demo.py --profile test`: verified all 32 selected
  existing local reference/Schaefer files against manifest SHA-256 values;
  no new download was needed. This does not test fresh network availability.

All original local atlas/reference files and prior derived outputs remain on
disk. They are excluded from Git, including prior full-catalog run artifacts.
Older local verification reports are not published or presented as results of
this prepublication test run. Optional TemplateFlow tests skip on a fresh clone
unless their inputs are separately obtained; a skip is never a passed conversion.

## Source-only staging check

An export of the exact staged files passed the data-free suite: **18 passed,
4 deselected** with no external data in the export. After linking only the
checksum-verified local reference files and Schaefer test annotations into that
temporary export, the Workbench selection reported **2 passed, 2 skipped,
18 deselected**. The skips explicitly identify the optional Desikan/Destrieux
inputs absent from the export. This mirrors CI's intended data scope using local
files; it does not claim a fresh download or a GitHub-hosted run succeeded.

The CFF metadata passed the official Citation File Format 1.2.0 JSON schema.
Issue forms and workflow YAML were parsed. The publication audit checks staged
UTF-8 files for token/key patterns and private workspace paths, rejects data and
binary extensions, and records file sizes/hashes locally. A pattern scan is not
a guarantee that no possible secret can exist. No findings were detected.

## Schaefer default and catalog availability update

- Existing-environment full suite with `ATLAS_RESCUE_WB=/usr/bin/wb_command`:
  **26 passed, no skips or failures**. Data-free selection: **22 passed,
  4 deselected**. The four new cases cover CLI defaults and missing left/present
  right catalog input guidance across all three atlas families.
- Downstream integration tests run with an environment-selected wrapper around
  Workbench: **2 passed, 7 deselected**; the wrapper recorded actual resampling
  calls, verifying that the chosen executable reached the converter.
- Downstream integration tests with `ATLAS_RESCUE_WB` unset (PATH lookup):
  **2 passed, 7 deselected**.
- The CLI with its default atlas and a fresh output directory produced 50
  Schaefer regional rows and passed all five downstream checks. Output remains
  local under `examples/output/schaefer-default-update/`.

The conversion algorithm, existing data and environment were not changed.
