$ErrorActionPreference = "Stop"

$taskName = "LeetCodeDashboardAutoSync"
$scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "sync.ps1"

# Run every 6 hours (repeat) starting now
$start = (Get-Date).AddMinutes(1)

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Once -At $start
$trigger.RepetitionInterval = (New-TimeSpan -Hours 6)
$trigger.RepetitionDuration = ([TimeSpan]::MaxValue)

# Run only when user is logged on (simple + no admin prompts)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel LeastPrivilege
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings

Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Write-Output "Registered Task Scheduler job: $taskName"
Write-Output "Runs: every 6 hours"
Write-Output "Script: $scriptPath"

