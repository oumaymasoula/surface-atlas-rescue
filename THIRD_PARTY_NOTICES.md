# Third-party code and data

## License boundary

[LICENSE](LICENSE) applies to original Surface Atlas Rescue code and documentation
by Oumayma Soula. It does **not** relicense dependencies, Workbench, atlas labels,
reference surfaces, third-party notices, or generated derivatives of those data.
No dependency source or binary is vendored. Existing local data and generated
runs are preserved on disk but excluded from Git publication.

## External software

- **neuromaps 0.0.7**: [CC BY-NC-SA 4.0](https://github.com/netneurolab/neuromaps/blob/main/LICENSE).
  Imported as an installed dependency (`neuromaps.images.annot_to_gifti`); the
  comparison script also invokes neuromaps transforms. No neuromaps source is
  copied into this repository. MIT permission for our code does not grant broader
  rights to neuromaps or remove its noncommercial/share-alike terms. Review those
  terms for the intended use, particularly commercial use or redistribution.
- **Connectome Workbench**: external executable, not distributed here. See its
  [license information](https://www.humanconnectome.org/software/workbench-license)
  and [source/distribution](https://github.com/Washington-University/workbench).
- Python dependencies are installed separately: NiBabel (MIT), NumPy (BSD and
  bundled-component notices), Plotly.py (MIT), Streamlit (Apache-2.0), pandas
  (BSD-3-Clause) and pytest (MIT). Their distributions retain their own licenses
  and transitive notices. Consult the installed versions; this is not a license
  grant for their bundled components. Plotly-generated standalone HTML embeds
  Plotly.js; generated HTML is excluded from this repository.

## Data and provenance

| Material | Source and notice | Publication decision |
|---|---|---|
| Schaefer fsaverage5 annotations | [CBIG Schaefer2018](https://github.com/ThomasYeoLab/CBIG/tree/master/stable_projects/brain_parcellation/Schaefer2018_LocalGlobal); [CBIG MIT notice](demo/CBIG_LICENSE.txt), copyright CBIG 2016 | Available by download, not committed; no claim of project authorship |
| Desikan2006 / Destrieux2009 fsaverage GIFTIs | TemplateFlow `tpl-fsaverage`, derived from FreeSurfer; [retained notice](catalog-data/DATA_NOTICES.md) and [FreeSurfer agreement](catalog-data/FreeSurfer_LICENSE.txt) | **Excluded**, including derived conversions, dictionaries and figures |
| fsaverage / fsLR reference spheres, area metrics, masks and meshes | neuromaps distribution, source commit `ffcc2e0f657943ce00a1b6a968396f32250e495c`; Zenodo record URLs and SHA-256/MD5 in [resources.json](resources.json) | All reference files and derivatives **excluded** pending complete upstream license/provenance confirmation |
| Custom inputs and outputs | User's own sources and applicable agreements | Private/local, never included automatically |

`resources.json` retains exact download routes and checksums for reproduction.
Its presence is not a declaration that every referenced file may be redistributed.
`prepare_demo.py` downloads reference files and Schaefer inputs; TemplateFlow
atlas downloads require explicit `--include-templateflow` after the user has
reviewed the applicable terms. Source URLs may change or be unavailable; a
checksum mismatch is a hard failure, never a reason to disable verification.

## Unresolved licensing questions

The retrieved TemplateFlow [template description](https://github.com/templateflow/tpl-fsaverage/blob/master/template_description.json)
says to see a LICENSE file; the corresponding LICENSE URL returned 404 during
prepublication inspection. The retained FreeSurfer agreement alone does not
resolve all rights in those particular TemplateFlow-distributed files. Confirm
the complete applicable terms before redistributing them or their derivatives.
The catalog identifiers contain “2009” for Destrieux; the paper citation is 2010.

Earlier local provenance notes describe the reference Zenodo records as CC0.
That metadata description has not been established as a complete rights chain
for every underlying surface, registration and mask. No blanket CC0 or MIT
claim is made here. Reference data and all generated artifacts are omitted from
publication as a conservative choice. Downloading is for local reproduction
subject to the source terms, not a substitute for obtaining redistribution rights.

No rights-holder contact has been made. This repository does not resolve legal
questions on behalf of users. Keep all supplied notices and cite the original
atlas, reference and software authors when using their material.
