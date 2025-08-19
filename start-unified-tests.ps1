# Unified Testing Environment Startup Script (PowerShell)
# Purpose: One-command startup for complete testing environment on Windows
# Usage: .\start-unified-tests.ps1 [-Build] [-Logs] [-Cleanup] [-Status] [-TestOnly] [-Stop]

param(
    [switch]$Build,
    [switch]$Cleanup,
    [switch]$Logs,
    [switch]$Status,
    [switch]$TestOnly,
    [switch]$Stop,
    [switch]$Help
)

# Configuration
$ComposeFile = "docker-compose.test.yml"
$EnvFile = ".env.test"
$ProjectName = "netra-unified-test"

# Function to print colored output
function Write-Status {
    param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to check if Docker is running
function Test-Docker {
    try {
        docker info | Out-Null
        Write-Success "Docker is running"
        return $true
    }
    catch {
        Write-Error-Custom "Docker is not running. Please start Docker Desktop."
        return $false
    }
}

# Function to check if docker-compose is available
function Test-DockerCompose {
    $script:DockerComposeCmd = $null
    
    try {
        docker-compose version | Out-Null
        $script:DockerComposeCmd = "docker-compose"
        Write-Success "Docker Compose is available"
        return $true
    }
    catch {
        try {
            docker compose version | Out-Null
            $script:DockerComposeCmd = "docker compose"
            Write-Success "Docker Compose (v2) is available"
            return $true
        }
        catch {
            Write-Error-Custom "docker-compose or 'docker compose' not available"
            return $false
        }
    }
}

# Function to validate configuration files
function Test-Config {
    if (-not (Test-Path $ComposeFile)) {
        Write-Error-Custom "Docker Compose file ($ComposeFile) not found"
        return $false
    }

    if (-not (Test-Path $EnvFile)) {
        Write-Error-Custom "Environment file ($EnvFile) not found"
        return $false
    }

    Write-Success "Configuration files found"
    return $true
}

# Function to cleanup existing containers
function Invoke-Cleanup {
    Write-Status "Cleaning up existing containers..."
    
    try {
        & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile down --volumes --remove-orphans
        
        # Remove any dangling images
        docker image prune -f | Out-Null
        
        Write-Success "Cleanup completed"
    }
    catch {
        Write-Warning "Some cleanup operations failed (this may be normal)"
    }
}

# Function to build images
function Invoke-BuildImages {
    Write-Status "Building Docker images..."
    
    try {
        & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile build --no-cache
        Write-Success "Images built successfully"
    }
    catch {
        Write-Error-Custom "Failed to build images"
        throw
    }
}

# Function to start services
function Start-Services {
    Write-Status "Starting unified test environment..."
    
    # Start databases first
    & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile up -d test-postgres test-clickhouse test-redis
    
    # Wait for databases to be ready
    Write-Status "Waiting for databases to be ready..."
    Start-Sleep -Seconds 30
    
    # Start application services
    & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile up -d auth-service backend-service
    
    # Wait for backend services
    Write-Status "Waiting for backend services..."
    Start-Sleep -Seconds 30
    
    # Start frontend
    & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile up -d frontend-service
    
    # Wait for frontend
    Write-Status "Waiting for frontend service..."
    Start-Sleep -Seconds 20
    
    Write-Success "All services started"
}

# Function to run migrations
function Invoke-Migrations {
    Write-Status "Running database migrations..."
    
    try {
        & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile run --rm migration-runner
        Write-Success "Migrations completed"
    }
    catch {
        Write-Warning "Migrations may have failed - continuing with tests"
    }
}

# Function to run tests
function Invoke-Tests {
    Write-Status "Running unified test suite..."
    
    try {
        & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile run --rm test-runner
        
        # Create test results directory if it doesn't exist
        if (-not (Test-Path "test_results_unified")) {
            New-Item -ItemType Directory -Path "test_results_unified" | Out-Null
        }
        
        Write-Success "Test results will be available in ./test_results_unified/"
    }
    catch {
        Write-Error-Custom "Tests failed or encountered errors"
        throw
    }
}

# Function to show service status
function Show-Status {
    Write-Status "Service Status:"
    & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile ps
    
    Write-Host ""
    Write-Status "Service Health Checks:"
    
    # Check PostgreSQL
    try {
        & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile exec test-postgres pg_isready -U test_user | Out-Null
        Write-Success "PostgreSQL: Healthy"
    }
    catch {
        Write-Warning "PostgreSQL: Not Ready"
    }
    
    # Check ClickHouse
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8124/ping" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "ClickHouse: Healthy"
        }
        else {
            Write-Warning "ClickHouse: Not Ready"
        }
    }
    catch {
        Write-Warning "ClickHouse: Not Ready"
    }
    
    # Check Redis
    try {
        & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile exec test-redis redis-cli -a test_password ping | Out-Null
        Write-Success "Redis: Healthy"
    }
    catch {
        Write-Warning "Redis: Not Ready"
    }
    
    # Check Auth Service
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "Auth Service: Healthy"
        }
        else {
            Write-Warning "Auth Service: Not Ready"
        }
    }
    catch {
        Write-Warning "Auth Service: Not Ready"
    }
    
    # Check Backend Service
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "Backend Service: Healthy"
        }
        else {
            Write-Warning "Backend Service: Not Ready"
        }
    }
    catch {
        Write-Warning "Backend Service: Not Ready"
    }
    
    # Check Frontend Service
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "Frontend Service: Healthy"
        }
        else {
            Write-Warning "Frontend Service: Not Ready"
        }
    }
    catch {
        Write-Warning "Frontend Service: Not Ready"
    }
}

# Function to show logs
function Show-Logs {
    & $DockerComposeCmd.Split() -f $ComposeFile --env-file $EnvFile logs -f
}

# Function to display usage
function Show-Usage {
    Write-Host "Usage: .\start-unified-tests.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Build         Force rebuild of Docker images"
    Write-Host "  -Cleanup       Clean up containers and volumes before starting"
    Write-Host "  -Logs          Show live logs after starting services"
    Write-Host "  -Status        Show service status and health checks"
    Write-Host "  -TestOnly      Only run tests (assume services are already running)"
    Write-Host "  -Stop          Stop all services"
    Write-Host "  -Help          Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\start-unified-tests.ps1                      # Start services and run tests"
    Write-Host "  .\start-unified-tests.ps1 -Build -Cleanup      # Clean rebuild and run tests"
    Write-Host "  .\start-unified-tests.ps1 -Status              # Check service health"
    Write-Host "  .\start-unified-tests.ps1 -Logs                # View live logs"
    Write-Host "  .\start-unified-tests.ps1 -Stop                # Stop all services"
}

# Main execution
function Main {
    if ($Help) {
        Show-Usage
        return
    }
    
    # Perform pre-flight checks
    if (-not (Test-Docker)) { return }
    if (-not (Test-DockerCompose)) { return }
    if (-not (Test-Config)) { return }
    
    if ($Stop) {
        Invoke-Cleanup
        return
    }
    
    if ($Status) {
        Show-Status
        return
    }
    
    if ($Logs) {
        Show-Logs
        return
    }
    
    # Main execution flow
    Write-Status "Starting Netra Unified Testing Environment"
    Write-Host "========================================" -ForegroundColor Cyan
    
    try {
        if ($Cleanup) {
            Invoke-Cleanup
        }
        
        if ($Build) {
            Invoke-BuildImages
        }
        
        if (-not $TestOnly) {
            Start-Services
            Invoke-Migrations
        }
        
        # Wait a bit more for services to fully stabilize
        Write-Status "Allowing services to stabilize..."
        Start-Sleep -Seconds 10
        
        Invoke-Tests
        
        if ($Logs) {
            Write-Status "Showing live logs (Press Ctrl+C to exit)..."
            Show-Logs
        }
        else {
            Write-Success "Unified testing completed!"
            Write-Status "To view logs: $DockerComposeCmd -f $ComposeFile logs"
            Write-Status "To stop services: $DockerComposeCmd -f $ComposeFile down"
            Show-Status
        }
    }
    catch {
        Write-Error-Custom "An error occurred during execution: $_"
        Write-Status "To stop services: $DockerComposeCmd -f $ComposeFile down"
    }
}

# Execute main function
Main