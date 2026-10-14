$ErrorActionPreference = 'Stop'
foreach ($taskServiceName in @('client','server')) {
    $taskPidPath = Join-Path $PSScriptRoot ".lab-runtime/$taskServiceName.pid"
    if (!(Test-Path -LiteralPath $taskPidPath)) { continue }
    $taskProcessId = [int](Get-Content -LiteralPath $taskPidPath)
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $taskProcessId"
    $taskExpectedDir = Join-Path $PSScriptRoot "04-lab/mcp-$taskServiceName/.venv/Scripts/python.exe"
    if ($taskProcess -and $taskProcess.ExecutablePath -eq $taskExpectedDir.Replace('/', '\')) {
        # Windows venv launchers spawn the managed Python interpreter as a child.
        & taskkill /PID $taskProcessId /T /F | Out-Null
        Write-Host "Stopped $taskServiceName (PID $taskProcessId)."
    }
    Remove-Item -LiteralPath $taskPidPath
}
