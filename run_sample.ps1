# LogMiner-QA: Verify installation and run sample pipeline
# Run from project root: .\run_sample.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== LogMiner-QA: Installation check and sample run ===" -ForegroundColor Cyan
Write-Host ""

# 1. Activate venv and run installation test
Write-Host "1. Running installation test..." -ForegroundColor Yellow
& "$ProjectRoot\.venv\Scripts\python.exe" "$ProjectRoot\test_installation.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installation test failed. Fix the issues above, then run this script again." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host ""

# 2. Ensure package is installed (editable mode)
Write-Host "2. Ensuring package is installed..." -ForegroundColor Yellow
$checkInstalled = & "$ProjectRoot\.venv\Scripts\python.exe" -c "import logminer_qa; print('installed')" 2>&1
if ($LASTEXITCODE -ne 0 -or $checkInstalled -notmatch "installed") {
    Write-Host "   Installing package in editable mode..." -ForegroundColor Yellow
    & "$ProjectRoot\.venv\Scripts\python.exe" -m pip install -e "$ProjectRoot" --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Installation failed. Falling back to PYTHONPATH method..." -ForegroundColor Yellow
        $env:PYTHONPATH = "$ProjectRoot\src"
    }
} else {
    Write-Host "   Package already installed." -ForegroundColor Green
}
Write-Host ""

# 3. Run sample pipeline
Write-Host "3. Running sample pipeline (data/sample_logs.jsonl -> sanitized.jsonl, report.json, generated_tests.feature)..." -ForegroundColor Yellow
& "$ProjectRoot\.venv\Scripts\python.exe" -m logminer_qa.cli `
  --input "$ProjectRoot\data\sample_logs.jsonl" `
  --output "$ProjectRoot\sanitized.jsonl" `
  --report "$ProjectRoot\report.json" `
  --tests "$ProjectRoot\generated_tests.feature"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pipeline failed. Check the error above." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done. Check sanitized.jsonl, report.json, and generated_tests.feature in the project root." -ForegroundColor Green
