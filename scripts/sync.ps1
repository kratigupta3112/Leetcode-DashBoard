$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

# Ensure local imports work even if package isn't installed
$env:PYTHONPATH = "src"

# Fetch + parse + export (compensation + interview experiences)
python -m salarytracker.cli --max-posts 500
python -m salarytracker.cli interview-sync --max-posts 400

