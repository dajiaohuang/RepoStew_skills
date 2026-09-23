param(
    [Parameter(Mandatory=$true)][string]$StateHome,
    [Parameter(Mandatory=$true)][string]$PythonPath,
    [Parameter(Mandatory=$true)][string]$RtkPath,
    [Parameter(Mandatory=$true)][string]$CodexPath,
    [Parameter(Mandatory=$true)][string]$GhPath
)
$ErrorActionPreference = 'Stop'
# Only this task process receives the verified executable directories.
$env:PATH = ((@($GhPath,$RtkPath,$CodexPath,$PythonPath) | ForEach-Object { Split-Path -Parent $_ } | Select-Object -Unique) -join ';') + ';' + $env:PATH
$dispatcher = Join-Path $PSScriptRoot 'event_dispatch.py'
& $RtkPath proxy $PythonPath $dispatcher --state-home $StateHome --execute --codex $CodexPath --rtk $RtkPath
exit $LASTEXITCODE
