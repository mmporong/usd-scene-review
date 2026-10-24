[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Sdk,
    [ValidateSet('doctor','verify','extension-path','snapshot','sample','compare','launch')][string]$Action='doctor',
    [string]$Workspace,
    [string]$Data,
    [string]$Before,
    [string]$After,
    [string]$Source,
    [switch]$Smoke
)
$sdkPython = Join-Path $Sdk 'kit/python/python.exe'
if (-not (Test-Path -LiteralPath $sdkPython -PathType Leaf)) { throw 'SDK_REQUIRED: select an existing Isaac Sim 4.5 SDK.' }
$reviewArguments = @('--sdk',$Sdk,$Action)
if ($Workspace) { $reviewArguments += @('--workspace',$Workspace) }
if ($Data) { $reviewArguments += @('--data',$Data) }
if ($Before) { $reviewArguments += @('--before',$Before) }
if ($After) { $reviewArguments += @('--after',$After) }
if ($Source) { $reviewArguments += @('--source',$Source) }
if ($Smoke) { $reviewArguments += @('--smoke','--timeout','300') }
& $sdkPython -B (Join-Path $PSScriptRoot 'review_kit.py') @reviewArguments
exit $LASTEXITCODE
