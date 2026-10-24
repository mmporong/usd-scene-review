"""Deterministic project-only distribution candidate; no SDK/assets/logs collected."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
import importlib.util
import shutil
from pathlib import PurePosixPath

VERSION='0.1.0-rc.4'
ROOT=Path(__file__).resolve().parents[1]


def payload():
    files={}
    inputs=('review_kit.py','launch.ps1','README.md','apps/scene-review.kit',
            'exts/usd.review.distribution/config/extension.toml',
            'exts/usd.review.distribution/distribution_bootstrap.py',
            'examples/synthetic/before.usda','examples/synthetic/after.usda')
    for name in inputs:
        path=ROOT/'distribution'/name
        if path.is_symlink():raise ValueError('Linked distribution input refused')
        files[name]=path.read_bytes()
    extension=ROOT/'exts/mmporong.scene.review'
    for path in extension.rglob('*'):
        if (path.is_file() and '__pycache__' not in path.parts
                and (path.suffix=='.py' or path.relative_to(extension).as_posix()
                     in ('config/extension.toml','docs/README.md'))):
            if path.is_symlink():raise ValueError('Linked extension input refused')
            name='exts/mmporong.scene.review/'+path.relative_to(extension).as_posix()
            files[name]=path.read_bytes()
    config='exts/mmporong.scene.review/config/extension.toml'
    files[config]=files[config].decode('utf-8').replace('path = "../../src"','path = "python"').encode('utf-8')
    for path in (ROOT/'src/usd_scene_review').glob('*.py'):
        if path.is_symlink():raise ValueError('Linked engine input refused')
        files['exts/mmporong.scene.review/python/usd_scene_review/'+path.name]=path.read_bytes()
    for name in ('quickstart-en.md','quickstart-ko.md','distribution-support.md','first-use.md'):
        files['docs/'+name]=(ROOT/'docs'/name).read_bytes()
    files['exts/mmporong.scene.review/docs/README.md'] = (
        b'# USD Scene Review\n\nRead the [packaged first-use guide](../../../docs/first-use.md).\n'
        b'Stage-free working-viewport overlay; Full/live A/B remains guarded.\n')
    files['NOTICE.txt']=('USD Scene Review '+VERSION+' — evaluation candidate\n'
        'Project license not selected. No open-source reuse or redistribution license is granted by this candidate.\n'
        'NVIDIA SDK, MDL template files, binaries and factory source assets are not included.\n'
        'Use your separately obtained SDK under its applicable terms.\n').encode('utf-8')
    return files


def inspect(files):
    allowed={'.py','.ps1','.kit','.toml','.md','.txt','.usda'}
    for name,data in files.items():
        suffix=Path(name).suffix
        if suffix not in allowed or any(part in ('__pycache__','.git') for part in Path(name).parts):
            raise ValueError('Unexpected payload type/path: '+name)
        if suffix=='.usda' and name not in ('examples/synthetic/before.usda','examples/synthetic/after.usda'):
            raise ValueError('Only the public synthetic USDA pair may be packaged')
        text=data.decode('utf-8')
        if re.search(r'(?i)(C:[\\/]Users[\\/]|D:[\\/]FactoryOps|/home/|LIMMM|BEGIN [A-Z ]*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{25,}|AKIA[A-Z0-9]{16})',text):
            raise ValueError('Private path/credential pattern detected: '+name)
    return {'files':len(files),'bytes_uncompressed':sum(map(len,files.values())),
            'source_assets':'only project-authored synthetic before/after USDA',
            'sdk_binaries':False,'raw_logs':False,'license':'not selected',
            'scope':'Windows stage-free overlay candidate; legacy minimal worker optional; not a formal release'}


def build(destination):
    destination=Path(destination)
    checksum=destination.with_name(destination.name+'.sha256')
    if any(p.exists() or p.is_symlink() for p in (destination,checksum)):
        raise ValueError('Use new archive and checksum destinations')
    # All payloads are UTF-8 text. Canonical LF makes checkout autocrlf irrelevant.
    files={name:data.replace(b'\r\n',b'\n') for name,data in payload().items()}
    audit=inspect(files)
    manifest={'schema':1,'version':VERSION,'files':{name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())},'audit':audit}
    files['candidate.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode('utf-8')
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            archive.writestr(info,data)
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    with checksum.open('x',encoding='utf-8') as stream:stream.write(digest+'  '+destination.name+'\n')
    return {'version':VERSION,'sha256':digest,
            'archive_bytes':destination.stat().st_size,'audit':audit}


def extract_for_validation(archive_path, root):
    """Use verified candidate bytes, never a fresh repository-built extension."""
    root=Path(root);extracted=root/'candidate';extracted.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate candidate archive entries')
        for entry in archive.infolist():
            name=entry.filename;rel=PurePosixPath(name)
            if (rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name
                    or not rel.parts or entry.is_dir() or (entry.external_attr>>16)&0o170000==0o120000):
                raise ValueError('Unsafe candidate archive entry')
        archive.extractall(extracted)
    spec=importlib.util.spec_from_file_location('trusted_candidate_verifier',ROOT/'distribution/review_kit.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    manifest=verifier.verify(extracted)
    source=extracted/'exts/mmporong.scene.review'
    target=root/'exts/mmporong.scene.review'
    shutil.copytree(source,target)
    prefix='exts/mmporong.scene.review/'
    expected={name[len(prefix):]:digest for name,digest in manifest['files'].items() if name.startswith(prefix)}
    actual={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in target.rglob('*') if p.is_file()}
    if expected!=actual:raise ValueError('Candidate extension copy differs from verified payload')
    return {'version':manifest['version'],'archive_sha256':hashlib.sha256(Path(archive_path).read_bytes()).hexdigest(),
            'verified_extension_files':len(expected),'copied_bytes_verified':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.destination),indent=2))
