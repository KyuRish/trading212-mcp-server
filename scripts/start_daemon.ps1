# Trading 212 Gold Tracker - Start Hidden Daemon
# Run this once to start the analyzer in the background
# Make sure 'uv' is in your PATH

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$workDir = Split-Path -Parent $scriptDir
$scriptPath = Join-Path $scriptDir "daily_analyzer.py"

# Start the process hidden
Start-Process -FilePath "uv" `
    -ArgumentList "run", "python", $scriptPath, "--daemon", "--time", "09:30" `
    -WorkingDirectory $workDir `
    -WindowStyle Hidden

Write-Host "Gold Tracker daemon started in background!"
Write-Host "It will run analysis daily at 09:30 and send notifications."
Write-Host ""
Write-Host "To stop it, use Task Manager to end the 'python' process."
