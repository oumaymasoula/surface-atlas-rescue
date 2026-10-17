# Atlas data notices

Atlas files are preserved locally but are not committed to GitHub. The manifest
in `../resources.json` retains source URLs and SHA-256 checksums. Run
`../prepare_demo.py` from the project root using its documented options.

Schaefer annotations: CBIG, Schaefer et al. 2018. See `../demo/CBIG_LICENSE.txt`.
Desikan and Destrieux GIFTIs: TemplateFlow tpl-fsaverage, derived from FreeSurfer.
The retrieved template description refers to a LICENSE file that was absent at
the corresponding source URL during inspection. The FreeSurfer agreement is
retained as an upstream notice, not as proof of complete TemplateFlow licensing.
Those files and their derivatives are excluded from publication pending clarity.
See `../THIRD_PARTY_NOTICES.md` for the scope and documented download route.

All or portions of this licensed product (such portions are the "Software") have
been obtained under license from The General Hospital Corporation and are subject
to the terms and conditions in FreeSurfer_LICENSE.txt.

Local source atlas files are unmodified. Local `verification-catalog-final`
outputs and example outputs are resampled/derived files, not original atlases.
They are excluded from Git publication; no MIT license is asserted over them.
