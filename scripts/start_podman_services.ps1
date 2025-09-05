# Podman Services Startup Script for Netra E2E Testing
# This script reliably starts all required services using Podman on Windows WSL

param(
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Status,
    [switch]$Clean,
    [switch]$Help
)

# Configuration
$PROJECT_ROOT = "C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1"
$COMPOSE_FILE = "docker-compose.podman.yml"
$PODMAN_MACHINE = "podman-machine-default"

function Show-Help {
    Write-Host "Netra Podman Services Management Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\start_podman_services.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Status     Check status of all services"
    Write-Host "  -Stop       Stop all services"
    Write-Host "  -Restart    Restart all services"
    Write-Host "  -Clean      Stop services and clean up containers"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    Write-Host "Default (no options): Start all services"
    Write-Host ""
    Write-Host "Services managed:"
    Write-Host "  - PostgreSQL (port 5433)"
    Write-Host "  - Redis (port 6380)"
    Write-Host "  - ClickHouse (port 8124)"
    Write-Host "  - Auth Service (port 8081)"
    Write-Host "  - Backend Service (port 8000)"
}

function Invoke-PodmanCommand {
    param([string]$Command)
    
    Write-Host "Executing: $Command" -ForegroundColor Yellow
    $result = wsl -d $PODMAN_MACHINE -- bash -c "cd /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1 && $Command"
    return $result
}

function Test-ServiceHealth {
    param([string]$ServiceName, [string]$Url)
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "✅ $ServiceName is healthy (Status: $($response.StatusCode))" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ $ServiceName is not responding at $Url" -ForegroundColor Red
        return $false
    }
}

function Wait-ForServices {
    Write-Host "Waiting for services to become healthy..." -ForegroundColor Yellow
    
    $services = @(
        @{Name="Backend"; Url="http://localhost:8000/health"},
        @{Name="Auth Service"; Url="http://localhost:8081/health"}
    )
    
    $maxAttempts = 30
    $attempt = 0
    
    do {
        $attempt++
        Write-Host "Health check attempt $attempt of $maxAttempts" -ForegroundColor Cyan
        
        $allHealthy = $true
        foreach ($service in $services) {
            $healthy = Test-ServiceHealth -ServiceName $service.Name -Url $service.Url
            $allHealthy = $allHealthy -and $healthy
        }
        
        if ($allHealthy) {
            Write-Host "🎉 All services are healthy!" -ForegroundColor Green
            return $true
        }
        
        if ($attempt -lt $maxAttempts) {
            Write-Host "Waiting 10 seconds before next health check..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
        }
    } while ($attempt -lt $maxAttempts)
    
    Write-Host "⚠️ Not all services became healthy within the timeout period" -ForegroundColor Yellow
    return $false
}

function Show-ServiceStatus {
    Write-Host "=== Podman Service Status ===" -ForegroundColor Green
    
    $containers = Invoke-PodmanCommand "podman ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    Write-Host $containers
    
    Write-Host "`n=== Compose Service Status ===" -ForegroundColor Green
    $composeStatus = Invoke-PodmanCommand "podman-compose -f $COMPOSE_FILE ps"
    Write-Host $composeStatus
    
    Write-Host "`n=== Service Health Checks ===" -ForegroundColor Green
    Test-ServiceHealth -ServiceName "Backend" -Url "http://localhost:8000/health"
    Test-ServiceHealth -ServiceName "Auth Service" -Url "http://localhost:8081/health"
    
    # Test database connections
    Write-Host "`n=== Database Connectivity ===" -ForegroundColor Green
    try {
        $pgResult = Invoke-PodmanCommand "podman exec netra-postgres pg_isready -U netra -d netra_dev"
        Write-Host "PostgreSQL: $pgResult" -ForegroundColor Green
    }
    catch {
        Write-Host "PostgreSQL: Not accessible" -ForegroundColor Red
    }
    
    try {
        $redisResult = Invoke-PodmanCommand "podman exec netra-redis redis-cli ping"
        Write-Host "Redis: $redisResult" -ForegroundColor Green
    }
    catch {
        Write-Host "Redis: Not accessible" -ForegroundColor Red
    }
}

function Start-Services {
    Write-Host "🚀 Starting Netra Podman Services..." -ForegroundColor Green
    
    # Ensure we're in the correct directory and start services
    $result = Invoke-PodmanCommand "podman-compose -f $COMPOSE_FILE up -d"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Services started successfully!" -ForegroundColor Green
        
        # Wait for services to become healthy
        $healthy = Wait-ForServices
        
        if ($healthy) {
            Write-Host "`n✅ All services are ready for E2E testing!" -ForegroundColor Green
            Show-ServiceStatus
        } else {
            Write-Host "`n⚠️ Services started but some may not be fully healthy yet" -ForegroundColor Yellow
            Write-Host "Run with -Status to check current state" -ForegroundColor Cyan
        }
    } else {
        Write-Host "❌ Failed to start services" -ForegroundColor Red
        Write-Host $result
        exit 1
    }
}

function Stop-Services {
    Write-Host "🛑 Stopping Netra Podman Services..." -ForegroundColor Yellow
    
    $result = Invoke-PodmanCommand "podman-compose -f $COMPOSE_FILE down"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Services stopped successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to stop services" -ForegroundColor Red
        Write-Host $result
    }
}

function Clean-Services {
    Write-Host "🧹 Cleaning up Podman containers and volumes..." -ForegroundColor Yellow
    
    # Stop and remove containers
    Invoke-PodmanCommand "podman-compose -f $COMPOSE_FILE down -v"
    
    # Remove any dangling images
    Invoke-PodmanCommand "podman image prune -f"
    
    Write-Host "Cleanup completed!" -ForegroundColor Green
}

function Restart-Services {
    Write-Host "🔄 Restarting Netra Podman Services..." -ForegroundColor Yellow
    Stop-Services
    Start-Sleep -Seconds 5
    Start-Services
}

# Main script logic
if ($Help) {
    Show-Help
    exit 0
}

if ($Status) {
    Show-ServiceStatus
    exit 0
}

if ($Clean) {
    Clean-Services
    exit 0
}

if ($Stop) {
    Stop-Services
    exit 0
}

if ($Restart) {
    Restart-Services
    exit 0
}

# Default action: Start services
Start-Services