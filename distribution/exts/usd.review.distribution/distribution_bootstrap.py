"""First-run workflow in this process's empty minimal Kit app only."""
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import traceback
import carb.settings
import omni.ext
import omni.kit.app


class DistributionBootstrap(omni.ext.IExt):
    def on_startup(self, ext_id):
        self.client = None
        self.result = {'status':'starting', 'checks':[]}
        self.config = json.loads(Path(carb.settings.get_settings().get(
            '/exts/usd.review.distribution/config')).read_text(encoding='utf-8'))
        self.root = Path(self.config['state'])
        self.task = asyncio.ensure_future(self.run())

    def check(self, name, passed):
        self.result['checks'].append({'name':name, 'passed':bool(passed)})
        self.record()
        if not passed:
            raise RuntimeError(name)

    def record(self):
        (self.root/'session-result.json').write_text(json.dumps(self.result, indent=2), encoding='utf-8')

    async def run(self):
        app = omni.kit.app.get_app()
        try:
            for _ in range(20):
                await app.next_update_async()
            from mmporong.scene.review.extension import get_active_extension
            from usd_scene_review.measurements import measurements
            owner = get_active_extension()
            self.check('packaged comparison extension loaded', owner is not None)
            self.client = owner._viewer
            manifests = {s:Path(p) for s,p in self.config['manifests'].items()}
            files = [p for manifest in manifests.values() for p in manifest.parent.rglob('*') if p.is_file()]
            original = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
            for side,path in manifests.items():
                owner._paths[side].set_value(str(path))
            await owner._compare_async()
            self.check('real sample comparison complete', owner._report['status']=='changed')
            change = next(c for c in owner._report['changes'] if c['path']=='/World/Rack')
            owner._select(change)
            owner._focus.set_value(True)
            owner._ghost.set_value(True)
            owner._export_path.set_value(str(self.root/'reports'))
            await owner._save_results()
            exported = json.loads((self.root/'reports/review.json').read_text(encoding='utf-8'))
            self.check('JSON and HTML saved from current comparison', exported==owner._report
                       and (self.root/'reports/review.html').stat().st_size>100)
            values = measurements(owner._report, change)['spaces']['world']['delta_meters']
            self.check('actual sample delta is right-to-left negative Y', values==[0,-.2,0])
            if self.config['smoke']:
                await owner._view('A')
                reply = await self.client._request('capture')
                self.check('A rendered and settled', reply['status']=='captured' and reply['display']['capture']['stable'])
                camera = reply['display']['camera']
                shutil.copyfile(self.client.directory/'review.png', self.root/'smoke-A.png')
            await owner._view('B')
            if self.config['smoke']:
                reply = await self.client._request('capture')
                self.check('B rendered and settled', reply['status']=='captured' and reply['display']['capture']['stable'])
                self.check('matching A/B camera', reply['display']['camera']==camera)
                self.check('translucent green helper loaded', reply['display']['ghost']['status']=='shown'
                           and reply['display']['ghost']['opacity']==.22
                           and reply['display']['ghost']['face_color']==[.12,.95,.22]
                           and reply['display']['ghost']['opacity_threshold']==0)
                shutil.copyfile(self.client.directory/'review.png', self.root/'smoke-B.png')
                from pxr import Gf
                view = Gf.Matrix4d(*[v for row in camera['transform'] for v in row]).GetInverse()
                positions = {}
                for side in ('A','B'):
                    lo,hi = camera['bounds'][side]
                    point = view.Transform(Gf.Vec3d(*[(a+b)/2 for a,b in zip(lo,hi)]))
                    positions[side] = point[0]/-point[2]
                self.check('old A projects right of current B', positions['A']>positions['B'])
                self.result['projected_horizontal'] = positions
                await owner._close()
                self.check('review receipt and worker exit zero', self.client.state=='closed'
                           and self.client.last_exit==0 and self.client.process is None)
                self.check('all sample bundle bytes preserved', original=={
                    str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
                await owner._view('B')
                self.check('normal host quit starts with owned active viewer',
                           self.client.state=='running' and self.client.process is not None)
                self.result['status']='passed'
                self.record()
                app.post_quit(0)
            else:
                self.result['status']='interactive'
                self.record()
        except Exception:
            self.result.update(status='failed', error=traceback.format_exc())
            self.record()
            app.post_quit(1)

    def on_shutdown(self):
        if self.task and not self.task.done():
            self.task.cancel()
        if self.result['status'] not in ('passed', 'interactive', 'closed'):
            self.result['status']='failed'
        if self.client:
            clean = self.client.shutdown_sync()
            self.result['worker_exit'] = self.client.last_exit
            self.result['preserved'] = bool(clean and self.client.last_receipt
                                           and self.client.last_receipt.get('preserved'))
            if not clean:
                self.result['status']='failed'
            elif self.result['status']=='interactive':
                self.result['status']='closed'
        self.record()
