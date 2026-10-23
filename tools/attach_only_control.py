"""Matched 60-update attach/wait controls; no viewport or capture creation."""
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4

UPDATE_BUDGET=60


def prepare_open_fixture(fixture,destination):
    data=fixture.read_bytes()
    with destination.open('xb') as stream:stream.write(data)
    return hashlib.sha256(data).hexdigest()


async def evaluate(parent,root,mode):
    if mode not in ('wait','attach','open'):
        raise ValueError('Unknown attach control')
    import omni.kit.app
    import omni.usd
    import omni.timeline
    from omni.kit.widget.viewport import ViewportWidget
    from pxr import Sdf,Usd,UsdUtils
    from shutdown_observation import context_receipt
    app=omni.kit.app.get_app()
    host=omni.usd.get_context();original=host.get_stage()
    fixture=root/'shutdown-fixture.usda'
    result={'mode':mode,'status':'running','update_budget':UPDATE_BUDGET,'updates_completed':0,
            'checks':[],'observations':[],'owned_stage_events':[],'owned_resources_remaining':True}
    parent.result['attach_control']=result
    name='review_attach_'+uuid4().hex
    ctx=timeline=stage=cache_id=task=subscription=None
    open_fixture=root/'owned-open-fixture.usda'
    def write():
        (root/'attach-control-result.json').write_text(json.dumps(result,indent=2))
        parent.write()
    def check(label,value):
        result['checks'].append({'name':label,'passed':bool(value)})
        write()
        if not value:raise RuntimeError(label)
    def sample(phase):
        parent.native_observe('attach-control:'+phase)
        row={'phase':phase,'default':context_receipt(host,host,original,fixture)}
        if ctx is not None:
            row['owned']=context_receipt(ctx,ctx,stage,fixture)
        result['observations'].append(row);write()
    initial=context_receipt(host,host,original,fixture)
    views=len(list(ViewportWidget.get_instances()))
    try:
        sample('before-context')
        ctx=omni.usd.create_context(name)
        timeline=omni.timeline.get_timeline_interface(name);ctx.set_timeline(name)
        sample('context-created')
        if mode=='open':
            result['owned_fixture_sha256']=prepare_open_fixture(fixture,open_fixture)
            check('separate pinned file copy',open_fixture.resolve()!=fixture.resolve())
        else:
            layer=Sdf.Layer.CreateAnonymous('attach-fixture.usda')
            check('pinned fixture copied',layer.ImportFromString(fixture.read_text(encoding='utf-8')))
            stage=Usd.Stage.Open(layer)
            cache_id=UsdUtils.StageCache.Get().Insert(stage)
        result['fixture_sha256']=hashlib.sha256(fixture.read_bytes()).hexdigest()
        def event(event):
            number=int(event.type)
            result['owned_stage_events'].append(number)
            if number==int(omni.usd.StageEventType.DIRTY_STATE_CHANGED):
                result.setdefault('owned_dirty_events',[]).append({'updates_completed':result['updates_completed'],
                    'state':context_receipt(ctx,ctx,stage,fixture)})
            write()
        subscription=ctx.get_stage_event_stream().create_subscription_to_pop(event,name='owned attach-only receipt')
        sample('fixture-ready')
        if mode=='attach':task=asyncio.ensure_future(ctx.attach_stage_async(stage))
        elif mode=='open':task=asyncio.ensure_future(ctx.open_stage_async(str(open_fixture)))
        for update in range(UPDATE_BUDGET):
            await app.next_update_async()
            result['updates_completed']=update+1
            if task is not None and task.done() and mode+'_completed_update' not in result:
                result[mode+'_completed_update']=update+1
                if mode=='open':stage=ctx.get_stage()
            sample('update-'+str(update+1))
        if task is not None:
            check('operation finished within budget',task.done())
            ok,error=task.result();result['operation_error']=error
            check('operation succeeded',ok)
            check('owned context holds independent stage',ctx.get_stage()==stage and stage!=original)
            if mode=='open':
                check('opened only owned file',Path(stage.GetRootLayer().realPath).resolve()==open_fixture.resolve())
        else:
            check('wait leaves context empty',ctx.get_stage() is None)
        check('no extra viewport',len(list(ViewportWidget.get_instances()))==views)
        final=context_receipt(host,host,original,fixture)
        check('default USD and edit target preserved',all(final[key]==initial[key] for key in
              ('same_context','same_stage','root_text_sha256','session_text_sha256','edit_target','root_dirty')))
        result['default_pending_preserved']=final['pending_at_entry']==initial['pending_at_entry']
        result['status']='passed'
    except Exception as exc:
        result.update(status='failed',reason=type(exc).__name__+': '+str(exc))
    finally:
        if task is not None and not task.done():
            task.cancel();await asyncio.gather(task,return_exceptions=True)
        if ctx is not None and ctx.get_stage() is not None:
            result['owned_stage_closed']=bool(ctx.close_stage())
        if ctx is not None:omni.usd.release_all_hydra_engines(ctx)
        subscription=None
        if cache_id is not None:UsdUtils.StageCache.Get().Erase(cache_id)
        task=stage=layer=None
        if ctx is not None:
            ctx=None;result['context_destroyed']=bool(omni.usd.destroy_context(name))
            timeline=None;result['timeline_destroyed']=bool(omni.timeline.destroy_timeline(name))
        result['owned_resources_remaining']=not (result.get('context_destroyed') and result.get('timeline_destroyed'))
        if mode=='open' and 'owned_fixture_sha256' in result:
            result['owned_fixture_preserved']=hashlib.sha256(open_fixture.read_bytes()).hexdigest()==result['owned_fixture_sha256']
            if not result['owned_fixture_preserved']:result.update(status='failed',reason='Owned open fixture changed')
        sample('after-cleanup');write()
    if result['status']!='passed' or result['owned_resources_remaining']:
        raise RuntimeError('Attach-only control failed: '+result.get('reason','cleanup'))
    return result
