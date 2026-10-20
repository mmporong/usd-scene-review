"""Process protocol/ownership tests; native rendering is validated separately."""
import asyncio
from pathlib import Path
import tempfile
import unittest

from usd_scene_review.worker_client import ViewerClient, read_message, write_message


class Process:
    def __init__(self):
        self.code = None
        self.terminated = False
    def poll(self):
        return self.code
    def terminate(self):
        self.terminated = True
        self.code = 1


class ViewerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manifests = {s: Path(self.temp.name) / (s + '.json') for s in ('A', 'B')}
        for path in self.manifests.values():
            path.write_text('{}')
        self.tasks = []
        self.directories = []

    async def asyncTearDown(self):
        import shutil
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        for directory in self.directories:
            shutil.rmtree(directory, ignore_errors=True)
        self.temp.cleanup()

    def client(self, exit_code=0, bad_nonce=False, silent=False):
        self.processes = []
        def launch(directory, config):
            self.directories.append(directory)
            process = Process()
            self.processes.append(process)
            async def serve():
                identity = {'schema': 1, 'nonce': 'bad' if bad_nonce else config['nonce']}
                write_message(directory / 'response.json', dict(identity, sequence=0, status='ready'))
                last = 0
                while process.poll() is None:
                    request = read_message(directory / 'request.json')
                    if request and request['sequence'] != last and not silent:
                        last = request['sequence']
                        status = 'viewing'
                        if request['operation'] == 'close':
                            status = 'closing'
                            write_message(directory / 'receipt.json', dict(identity, sequence=last,
                                          status='closed', preserved=True))
                        write_message(directory / 'response.json', dict(identity, sequence=last, status=status))
                        if status == 'closing':
                            await asyncio.sleep(.02)
                            process.code = exit_code
                    await asyncio.sleep(.005)
            self.tasks.append(asyncio.ensure_future(serve()))
            return process, None
        return ViewerClient(launch, timeout=.3)

    async def view(self, client):
        return await client.view(self.manifests, 'A', None, sdk='unused', worker_module='unused')

    async def test_graceful_receipt_and_actual_exit_required(self):
        client = self.client()
        await self.view(client)
        self.assertEqual(client.state, 'running')
        self.assertEqual((await client.frame('/World'))['status'], 'viewing')
        self.assertTrue(await client.close())
        self.assertEqual(client.last_exit, 0)
        self.assertIsNone(client.process)
        self.assertIsNone(client.directory)
        self.assertTrue(await client.close())

    async def test_receipt_with_failed_exit_never_passes(self):
        client = self.client(exit_code=7)
        await self.view(client)
        self.assertFalse(await client.close())
        self.assertEqual(client.last_exit, 7)
        self.assertEqual(client.state, 'failed')
        with self.assertRaises(RuntimeError):
            await self.view(client)
        self.assertTrue(client.acknowledge_failure())
        self.assertTrue(client.directory.is_dir())  # diagnostics retained

    async def test_wrong_identity_stops_only_owned_process(self):
        client = self.client(bad_nonce=True)
        with self.assertRaises(ValueError):
            await self.view(client)
        self.assertTrue(self.processes[0].terminated)
        self.assertEqual(client.state, 'failed')

    async def test_timeout_is_failure_and_owned_process_is_stopped(self):
        client = self.client(silent=True)
        with self.assertRaises(TimeoutError):
            await self.view(client)
        self.assertTrue(self.processes[0].terminated)
        self.assertIsNone(client.process)
        self.assertEqual(client.state, 'failed')

    async def test_disable_queues_close_and_blocks_new_launch(self):
        client = self.client()
        await self.view(client)
        closing = client.begin_shutdown()
        with self.assertRaises(RuntimeError):
            await self.view(client)
        self.assertTrue(await closing)
        self.assertEqual(len(self.processes), 1)
        await self.view(client)
        self.assertEqual(len(self.processes), 2)
        self.assertTrue(await client.close())

    async def test_changing_manifest_requires_close(self):
        client = self.client()
        await self.view(client)
        self.manifests['A'].write_text('{"changed":true}')
        with self.assertRaises(RuntimeError):
            await self.view(client)
        self.assertEqual(len(self.processes), 1)
        self.assertTrue(await client.close())

    async def test_manifest_identity_from_compare_is_not_replaced(self):
        client = self.client()
        with self.assertRaises(RuntimeError):
            await client.view(self.manifests, 'A', None, sdk='unused', worker_module='unused',
                              expected_hashes={'A': 'previous-identity', 'B': 'previous-identity'})
        self.assertEqual(self.processes, [])

    async def test_disable_before_first_view_does_not_block_future_use(self):
        client = self.client()
        self.assertTrue(await client.begin_shutdown())
        await self.view(client)
        self.assertTrue(await client.close())

    async def test_unconfirmed_termination_retains_owner_and_blocks_launch(self):
        from unittest.mock import AsyncMock, Mock
        client = ViewerClient()
        process = Mock(); process.poll.return_value = None
        client.process = process
        client._wait = AsyncMock(side_effect=TimeoutError('not confirmed'))
        await client._abort(RuntimeError('request failed'))
        self.assertIs(client.process, process)
        self.assertEqual(client.state, 'failed')
        self.assertFalse(client.acknowledge_failure())
        with self.assertRaises(RuntimeError):
            await self.view(client)
