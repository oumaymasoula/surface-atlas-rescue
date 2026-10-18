"""Run with: streamlit run app.py"""
import io
import os
from pathlib import Path
import tempfile
import threading
import shutil
import zipfile
import traceback

import nibabel as nib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from converter import convert, load_source, label_dictionary, check_hemisphere, setup_issues, display_mesh_paths
from catalog import entries, get_entry, source_file

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Surface Atlas Rescue', layout='wide')
st.title('Surface Atlas Rescue')
workflow = st.sidebar.radio('Workflow', ['Atlas conversion', 'Atlas sensitivity (experimental)'],
                            key='workflow')
if workflow == 'Atlas sensitivity (experimental)':
    from experimental.atlas_sensitivity.ui import render
    render()
    st.stop()
st.write('Convert a labelled atlas from fsaverage5 to fsLR 32k, preserving its names and colours.')
st.caption('Research prototype · one hemisphere per run · file checks do not prove anatomical alignment')


def clear_results():
    st.session_state.pop('result',None)


@st.cache_resource
def conversion_slots():
    # Shared across sessions of this one Streamlit server process only.
    return threading.BoundedSemaphore(2)


def surface_plot(image, mesh, title):
    surface = nib.load(mesh)
    coords, faces = surface.agg_data()
    labels = image.agg_data().astype(int)
    table = label_dictionary(image)
    colors, names = [], []
    for key in labels:
        item = table[int(key)]
        rgba = item['rgba']
        colors.append('rgb(160,160,160)' if key == 0 else
                      f'rgb({round(rgba[0]*255)},{round(rgba[1]*255)},{round(rgba[2]*255)})')
        names.append(f'{int(key)}: {item["name"]}')
    fig = go.Figure(go.Mesh3d(x=coords[:,0], y=coords[:,1], z=coords[:,2],
        i=faces[:,0], j=faces[:,1], k=faces[:,2], vertexcolor=colors,
        text=names, hovertemplate='%{text}<extra></extra>', flatshading=True))
    fig.update_layout(title=title, height=430, margin=dict(l=0,r=0,b=0,t=40),
        scene=dict(xaxis_visible=False,yaxis_visible=False,zaxis_visible=False,aspectmode='data'))
    return fig


with st.sidebar:
    st.header('Conversion route')
    st.write('fsaverage5 → fsLR 32k')
    st.caption('Three atlas families · 14 configurations · left or right hemisphere')
    local_wb=ROOT/'tools/workbench/bin_linux64/wb_command'
    default_wb=os.environ.get('ATLAS_RESCUE_WB') or shutil.which('wb_command') or (str(local_wb) if local_wb.is_file() else 'wb_command')
    with st.expander('Advanced runtime settings'):
        data_dir = st.text_input('Reference-data directory', os.environ.get('ATLAS_RESCUE_DATA', str(ROOT/'reference-data')),on_change=clear_results)
        wb = st.text_input('Workbench executable',default_wb,on_change=clear_results)
    st.caption('At most two conversions run at a time per server process. Additional jobs wait.')

st.subheader('1. Choose your atlas')
mode = st.radio('Input', ['Atlas catalog', 'Upload my atlas'], horizontal=True,on_change=clear_results)
catalog=entries()
hemi = st.selectbox('Hemisphere', ['L','R'], format_func=lambda x:'Left' if x=='L' else 'Right',
                    key='hemisphere', on_change=clear_results)
selected=st.selectbox('Choose a bundled atlas', [e['id'] for e in catalog],
                      format_func=lambda k: get_entry(k)['name'] +
                      (f' — missing {hemi} file' if not source_file(k, hemi).is_file() else ''),
                      key='atlas', on_change=clear_results) if mode=='Atlas catalog' else None
uploaded = None
if mode == 'Upload my atlas':
    uploaded = st.file_uploader('One fsaverage5 .annot or .label.gii file', type=['annot','gii'],on_change=clear_results)
    st.caption('Upload an existing fsaverage5 .annot or .label.gii atlas with 10,242 vertices and original names/colours. Pictures, MRI volumes and native-subject annotations are not supported; they are not converted to fsaverage5 by this app.')
else:
    st.caption('Atlas catalog uses local catalog files directly. No upload is needed. On a fresh clone, run prepare_demo.py to download Schaefer inputs; see README for other atlases.')
    entry=get_entry(selected)
    if not source_file(selected, hemi).is_file():
        st.warning(f'The selected atlas has no local {hemi} hemisphere file.')
        if entry['family'] == 'Schaefer':
            st.code('python prepare_demo.py', language='bash')
        else:
            st.markdown('Desikan/Destrieux downloads are optional. Review the '
                        '[third-party notices](https://github.com/oumaymasoula/surface-atlas-rescue/blob/main/THIRD_PARTY_NOTICES.md) '
                        'and applicable upstream terms before using the download route:')
            st.code('python prepare_demo.py --include-templateflow', language='bash')
        st.caption('Run the command from the project directory with the project environment active. No files are downloaded automatically.')
    st.caption(f'{entry["citation"]} · source: {entry["source"]}')
    if entry['id']=='desikan2006':
        st.info('These source files contain 34 cortical regions plus one corpus-callosum label per hemisphere. See coverage warnings after conversion.')
    if entry['id']=='destrieux2009':
        st.info('These source files contain 74 anatomical regions plus a labelled medial wall per hemisphere. The target cortical mask excludes the medial wall.')
confirmed = st.checkbox('I confirm this is a labelled fsaverage5 atlas for the selected hemisphere.')
st.subheader('2. Convert and verify')
source_for_check = source_file(selected, hemi) if mode == 'Atlas catalog' else None
issues = setup_issues(data_dir, hemi, wb, source_for_check, uploaded is not None)
if uploaded is not None:
    if not uploaded.name.endswith(('.annot', '.label.gii')):
        issues.append('Choose an .annot or .label.gii file; other GIFTI files are not accepted.')
    if uploaded.size > 10*1024*1024:
        issues.append('Choose an atlas file no larger than 10 MB.')
if issues:
    st.session_state.pop('result', None)
    st.warning('Conversion is disabled until these setup issues are fixed:')
    for issue in issues:
        st.write('• ' + issue)
if st.button('Convert and check', type='primary', disabled=not confirmed or bool(issues)):
    st.session_state.pop('result', None)
    try:
        with tempfile.TemporaryDirectory(prefix='atlas_rescue_app_') as tmp:
            tmp = Path(tmp)
            if mode == 'Upload my atlas':
                if uploaded is None: raise ValueError('Upload an atlas first.')
                if uploaded.size > 10*1024*1024: raise ValueError('This prototype accepts atlas files up to 10 MB.')
                check_hemisphere(uploaded.name,hemi)
                suffix = '.annot' if uploaded.name.endswith('.annot') else '.label.gii'
                if not uploaded.name.endswith(('.annot','.label.gii')):
                    raise ValueError('Upload .annot or .label.gii; continuous .gii metrics are not accepted.')
                source = tmp / Path(uploaded.name).name
                source.write_bytes(uploaded.getvalue())
            else:
                source = source_file(selected,hemi)
                if not source.exists(): raise FileNotFoundError('Run prepare_demo.py to download demo inputs.')
            with st.status('Waiting for a conversion slot…',expanded=True) as status:
                with conversion_slots():
                    st.write('Checking input and resampling categorical labels…')
                    report = convert(source,tmp/'output',hemi,data_dir,wb)
                    st.write('Names, colours and Workbench file compatibility checked.')
                status.update(label='Conversion finished',state='complete',expanded=False)
            out = tmp/'output'
            target = out / report['target']['filename']
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer,'w',zipfile.ZIP_DEFLATED) as z:
                for f in sorted(out.iterdir()): z.write(f, f.name)
            source_mesh, target_mesh = display_mesh_paths(data_dir, hemi)
            figs = (surface_plot(load_source(source), source_mesh, 'Input: fsaverage5'),
                    surface_plot(nib.load(target), target_mesh, 'Output: fsLR 32k'))
            st.session_state.result = (report,pd.read_csv(out/'labels.tsv',sep='\t'),zip_buffer.getvalue(),figs)
    except Exception as exc:
        st.error('Conversion could not finish. ' + str(exc))
        st.info('Check the selected hemisphere and use an existing fsaverage5 atlas with 10,242 vertices, LABEL data and original names/colours. For missing files, restore the bundle or run ./.venv/bin/python prepare_demo.py. For Workbench failures, run the configured executable with -version in a terminal and fix its path or installation, then retry. If checks still fail, retain the details below when reporting the issue.')
        with st.expander('Technical error details'):
            st.code(traceback.format_exc(), language='text')

if 'result' in st.session_state:
    report, table, bundle, figs = st.session_state.result
    st.subheader('3. Inspect and download')
    st.success('Conversion and file compatibility checks passed.')
    st.write(f'Hemisphere: {report["source"]["hemisphere"]} · regions present: {report["source_parcels_present"]} → {report["target_parcels_present"]}')
    if report['parcels_without_target_vertices']:
        missing=table[table['index'].isin(report['parcels_without_target_vertices'])]
        st.warning('Labels without target vertices: '+', '.join(missing['name'].tolist())+'. Their dictionary entries are retained. Review whether the exclusion is expected.')
    cols=st.columns(2)
    for col, fig in zip(cols,figs):
        with col: st.plotly_chart(fig,width='stretch')
    st.write('Names and RGBA colours preserved; Workbench read and label-table export succeeded.')
    st.dataframe(table,hide_index=True)
    st.download_button('Download converted atlas and report',bundle,
        file_name=f'surface-atlas-{report["source"]["hemisphere"]}-output.zip',mime='application/zip')
    with st.expander('Checks, versions and limitations'): st.json(report)
