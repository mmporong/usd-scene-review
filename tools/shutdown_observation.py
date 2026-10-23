"""Read-only close receipts. No Kit imports, prompt actions or state restoration."""
from pathlib import Path
import hashlib
import sys


SAVE_PROMPT = 'Would you like to save this stage?'


def window_receipts(windows, find_all, prompt_title=None):
    """Inspect only an existing file prompt; never traverse general editing UI."""
    result = []
    for window in windows:
        title = window.title
        receipt = {'title': title, 'visible': bool(window.visible)}
        if receipt['visible'] and title == prompt_title and title and '//' not in title:
            labels = find_all(title + '//Frame/**/Label[*]')
            receipt['save_prompt'] = any(label.widget.text == SAVE_PROMPT for label in labels)
        else:
            receipt['save_prompt'] = False
            receipt['query_skipped'] = True
        result.append(receipt)
    return result


def context_receipt(ctx, initial_ctx, initial_stage, fixture):
    pending_at_entry = bool(ctx.has_pending_edit())
    stage = ctx.get_stage()
    receipt = {
        'context_name': ctx.get_name(), 'stage_id': int(ctx.get_stage_id()),
        'same_context': ctx is initial_ctx, 'same_stage': stage == initial_stage,
        'stage_present': stage is not None, 'pending_edit': bool(ctx.has_pending_edit()),
        'can_close_stage': bool(ctx.can_close_stage()),
        'pending_at_entry': pending_at_entry,
    }
    if stage is not None:
        root = stage.GetRootLayer()
        session = stage.GetSessionLayer()
        edit_layer = stage.GetEditTarget().GetLayer()
        receipt.update(fixture_active=bool(root.realPath) and Path(root.realPath).resolve() == fixture,
                       root_dirty=bool(root.dirty), session_dirty=bool(session.dirty),
                       edit_target='root' if edit_layer == root else ('session' if edit_layer == session else 'other'),
                       root_text_sha256=hashlib.sha256(root.ExportToString().encode()).hexdigest(),
                       session_text_sha256=hashlib.sha256(session.ExportToString().encode()).hexdigest(),
                       camera_prims=[str(prim.GetPath()) for prim in stage.Traverse() if prim.GetTypeName() == 'Camera'])
    utility = sys.modules.get('omni.kit.viewport.utility')
    viewport = utility.get_active_viewport() if utility is not None else None
    receipt['viewport_api_present'] = viewport is not None
    if viewport is not None:
        receipt['viewport_camera_path'] = str(viewport.camera_path)
    receipt['pending_after_native_observation'] = bool(ctx.has_pending_edit())
    return receipt


def close_receipt(ctx, initial_ctx, initial_stage, fixture, file_impl, windows):
    receipt = context_receipt(ctx, initial_ctx, initial_stage, fixture)
    utility = file_impl._file_util_instance
    task = utility._task if utility is not None else None
    task_state = 'absent'
    task_error = None
    if task is not None:
        task_state = 'cancelled' if task.cancelled() else ('done' if task.done() else 'pending')
        if task_state == 'done':
            error = task.exception()
            task_error = type(error).__name__ + ': ' + str(error) if error else None
    receipt.update({
        'file_utility_present': utility is not None, 'file_task_state': task_state,
        'file_task_error': task_error, 'windows': windows,
        'save_prompt_observed': any(window['save_prompt'] for window in windows),
    })
    return receipt
