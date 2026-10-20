"""Owned child UI, populated exclusively by comparator evidence and human metadata."""
import omni.ui as ui
from usd_scene_review.evidence import evidence_rows

class EvidencePanel:
    def __init__(self):
        self.window=ui.Window('Review evidence',width=470,height=860)
        self.window.position_x=1100;self.window.position_y=35
        self.window.frame.set_style({'Frame':{'background_color':0xFFF8F7F5},
            'ScrollingFrame':{'background_color':0xFFF8F7F5},
            'Label':{'color':0xFF302218,'font_size':18}})
        with self.window.frame:
            with ui.ScrollingFrame():self.rows=ui.VStack(spacing=3)
    def update(self,report,selected,side,review,display,lighting):
        change=next((c for c in report.get('changes',[]) if c['path']==selected),None)
        rows=evidence_rows(report,change,review)
        self.rows.clear()
        with self.rows:
            ui.Label('BEFORE A / CURRENT B',height=26,style={'font_size':22})
            ui.Label(('A: before saved scene' if side=='A' else 'B: current saved scene'),height=25,
                     style={'color':0xFFBC5D0C if side=='A' else 0xFF0754C0})
            ghost=display.get('ghost',{})
            ghost_text=('OLD A: translucent BLUE ('+str(ghost.get('count',0))+' shapes)'
                        if ghost.get('status')=='shown' else 'OLD A overlay: '+ghost.get('status','off'))
            ui.Label(ghost_text,height=26,style={'color':0xFFBC5D0C})
            ui.Label('CURRENT B: original materials / orange bounds',height=25,style={'color':0xFF0754C0})
            if ghost.get('status')=='unsupported':rows.insert(0,('Ghost unsupported',ghost.get('reason','unknown')))
            for name,value in rows:
                ui.Label(name,height=16,style={'font_size':14,'color':0xFF665545})
                lines=max(1,(len(value)+44)//45)
                ui.Label(value,height=min(57,19*lines),word_wrap=True,style={'font_size':16})
            ui.Label('Preview illumination',height=19,style={'font_size':15})
            ui.Label(lighting.get('label','unavailable')+'; fixed manual exposure',height=55,word_wrap=True)
    def destroy(self):
        self.rows.clear();self.rows=None
        self.window.destroy();self.window=None
