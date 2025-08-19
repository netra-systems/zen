# Staging Database Migration Script
# Runs database migrations against the staging environment

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$ForceRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Blue
Write-Host "    NETRA STAGING DATABASE MIGRATIONS          " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"

# Function to get database URL from secret
function Get-DatabaseUrl {
    Write-Host "Retrieving database URL from Google Secret Manager..." -ForegroundColor Yellow
    
    try {
        $dbUrl = gcloud secrets versions access latest `
            --secret="database-url-staging" `
            --project=$PROJECT_ID 2>$null
        
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($dbUrl)) {
            Write-Host "Failed to retrieve database URL from secrets" -ForegroundColor Red
            return $null
        }
        
        Write-Host "  Database URL retrieved successfully" -ForegroundColor Green
        return $dbUrl
    } catch {
        Write-Host "Error retrieving database URL: $_" -ForegroundColor Red
        return $null
    }
}

# Function to check current migration status
function Check-MigrationStatus {
    param($dbUrl)
    
    Write-Host "Checking current migration status..." -ForegroundColor Yellow
    
    # Set environment variable for alembic
    $env:DATABASE_URL = $dbUrl
    
    # Get current revision
    $currentRevision = python -m alembic -c config/alembic.ini current 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to get current revision" -ForegroundColor Red
        return $false
    }
    
    # Get head revision
    $headRevision = python -m alembic -c config/alembic.ini heads 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to get head revision" -ForegroundColor Red
        return $false
    }
    
    Write-Host "  Current revision: $currentRevision" -ForegroundColor Cyan
    Write-Host "  Head revision: $headRevision" -ForegroundColor Cyan
    
    # Check if migration is needed
    if ($currentRevision -like "*head*") {
        Write-Host "  Database is up-to-date" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  Migration needed" -ForegroundColor Yellow
        return $false
    }
}

# Function to run migrations
function Run-Migrations {
    param($dbUrl)
    
    Write-Host "Running database migrations..." -ForegroundColor Yellow
    
    # Set environment variable for alembic
    $env:DATABASE_URL = $dbUrl
    
    # Run migrations to head
    $output = python -m alembic -c config/alembic.ini upgrade head 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Migrations completed successfully" -ForegroundColor Green
        Write-Host $output -ForegroundColor Gray
        return $true
    } else {
        Write-Host "  Migration failed!" -ForegroundColor Red
        Write-Host $output -ForegroundColor Red
        return $false
    }
}

# Main execution
function Main {
    # Check prerequisites
    if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
        Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
    
    if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
        Write-Host "Error: Google Cloud SDK is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
    
    # Check if alembic.ini exists
    if (-not (Test-Path "config/alembic.ini")) {
        Write-Host "Error: alembic.ini not found at config/alembic.ini" -ForegroundColor Red
        Write-Host "Please run this script from the project root directory" -ForegroundColor Red
        exit 1
    }
    
    # Get database URL
    $dbUrl = Get-DatabaseUrl
    if (-not $dbUrl) {
        Write-Host "Cannot proceed without database URL" -ForegroundColor Red
        exit 1
    }
    
    # Check migration status
    $isUpToDate = Check-MigrationStatus $dbUrl
    
    if ($CheckOnly) {
        if ($isUpToDate) {
            Write-Host ""
            Write-Host "No migrations needed" -ForegroundColor Green
            exit 0
        } else {
            Write-Host ""
            Write-Host "Migrations are needed" -ForegroundColor Yellow
            exit 0
        }
    }
    
    # Run migrations if needed
    if ($isUpToDate -and -not $ForceRun) {
        Write-Host ""
        Write-Host "No migrations needed" -ForegroundColor Green
    } else {
        if ($ForceRun) {
            Write-Host ""
            Write-Host "Force running migrations..." -ForegroundColor Yellow
        }
        
        $success = Run-Migrations $dbUrl
        
        if ($success) {
            Write-Host ""
            Write-Host "Database migrations completed successfully!" -ForegroundColor Green
            
            # Verify final status
            $finalStatus = Check-MigrationStatus $dbUrl
            if (-not $finalStatus) {
                Write-Host "Warning: Database may still need migrations" -ForegroundColor Yellow
                exit 1
            }
        } else {
            Write-Host ""
            Write-Host "Migration failed! Please check the error messages above." -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host ""
    Write-Host "Migration process completed" -ForegroundColor Green
}

# Run main function
Main