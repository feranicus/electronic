<#
  Registers Windows Scheduled Tasks so Send-Meddpicc.ps1 runs automatically
  every Monday and Friday at 09:00. Run this ONCE (normal PowerShell is fine).
#>
$ErrorActionPreference = 'Stop'
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here 'Send-Meddpicc.ps1'
$psexe  = (Get-Command powershell.exe).Source

function New-MeddpiccTask([string]$name, [string]$day, [string]$mode) {
  $action  = New-ScheduledTaskAction -Execute $psexe `
             -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Mode $mode"
  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $day -At 9:00AM
  $set     = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun
  Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
    -Settings $set -Description "MEDDPICC STEP UP ($mode)" -Force | Out-Null
  Write-Host "Registered: $name  ($day 09:00)"
}

New-MeddpiccTask 'MEDDPICC STEP UP - Monday' 'Monday' 'monday'
New-MeddpiccTask 'MEDDPICC STEP UP - Friday' 'Friday' 'friday'

Write-Host ""
Write-Host "Scheduled: Monday & Friday 09:00. Your PC must be on (or able to wake) at that time."
Write-Host "To remove later: Unregister-ScheduledTask -TaskName 'MEDDPICC STEP UP - Monday','MEDDPICC STEP UP - Friday'"
