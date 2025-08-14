# Quick Start Script for Terraform Development Database (Windows PowerShell)
# This script automates the setup of the development database infrastructure

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "   Netra Development Database Quick Start" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker Desktop first!" -ForegroundColor Red
    Write-Host "  Download from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Gray
    exit 1
}

# Check if Terraform is installed
Write-Host "Checking Terraform..." -ForegroundColor Yellow
$terraformInstalled = $false

# Try to run terraform version command
try {
    terraform version *>&1 | Out-Null
    Write-Host "✓ Terraform is installed" -ForegroundColor Green
    $terraformInstalled = $true
}
catch {
    # Terraform not found
    $terraformInstalled = $false
}

if (-not $terraformInstalled) {
    Write-Host "✗ Terraform is not installed" -ForegroundColor Red
    Write-Host "  Installing Terraform via Chocolatey..." -ForegroundColor Yellow
    
    # Check if Chocolatey is installed
    if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "  Installing Chocolatey first..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    }
    
    # Install Terraform
    choco install terraform -y
    refreshenv
    
    # Verify installation
    if (Get-Command terraform -ErrorAction SilentlyContinue) {
        Write-Host "✓ Terraform installed successfully" -ForegroundColor Green
    } else {
        Write-Host "Failed to install Terraform. Please install manually from:" -ForegroundColor Red
        Write-Host "https://www.terraform.io/downloads" -ForegroundColor Gray
        exit 1
    }
}

Write-Host ""
Write-Host "Initializing Terraform..." -ForegroundColor Yellow
terraform init

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to initialize Terraform" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Creating development database infrastructure..." -ForegroundColor Yellow
Write-Host "This will create:" -ForegroundColor Gray
Write-Host "  • PostgreSQL 14 database on port 5432" -ForegroundColor Gray
Write-Host "  • Redis 7 cache on port 6379" -ForegroundColor Gray
Write-Host "  • ClickHouse analytics on ports 8123/9000" -ForegroundColor Gray
Write-Host "  • Persistent data volumes" -ForegroundColor Gray
Write-Host "  • Auto-generated .env.development.local file" -ForegroundColor Gray
Write-Host ""

$response = Read-Host "Continue? (y/n)"
if ($response -ne 'y') {
    Write-Host "Setup cancelled" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
terraform apply -auto-approve

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "✓ Development Database Setup Complete!" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Database is now running with:" -ForegroundColor Cyan
    Write-Host "  • PostgreSQL: localhost:5432" -ForegroundColor White
    Write-Host "  • Redis: localhost:6379" -ForegroundColor White
    Write-Host "  • ClickHouse: localhost:8123 (HTTP) / 9000 (native)" -ForegroundColor White
    Write-Host ""
    Write-Host "Configuration files created:" -ForegroundColor Cyan
    Write-Host "  • ..\.env.development.local (auto-loaded by dev_launcher)" -ForegroundColor White
    Write-Host "  • connection_info.txt (all credentials)" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Go back to project root: cd .." -ForegroundColor White
    Write-Host "  2. Start the application: python dev_launcher.py" -ForegroundColor White
    Write-Host ""
    Write-Host "To manage the database:" -ForegroundColor Yellow
    Write-Host "  • View status: .\manage.ps1 status" -ForegroundColor White
    Write-Host "  • View logs: .\manage.ps1 logs" -ForegroundColor White
    Write-Host "  • Stop database: .\manage.ps1 stop" -ForegroundColor White
    Write-Host "  • Connect to DB: .\manage.ps1 connect" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ Setup failed. Please check the error messages above." -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  • Docker not running - Start Docker Desktop" -ForegroundColor Gray
    Write-Host "  • Port already in use - Check if another database is running" -ForegroundColor Gray
    Write-Host "  • Insufficient resources - Check Docker Desktop settings" -ForegroundColor Gray
    Write-Host ""
    exit 1
}