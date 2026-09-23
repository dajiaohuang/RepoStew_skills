param(
    [Parameter(Mandatory=$true)][string]$StateHome,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$anchor = (Resolve-Path -LiteralPath $StateHome).Path
$config = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $anchor 'paths.json') | ConvertFrom-Json
if ($config.schema_version -ne 2 -or $config.paths.state_home -ne '.') { throw 'Invalid state anchor' }
$skillRoot = [IO.Path]::GetFullPath((Join-Path $anchor $config.paths.skill_home))
$repoRoot = [IO.Path]::GetFullPath((Join-Path $anchor $config.paths.repos_home))
if ($skillRoot.TrimEnd('\') -ne (Split-Path -Parent $PSScriptRoot).TrimEnd('\')) { throw 'Selected skill root differs from this installer' }
foreach ($binding in @(@('REPOSTEW_HOME',$anchor),@('REPOSTEW_SKILL_HOME',$skillRoot),@('REPOSTEW_REPOS_HOME',$repoRoot))) {
    if (!(Test-Path -LiteralPath $binding[1] -PathType Container)) { throw 'Selected root missing' }
    $configured = [Environment]::GetEnvironmentVariable($binding[0], 'Process')
    if ($configured -and [IO.Path]::GetFullPath($configured).TrimEnd('\') -ne $binding[1].TrimEnd('\')) { throw ('Conflicting ' + $binding[0]) }
}
$scriptPath = Join-Path $skillRoot 'scripts\event_dispatch.py'
if (!(Test-Path -LiteralPath $scriptPath) -or !(Test-Path -LiteralPath (Join-Path $anchor 'repostew.sqlite'))) { throw 'Missing dispatcher or live state' }
$python = (Get-Command python -ErrorAction Stop).Source
$rtk = (Get-Command rtk -ErrorAction SilentlyContinue).Source
if (!$rtk -and (Test-Path -LiteralPath 'C:\Users\dajiaohuang\.local\bin\rtk.exe')) { $rtk = 'C:\Users\dajiaohuang\.local\bin\rtk.exe' }
if (!$rtk) { throw 'Existing RTK executable required' }
$codex = (Get-Command codex -ErrorAction Stop).Source
$gh = (Get-Command gh -ErrorAction Stop).Source
$name = 'RepoStew-Events-Luna'
# Explicit executable arguments; no credentials, user profile edits or public endpoints.
$wrapper = Join-Path $skillRoot 'scripts\run_event_task.ps1'
$powershell = (Get-Command powershell -ErrorAction Stop).Source
$arguments = '-NoProfile -WindowStyle Hidden -File "{0}" -StateHome "{1}" -PythonPath "{2}" -RtkPath "{3}" -CodexPath "{4}" -GhPath "{5}"' -f $wrapper,$anchor,$python,$rtk,$codex,$gh
$preview = [ordered]@{ TaskName=$name; Execute=$powershell; Arguments=$arguments; WorkingDirectory=$repoRoot; IntervalMinutes=5; Model='gpt-6-luna'; Effort='xhigh'; Logon='Interactive'; Applied=[bool]$Apply }
$existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Description -ne 'RepoStew v2 lightweight event intake and Luna dispatch') { throw 'Existing task ownership mismatch' }
    if ($existing.Actions.Count -ne 1 -or $existing.Actions[0].WorkingDirectory -ne $repoRoot -or !$existing.Actions[0].Arguments.Contains($anchor)) { throw 'Existing task belongs to a different installation; do not overwrite' }
    $same = $existing.Actions[0].Execute -eq $powershell -and $existing.Actions[0].Arguments -eq $arguments -and $existing.Triggers.Count -eq 1 -and $existing.Triggers[0].Repetition.Interval -eq 'PT5M' -and $existing.Settings.MultipleInstances -eq 2 -and $existing.Settings.Enabled
    if ($same) {
        $preview['Action'] = 'reuse'
        $preview | ConvertTo-Json
        exit 0
    }
}
$preview['Action'] = 'register-or-update'
if ($Apply) {
    $action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments -WorkingDirectory $repoRoot
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5)
    $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
    $task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'RepoStew v2 lightweight event intake and Luna dispatch'
    Register-ScheduledTask -TaskName $name -InputObject $task -Force | Out-Null
}
$preview | ConvertTo-Json
