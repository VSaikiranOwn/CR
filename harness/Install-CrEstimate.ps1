<#
.SYNOPSIS
    Install the cr-estimate skill and its validator into the DCP AI harness.

.DESCRIPTION
    Copies .github/skills/cr-estimate and .github/validators/cr_complete.py into
    the harness workspace, checking the target looks like the harness first.
    One command, no shell variables to lose on paste.

.PARAMETER HarnessRoot
    Folder containing the harness .github directory,
    e.g. C:\Microservices\Workspace\aiv2

.PARAMETER Batch
    Optional batch id. When given, a --dry-run estimate is run afterwards as a
    smoke test, e.g. -Batch 41000

.EXAMPLE
    .\harness\Install-CrEstimate.ps1 -HarnessRoot "C:\Microservices\Workspace\aiv2"

.EXAMPLE
    .\harness\Install-CrEstimate.ps1 -HarnessRoot "C:\Microservices\Workspace\aiv2" -Batch 41000
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $HarnessRoot,

    [string] $Batch
)

$ErrorActionPreference = 'Stop'

function Write-Step { param([string] $Text) Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Ok   { param([string] $Text) Write-Host "    OK  $Text" -ForegroundColor Green }
function Write-Warn { param([string] $Text) Write-Host "    !   $Text" -ForegroundColor Yellow }

$bundle = Join-Path $PSScriptRoot 'bundle'
$skillSource = Join-Path $bundle 'skills\cr-estimate'
$validatorSource = Join-Path $bundle 'validators\cr_complete.py'

Write-Step "Checking the bundle"
if (-not (Test-Path $skillSource)) {
    throw ("Bundle not found at '$bundle'. You are probably on the wrong branch — " +
           "run:  git checkout claude/cr-generation-utility-s8sfrz")
}
Write-Ok "found $skillSource"

Write-Step "Checking the harness"
$dotGithub = Join-Path $HarnessRoot '.github'
foreach ($required in @('skills', 'validators', 'workspace')) {
    if (-not (Test-Path (Join-Path $dotGithub $required))) {
        throw ("'$dotGithub\$required' not found — is '$HarnessRoot' really the folder " +
               "that contains the harness .github directory?")
    }
}
Write-Ok "found $dotGithub"

Write-Step "Installing"
$skillTarget = Join-Path $dotGithub 'skills\cr-estimate'
if (Test-Path $skillTarget) {
    Write-Warn "replacing the existing $skillTarget"
    Remove-Item -Recurse -Force $skillTarget
}
Copy-Item -Recurse -Force $skillSource (Join-Path $dotGithub 'skills')
Copy-Item -Force $validatorSource (Join-Path $dotGithub 'validators')
Write-Ok "skills\cr-estimate"
Write-Ok "validators\cr_complete.py"

Write-Step "Checking python and openpyxl"
$python = $null
foreach ($candidate in @('python', 'py', 'python3')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    # The Microsoft Store alias is a 0-byte stub that opens the Store, not python.
    if ($command -and $command.Source -notlike '*WindowsApps*') { $python = $candidate; break }
}
if (-not $python) {
    Write-Warn "no python found on PATH. Install Python 3.10+ and re-run, or run the skill manually."
} else {
    Write-Ok "using '$python'"
    & $python -c "import openpyxl" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "openpyxl missing — installing"
        & $python -m pip install --quiet openpyxl
    }
    Write-Ok "openpyxl available"
}

Write-Host ""
Write-Host "Installed. Next:" -ForegroundColor Cyan
Write-Host "  1. Make the three edits in harness/INSTALL.md section 3"
Write-Host "     (design.agent.md, docs/design.md, copilot-instructions.md)"
Write-Host "  2. Run an estimate:"
Write-Host "     cd `"$HarnessRoot`""
Write-Host "     $(if ($python) { $python } else { 'python' }) .github\skills\cr-estimate\scripts\cr_estimate.py .github\workspace\<batch-id>"
Write-Host ""

if ($Batch -and $python) {
    Write-Step "Smoke test on batch $Batch"
    Push-Location $HarnessRoot
    try {
        & $python '.github\skills\cr-estimate\scripts\cr_estimate.py' ".github\workspace\$Batch" '--dry-run'
    } finally {
        Pop-Location
    }
}
