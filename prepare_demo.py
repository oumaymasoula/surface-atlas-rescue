"""Download missing demo/reference files and verify pinned checksums."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parent


def ensure(item):
    path=ROOT/item['path']
    def valid():
        return path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
    if valid(): return f'Verified: {item["path"]}'
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.download')
    try:
        urllib.request.urlretrieve(item['url'],temporary)
        if hashlib.sha256(temporary.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError(f'Checksum mismatch: {item["path"]}. Source may have changed.')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return f'Downloaded and verified: {item["path"]}'


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-templateflow', action='store_true',
                        help='Download Desikan/Destrieux after reviewing upstream terms; see THIRD_PARTY_NOTICES.md')
    parser.add_argument('--profile', choices=['all', 'test'], default='all',
                        help='test: references and Schaefer-100/7-network only')
    args = parser.parse_args()
    manifest=json.loads((ROOT/'resources.json').read_text())
    items = manifest['files']
    if not args.include_templateflow:
        items = [item for item in items if 'templateflow' not in item['url']]
        print('TemplateFlow atlas files omitted; see --include-templateflow and THIRD_PARTY_NOTICES.md.')
    if args.profile == 'test':
        items = [item for item in items if item['path'].startswith('reference-data/')
                 or '100Parcels_7Networks' in item['path']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for message in pool.map(ensure,items): print(message)
