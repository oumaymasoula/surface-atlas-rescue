# Surface Atlas Rescue

Convert **one labelled fsaverage5 hemisphere to fsLR32k** while preserving its
region names and RGBA colours. This research prototype provides a local Streamlit
interface, a command-line converter and explicit checks on the saved output.

It is intended for researchers who already have a custom fsaverage5 cortical
atlas and need its categorical labels in an fsLR32k workflow. For example, convert
a left-hemisphere atlas, inspect its retained label dictionary, then summarize a
continuous measurement that is **already aligned** to the matching fsLR32k mesh.
Use an **official target-space atlas when a suitable one is available**; resampling
an atlas adds assumptions and is not always necessary.

## Inputs and outputs

| Input | Output |
|---|---|
| One hemisphere, fsaverage5, 10,242 vertices | fsLR32k labelled GIFTI, 32,492 vertices |
| FreeSurfer `.annot` or GIFTI `.label.gii` | Label dictionary and vertex counts in `labels.tsv` |
| Original label names/colours and background ID 0 | JSON/HTML verification report and Workbench read/export evidence |

**Atlas catalog** uses local catalog files directly; no browser upload is needed.
The catalog defines 14 configurations across Schaefer, Desikan–Killiany and
Destrieux. **GitHub does not redistribute the data**: download them as described
below. The original workspace's existing data remain local and can still be used.
**Upload my atlas** sends a single existing fsaverage5 atlas to your running
Streamlit server. A picture, MRI volume or native-subject annotation is not an
acceptable substitute. Run the server locally to keep processing on your computer.

Names and colours are **metadata, not registration inputs**. Correspondence is
supplied by registered reference spheres. The converter calls Workbench
`-label-resample` with `ADAP_BARY_AREA`, area metrics and a source cortical ROI,
then `-label-mask` with the target cortical mask. Background ID 0 is temporarily
named `???` for Workbench and restored afterwards. The conversion method has not
been changed for GitHub publication.

## Ubuntu setup

Python 3.12 on Linux is the tested environment. Commands below run from the
repository root (the directory containing `app.py`).

1. Install Python environment support and Workbench:

   ```bash
   sudo apt update
   sudo apt install python3 python3-venv connectome-workbench
   ```

2. Clone this repository and enter its directory. On a fresh clone create the
   environment; **reuse an existing `.venv` instead of recreating it**:

   ```bash
   git clone https://github.com/oumaymasoula/surface-atlas-rescue.git
   cd surface-atlas-rescue
   python3 -m venv .venv
   ./.venv/bin/python -m pip install -r requirements.txt
   ```

3. Verify the executable:

   ```bash
   which wb_command
   wb_command -version
   ```

   On a typical Ubuntu installation it is `/usr/bin/wb_command`. If the package
   is unavailable for your Ubuntu release, use the official
   [Workbench installation](https://www.humanconnectome.org/software/get-connectome-workbench).
   Keep its launcher and shared libraries together, and run its full path with
   `-version` before using it.

4. Review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), then download references
   and Schaefer inputs with checksum verification (network required):

   ```bash
   ./.venv/bin/python prepare_demo.py
   ```

   Desikan/Destrieux TemplateFlow file terms remain unresolved for redistribution.
   They and their derivatives are excluded from GitHub. If you have reviewed the
   upstream terms and are entitled to obtain them for your use, the documented
   download route is:

   ```bash
   ./.venv/bin/python prepare_demo.py --include-templateflow
   ```

   `resources.json` records exact sources and checksums. The references are also
   external downloads; this project's MIT license does not cover them.

5. Launch the app:

   ```bash
   ./.venv/bin/python -m streamlit run app.py --browser.gatherUsageStats false
   ```

   Open the local URL printed in the terminal (normally `http://localhost:8501`).
   Keep the terminal running; stop with Ctrl+C. Under **Advanced runtime settings**
   set the Workbench executable and reference-data directory if needed. You can
   also launch with `ATLAS_RESCUE_WB=/usr/bin/wb_command` and
   `ATLAS_RESCUE_DATA=/absolute/path/reference-data` environment variables.

Select the input mode, hemisphere and atlas, confirm the declared fsaverage5
space, then choose **Convert and check**. Conversion stays disabled while
Workbench cannot run `-version`, any required hemisphere reference/display mesh
is missing, or no input is available. Inspect warnings, previews and labels before
downloading. Atlas options marked “missing L file” or “missing R file” are
unavailable for the selected hemisphere; conversion remains disabled and the app
shows the appropriate manual download command and optional TemplateFlow notices.
No downloads start automatically. The app allows two concurrent conversions per server process;
this is not a public-server capacity guarantee.

## Command-line conversion

```bash
./.venv/bin/python converter.py \
  demo/input/lh.Schaefer2018_100Parcels_7Networks_order.annot \
  results-left --hemi L --data-dir reference-data --wb /usr/bin/wb_command
```

Use a new or empty output directory. The output report records input/reference
hashes, versions, dictionary checks and parcels with no target vertices.
FreeSurfer RGB-packed annotation codes are normalized to parcel indices by
neuromaps; original packed codes are not preserved as IDs.

## Separate downstream example

The example remains separate from the app:

```bash
./.venv/bin/python examples/downstream_demo.py --wb /usr/bin/wb_command \
  --atlas schaefer100-7net --output examples/output/schaefer-L-synthetic
```

It converts a catalog atlas through the existing converter, generates a
**SYNTHETIC** continuous map with fixed seed `20261016` on the matching fsLR32k
mesh, and writes `regional_values.tsv`, a measurement GIFTI, a self-contained
interactive HTML figure and numerical checks. Simulated values have arbitrary
units and are **not participant MRI or evidence of biological validity**.

Means are ordinary vertex means, **not area weighted**. Background is excluded;
Desikan's corpuscallosum and Destrieux's Medial_wall are explicitly excluded when
present. Empty regions retain count 0 and mean NaN. The default atlas is
`schaefer100-7net`, with output directory `examples/output/schaefer-L-synthetic`,
so the example works after the standard download setup. Desikan remains an
explicit `--atlas desikan2006` choice requiring its optional local data.
Use a new `--output` folder for each run.

See [examples/USEFULNESS_TEST.md](examples/USEFULNESS_TEST.md) for repeating the task
with a researcher's custom fsaverage5 atlas and an already aligned fsLR32k
measurement. Neither conversion nor this example aligns measurement maps.

## What verification establishes

Checks cover label intent, density, complete names/colours, preservation of the
normalized dictionary, no new parcel IDs, cortical masking, and Workbench reading
and exporting the saved file. Disappeared parcels are reported, not silently
removed from the dictionary. The downstream checks compare extracted means to
independent direct NumPy calculations and deliberately reject mismatched lengths.

**Matching counts alone do not prove spatial alignment, hemisphere or vertex
ordering.** No independent anatomical accuracy validation is provided. Desikan's
source includes a noncortical corpus-callosum label; Destrieux's source includes
a labelled medial wall. Neither should be interpreted as additional cortex.

This prototype does not perform native-subject conversion, MRI preprocessing,
volume-to-surface mapping, continuous-map conversion, automatic registration,
other densities, missing-name reconstruction or bilateral CIFTI assembly. It is
not clinically validated. Synthetic examples demonstrate software functionality;
research demand requires real users and has not been established.

## Troubleshooting

| Symptom | Action |
|---|---|
| `streamlit` or Python module not found | Run `./.venv/bin/python -m pip install -r requirements.txt`, then launch with that same Python |
| Wrong working directory / file not found | Enter the repository root containing `app.py` before using relative commands |
| Missing or failing Workbench | Run `which wb_command` and its full path with `-version`; fix its installation/libraries and enter the working path in runtime settings |
| Missing references, display meshes or catalog input | Check Reference-data directory, restore the local bundle or run `prepare_demo.py`; TemplateFlow atlases require the explicit option and terms review |
| Download TLS/503 error or changed upstream file | Check network/source availability, retry later; retain checksum validation. The manifest uses recorded Zenodo URLs for reference downloads rather than a new OSF fetch |
| Hemisphere mismatch / unsupported input | Choose the matching hemisphere and an existing fsaverage5 `.annot` or `.label.gii` with original metadata; `.gii` metrics are not label atlases |
| Region disappears after conversion | Inspect `parcels_without_target_vertices` and masking warnings; a retained dictionary entry need not have target vertices |
| Existing output directory rejected | Choose a new or empty directory; previous results are intentionally not overwritten |
| Downstream map length or NaN/Inf rejected | Supply one finite continuous array in the exact target hemisphere/vertex order; define a separate missing-data policy if needed |
| App conversion fails | Follow the message and open **Technical error details**; report a sanitized traceback and reproduction steps |

No tracking or analytics has been added. The launch command disables Streamlit's
usage statistics. Processing is on the server you start; downloads access the
listed upstream sources. Do not attach participant/private data to issues.

## Tests and contributions

```bash
# No Workbench or external data required
./.venv/bin/python -m pytest -q -m 'not workbench'

# Real conversions: Workbench plus the specified local data required
ATLAS_RESCUE_WB=/usr/bin/wb_command ./.venv/bin/python -m pytest -q

# Optional full catalog reproduction after obtaining all required data
./.venv/bin/python test_all_atlases.py --wb /usr/bin/wb_command --workers 2
```

GitHub Actions separates data-free tests from a Workbench/Schaefer integration
job. Optional TemplateFlow integration cases skip when those files are absent;
skips are not conversion passes. See [CONTRIBUTING.md](CONTRIBUTING.md) for the
exact setup, feedback forms and test expectations. No external users or demand
results are claimed.

## License and citation

Original project code: **MIT**, copyright Oumayma Soula. Dependencies and data
retain their separate terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
[CITATION.cff](CITATION.cff) describes this software without an invented DOI or
publication. Please also cite the relevant upstream work:

- Markello et al. (2022), *neuromaps: structural and functional interpretation of
  brain maps*, Nature Methods. [doi:10.1038/s41592-022-01625-w](https://doi.org/10.1038/s41592-022-01625-w);
  [documentation and transformation citation guidance](https://netneurolab.github.io/neuromaps/).
- [Connectome Workbench](https://www.humanconnectome.org/software/connectome-workbench)
  and its label-resampling/masking tools. Workbench acknowledgment guidance cites
  Marcus et al. (2011), *Informatics and data mining tools and strategies for the
  Human Connectome Project*, [doi:10.3389/fninf.2011.00004](https://doi.org/10.3389/fninf.2011.00004).
  Related HCP methods: Glasser et al.
  (2013), *The minimal preprocessing pipelines for the Human Connectome Project*.
  [doi:10.1016/j.neuroimage.2013.04.127](https://doi.org/10.1016/j.neuroimage.2013.04.127).
- Schaefer et al. (2018), *Local-Global Parcellation of the Human Cerebral Cortex
  from Intrinsic Functional Connectivity MRI*.
  [doi:10.1093/cercor/bhx179](https://doi.org/10.1093/cercor/bhx179);
  [CBIG fsaverage5 sources](https://github.com/ThomasYeoLab/CBIG/tree/master/stable_projects/brain_parcellation/Schaefer2018_LocalGlobal/Parcellations/FreeSurfer5.3/fsaverage5/label).
- Desikan et al. (2006), *An automated labeling system for subdividing the human
  cerebral cortex on MRI scans into gyral based regions of interest*.
  [doi:10.1016/j.neuroimage.2006.01.021](https://doi.org/10.1016/j.neuroimage.2006.01.021).
- Destrieux et al. (2010), *Automatic parcellation of human cortical gyri and sulci
  using standard anatomical nomenclature*.
  [doi:10.1016/j.neuroimage.2010.06.010](https://doi.org/10.1016/j.neuroimage.2010.06.010).
- Anatomical atlas files: [TemplateFlow tpl-fsaverage](https://github.com/templateflow/tpl-fsaverage).
  References: neuromaps-distributed fsaverage/fsLR surfaces, masks and area metrics;
  exact records and checksums in [resources.json](resources.json). These sources
  are attribution/provenance, not a claim of redistribution permission.
