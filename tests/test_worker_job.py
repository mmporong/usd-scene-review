"""Real Windows containment and event-loop-independent graceful shutdown."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from usd_scene_review.worker_client import ViewerClient, WindowsJob, resume_owned_process


@unittest.skipUnless(os.name == 'nt', 'Windows process ownership API')
class WindowsOwnershipTests(unittest.TestCase):
    def test_job_assigned_before_immediate_descendant_runs(self):
        import ctypes as c
        from ctypes import wintypes as w
        with tempfile.TemporaryDirectory() as temp:
            pidfile = Path(temp) / 'child.pid'
            script = ('import subprocess,sys,time; from pathlib import Path; '
                      'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]); '
                      'Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)')
            process = subprocess.Popen([sys.executable, '-c', script, str(pidfile)],
                                       creationflags=4, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            job = None
            handle = None
            api = c.WinDLL('kernel32', use_last_error=True)
            api.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]; api.OpenProcess.restype = w.HANDLE
            api.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]; api.WaitForSingleObject.restype = w.DWORD
            api.CloseHandle.argtypes = [w.HANDLE]; api.CloseHandle.restype = w.BOOL
            try:
                self.assertFalse(pidfile.exists())
                job = WindowsJob(process)
                resume_owned_process(process)
                deadline = time.monotonic() + 10
                while not pidfile.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(pidfile.exists())
                handle = api.OpenProcess(0x100000 | 0x1000, False, int(pidfile.read_text()))
                self.assertTrue(handle)
                job.terminate()
                process.wait(timeout=10)
                self.assertEqual(api.WaitForSingleObject(handle, 10000), 0, 'owned descendant must exit')
            finally:
                if job:
                    job.close()
                if process.poll() is None:
                    process.terminate(); process.wait(timeout=10)
                if handle:
                    api.CloseHandle(handle)

    def test_synchronous_shutdown_needs_no_host_asyncio_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            script = '''import json,sys,time
from pathlib import Path
root=Path(sys.argv[1]); nonce=sys.argv[2]
def write(name, value):
 p=root/name; t=p.with_suffix('.pending');t.write_text(json.dumps(value));t.replace(p)
identity=dict(schema=1,nonce=nonce)
write('response.json',dict(identity,sequence=0,status='ready'))
while not (root/'request.json').is_file():time.sleep(.01)
r=json.loads((root/'request.json').read_text())
write('receipt.json',dict(identity,sequence=r['sequence'],status='closed',preserved=True))
write('response.json',dict(identity,sequence=r['sequence'],status='closing'))
'''
            client = ViewerClient()
            client.directory = directory
            client.nonce = 'test-owned-shutdown'
            client.process = subprocess.Popen([sys.executable, '-c', script, str(directory), client.nonce],
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            client.state = 'starting'
            self.assertTrue(client.shutdown_sync(timeout=10))
            self.assertEqual(client.last_exit, 0)
            self.assertIsNone(client.process)

    def test_failed_job_assignment_keeps_spawned_handle_owned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'kit').mkdir(); (root / 'kit/kit.exe').write_bytes(b'')
            (root / 'extscache').mkdir()
            from unittest.mock import Mock
            process = Mock(); process.poll.return_value = None
            client = ViewerClient()
            with patch('usd_scene_review.worker_client.subprocess.Popen', return_value=process) as spawn:
                with patch('usd_scene_review.worker_client.WindowsJob', side_effect=OSError('assignment refused')):
                    with self.assertRaises(OSError):
                        client._launch_kit(root, dict(sdk=str(root), worker_module=str(root)))
            self.assertIs(client.process, process)
            self.assertEqual(spawn.call_args.kwargs['creationflags'], 4)
            client._log.close()
