"""CPU-only policy and receipts for owned shutdown diagnostics; no Kit imports."""
import csv
import ctypes
import hashlib
import io
import json
import ntpath
import os
from pathlib import Path
import re
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PROFILES=('no-navigation','matched-full')
REQUIRED_CHECKS={'supported route','owned portable config','review extension never enabled',
    'only fresh anonymous startup replaced','owned fixture opened','only owned fixture active',
    'fixture root is not dirty','public close leaves no stage','navigation core matches profile',
    'navigation recast matches profile','navigation schema retained','native navigation module matches profile',
    'no startup dependency failures','startup inventory matches pinned profile'}


def load_profile(variant):
    if variant not in PROFILES:
        raise ValueError('Unknown shutdown diagnostic profile')
    value=json.loads((ROOT/'diagnostics/isaac45-shutdown-v1.json').read_text(encoding='utf-8'))
    value['variant']=variant
    value['owner']='USDSceneReview-shutdown-'+variant+'-v1'
    value['exclusions']=value['navigation_extensions'] if variant=='no-navigation' else []
    data=(ROOT/'diagnostics/shutdown-clean.usda').read_bytes()
    if hashlib.sha256(data).hexdigest()!=value['fixture_sha256']:
        raise ValueError('Pinned shutdown fixture changed')
    return value,data


def startup_extensions(log):
    return sorted(set(re.findall(r'\[ext: ([A-Za-z0-9_.]+-[^\]]+)\] startup',log)))


def log_summary(log):
    errors={}
    for category in re.findall(r'\[Error\] \[([^\]]+)\]',log):
        errors[category]=errors.get(category,0)+1
    return {'error_lines':sum('[Error]' in line for line in log.splitlines()),
            'warning_lines':sum('[Warning]' in line for line in log.splitlines()),
            'error_categories':errors,
            'traceback_observed':'Traceback (most recent call last)' in log,
            'graphics_objects_leaked':'Leaking graphics objects' in log,
            'fabric_history_outstanding':bool(re.search(r'had [1-9][0-9]* outstanding SimStageWithHistory',log))}


def reuse_check_names():
    names=set()
    for cycle in range(2):
        names.add('owned viewport created '+str(cycle))
        for step in range(3):
            suffix=str(cycle)+'/'+str(step)
            for prefix in ('attach ','one extra viewport only ','independent stage namespace ','source roots and cameras preserved '):
                names.add(prefix+suffix)
        for prefix in ('common camera pose/projection ','actual A/B/A rendered content ',
                       'owned viewport actually removed ','owned stage closed ','owned context destroyed ',
                       'owned timeline destroyed ','working stage selection and time preserved '):
            names.add(prefix+str(cycle))
    return names


def assess(report, process, log, profile=None):
    """Do not turn exit0 or the historical warning counts into an allowed budget."""
    summary=log_summary(log)
    checks=report.get('checks',[])
    native_ok=(process.get('process_exit')==0 and not process.get('native_errors')
               and not process.get('timed_out') and not process.get('termination'))
    conditions=bool(report.get('status')=='passed' and checks and all(c.get('passed') is True for c in checks)
                    and process.get('owned_process_reaped') is True
                    and process.get('owned_job_empty') is True
                    and process.get('owned_job_closed') is True
                    and process.get('fixture_bytes_preserved',True) is True
                    and not process.get('descendant_containment_required'))
    reasons=[]
    if profile:
        nav=report.get('navigation_control',{})
        expected=profile['variant']=='matched-full'
        expected_ids=list(profile['observation']['startup_extensions'])
        if expected:
            expected_ids+=profile['navigation_extension_ids']
        bounds=profile.get('candidate') in ('viewport-bounds','viewport-bounds-scale','viewport-bounds-stability')
        required_checks=set(REQUIRED_CHECKS)
        if bounds:
            expected_ids+=['mmporong.scene.review-0.1.0']
            required_checks.remove('review extension never enabled')
            required_checks.update(('review initially disabled','review disabled after candidate'))
            if profile.get('candidate') in ('viewport-bounds-scale','viewport-bounds-stability'):required_checks.add('QA restored pinned fixture epoch')
        events=report.get('stage_events',[])
        required={
            'required_checks':required_checks.issubset({c.get('name') for c in checks if c.get('passed') is True}),
            'fixture':process.get('fixture_bytes_preserved') is True and report.get('fixture_sha256')==profile['fixture_sha256'],
            'public_close':report.get('file_close_callback') is True,
            'stage_event_order':'CLOSING' in events and 'CLOSED' in events and events.index('CLOSING')<events.index('CLOSED'),
            'navigation_state':nav.get('core_enabled') is expected and nav.get('recast_enabled') is expected and nav.get('core_dll_loaded') is expected and nav.get('schema_enabled') is True,
            'startup_inventory':startup_extensions(log)==sorted(set(expected_ids)),
            'review_disabled':any(c.get('name')==('review disabled after candidate' if bounds else 'review extension never enabled') and c.get('passed') is True for c in checks),
            'lease':process.get('shared_admission',{}).get('admitted') is True,
        }
        if profile.get('candidate'):
            candidate=report.get('candidate',{})
            candidate_checks=candidate.get('checks',[])
            if bounds:
                if profile.get('candidate') in ('viewport-bounds-scale','viewport-bounds-stability'):
                    from viewport_bounds_scale_qa import check_names
                else:
                    from viewport_bounds_candidate import check_names
                names=check_names((2048,),33) if profile.get('candidate')=='viewport-bounds-stability' else check_names()
            else:names=reuse_check_names()
            required['candidate']=(profile['variant']=='no-navigation' and candidate.get('status')=='passed'
                and len(candidate_checks)==len(names) and {c.get('name') for c in candidate_checks if c.get('passed') is True}==names
                and candidate.get('owned_resources_remaining') is False and candidate.get('working_stage_preserved') is True
                and report.get('candidate_settings_preserved') is True)
            if bounds:required['candidate']=(required['candidate'] and candidate.get('pending_before') is False and candidate.get('pending_after') is False
                and candidate.get('activation_mode')=='persistent-manager-exclusions-v1'
                and candidate.get('exclusion_preflight',{}).get('navigation_absent') is True)
            if profile.get('candidate') in ('viewport-bounds-scale','viewport-bounds-stability'):
                from viewport_bounds_scale_qa import metrics_complete,stability_metrics_complete
                complete=stability_metrics_complete(candidate.get('scales',[])) if profile.get('candidate')=='viewport-bounds-stability' else metrics_complete(candidate.get('scales',[]))
                required['scale_qa']=(candidate.get('fixture_epoch_restored') is True and complete)
        if profile.get('attach_control'):
            control=report.get('attach_control',{})
            required['attach_control']=(profile['variant']=='no-navigation' and not profile.get('candidate')
                and control.get('mode')==profile['attach_control'] and control.get('status')=='passed'
                and control.get('update_budget')==60 and control.get('updates_completed')==60
                and control.get('default_pending_preserved') is True
                and control.get('owned_resources_remaining') is False
                and bool(control.get('checks')) and all(check.get('passed') is True for check in control['checks'])
                and (control.get('mode')=='wait' or control.get('owned_stage_closed') is True)
                and (control.get('mode')!='open' or control.get('owned_fixture_preserved') is True))
        reasons=[name for name,ok in required.items() if not ok]
        conditions=conditions and not reasons
    clean=native_ok and conditions and not any(summary.get(k) for k in
          ('error_lines','warning_lines','traceback_observed','graphics_objects_leaked','fabric_history_outstanding'))
    return {'native_exit_ok':native_ok,'profile_conditions_met':conditions,
            'strict_clean_shutdown':clean,'passed':clean,'qualification_failures':reasons,
            'log_summary':summary,
            'status':'clean' if clean else ('exited_with_diagnostics' if native_ok and conditions else 'failed_or_incomplete')}


def validate_sdk(sdk, profile):
    if (sdk/'VERSION').read_text().strip()!=profile['sdk_version_file']:
        raise ValueError('SDK build differs from the recorded profile; do not silently upgrade')
    if not (sdk/'apps/isaacsim.exp.full.kit').is_file() or not (sdk/'kit/kit.exe').is_file():
        raise ValueError('Expected installed Windows Full Isaac 4.5')
    for relative,digest in profile['sdk_files_sha256'].items():
        if hashlib.sha256((sdk/relative).read_bytes()).hexdigest()!=digest:
            raise ValueError('SDK file differs from pinned profile: '+relative)
    try:
        import tomllib
    except ImportError:
        import toml as tomllib
    for name,version in profile['sdk_extension_versions'].items():
        candidates=list((sdk/'extscache').glob(name+'-*/config/extension.toml'))
        if len(candidates)!=1 or tomllib.loads(candidates[0].read_text(encoding='utf-8'))['package']['version']!=version:
            raise ValueError('SDK extension differs from profile: '+name)


def exclusive_lock_observed(path):
    """OPEN_EXISTING read-only probe, never create/acquire/overwrite a lease."""
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
    kernel.CreateFileW.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.CreateFileW(str(path),0x80000000,7,None,3,0,None)
    if handle==ctypes.c_void_p(-1).value:
        if ctypes.get_last_error()==32:
            return True
        raise OSError('Cannot verify canonical shared lock')
    kernel.CloseHandle(handle)
    return False


def validate_admission(metadata, processes, own_pid, exclusive, gpu, blockers, owner=None):
    """Pure policy, used by real admission and hostile-input CPU regression."""
    by_id={int(p['ProcessId']):p for p in processes}
    ancestors=set()
    current=own_pid
    while current and current not in ancestors:
        ancestors.add(current)
        current=int(by_id.get(current,{}).get('ParentProcessId',0))
    actual_owner=metadata.get('owner','')
    if (metadata.get('state')!='running' or not metadata.get('leaseId') or
        not actual_owner.startswith('USDSceneReview-') or (owner and owner!=actual_owner) or
        metadata.get('wrapperPid') not in ancestors or metadata.get('childPid') not in ancestors or
        metadata.get('wrapperPid')==metadata.get('childPid') or not exclusive):
        raise ValueError('Active canonical official shared lease/owned lineage not verified')
    if any(str(p.get('Name','')).lower()=='kit.exe' for p in processes) or blockers:
        raise ValueError('Another Kit or unmanaged GPU workload exists')
    if len(gpu)!=1 or int(gpu[0][0])>15 or int(gpu[0][1])>3500:
        raise ValueError('GPU resource conditions differ from the idle profile')
    return {'admitted':True,'lease_id':metadata['leaseId'],'owner':actual_owner,
            'wrapper_pid':metadata['wrapperPid'],'child_pid':metadata['childPid'],
            'exclusive_handle_observed':True,'gpu_utilization':int(gpu[0][0]),
            'gpu_memory_mib':int(gpu[0][1]),'gpu_total_mib':int(gpu[0][2]),
            'gpu_name':gpu[0][3].strip() if len(gpu[0])>3 else None,
            'driver':gpu[0][4].strip() if len(gpu[0])>4 else None}


def unmanaged_clients(clients, processes, own_pid):
    # Desktop draw clients are present in Windows nvidia-smi output. Unknown or
    # permission-hidden clients must be resolved by PID or fail closed.
    desktop={'system','dwm.exe','shellhost.exe','explorer.exe','crossdeviceresume.exe',
        'startmenuexperiencehost.exe','searchhost.exe','nvidia overlay.exe',
        'msedgewebview2.exe','textinputhost.exe','powertoys.quickaccess.exe',
        'microsoft.cmdpal.ui.exe','powertoys.exe','powertoys.colorpickerui.exe',
        'powertoys.peek.ui.exe','asus_framework.exe','windowsterminal.exe',
        'video.ui.exe','discord.exe','shellexperiencehost.exe','chrome.exe',
        'powertoys.fancyzones.exe','chatgpt.exe','codex-computer-use-swift.exe',
        'claude.exe','slack.exe','msedge.exe','yourphone.exe',
        'phoneexperiencehost.exe','tabtip.exe','remoting_desktop.exe'}
    by_id={int(p['ProcessId']):p for p in processes}
    blockers=[]
    for row in clients:
        if len(row)!=2 or not row[0].strip().isdigit():
            raise ValueError('Malformed GPU client receipt')
        pid=int(row[0])
        name=ntpath.basename(row[1].strip()).lower()
        if name.startswith('['):name=str(by_id.get(pid,{}).get('Name','')).lower()
        if pid!=own_pid and name not in desktop:
            blockers.append({'pid':pid,'name':name or 'unresolved'})
    return blockers


def shared_admission(owner=None):
    if os.name!='nt':
        raise ValueError('Owned Kit diagnostics require Windows shared lease')
    root=Path.home()/'CodexSignals'
    if not (root/'Use-GpuLease.ps1').is_file():
        raise ValueError('Existing canonical shared wrapper is required; do not install or bypass it')
    metadata=json.loads((root/'gpu-lease.json').read_text(encoding='utf-8-sig'))
    query='Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress'
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',query],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=10,check=True)
    processes=json.loads(result.stdout)
    if isinstance(processes,dict):processes=[processes]
    def smi(fields):
        result=subprocess.run(['nvidia-smi',fields,'--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,check=True)
        return list(csv.reader(io.StringIO(result.stdout)))
    gpu=smi('--query-gpu=utilization.gpu,memory.used,memory.total,name,driver_version')
    clients=smi('--query-compute-apps=pid,process_name')
    blockers=unmanaged_clients(clients,processes,os.getpid())
    return validate_admission(metadata,processes,os.getpid(),exclusive_lock_observed(root/'gpu-lease.lock'),gpu,blockers,owner)


def job_count(job):
    from ctypes import wintypes
    class Accounting(ctypes.Structure):
        _fields_=[(n,ctypes.c_longlong) for n in ('user','kernel','period_user','period_kernel')]+[(n,wintypes.DWORD) for n in ('faults','total','active','terminated')]
    query=job.api.QueryInformationJobObject
    query.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p]
    query.restype=wintypes.BOOL
    value=Accounting()
    if not query(job.handle,1,ctypes.byref(value),ctypes.sizeof(value),None):
        raise OSError('Owned Job emptiness could not be verified')
    return value.active


def finish_job(job):
    forced=job_count(job)>0
    if forced:job.terminate()
    deadline=time.monotonic()+5
    while job_count(job) and time.monotonic()<deadline:time.sleep(.01)
    empty=job_count(job)==0
    job.close()
    return {'owned_job_empty':empty,'owned_job_closed':True,'descendant_containment_required':forced}
