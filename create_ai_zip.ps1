# ==========================================
# EuroCompass AI ZIP Creator v2
# ==========================================

$ProjectRoot = Get-Location
$Parent = Split-Path $ProjectRoot -Parent

$TempFolder = Join-Path $Parent "EuroCompass_AI"
$ZipFile = Join-Path $Parent "EuroCompass_AI.zip"

Write-Host ""
Write-Host "Creating AI package..."
Write-Host ""

# Cleanup previous run
if(Test-Path $TempFolder){
    Remove-Item $TempFolder -Recurse -Force
}

if(Test-Path $ZipFile){
    Remove-Item $ZipFile -Force
}

$ExcludedFolders = @(
    ".git",
    ".venv",
    ".wrangler",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "exports"
)

$ExcludedExtensions = @(
    ".pyc",
    ".pyo"
)

Write-Host "Copying files..."

Get-ChildItem $ProjectRoot -Recurse -Force -File |
Where-Object {

    $skip = $false

    foreach($folder in $ExcludedFolders){

        if($_.FullName -match "\\$folder(\\|$)"){
            $skip = $true
            break
        }

    }

    if($ExcludedExtensions -contains $_.Extension){
        $skip = $true
    }

    -not $skip

} | ForEach-Object {

    $relative = $_.FullName.Substring($ProjectRoot.Path.Length + 1)

    $destination = Join-Path $TempFolder $relative

    $directory = Split-Path $destination

    if(!(Test-Path $directory)){
        New-Item $directory -ItemType Directory -Force | Out-Null
    }

    Copy-Item $_.FullName $destination

}

Write-Host ""
Write-Host "Creating ZIP..."

Compress-Archive `
    -Path $TempFolder `
    -DestinationPath $ZipFile `
    -Force

$size = [math]::Round((Get-Item $ZipFile).Length/1MB,2)

Write-Host ""
Write-Host "ZIP Size: $size MB"

Remove-Item $TempFolder -Recurse -Force

Write-Host ""
Write-Host "Done!"