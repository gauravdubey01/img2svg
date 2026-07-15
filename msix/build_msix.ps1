param(
    [string]$Version = "1.0.0.0",
    [string]$OutputDir = (Join-Path $PSScriptRoot "..\dist"),
    [string]$CertPassword = "temp123"
)

$ScriptDir = $PSScriptRoot
$ProjectRoot = Join-Path $ScriptDir ".."
$PayloadDir = Join-Path $ScriptDir "payload"
$AssetsDir = Join-Path $ScriptDir "Assets"
$ExePath = Join-Path $ProjectRoot "dist\ImageToSVG.exe"
$MsixPath = Join-Path $OutputDir "ImageToSVG.msix"
$CertPath = Join-Path $ScriptDir "temp_cert.pfx"

$MakeAppx = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe"
$SignTool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"

Write-Host "=== ImageToSVG MSIX Builder ===" -ForegroundColor Cyan

# 1. Generate assets
Write-Host ">> Generating assets..." -ForegroundColor Yellow
python (Join-Path $ScriptDir "generate_assets.py")
if (-not $?) { exit 1 }

# 2. Prepare payload
Write-Host ">> Preparing payload..." -ForegroundColor Yellow
if (Test-Path $PayloadDir) { Remove-Item -Recurse -Force $PayloadDir }
New-Item -ItemType Directory -Path $PayloadDir -Force | Out-Null
Copy-Item $ExePath (Join-Path $PayloadDir "ImageToSVG.exe")
Copy-Item -Path $AssetsDir -Destination (Join-Path $PayloadDir "Assets") -Recurse
Copy-Item (Join-Path $ScriptDir "AppxManifest.xml") $PayloadDir\

# 3. Update version in manifest
$Manifest = Join-Path $PayloadDir "AppxManifest.xml"
(Get-Content $Manifest) -replace 'Version="[^"]+"', "Version=`"$Version`"" | Set-Content $Manifest

# 4. Create self-signed cert if not exists
if (-not (Test-Path $CertPath)) {
    Write-Host ">> Creating self-signed certificate..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate -Type Custom -Subject "CN=0A36019C-61EA-47F2-A9AE-D3B27D5E13D4" `
        -KeyUsage DigitalSignature -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3") `
        -CertStoreLocation "Cert:\CurrentUser\My"
    $pwd = ConvertTo-SecureString -String $CertPassword -Force -AsPlainText
    Export-PfxCertificate -Cert $cert -FilePath $CertPath -Password $pwd
}

# 5. Build MSIX
Write-Host ">> Building MSIX package..." -ForegroundColor Yellow
& $MakeAppx pack /p $MsixPath /d $PayloadDir /o
if (-not $?) { exit 1 }

# 6. Sign
Write-Host ">> Signing MSIX package..." -ForegroundColor Yellow
& $SignTool sign /fd SHA256 /a /f $CertPath /p $CertPassword $MsixPath
if (-not $?) { exit 1 }

# Cleanup
Remove-Item -Recurse -Force $PayloadDir

Write-Host "=== Done: $MsixPath ===" -ForegroundColor Green
