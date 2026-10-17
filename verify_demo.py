"""Run the actual bilateral conversion and reproduce the neuromaps baseline."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess

import nibabel as nib
import numpy as np
from converter import convert,load_source

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--wb',default='wb_command')
    p.add_argument('--data-dir',default=str(ROOT/'reference-data'))
    a=p.parse_args()
    import shutil
    wb=shutil.which(a.wb)
    if not wb:raise RuntimeError('Install Workbench and set --wb.')
    os.environ['PATH']=str(Path(wb).parent)+os.pathsep+os.environ.get('PATH','')
    os.environ['NEUROMAPS_DATA']=str(Path(a.data_dir).resolve())
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=ROOT/'runs'/stamp;out.mkdir(parents=True)
    from neuromaps import transforms
    # All reference files actually used by this route are local and checked by
    # the converter. Avoid an unnecessary all-files OSF fetch in this baseline.
    old_fetch=transforms.fetch_atlas
    transforms.fetch_atlas=lambda *args,**kwargs: None
    summary=[]
    try:
        for h,hemi in [('lh','L'),('rh','R')]:
            source=ROOT/'demo/input'/f'{h}.Schaefer2018_100Parcels_7Networks_order.annot'
            fixed=convert(source,out/hemi,hemi,a.data_dir,wb)
            baseline={'hemisphere':hemi}
            try:
                source_img=load_source(source)
                result,=transforms.fsaverage_to_fslr(source_img,hemi=hemi,method='nearest')
                file=out/f'hemi-{hemi}_unmodified.func.gii';nib.save(result,file)
                baseline.update({'intent':nib.nifti1.intent_codes.label[result.darrays[0].intent],
                                 'label_dictionary_entries':len(result.labeltable.labels)})
                r=subprocess.run([wb,'-label-export-table',str(file),str(out/f'{hemi}_baseline_labels.txt')],capture_output=True,text=True)
                baseline['workbench_label_export_returncode']=r.returncode
                baseline['workbench_label_export_stderr']=r.stderr
                baseline['exported_table_bytes']=(out/f'{hemi}_baseline_labels.txt').stat().st_size if (out/f'{hemi}_baseline_labels.txt').exists() else 0
                target=nib.load(out/hemi/fixed['target']['filename']).agg_data()
                arr=result.agg_data();foreground=target!=0
                baseline['numeric_agreement_on_corrected_foreground']=float(np.mean(arr[foreground]==target[foreground]))
            except Exception as e:
                baseline['conversion_error']=str(e)
            summary.append({'hemisphere':hemi,'fixed_status':fixed['status'],
                            'source_parcels':fixed['source_parcels_present'],'target_parcels':fixed['target_parcels_present'],
                            'baseline':baseline})
    finally:
        transforms.fetch_atlas=old_fetch
    (out/'verification_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({'output_directory':str(out),'summary':summary},indent=2))


if __name__=='__main__':main()
