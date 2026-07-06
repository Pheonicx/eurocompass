# ============================================================
# EuroCompass Project Packager
#
# Creates a clean ZIP for ChatGPT or code review.
# Excludes virtual environments, Git metadata, caches,
# and other unnecessary files.
# ============================================================

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."

$TempFolder = Join-Path $env:TEMP "EuroCompass_ChatGPT"
$ZipFile = Join-Path $ProjectRoot "EuroCompass_ChatGPT_Package.zip"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " EuroCompass Project Packager" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Clean previous temp folder
if (Test-Path $TempFolder) {
    Remove-Item $TempFolder -Recurse -Force
}

New-Item -ItemType Directory -Path $TempFolder | Out-Null

$ExcludeFolders = @(
    ".git",
    ".venv",
    "__pycache__",
    ".wrangler",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode"
)

Write-Host "Copying project..."

robocopy `
    $ProjectRoot `
    $TempFolder `
    /E `
    /XD $ExcludeFolders `
    /XF *.pyc *.pyo *.log *.tmp `
    /NFL /NDL /NJH /NJS /NC /NS | Out-Null

if (Test-Path $ZipFile) {
    Remove-Item $ZipFile -Force
}

Write-Host "Creating ZIP..."

Compress-Archive `
    -Path "$TempFolder\*" `
    -DestinationPath $ZipFile `
    -CompressionLevel Optimal

Remove-Item $TempFolder -Recurse -Force

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host ""
Write-Host "Package created:"
Write-Host $ZipFile -ForegroundColor Yellow
Write-Host ""