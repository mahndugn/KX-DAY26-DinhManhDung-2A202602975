$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$taskRepoRoot = $PSScriptRoot
$taskUvCommand = Get-Command uv -ErrorAction SilentlyContinue
$taskUvPath = if ($taskUvCommand) { $taskUvCommand.Source } else { Join-Path $env:LOCALAPPDATA 'day26-tools/uv.exe' }
if (!(Test-Path -LiteralPath $taskUvPath)) { throw 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/' }
$taskLogDir = Join-Path $taskRepoRoot '.lab-runtime'
New-Item -ItemType Directory -Path $taskLogDir -Force | Out-Null

foreach ($taskService in @(
    @{ Name='server'; Directory='04-lab/mcp-server'; Port=8085; Arguments=@('-u','weather.py') },
    @{ Name='client'; Directory='04-lab/mcp-client'; Port=8000; Arguments=@('-u','-m','google.adk.cli','web','--host','127.0.0.1','--port','8000') }
)) {
    $taskServiceDir = Join-Path $taskRepoRoot $taskService.Directory
    $taskPython = Join-Path $taskServiceDir '.venv/Scripts/python.exe'
    if (Get-NetTCPConnection -State Listen -LocalPort $taskService.Port -ErrorAction SilentlyContinue) {
        Write-Host "$($taskService.Name): port $($taskService.Port) is already listening; skipped."
        continue
    }
    Push-Location $taskServiceDir
    try {
        & $taskUvPath sync --python 3.12 --locked
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    } finally { Pop-Location }
    $taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskService.Arguments -WorkingDirectory $taskServiceDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogDir "$($taskService.Name).out.log") -RedirectStandardError (Join-Path $taskLogDir "$($taskService.Name).err.log") -PassThru
    $taskProcess.Id | Set-Content (Join-Path $taskLogDir "$($taskService.Name).pid")
    for ($taskWaitIndex = 0; $taskWaitIndex -lt 60; $taskWaitIndex++) {
        if (Get-NetTCPConnection -State Listen -LocalPort $taskService.Port -ErrorAction SilentlyContinue) { break }
        if ($taskProcess.HasExited) { throw "$($taskService.Name) exited; inspect .lab-runtime logs." }
        Start-Sleep -Milliseconds 300
    }
    if (!(Get-NetTCPConnection -State Listen -LocalPort $taskService.Port -ErrorAction SilentlyContinue)) {
        throw "$($taskService.Name) did not start; inspect .lab-runtime logs."
    }
    Write-Host "$($taskService.Name) started, PID $($taskProcess.Id)."
}
$taskApps = Invoke-RestMethod 'http://localhost:8000/list-apps'
if ($taskApps -notcontains 'weather_agent') { throw 'ADK Web did not list weather_agent.' }
Write-Host 'Open http://localhost:8000 and select weather_agent. Logs: .lab-runtime/'
