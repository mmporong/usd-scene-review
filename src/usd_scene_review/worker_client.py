"""Owned viewer process transport. This module imports no Kit/native UI APIs."""
import asyncio
import builtins
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from uuid import uuid4

SCHEMA = 1
_REGISTRY = '_usd_scene_review_viewer_v1'


def write_message(path, value):
    path = Path(path)
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(value, sort_keys=True), encoding='utf-8')
    # A Windows reader may briefly hold response.json without delete sharing.
    # Keep the old complete message until atomic replacement succeeds; never
    # unlink it or spin indefinitely on a persistent permission failure.
    for attempt in range(101):
        try:
            temporary.replace(path)
            return
        except PermissionError as exc:
            if os.name != 'nt' or getattr(exc, 'winerror', None) not in (5, 32) or attempt == 100:
                raise
            time.sleep(.01)


def _read_message_bytes(path):
    with Path(path).open('rb') as stream:
        return stream.read(1024 * 1024 + 1)


def read_message(path):
    path = Path(path)
    for attempt in range(101):
        try:
            raw = _read_message_bytes(path)
            break
        except FileNotFoundError:
            return None
        except PermissionError as exc:
            if (os.name != 'nt' or (getattr(exc, 'winerror', None) not in (5, 32) and exc.errno != 13)
                    or attempt == 100):
                raise
            time.sleep(.01)
    if len(raw) > 1024 * 1024:
        raise ValueError('Viewer response exceeds protocol limit')
    value = json.loads(raw.decode('utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Viewer response must be an object')
    return value


class WindowsJob:
    """Keep this process's worker and descendants inside one owned Windows Job."""
    def __init__(self, process):
        import ctypes as c
        from ctypes import wintypes as w
        class Basic(c.Structure):
            _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong),
                        ('flags', w.DWORD), ('minimum', c.c_size_t), ('maximum', c.c_size_t),
                        ('active', w.DWORD), ('affinity', c.c_size_t),
                        ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class Io(c.Structure):
            _fields_ = [(name, c.c_ulonglong) for name in ('ro', 'wo', 'oo', 'rt', 'wt', 'ot')]
        class Limits(c.Structure):
            _fields_ = [('basic', Basic), ('io', Io), ('process_memory', c.c_size_t),
                        ('job_memory', c.c_size_t), ('peak_process', c.c_size_t),
                        ('peak_job', c.c_size_t)]
        self.api = c.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        self.api.SetInformationJobObject.restype = w.BOOL
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.api.AssignProcessToJobObject.restype = w.BOOL
        self.api.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        self.api.TerminateJobObject.restype = w.BOOL
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.api.CloseHandle.restype = w.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError('Could not create owned viewer job')
        limits = Limits(); limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
            self.close(); raise OSError('Could not configure owned viewer job')
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            self.close(); raise OSError('Could not assign viewer to owned job')

    def terminate(self):
        if self.handle and not self.api.TerminateJobObject(self.handle, 1):
            raise OSError('Owned viewer job termination was not confirmed')

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle); self.handle = None

    def __del__(self):
        self.close()


def resume_owned_process(process):
    """Resume the sole primary thread after assigning a suspended owned process."""
    import ctypes as c
    from ctypes import wintypes as w
    class ThreadEntry(c.Structure):
        _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('thread', w.DWORD),
                    ('owner', w.DWORD), ('priority', w.LONG), ('delta', w.LONG), ('flags', w.DWORD)]
    api = c.WinDLL('kernel32', use_last_error=True)
    api.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    api.CreateToolhelp32Snapshot.restype = w.HANDLE
    api.Thread32First.argtypes = api.Thread32Next.argtypes = [w.HANDLE, c.POINTER(ThreadEntry)]
    api.Thread32First.restype = api.Thread32Next.restype = w.BOOL
    api.OpenThread.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    api.OpenThread.restype = w.HANDLE
    api.ResumeThread.argtypes = [w.HANDLE]
    api.ResumeThread.restype = w.DWORD
    api.CloseHandle.argtypes = [w.HANDLE]
    api.CloseHandle.restype = w.BOOL
    snapshot = api.CreateToolhelp32Snapshot(4, 0)
    if snapshot == c.c_void_p(-1).value:
        raise OSError('Cannot enumerate owned suspended process thread')
    threads = []
    try:
        entry = ThreadEntry(); entry.size = c.sizeof(entry)
        present = api.Thread32First(snapshot, c.byref(entry))
        while present:
            if entry.owner == process.pid:
                threads.append(entry.thread)
            present = api.Thread32Next(snapshot, c.byref(entry))
    finally:
        api.CloseHandle(snapshot)
    if len(threads) != 1:
        raise OSError('Suspended viewer did not have exactly one primary thread')
    thread = api.OpenThread(2, False, threads[0])
    if not thread:
        raise OSError('Cannot access owned viewer primary thread')
    try:
        if api.ResumeThread(thread) != 1:
            raise OSError('Owned viewer primary thread resume was not confirmed')
    finally:
        api.CloseHandle(thread)


class ViewerClient:
    version = SCHEMA

    def __init__(self, launch=None, timeout=90):
        self.process = None
        self.job = None
        self.directory = None
        self.state = 'closed'
        self.error = ''
        self.last_exit = None
        self.last_receipt = None
        self.nonce = None
        self.sequence = 0
        self.manifests = None
        self._launch = launch or self._launch_kit
        self.timeout = timeout
        self._lock = asyncio.Lock()
        self._closing_task = None
        self._log = None
        self._shutdown_requested = False
        self._last_operation = None

    def _launch_kit(self, directory, config):
        if os.name != 'nt':
            raise RuntimeError('Viewer is qualified only on Windows Isaac Sim 4.5')
        sdk = Path(config['sdk'])
        executable = sdk / 'kit/kit.exe'
        if not executable.is_file() or not (sdk / 'extscache').is_dir():
            raise RuntimeError('Existing Isaac Sim SDK was not found; use a matching installed runtime')
        runner = directory / 'exts/usd.review.viewer'
        (runner / 'config').mkdir(parents=True)
        # JSON string syntax is also valid TOML basic-string syntax for these paths.
        engine = json.dumps(str(Path(__file__).resolve().parents[1]))
        worker = json.dumps(config['worker_module'])
        (runner / 'config/extension.toml').write_text('''[package]
version="0.1.0"
[dependencies]
"omni.usd"={}
"omni.kit.viewport.window"={}
"omni.kit.viewport.utility"={}
[[python.module]]
name="usd_scene_review"
path=''' + engine + '''
[[python.module]]
name="scene_review_worker"
path=''' + worker + '\n', encoding='utf-8')
        app = directory / 'viewer.kit'
        app.write_text('''[package]
title="USD Scene Review Viewer"
[dependencies]
"omni.kit.uiapp"={}
"omni.kit.viewport.rtx"={}
"usd.review.viewer"={}
[settings]
app.asyncRendering=false
app.settings.persistent=false
app.extensions.registryEnabled=false
app.extensions.syncRegistryOnStartup=false
app.file.ignoreUnsavedOnExit=true
app.fastShutdown=false
app.window.width=1600
app.window.height=1000
renderer.multiGpu.autoEnable=false
app.viewport.defaults.hud.visible=false
app.viewport.defaults.guide.grid.visible=false
app.viewport.grid.enabled=false
exts."omni.kit.viewport.window".startup.disableWindowOnLoad=true
''', encoding='utf-8')
        command = [str(executable), str(app), '--portable', '--portable-root', str(directory / 'state'),
                   '--ext-folder', str(sdk / 'extscache'), '--ext-folder', str(sdk / 'exts'),
                   '--ext-folder', str(directory / 'exts'), '--/log/file=' + str(directory / 'kit.log'),
                   '--/app/userConfigPath=' + str(directory / 'user.config.json'),
                   '--/exts/usd.review.viewer/runDirectory=' + str(directory)]
        self._log = (directory / 'console.log').open('w', encoding='utf-8')
        # Kit 106 shader identifiers include SDK-relative paths. Keep its working
        # directory at the installed SDK, while all mutable state stays private.
        process = subprocess.Popen(command, cwd=sdk, stdout=self._log, stderr=subprocess.STDOUT,
                                   shell=False, creationflags=0x00000004)  # CREATE_SUSPENDED
        # Retain ownership before any operation that can fail. The suspended Kit
        # cannot spawn descendants before assignment to this kill-on-close Job.
        self.process = process
        self.job = WindowsJob(process)
        resume_owned_process(process)
        return process, self.job

    async def _wait(self, predicate, timeout=None):
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while time.monotonic() < deadline:
            value = predicate()
            if value is not None:
                return value
            await asyncio.sleep(0.05)
        raise TimeoutError('Viewer did not finish within the bounded wait')

    def _reply(self, sequence):
        response = read_message(self.directory / 'response.json')
        if response is None:
            if self.process.poll() is not None:
                raise RuntimeError('Viewer exited before confirming the request')
            return None
        if response.get('schema') != SCHEMA or response.get('nonce') != self.nonce:
            raise ValueError('Viewer response identity did not match')
        if response.get('sequence') != sequence:
            if self.process.poll() is not None:
                raise RuntimeError('Viewer exited before confirming the request')
            return None
        if response.get('status') == 'error':
            raise RuntimeError(response.get('message', 'Viewer failed'))
        return response

    async def _request(self, operation, **fields):
        self.sequence += 1
        self._last_operation = operation
        write_message(self.directory / 'request.json',
                      dict(schema=SCHEMA, nonce=self.nonce, sequence=self.sequence,
                           operation=operation, **fields))
        return await self._wait(lambda: self._reply(self.sequence))

    async def view(self, manifests, side, selected, *, sdk, worker_module, expected_hashes=None, focus=False, ghost=False, normalized=True, review=None):
        async with self._lock:
            if self._shutdown_requested or self.state in ('closing', 'failed'):
                raise RuntimeError(self.error or 'Viewer is still closing; wait before opening another')
            pinned = {s: {'path': str(Path(p).resolve()),
                          'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()}
                      for s, p in manifests.items()}
            if set(pinned) != {'A', 'B'} or side not in pinned:
                raise ValueError('Viewer requires the compared A and B manifests')
            if expected_hashes is not None and {s: r['sha256'] for s, r in pinned.items()} != expected_hashes:
                raise RuntimeError('Compared manifest identity changed; compare again')
            if self.process and self.manifests != pinned:
                raise RuntimeError('Close the current viewer before changing snapshots')
            try:
                if self.process is None:
                    self.nonce = uuid4().hex; self.sequence = 0; self.manifests = pinned
                    self._last_operation = None
                    self.directory = Path(tempfile.mkdtemp(prefix='usd-scene-review-'))
                    config = dict(schema=SCHEMA, nonce=self.nonce, manifests=pinned,
                                  sdk=str(sdk), worker_module=str(worker_module))
                    write_message(self.directory / 'config.json', config)
                    self.state = 'starting'
                    self.process, self.job = self._launch(self.directory, config)
                    ready = await self._wait(lambda: self._reply(0))
                    if ready.get('status') != 'ready':
                        raise RuntimeError(ready.get('message', 'Viewer could not start'))
                reply = await self._request('view', side=side, selected=selected, focus=focus, ghost=ghost, normalized=normalized, review=review or {})
                self.state = 'running'
                return reply
            except Exception as exc:
                await self._abort(exc)
                raise

    async def frame(self, selected, *, focus=None, ghost=None, review=None):
        async with self._lock:
            if self.state != 'running' or self.process is None:
                raise RuntimeError('Open View A or View B before framing a result')
            try:
                fields={}
                if focus is not None:fields['focus']=focus
                if ghost is not None:fields['ghost']=ghost
                if review is not None:fields['review']=review
                return await self._request('frame', selected=selected, **fields)
            except Exception as exc:
                await self._abort(exc)
                raise

    async def close(self):
        async with self._lock:
            if self.process is None:
                if self.state == 'closed':
                    self._shutdown_requested = False
                return self.state == 'closed'
            self.state = 'closing'
            try:
                reply = await self._request('close')
                if reply.get('status') != 'closing':
                    raise RuntimeError('Viewer did not accept graceful close')
                code = await self._wait(lambda: self.process.poll(), timeout=45)
                receipt = read_message(self.directory / 'receipt.json')
                self.last_exit, self.last_receipt = code, receipt
                if (code != 0 or not receipt or receipt.get('schema') != SCHEMA
                        or receipt.get('nonce') != self.nonce or receipt.get('status') != 'closed'
                        or receipt.get('sequence') != self.sequence
                        or receipt.get('preserved') is not True):
                    raise RuntimeError('Viewer close was not confirmed by receipt and exit code 0')
                self._release_process()
                self.state = 'closed'; self.error = ''
                self._shutdown_requested = False
                # Private files belong to the unique directory allocated by this instance.
                shutil.rmtree(self.directory)
                self.directory = None
                return True
            except Exception as exc:
                await self._abort(exc)
                return False

    async def _abort(self, error):
        self.error = type(error).__name__ + ': ' + str(error)
        self.state = 'failed'
        if self.process is not None and self.process.poll() is None:
            if self.job:
                self.job.terminate()
            else:
                self.process.terminate()
            try:
                await self._wait(lambda: self.process.poll(), timeout=10)
            except TimeoutError:
                self.error += '; owned process termination remains unconfirmed'
                return
        self._release_process()

    def _release_process(self):
        if self.job:
            self.job.close(); self.job = None
        if self._log:
            self._log.close(); self._log = None
        self.process = None

    def acknowledge_failure(self):
        if self.process is not None:
            return False
        self.state = 'closed'; self.error = ''
        self._shutdown_requested = False
        return True

    def begin_shutdown(self):
        self._shutdown_requested = True
        if self._closing_task is None or self._closing_task.done():
            self._closing_task = asyncio.ensure_future(self.close())
        return self._closing_task

    def shutdown_sync(self, timeout=60):
        """Bounded graceful close even when the host event loop is stopping.

        The child has its own loop. Wait for an in-flight command's acknowledgement
        before posting close, so no sequence is skipped or native attach cancelled.
        Forced containment is a failure, never a successful close.
        """
        self._shutdown_requested = True
        if self.process is None:
            if self.state == 'closed':
                self._shutdown_requested = False
            return self.state == 'closed'
        deadline = time.monotonic() + timeout
        def wait(predicate):
            while time.monotonic() < deadline:
                value = predicate()
                if value is not None:
                    return value
                time.sleep(.05)
            raise TimeoutError('Viewer graceful shutdown deadline exceeded')
        try:
            wait(lambda: self._reply(self.sequence))
            if self._last_operation != 'close':
                self.sequence += 1
                self._last_operation = 'close'
                write_message(self.directory / 'request.json', dict(
                    schema=SCHEMA, nonce=self.nonce, sequence=self.sequence, operation='close'))
            self.state = 'closing'
            reply = wait(lambda: self._reply(self.sequence))
            if reply.get('status') != 'closing':
                raise RuntimeError('Viewer did not acknowledge graceful close')
            code = wait(lambda: self.process.poll())
            receipt = read_message(self.directory / 'receipt.json')
            self.last_exit, self.last_receipt = code, receipt
            if (code != 0 or not receipt or receipt.get('schema') != SCHEMA
                    or receipt.get('nonce') != self.nonce or receipt.get('sequence') != self.sequence
                    or receipt.get('status') != 'closed' or receipt.get('preserved') is not True):
                raise RuntimeError('Viewer shutdown receipt and exit 0 not confirmed')
            self._release_process()
            self.state = 'closed'; self.error = ''; self._shutdown_requested = False
            shutil.rmtree(self.directory)
            self.directory = None
            return True
        except Exception as exc:
            self.state = 'failed'
            self.error = type(exc).__name__ + ': ' + str(exc)
            try:
                if self.process.poll() is None:
                    if self.job:
                        self.job.terminate()
                    else:
                        self.process.terminate()
                    self.process.wait(timeout=10)
                self._release_process()
            except Exception:
                self.error += '; owned termination is unconfirmed'
            return False


def get_viewer_client():
    client = getattr(builtins, _REGISTRY, None)
    if client is None:
        client = ViewerClient(); setattr(builtins, _REGISTRY, client)
    if getattr(client, 'version', None) != SCHEMA:
        raise RuntimeError('Existing viewer owner has an incompatible protocol; restart the app')
    return client
