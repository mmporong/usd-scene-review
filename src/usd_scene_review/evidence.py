"""Concise review evidence; observed changes, policy and human metadata stay separate."""
from .measurements import measurements,vector,number


def evidence_rows(report,change,review=None):
    if not change:return [('Selection','Select a changed prim'),('Policy','Not evaluated'),('Human review','Unreviewed')]
    data=measurements(report,change);world=data['spaces']['world'];local=data['spaces']['local']
    changed=list(change.get('fields',{}))
    if change.get('authored'):changed.append('authored opinions')
    rows=[('Selected prim',change['path']),('Changed properties',', '.join(changed) or change.get('kind','change')),
          ('Motion',data['motion']),('Before A world [m]',vector(world['meters']['before'])),
          ('After B world [m]',vector(world['meters']['after'])),('World delta [m]',vector(world['delta_meters'])),
          ('Local delta [stage units]',vector(local['delta']))]
    angle=world['rotation_degrees']
    rows.append(('Rigid rotation delta',number(angle)+' deg' if angle is not None else 'UNKNOWN (non-rigid or unavailable)'))
    for label,space in [('Local',local),('World',world)]:
        angle=space['effective_rotation_degrees']
        rows.append((label+' effective orientation delta',
                     number(angle)+' deg; scale-normalized, not authored rotation' if angle is not None
                     else 'UNKNOWN: '+str(space['effective_orientation_reason'])))
        rows.append((label+' unsigned axis magnitudes',
                     'A '+vector(space['axis_magnitudes']['before'])+' / B '+vector(space['axis_magnitudes']['after'])))
    policies=[p for p in report.get('policy',[]) if p.get('path')==change['path']]
    rows.append(('Independent policy',', '.join(p.get('status','unknown').upper() for p in policies) if policies else 'NOT EVALUATED (no thresholds configured)'))
    rows.append(('Clash',report.get('clash',{}).get('status','unknown').upper()+'; no collision verdict'))
    human=review or {};status=human.get('disposition','unreviewed')
    rows.append(('Human review',status.upper()+(': '+human['reason'] if human.get('reason') else '')+' (local, unverified; no policy waiver)'))
    context=[c for c in report.get('changes',[]) if c['path']!=change['path'] and
             any(k in c.get('fields',{}) for k in ('visibility','active','attributes'))]
    if context:
        rows.append(('Source appearance also changed', '; '.join(c['path'].rsplit('/',1)[-1]+': '+','.join(c['fields']) for c in context[:4])+'; A/B appearance may differ'))
    return rows
