# Contributing

Bug reports, implementation improvements and concrete use-case feedback are
welcome. Use the GitHub issue forms. Do not attach participant/private data,
identifiers, credentials, private file paths or unsanitized reports/tracebacks.
Use a small synthetic reproducer where possible. Feedback is voluntary: no
tracking or analytics is included and no users or demand results are assumed.

## Local setup

Follow [README.md](README.md) for Ubuntu Python 3.12, Workbench and source terms.
From the directory containing `app.py`, reuse `.venv` if it already exists:

```bash
# Only on a fresh checkout without an environment
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pytest -q -m 'not workbench'
```

Data-free tests use constructed GIFTI labels and NumPy arrays and simulate
Workbench failure. They require neither downloaded atlases nor Workbench.

For actual conversion checks, review THIRD_PARTY_NOTICES.md, install Workbench
(`sudo apt install connectome-workbench`) and obtain local test inputs:

```bash
which wb_command
/usr/bin/wb_command -version
./.venv/bin/python prepare_demo.py --profile test
ATLAS_RESCUE_WB=/usr/bin/wb_command ./.venv/bin/python -m pytest -q -m workbench -rs
```

The test download profile obtains only reference files plus Schaefer-100/7-network
inputs. The Schaefer app integration test fails if these inputs are missing. Downstream
integration tests skip explicitly when required data or Workbench are unavailable;
they resolve `ATLAS_RESCUE_WB` first, then `wb_command` on PATH, and pass that
executable to the example. A skip is never a conversion pass. Tests requiring optional
TemplateFlow Desikan/Destrieux skip explicitly if those atlases are missing.
To exercise those locally after reviewing their source terms:

```bash
./.venv/bin/python prepare_demo.py --include-templateflow
ATLAS_RESCUE_WB=/usr/bin/wb_command ./.venv/bin/python -m pytest -q -rs
```

Always report actual passes/skips/failures. A missing binary may skip integration
tests; the integration CI job explicitly checks the installed executable first.
Do not claim anatomical accuracy or treat synthetic results as user evidence.

## Pull requests

Describe the problem, resulting behavior and checks actually run. Preserve
categorical labels, names/colours and source attribution. Include meaningful
numerical or integration checks for behavioral changes. Keep the downstream
example separate from the app unless a change is explicitly discussed. Never
add third-party data or derived reports/figures without establishing permission
and preserving notices. MIT applies only to original project contributions;
contributors must have the rights to contribute their code.

Do not commit `.venv`, binaries, caches, outputs, participant data or secrets.
Review `git diff --cached` and the staged file list before committing. No
force-push or rewritten shared history is needed for routine contributions.

## CI scope

`.github/workflows/tests.yml` has two jobs: data-free unit/interface tests and
real Workbench/Schaefer conversions. Network/package/download failures are CI
failures, not silently accepted skips. Optional TemplateFlow cases are clearly
reported as skipped when absent; CI does not redistribute their source or
outputs. Generated conversion artifacts remain local and are not uploaded.
