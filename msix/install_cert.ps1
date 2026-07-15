# Run this as Administrator to trust the self-signed cert for local MSIX install
param(
    [string]$CerFile = "$PSScriptRoot\temp_cert.cer"
)

if (-not (Test-Path $CerFile)) {
    Write-Host "Certificate not found at $CerFile" -ForegroundColor Red
    Write-Host "Run build_msix.ps1 first to generate it." -ForegroundColor Yellow
    exit 1
}

Write-Host "Installing certificate to LocalMachine stores..." -ForegroundColor Cyan
certutil -addstore Root "$CerFile"
certutil -addstore TrustedPublisher "$CerFile"
Write-Host "Done. You can now run: Add-AppxPackage -Path <path>\ImageToSVG.msix" -ForegroundColor Green
