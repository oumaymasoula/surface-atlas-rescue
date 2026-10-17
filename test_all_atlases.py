"""Convert every catalog atlas/hemisphere; save machine-readable verification.

Run: python test_all_atlases.py --workers 2
More workers are NOT an estimate of supported public users.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
from pathlib import Path
import shutil
import csv

from catalog import entries,source_file,ROOT
from converter import convert,load_source,validate_label_image


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wb', default='wb_command')
    p.add_argument('--data-dir', default=str(ROOT/'reference-data'))
    p.add_argument('--workers',type=int,default=1,choices=[1,2])
    p.add_argument('--output',default=None)
    args=p.parse_args()
    wb=shutil.which(args.wb)
    if not wb:
        candidate=ROOT/'tools/workbench/bin_linux64/wb_command'
        wb=str(candidate) if candidate.is_file() else None
    if not wb:raise SystemExit('Workbench not found: add it to PATH or pass --wb /absolute/path/to/wb_command')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=Path(args.output) if args.output else ROOT/'catalog-tests'/stamp
    output.mkdir(parents=True,exist_ok=False)
    jobs=[(entry,h) for entry in entries() for h in ['L','R']]
    def run(job):
        entry,hemi=job
        row={'atlas':entry['id'],'family':entry['family'],'hemisphere':hemi}
        try:
            source=source_file(entry['id'],hemi)
            report=convert(source,output/entry['id']/hemi,hemi,args.data_dir,wb)
            row.update(status=report['status'],source_regions=report['source_parcels_present'],
                       output_regions=report['target_parcels_present'],
                       disappeared_regions=report['parcels_without_target_vertices'],
                       checks_passed=all(report['checks'].values()))
        except Exception as exc:
            row.update(status='failed',error=str(exc),checks_passed=False)
        print(f'{row["atlas"]} {hemi}: {row["status"]}',flush=True)
        return row
    with ThreadPoolExecutor(max_workers=args.workers) as pool:results=list(pool.map(run,jobs))
    summary={'workers':args.workers,'jobs':len(jobs),'passed':sum(r['checks_passed'] for r in results),
             'failed':sum(not r['checks_passed'] for r in results),'results':results}
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    fields=['atlas','family','hemisphere','status','source_regions','output_regions','disappeared_regions','checks_passed','error']
    with (output/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(results)
    print(f'{summary["passed"]}/{len(jobs)} passed. Results: {output}')
    if summary['failed']:raise SystemExit(1)


if __name__=='__main__':main()
