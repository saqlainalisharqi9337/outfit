# Runs after the 4-class bag trainer exits: held-out eval, then structure retrain.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$trainPid = 19664
if (Get-Process -Id $trainPid -ErrorAction SilentlyContinue) {
    Write-Host "Waiting for bag trainer PID $trainPid ..."
    Wait-Process -Id $trainPid
}
Write-Host "Running held-out bag eval..."
$env:PYTHONUNBUFFERED = "1"
$env:TF_CPP_MIN_LOG_LEVEL = "2"
.\.venv\Scripts\python.exe eval_bag_heldout.py --limit 96
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Starting letterbox / structure retrain..."
.\.venv\Scripts\python.exe train_bag_shoes.py
