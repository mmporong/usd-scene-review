"""Local single-writer human disposition history, separate from USD evidence.

This is not authenticated approval or tamper-proof multi-user storage.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


MAX_BYTES = 8 * 1024 * 1024


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def change_identity(manifest_hashes, change):
    if set(manifest_hashes) != {'A', 'B'} or any(
            len(v) != 64 or any(c not in '0123456789abcdef' for c in v) for v in manifest_hashes.values()):
        raise ValueError('Exact compared A/B manifest hashes are required')
    return dict(manifests=dict(manifest_hashes), path=change['path'],
                change_sha256=hashlib.sha256(_canonical(change).encode('utf-8')).hexdigest())


def _path(path, forbidden_roots):
    path = Path(path).expanduser()
    if path.is_symlink():
        raise ValueError('Review log symlinks are unsupported')
    path = path.resolve()
    if path.suffix.lower() != '.jsonl' or not path.parent.is_dir():
        raise ValueError('Choose a .jsonl log in an existing separate folder')
    if any(path == Path(r).resolve() or path.is_relative_to(Path(r).resolve()) for r in forbidden_roots):
        raise ValueError('Review history must be outside immutable snapshot bundles')
    if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
        raise ValueError('Review history requires a regular single-link file')
    return path


@contextmanager
def _locked(path):
    lock = path.with_name(path.name + '.lock')
    # Never break another writer's lock or erase uncertain history after a crash.
    with lock.open('x', encoding='utf-8') as stream:
        stream.write('local review writer\n')
    try:
        yield
    finally:
        lock.unlink()


def _read(path):
    if not path.exists():
        return []
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Review history exceeds this MVP size limit')
    data = path.read_text(encoding='utf-8')
    if data and not data.endswith('\n'):
        raise ValueError('Incomplete review history; retain and inspect it separately')
    result, previous = [], ''
    for line in data.split('\n')[:-1]:
        event = json.loads(line)
        digest = event.pop('sha256')
        if (event.get('schema') != 1 or event.get('sequence') != len(result) + 1
                or event.get('previous') != previous
                or event.get('disposition') not in ('intentional', 'needs-review')
                or not isinstance(event.get('reason'), str) or not event['reason'].strip()
                or hashlib.sha256(_canonical(event).encode('utf-8')).hexdigest() != digest):
            raise ValueError('Invalid review history; nothing overwritten')
        event['sha256'] = digest
        result.append(event); previous = digest
    return result


def history(path, *, forbidden_roots=()):
    path = _path(path, forbidden_roots)
    with _locked(path):
        return _read(path)


def latest(events, identity):
    return next((e for e in reversed(events) if e['identity'] == identity), None)


def record(path, identity, disposition, reason, *, forbidden_roots=()):
    if disposition not in ('intentional', 'needs-review') or not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 2000:
        raise ValueError('Choose a human disposition and enter a reason (1-2000 characters)')
    path = _path(path, forbidden_roots)
    with _locked(path):
        events = _read(path)
        event = dict(schema=1, sequence=len(events)+1, previous=events[-1]['sha256'] if events else '',
                     timestamp=datetime.now(timezone.utc).isoformat(), actor='local user (unverified)',
                     identity=identity, disposition=disposition, reason=reason.strip())
        event['sha256'] = hashlib.sha256(_canonical(event).encode('utf-8')).hexdigest()
        encoded = _canonical(event)+'\n'
        if (path.stat().st_size if path.exists() else 0) + len(encoded.encode('utf-8')) > MAX_BYTES:
            raise ValueError('Review history size limit reached; nothing appended')
        with path.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
        return event
