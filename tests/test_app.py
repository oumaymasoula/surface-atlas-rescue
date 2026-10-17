"""Functional interface and session-isolation tests (Workbench required)."""
import os
from pathlib import Path
import shutil
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


@pytest.mark.workbench
def test_conversion_and_session_isolation(monkeypatch):
    from streamlit.testing.v1 import AppTest
    wb=os.environ.get('ATLAS_RESCUE_WB') or shutil.which('wb_command')
    local=ROOT/'tools/workbench/bin_linux64/wb_command'
    if not wb and local.is_file():wb=str(local)
    if not wb:pytest.skip('Workbench required for interface integration test')
    from catalog import source_file
    if not source_file('destrieux2009', 'L').is_file():
        pytest.skip('Optional TemplateFlow Destrieux input not downloaded')
    monkeypatch.setenv('ATLAS_RESCUE_WB',wb)
    monkeypatch.setenv('ATLAS_RESCUE_DATA',str(ROOT/'reference-data'))
    a=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
    a.selectbox(key='atlas').select('destrieux2009').run()
    a.checkbox[0].check().run();a.button[0].click().run(timeout=60)
    assert not a.exception and not a.error and a.success
    report=a.session_state['result'][0]
    assert report['source_parcels_present']==75  # 74 regions plus a labelled medial wall
    assert report['target_parcels_present']==74
    assert report['parcels_without_target_vertices']==[42]
    b=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
    assert not b.success
    assert 'result' not in b.session_state
    a.selectbox(key='hemisphere').select('R').run()
    assert 'result' not in a.session_state
    assert not a.success


def test_missing_workbench_disables_conversion(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('ATLAS_RESCUE_WB', '/missing/workbench/wb_command')
    app = AppTest.from_file(str(ROOT/'app.py')).run()
    app.checkbox[0].check().run()
    assert not app.exception
    assert app.button[0].disabled
    assert app.warning
    assert any('sudo apt install connectome-workbench' in item.value for item in app.markdown)


def test_missing_selected_hemisphere_files(tmp_path, monkeypatch):
    import converter
    monkeypatch.setattr(converter, 'check_workbench', lambda wb: (wb, 'test'))
    issues = converter.setup_issues(tmp_path, 'R', 'wb_command', tmp_path/'missing.annot')
    assert len(issues) == 9
    assert all('hemi-R' in issue for issue in issues[:8])
    assert 'Missing input atlas' in issues[-1]


def test_failing_workbench_version(tmp_path, monkeypatch):
    import converter
    import subprocess
    monkeypatch.setattr(converter.shutil, 'which', lambda wb: '/fake/wb_command')
    def fail(*args, **kwargs):
        assert args[0] == ['/fake/wb_command', '-version']
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(converter.subprocess, 'run', fail)
    assert 'Workbench could not run -version' in converter.setup_issues(tmp_path, 'L', 'wb', None)[0]


@pytest.mark.workbench
def test_schaefer_conversion_from_public_download_profile(monkeypatch):
    from streamlit.testing.v1 import AppTest
    wb = os.environ.get('ATLAS_RESCUE_WB') or shutil.which('wb_command')
    if not wb:
        pytest.skip('Workbench required for Schaefer interface integration')
    monkeypatch.setenv('ATLAS_RESCUE_WB', wb)
    monkeypatch.setenv('ATLAS_RESCUE_DATA', str(ROOT/'reference-data'))
    app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=60).run()
    app.checkbox[0].check().run()
    assert not app.button[0].disabled, 'Run prepare_demo.py --profile test for required inputs'
    app.button[0].click().run(timeout=60)
    assert not app.exception and not app.error and app.success
    report = app.session_state['result'][0]
    assert report['source_parcels_present'] == report['target_parcels_present'] == 50
    assert all(report['checks'].values())


@pytest.mark.parametrize('atlas', ['schaefer100-7net', 'desikan2006', 'destrieux2009'])
def test_catalog_marks_missing_selected_hemisphere(monkeypatch, tmp_path, atlas):
    from streamlit.testing.v1 import AppTest
    import catalog
    import converter
    # Isolate input availability without modifying any real atlas/reference files.
    right = tmp_path/'R.annot'
    right.touch()
    monkeypatch.setattr(catalog, 'source_file', lambda key, hemi: tmp_path/f'{hemi}.annot')
    monkeypatch.setattr(converter, 'check_workbench', lambda wb: (wb, 'test'))
    monkeypatch.setattr(converter, 'required_reference_paths', lambda data, hemi: {})
    monkeypatch.setattr(converter, 'display_mesh_paths', lambda data, hemi: ())
    app = AppTest.from_file(str(ROOT/'app.py')).run()
    app.selectbox(key='atlas').select(atlas).run()
    app.checkbox[0].check().run()
    assert not app.exception
    assert app.button[0].disabled
    assert all('missing L file' in option for option in app.selectbox(key='atlas').options)
    commands = [item.value for item in app.code]
    if atlas == 'schaefer100-7net':
        assert 'python prepare_demo.py' in commands
        assert not any('--include-templateflow' in command for command in commands)
    else:
        assert 'python prepare_demo.py --include-templateflow' in commands
        assert any('THIRD_PARTY_NOTICES.md' in item.value for item in app.markdown)
    app.selectbox(key='hemisphere').select('R').run()
    assert not app.exception
    assert not app.button[0].disabled
    assert app.selectbox(key='atlas').value == atlas
    assert all('missing' not in option for option in app.selectbox(key='atlas').options)
    assert not app.code  # no download prompt for the available hemisphere
