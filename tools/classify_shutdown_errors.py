"""Read-only signature audit; never changes SDK logs, qualification or runtime."""
import re
from collections import Counter

HEADER=re.compile(r'\[([\d,]+)ms\] \[Error\] \[([^\]]+)\] (.*)')
EXT=re.compile(r'\[([\d.]+)s\] \[ext: ([^\]]+)\] shutdown')


def signature(category,message):
    if category=='carb.scripting-python.plugin':
        for token,key in (('has no attribute \'GetPrimAtPath\'','python.none_get_prim'),
            ('has no attribute \'_menu_button1\'','python.missing_menu_button'),
            ("name 'ManipulatorFactory' is not defined",'python.missing_manipulator_factory')):
            if token in message:return key
    if category=='omni.ext.plugin' and 'shutdown_extensions' in message:
        for token,key in (('isaacsim.robot_setup.xrdf_editor','shutdown.xrdf_editor'),
            ('isaacsim.sensors.physx.ui','shutdown.physx_ui'),('omni.kit.manipulator.prim.core','shutdown.manipulator_core')):
            if token in message:return key
    if category=='omni.kit.menu.utils.app_menu':
        for token,key in (("has no attribute '_window'",'menu.missing_window'),
            ("has no attribute 'get_stage_state'",'menu.none_stage_state'),("has no attribute 'get_selection'",'menu.none_selection')):
            if token in message:return key
    return 'unclassified'


def classify(text):
    lines=text.splitlines();markers={};groups={}
    for line in lines:
        found=EXT.search(line)
        if found:
            ms=round(float(found[1])*1000)
            if not found[2].startswith('mmporong.scene.review-'):markers.setdefault('first_shutdown_ms',ms)
            if found[2].startswith('mmporong.scene.review-'):markers.setdefault('review_shutdown_ms',ms)
            if found[2].startswith('omni.usd-'):markers.setdefault('usd_shutdown_ms',ms)
            if found[2].startswith('semantics.schema.editor-'):markers.setdefault('semantics_shutdown_ms',ms)
    for index,line in enumerate(lines):
        found=HEADER.search(line)
        if not found:continue
        ms=int(found[1].replace(',',''));key=signature(found[2],found[3])
        row=groups.setdefault(key,{'count':0,'first_ms':ms,'last_ms':ms,'after_shutdown_begin':0,
            'after_usd_shutdown':0,'after_review_shutdown':0,'after_semantics_shutdown':0,'menu_items':Counter(),'frames':set(),'project_frame_observed':False})
        row['count']+=1;row['last_ms']=max(row['last_ms'],ms);row['first_ms']=min(row['first_ms'],ms)
        for marker,field in (('first_shutdown_ms','after_shutdown_begin'),('usd_shutdown_ms','after_usd_shutdown'),('review_shutdown_ms','after_review_shutdown'),('semantics_shutdown_ms','after_semantics_shutdown')):
            row[field]+=marker in markers and ms>=markers[marker]
        menu=re.search(r"name:'([^']+)'",found[3])
        if menu:row['menu_items'][menu[1]]+=1
        for nextline in lines[index+1:]:
            if HEADER.search(nextline) or re.match(r'^\d{4}-\d\d-\d\d .*\[.*ms\]|^\[[\d.]+s\]',nextline):break
            frame=re.search(r'File "([^"]+\.py)", line \d+, in (.*)',nextline) or re.match(r'\s+(.+\.py)\(\d+\):\s+(.*)',nextline)
            if frame:
                path=frame[1].replace('\\','/');lower=path.lower();sdk='/isaac-sim-4.5.0/'
                project='/usd_scene_review/' in lower or '/mmporong/scene/review/' in lower
                row['project_frame_observed']|=project
                if sdk in lower:display=path[lower.index(sdk)+len(sdk):]
                else:
                    display='<project-frame>' if project else '<non-sdk-frame>'
                row['frames'].add(display+' :: '+frame[2])
    for row in groups.values():
        row['frames']=sorted(row['frames']);row['menu_items']=dict(sorted(row['menu_items'].items()))
    return {'error_lines':sum(row['count'] for row in groups.values()),'markers':markers,'signatures':dict(sorted(groups.items())),
        'unclassified_errors':groups.get('unclassified',{}).get('count',0)}
