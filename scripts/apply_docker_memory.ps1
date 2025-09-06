# PowerShell script to apply Docker memory changes
Write-Host "Applying Docker Memory Configuration..." -ForegroundColor Green

# Show current WSL status
Write-Host "`nCurrent WSL distributions:" -ForegroundColor Yellow
wsl --list --verbose

# Shutdown WSL
Write-Host "`nShutting down WSL..." -ForegroundColor Yellow
wsl --shutdown

Write-Host "WSL shutdown complete." -ForegroundColor Green

# Wait a moment
Start-Sleep -Seconds 2

# Restart Docker Desktop
Write-Host "`nRestarting Docker Desktop..." -ForegroundColor Yellow
$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue

if ($dockerProcess) {
    # Stop Docker Desktop
    Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

# Start Docker Desktop
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerPath) {
    Start-Process $dockerPath
    Write-Host "Docker Desktop is restarting..." -ForegroundColor Green
    Write-Host "Please wait for Docker to fully start (this may take 30-60 seconds)" -ForegroundColor Yellow
} else {
    Write-Host "Docker Desktop not found at expected location. Please restart manually." -ForegroundColor Red
}

Write-Host "`nTo verify the new memory allocation after Docker starts, run:" -ForegroundColor Cyan
Write-Host "  docker system info | findstr Memory" -ForegroundColor White
Write-Host "  OR" -ForegroundColor Cyan
Write-Host "  python scripts\check_docker_memory.py" -ForegroundColor White