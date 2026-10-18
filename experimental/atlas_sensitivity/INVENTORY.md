# Inventory at experiment start

- Existing catalog: Schaefer 100/200/400/600/800/1000 with 7/17 networks,
  left/right fsaverage5 annotation files; Desikan and Destrieux optional GIFTIs.
  Schaefer 100/200/400 7-network local left files were present.
- Existing references: fsaverage 10k and fsLR32k left/right spheres, midthickness
  group vertex-area metrics, cortical masks and display meshes. These belong to
  the existing conversion workflow and were not altered. They are **not** reused
  as weights for 164k experimental maps.
- Existing downstream example: `examples/downstream_demo.py` converts one atlas
  through `converter.py`, generates a labelled synthetic fsLR32k measurement,
  extracts ordinary vertex means and writes tables/report. Its synthetic example
  was inspected but is not the real-data input of this experiment.
- Existing tests cover validation, conversion/interface behavior, missing files,
  Schaefer/Desikan downstream extraction and independent numerical checks.
- Installed environment already had NumPy, SciPy, NiBabel, Plotly, Streamlit,
  pandas and pytest. No package installation or environment recreation was needed.
- New local inputs: eight hash-pinned files in `data_manifest.json`: two real
  BigBrainWarp gradients and the author sphere, three original CBIG fsaverage
  164k annotations, plus CBIG reference sphere and area metric. All are left
  hemisphere. Only this independent experiment uses them.
- Additional inspected author 10k map files remain ignored in `data/`; they are
  not analyzed. Original 164k distributions were chosen to avoid uncertain MRI
  10k resampling provenance. No continuous map is transformed by this prototype.
