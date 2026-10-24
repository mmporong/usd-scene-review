[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$IsaacRoot,
    [Parameter(Mandatory=$true)][string]$Output,
    [ValidateSet('no-navigation','matched-full')][string]$DiagnosticProfile='no-navigation',
    [ValidateSet('none','viewport-reuse','viewport-bounds','viewport-bounds-scale','viewport-bounds-stability','viewport-faces')][string]$Candidate='none',
    [ValidateSet('none','wait','attach','open')][string]$AttachControl='none',
    [ValidateRange(1,1800)][int]$LeaseWaitSeconds=1,
    [string]$CandidateArchive,
    [switch]$OwnedChild
)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent
$sharedRoot=Join-Path ([Environment]::GetFolderPath('UserProfile')) 'CodexSignals'
$wrapper=Join-Path $sharedRoot 'Use-GpuLease.ps1'
$outputPath=[System.IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $outputPath){throw 'Output must be new; never overwrite evidence'}
if($Candidate -ne 'none' -and $DiagnosticProfile -ne 'no-navigation'){throw 'Candidate only allowed on pinned reduced profile'}
if($AttachControl -ne 'none' -and ($DiagnosticProfile -ne 'no-navigation' -or $Candidate -ne 'none')){throw 'Attach control only allowed on reduced profile without candidate'}
if(-not (Test-Path -LiteralPath $wrapper)){throw 'Existing canonical shared wrapper required; no install or bypass'}
$owner='USDSceneReview-shutdown-'+$DiagnosticProfile+'-v1'
if(-not $OwnedChild){
    $childShell=(Get-Process -Id $PID).Path
    $childArguments=@('-NoProfile','-NonInteractive','-File',$PSCommandPath,'-IsaacRoot',$IsaacRoot,'-Output',$outputPath,'-DiagnosticProfile',$DiagnosticProfile,'-Candidate',$Candidate,'-AttachControl',$AttachControl,'-OwnedChild')
    if($CandidateArchive){$childArguments+=@('-CandidateArchive',$CandidateArchive)}
    & $wrapper -Owner $owner -FilePath $childShell -ArgumentList $childArguments -WaitTimeoutSeconds $LeaseWaitSeconds -PollIntervalMilliseconds 1000 -GpuProbeTimeoutSeconds 1
    $wrapperExit=$LASTEXITCODE
    if(Test-Path -LiteralPath $outputPath){
        $lease=Get-Content -LiteralPath (Join-Path $sharedRoot 'gpu-lease.json') -Raw | ConvertFrom-Json
        $native=Get-Content -LiteralPath (Join-Path $outputPath 'process-result.json') -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
        $readableAfterReturn=$null
        $readHandle=$null
        try {
            $readHandle=[System.IO.File]::Open((Join-Path $sharedRoot 'gpu-lease.lock'),[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,([System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete))
            $readableAfterReturn=$true
        } catch [System.IO.IOException] {
            if(($_.Exception.HResult -band 65535) -eq 32){$readableAfterReturn=$false}
        } finally {if($null -ne $readHandle){$readHandle.Dispose()}}
        [ordered]@{wrapper_exit=$wrapperExit;owner=$lease.owner;lease_id=$lease.leaseId;matches_inner_lease=($lease.leaseId -eq $native.shared_admission.lease_id);state=$lease.state;completed_utc=$lease.completedUtc;lock_readable_after_return=$readableAfterReturn;native_pid=$native.owned_pid;owned_job_empty=$native.owned_job_empty;owned_job_closed=$native.owned_job_closed;note='Exit2 retains diagnostic errors/warnings; a new owner may acquire after our wrapper returns'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputPath 'shared-wrapper-result.json') -Encoding UTF8
    }
    exit $wrapperExit
}
$lease=Get-Content -LiteralPath (Join-Path $sharedRoot 'gpu-lease.json') -Raw | ConvertFrom-Json
if($lease.owner -ne $owner -or $lease.state -ne 'running' -or [int]$lease.childPid -ne $PID){throw 'Not the official shared wrapper owned child'}
$sdk=[System.IO.Path]::GetFullPath($IsaacRoot)
$bundles=@(Get-ChildItem (Join-Path $sdk 'extscache') -Directory -Filter 'omni.kit.pip_archive-*.wx64.cp310')
if($bundles.Count -ne 1){throw 'Expected one installed Python3.10 pip bundle; no runtime installation'}
$env:PYTHONPATH=Join-Path $bundles[0].FullName 'pip_prebundle'
$env:PYTHONUTF8='1'
$python=Join-Path $sdk 'kit/python/python.exe'
$candidateArgs=@()
if($Candidate -ne 'none'){$candidateArgs=@('--shutdown-candidate',$Candidate)}
if($AttachControl -ne 'none'){$candidateArgs=@('--attach-control',$AttachControl)}
if($CandidateArchive){$candidateArgs+=@('--candidate-archive',$CandidateArchive)}
$hostLimit=240
if($Candidate -in @('viewport-bounds-scale','viewport-bounds-stability')){$hostLimit=600}
& $python -B (Join-Path $PSScriptRoot 'with_openusd.py') --isaac-root $sdk --python $python --timeout ($hostLimit+60) -- (Join-Path $PSScriptRoot 'run_in_app_validation.py') --isaac-root $sdk --output $outputPath --full-app --baseline --shutdown-control file-close --shutdown-profile $DiagnosticProfile --fail-fast-native --timeout $hostLimit @candidateArgs
exit $LASTEXITCODE
