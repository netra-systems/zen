# PowerShell script for managing development database on Windows

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "clean", "connect")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"

function Write-ColorOutput($ForegroundColor, $Message) {
    Write-Host $Message -ForegroundColor $ForegroundColor
}

function Check-Prerequisites {
    Write-ColorOutput Yellow "Checking prerequisites..."
    
    # Check Docker
    try {
        docker version | Out-Null
        Write-ColorOutput Green "✓ Docker is installed and running"
    } catch {
        Write-ColorOutput Red "✗ Docker is not running. Please start Docker Desktop."
        exit 1
    }
    
    # Check Terraform
    try {
        terraform version | Out-Null
        Write-ColorOutput Green "✓ Terraform is installed"
    } catch {
        Write-ColorOutput Red "✗ Terraform is not installed. Please install Terraform."
        exit 1
    }
}

function Start-DevDatabase {
    Write-ColorOutput Cyan "Starting development database infrastructure..."
    
    if (-not (Test-Path ".terraform")) {
        Write-ColorOutput Yellow "Initializing Terraform..."
        terraform init
    }
    
    Write-ColorOutput Yellow "Creating infrastructure..."
    terraform apply -auto-approve
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "`n✓ Development database started successfully!"
        Write-ColorOutput Cyan "Connection details saved in: connection_info.txt"
        Write-ColorOutput Cyan "Environment file created: ../.env.development.local"
        
        # Show connection strings
        Write-Host "`nQuick Connect:" -ForegroundColor Yellow
        Write-Host "PostgreSQL: psql -h localhost -p 5432 -U postgres -d netra_dev" -ForegroundColor White
        Write-Host "Redis:      redis-cli -h localhost -p 6379" -ForegroundColor White
        Write-Host "ClickHouse: http://localhost:8123" -ForegroundColor White
    } else {
        Write-ColorOutput Red "Failed to start infrastructure"
        exit 1
    }
}

function Stop-DevDatabase {
    Write-ColorOutput Cyan "Stopping development database infrastructure..."
    terraform destroy -auto-approve
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "✓ Infrastructure stopped successfully"
    } else {
        Write-ColorOutput Red "Failed to stop infrastructure"
        exit 1
    }
}

function Restart-DevDatabase {
    Stop-DevDatabase
    Start-Sleep -Seconds 2
    Start-DevDatabase
}

function Get-Status {
    Write-ColorOutput Cyan "Development Database Status"
    Write-Host "=" * 50 -ForegroundColor Gray
    
    $containers = @("netra-postgres-dev", "netra-redis-dev", "netra-clickhouse-dev")
    
    foreach ($container in $containers) {
        try {
            $status = docker inspect $container --format='{{.State.Status}}' 2>$null
            if ($status -eq "running") {
                Write-ColorOutput Green "✓ $container : running"
                
                # Get port mappings
                $ports = docker port $container 2>$null
                if ($ports) {
                    Write-Host "  Ports: $ports" -ForegroundColor Gray
                }
            } else {
                Write-ColorOutput Yellow "⚠ $container : $status"
            }
        } catch {
            Write-ColorOutput Red "✗ $container : not found"
        }
    }
    
    # Check volumes
    Write-Host "`nVolumes:" -ForegroundColor Cyan
    $volumes = @("netra-postgres-dev-data", "netra-redis-dev-data", "netra-clickhouse-dev-data")
    foreach ($volume in $volumes) {
        try {
            docker volume inspect $volume | Out-Null
            Write-ColorOutput Green "✓ $volume"
        } catch {
            Write-ColorOutput Red "✗ $volume : not found"
        }
    }
    
    # Check network
    Write-Host "`nNetwork:" -ForegroundColor Cyan
    try {
        docker network inspect netra-dev-network | Out-Null
        Write-ColorOutput Green "✓ netra-dev-network"
    } catch {
        Write-ColorOutput Red "✗ netra-dev-network : not found"
    }
}

function Show-Logs {
    Write-ColorOutput Cyan "Showing logs (Ctrl+C to exit)..."
    
    $container = Read-Host "Enter container name (postgres/redis/clickhouse) [postgres]"
    if ([string]::IsNullOrWhiteSpace($container)) {
        $container = "postgres"
    }
    
    $fullName = "netra-$container-dev"
    docker logs -f $fullName
}

function Clean-All {
    Write-ColorOutput Yellow "WARNING: This will delete all data!"
    $confirm = Read-Host "Are you sure? (yes/no)"
    
    if ($confirm -eq "yes") {
        Write-ColorOutput Red "Cleaning up everything..."
        
        # Destroy infrastructure
        terraform destroy -auto-approve
        
        # Remove volumes
        docker volume rm netra-postgres-dev-data 2>$null
        docker volume rm netra-redis-dev-data 2>$null
        docker volume rm netra-clickhouse-dev-data 2>$null
        
        # Remove network
        docker network rm netra-dev-network 2>$null
        
        # Remove terraform state
        Remove-Item -Force -Recurse .terraform* -ErrorAction SilentlyContinue
        Remove-Item -Force terraform.tfstate* -ErrorAction SilentlyContinue
        Remove-Item -Force connection_info.txt -ErrorAction SilentlyContinue
        Remove-Item -Force ../.env.development.local -ErrorAction SilentlyContinue
        
        Write-ColorOutput Green "✓ Cleanup complete"
    } else {
        Write-ColorOutput Yellow "Cleanup cancelled"
    }
}

function Connect-Database {
    Write-ColorOutput Cyan "Connect to database"
    Write-Host "1. PostgreSQL" -ForegroundColor White
    Write-Host "2. Redis" -ForegroundColor White
    Write-Host "3. ClickHouse" -ForegroundColor White
    
    $choice = Read-Host "Select database (1-3)"
    
    switch ($choice) {
        "1" {
            Write-ColorOutput Yellow "Connecting to PostgreSQL..."
            docker exec -it netra-postgres-dev psql -U postgres -d netra_dev
        }
        "2" {
            Write-ColorOutput Yellow "Connecting to Redis..."
            docker exec -it netra-redis-dev redis-cli
        }
        "3" {
            Write-ColorOutput Yellow "Opening ClickHouse in browser..."
            Start-Process "http://localhost:8123"
        }
        default {
            Write-ColorOutput Red "Invalid choice"
        }
    }
}

# Main execution
Write-Host "`nNetra Development Database Manager" -ForegroundColor Magenta
Write-Host "=" * 50 -ForegroundColor Gray

Check-Prerequisites

switch ($Action) {
    "start" { Start-DevDatabase }
    "stop" { Stop-DevDatabase }
    "restart" { Restart-DevDatabase }
    "status" { Get-Status }
    "logs" { Show-Logs }
    "clean" { Clean-All }
    "connect" { Connect-Database }
    default { Get-Status }
}

Write-Host "`n" # Add newline at end