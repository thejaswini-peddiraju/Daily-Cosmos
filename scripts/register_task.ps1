<#
Registers a Windows Task Scheduler task that runs Daily Cosmos every day.
Usage (from the project folder):   .\scripts\register_task.ps1
Custom time:                       .\scripts\register_task.ps1 -Time "08:30"
Remove the task later:             Unregister-ScheduledTask -TaskName DailyCosmos -Confirm:$false
#>
param(
    [string]$Time = "11:00",
    [string]$TaskName = "DailyCosmos"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonW = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"
$User = "$env:USERDOMAIN\$env:USERNAME"

if (-not (Test-Path $PythonW)) {
    throw "Could not find $PythonW. Create the virtual environment first."
}

# What to run: the venv's Python, as a module, from the project folder.
$action = New-ScheduledTaskAction -Execute $PythonW -Argument "-m daily_cosmos" -WorkingDirectory $ProjectRoot

# When to run: every day at $Time, and shortly after you log in.
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At $Time
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $User
$logonTrigger.Delay = "PT1M"

# Who: you, only while logged in (needed to change your wallpaper), no admin rights.
$principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($dailyTrigger, $logonTrigger) `
    -Principal $principal `
    -Settings $settings `
    -Description "Downloads NASA's Astronomy Picture of the Day and sets it as the wallpaper." `
    -Force | Out-Null

Write-Host "Task '$TaskName' registered."
Write-Host "Runs daily at $Time and at logon."
Write-Host ("Next run: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime)