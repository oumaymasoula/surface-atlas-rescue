"""Small experimental UI for the already demonstrated local real-map analysis."""
import io
from pathlib import Path
import tempfile
import traceback
import zipfile

import streamlit as st

from atlas_sensitivity import interactive_report
from experimental.atlas_sensitivity.demo import (HERE, LIMITATIONS, SOURCES, X_NAME, Y_NAME,
                                                 prepare_data, run)


def render():
    st.subheader('Atlas sensitivity · experimental')
    st.write('Compare the same BigBrain Hist_G1 and qT1-derived MRI Micro_G1 maps across '
             'Schaefer 100, 200 and 400 (7 networks), using author-distributed fsaverage 164k left-hemisphere files.')
    st.info(LIMITATIONS)
    st.caption('Dimensionless gradients; not raw cell density or T1 relaxation values. '
               'Common finite-data/cortical mask; group-average midthickness area weighting. '
               'Finite zeros are retained: author MRI .curv does not specify an extra sentinel convention.')
    st.markdown(f'[Source and correspondence documentation]({SOURCES["common_surface_documentation"]}) · '
                '[BigBrainWarp paper](https://doi.org/10.7554/eLife.70119)')
    data_dir = st.text_input('Experimental data directory', str(HERE/'data'), key='sensitivity_data',
                             on_change=lambda: st.session_state.pop('sensitivity_result', None))
    ready = True
    try:
        prepare_data(Path(data_dir), download=False)
    except (OSError, ValueError) as exc:
        ready = False
        st.session_state.pop('sensitivity_result', None)
        st.warning(str(exc))
        st.write('No automatic downloads. Review experimental/atlas_sensitivity/README.md and source terms, '
                 'then run the separate real-data CLI:')
        st.code('./.venv/bin/python experimental/atlas_sensitivity/demo.py --download --output /tmp/atlas-sensitivity-real', language='bash')
    if st.button('Compare atlas configurations', disabled=not ready, key='run_sensitivity'):
        st.session_state.pop('sensitivity_result', None)
        try:
            with st.spinner('Checking correspondence, common mask, weighted means and descriptive estimates…'):
                with tempfile.TemporaryDirectory(prefix='atlas_sensitivity_ui_') as tmp:
                    output = Path(tmp)/'analysis'
                    tables, summary, diagnostics = run(Path(data_dir), output)
                    buffer = io.BytesIO()
                    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as bundle:
                        for path in sorted(output.iterdir()):
                            bundle.write(path, path.name)
                    st.session_state.sensitivity_result = (tables, summary, diagnostics, buffer.getvalue())
        except Exception as exc:
            st.error(str(exc))
            with st.expander('Technical details'):
                st.code(traceback.format_exc(), language='text')
    if 'sensitivity_result' in st.session_state:
        tables, summary, diagnostics, bundle = st.session_state.sensitivity_result
        st.success('Software checks completed. Estimates are descriptive only.')
        st.dataframe(summary, hide_index=True)
        st.plotly_chart(interactive_report(tables, summary, X_NAME, Y_NAME), width='stretch')
        st.warning(f"{diagnostics['zero_y_in_common']} finite MRI zeros retained; reported coverage is numerical "
                   'coverage under the declared mask, not proof of valid biological sampling.')
        st.download_button('Download experimental tables, report and provenance', bundle,
                           file_name='atlas-sensitivity-experimental-L.zip', mime='application/zip')
        with st.expander('Mask and numerical checks'):
            st.json(diagnostics)
