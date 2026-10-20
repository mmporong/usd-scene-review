"""Exercise actual adapter lifecycle methods with GPU-free boundary stubs.

Only the class base is replaced; method bodies come from the adapter's AST. These
tests establish Python ownership ordering, not Kit native or GUI compatibility.
"""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest


ADAPTER = (Path(__file__).resolve().parents[1] / "exts/mmporong.scene.review"
           / "mmporong/scene/review/extension.py")


def harness(outcome=True, remains_attached=False):
    events = []
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    adapter = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    adapter.bases = [ast.Name(id="object", ctx=ast.Load())]
    module = ast.fix_missing_locations(ast.Module(body=[adapter], type_ignores=[]))
    cache = SimpleNamespace(Erase=lambda key: events.append("cache_erase"))
    namespace = {
        "asyncio": asyncio,
        "carb": SimpleNamespace(log_error=lambda text: events.append("error"),
                                log_warn=lambda text: events.append("warn")),
        "omni": SimpleNamespace(usd=SimpleNamespace(
            destroy_context=lambda name: events.append("context_destroy") or True),
            timeline=SimpleNamespace(destroy_timeline=lambda name: events.append("timeline_destroy") or True)),
        "UsdUtils": SimpleNamespace(StageCache=SimpleNamespace(Get=lambda: cache)),
        "_CLEANUP_TASKS": set(), "_RETAINED_OWNERS": set(),
    }
    exec(compile(module, str(ADAPTER), "exec"), namespace)

    class Context:
        stage = object()

        def get_stage(self):
            return self.stage

        def close_stage(self):
            events.append("stage_close")
            if isinstance(self.outcome, Exception):
                raise self.outcome
            if self.outcome and not remains_attached:
                self.stage = None
            return self.outcome

    class Layer:
        dirty = False

        def SetPermissionToEdit(self, permission):
            events.append(("edit", permission))

        def SetPermissionToSave(self, permission):
            events.append(("save", permission))

    owner = namespace["SceneReviewExtension"]()
    owner._context = Context()
    owner._context.outcome = outcome
    owner._context_name = "owned-only"
    owner._timeline = object()
    owner._viewport = SimpleNamespace(destroy=lambda: events.append("viewport_destroy"))
    owner._window = SimpleNamespace(destroy=lambda: events.append("panel_destroy"))
    owner._attachment_pending = False
    owner._shutting_down = False
    owner._release_blocked = False
    owner._release_error = ""
    owner._task = None
    owner._cleanup_task = None
    owner._stage_id = 7
    owner._layer_permissions = [(Layer(), True, True, False)]
    owner._snapshot = object()
    owner._side = "A"
    owner._report = {"status": "changed"}
    owner._messages = []
    owner._message = owner._messages.append
    return owner, events, namespace


class CloseOwnershipTests(unittest.TestCase):
    def assert_protected(self, owner, events, snapshot):
        self.assertEqual(owner._stage_id, 7)
        self.assertIs(owner._snapshot, snapshot)
        self.assertEqual(len(owner._layer_permissions), 1)
        self.assertNotIn("cache_erase", events)
        self.assertNotIn("viewport_destroy", events)
        self.assertFalse(any(isinstance(event, tuple) for event in events))
        self.assertTrue(owner._release_blocked)
        self.assertIn("unconfirmed", owner._messages[-1])

    def test_false_and_exception_preserve_resources_and_block_transitions(self):
        for outcome in (False, RuntimeError("native close failed")):
            with self.subTest(outcome=type(outcome).__name__):
                owner, events, _ = harness(outcome)
                snapshot = owner._snapshot
                self.assertFalse(owner._release_stage())
                self.assert_protected(owner, events, snapshot)
                close_count = events.count("stage_close")
                owner._compare()
                owner._schedule_view("B")
                owner._close_review()
                owner._frame_selection()
                self.assertEqual(events.count("stage_close"), close_count)
                self.assertIsNone(owner._task)
                self.assert_protected(owner, events, snapshot)

    def test_success_flag_with_attached_stage_is_unconfirmed(self):
        owner, events, _ = harness(True, remains_attached=True)
        snapshot = owner._snapshot
        self.assertFalse(owner._release_stage())
        self.assert_protected(owner, events, snapshot)

    def test_confirmed_close_releases_then_destroys_viewport(self):
        owner, events, _ = harness()
        self.assertTrue(owner._dispose_review())
        self.assertLess(events.index("stage_close"), events.index("cache_erase"))
        self.assertLess(events.index("cache_erase"), events.index(("edit", True)))
        self.assertLess(events.index(("save", True)), events.index("viewport_destroy"))
        self.assertIsNone(owner._stage_id)
        self.assertIsNone(owner._snapshot)
        self.assertEqual(owner._layer_permissions, [])
        self.assertFalse(owner._release_blocked)

    def test_shutdown_failed_close_never_destroys_context(self):
        for outcome in (False, RuntimeError("native close failed")):
            with self.subTest(outcome=type(outcome).__name__):
                owner, events, namespace = harness(outcome)
                snapshot = owner._snapshot
                owner.on_shutdown()
                self.assert_protected(owner, events, snapshot)
                self.assertNotIn("context_destroy", events)
                self.assertIn(owner, namespace["_RETAINED_OWNERS"])

    def test_shutdown_can_retry_confirmed_close_without_early_release(self):
        owner, events, namespace = harness(False)
        snapshot = owner._snapshot
        self.assertFalse(owner._release_stage())
        self.assert_protected(owner, events, snapshot)
        owner._context.outcome = True
        owner.on_shutdown()
        self.assertIsNone(owner._context)
        self.assertIsNone(owner._snapshot)
        self.assertLess(events.index("cache_erase"), events.index("context_destroy"))
        self.assertLess(events.index("context_destroy"), events.index("timeline_destroy"))
        self.assertNotIn(owner, namespace["_RETAINED_OWNERS"])


class AttachmentOrderingTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_waits_for_native_completion(self):
        owner, events, _ = harness()
        owner._attachment_pending = True
        ready = asyncio.Event()

        async def attach():
            await ready.wait()
            events.append("attach_finished")
            owner._attachment_pending = False

        owner._task = asyncio.create_task(attach())
        await asyncio.sleep(0)
        owner.on_shutdown()
        await asyncio.sleep(0)
        self.assertNotIn("stage_close", events)
        self.assertNotIn("context_destroy", events)
        self.assertFalse(owner._task.cancelled())
        ready.set()
        await owner._cleanup_task
        self.assertLess(events.index("attach_finished"), events.index("stage_close"))
        self.assertIsNone(owner._context)

    async def test_external_cancellation_retains_unknown_attachment_owner(self):
        owner, events, namespace = harness()
        owner._attachment_pending = True
        owner._task = asyncio.create_task(asyncio.Event().wait())
        await asyncio.sleep(0)
        owner.on_shutdown()
        owner._task.cancel()
        await owner._cleanup_task
        self.assertNotIn("stage_close", events)
        self.assertNotIn("context_destroy", events)
        self.assertIn(owner, namespace["_RETAINED_OWNERS"])


if __name__ == "__main__":
    unittest.main()
