# PowerShell Deployment Script for GCP Staging Infrastructure
# This script orchestrates the complete PostgreSQL 17 migration

$ErrorActionPreference = "Stop"

# Configuration
$PROJECT_ID = if ($env:PROJECT_ID) { $env:PROJECT_ID } else { "netra-staging" }
$OLD_INSTANCE = if ($env:OLD_INSTANCE) { $env:OLD_INSTANCE } else { "staging-shared-postgres" }
$TERRAFORM_DIR = "."

Write-Host "========================================" -ForegroundColor Green
Write-Host "GCP Staging Infrastructure Deployment" -ForegroundColor Green
Write-Host "PostgreSQL 14 → 17 Migration" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Function to check command exists
function Test-Command {
    param($Command)
    if (!(Get-Command $Command -ErrorAction SilentlyContinue)) {
        Write-Host "Error: $Command is not installed" -ForegroundColor Red
        exit 1
    }
}

# Function to confirm action
function Confirm-Action {
    param($Message)
    $response = Read-Host "$Message (y/n)"
    if ($response -ne 'y') {
        Write-Host "Aborted" -ForegroundColor Yellow
        exit 0
    }
}

# Step 1: Check prerequisites
Write-Host "`nStep 1: Checking prerequisites..." -ForegroundColor Yellow
Test-Command gcloud
Test-Command terraform
Test-Command python

# Check GCloud authentication
Write-Host "Checking GCloud authentication..."
$activeAccount = gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>$null
if (!$activeAccount) {
    Write-Host "Not authenticated with GCloud" -ForegroundColor Red
    Write-Host "Please run: gcloud auth login"
    exit 1
}

# Set project
Write-Host "Setting GCP project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Step 2: Initialize Terraform
Write-Host "`nStep 2: Initializing Terraform..." -ForegroundColor Yellow
Set-Location $TERRAFORM_DIR

if (!(Test-Path terraform.tfvars)) {
    Write-Host "Creating terraform.tfvars from example..."
    Copy-Item terraform.tfvars.example terraform.tfvars
    Write-Host "Please review terraform.tfvars and adjust if needed" -ForegroundColor Yellow
    Read-Host "Press enter to continue"
}

terraform init

# Step 3: Plan Terraform changes
Write-Host "`nStep 3: Planning infrastructure changes..." -ForegroundColor Yellow
terraform plan -out=tfplan

Write-Host "`nReview the plan above carefully!" -ForegroundColor Yellow
Confirm-Action "Do you want to apply these changes?"

# Step 4: Apply Terraform changes
Write-Host "`nStep 4: Creating new PostgreSQL 17 infrastructure..." -ForegroundColor Yellow
terraform apply tfplan

# Get new instance name
$NEW_INSTANCE = terraform output -raw database_instance_name
Write-Host "✓ New instance created: $NEW_INSTANCE" -ForegroundColor Green

# Step 5: Backup old database
Write-Host "`nStep 5: Backing up old database..." -ForegroundColor Yellow
Confirm-Action "Do you want to create a backup of $OLD_INSTANCE?"

$BACKUP_NAME = "pre-migration-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
gcloud sql backups create `
    --instance=$OLD_INSTANCE `
    --project=$PROJECT_ID `
    --description="Backup before PostgreSQL 17 migration"

Write-Host "✓ Backup created" -ForegroundColor Green

# Step 6: Migrate data
Write-Host "`nStep 6: Migrating data..." -ForegroundColor Yellow
Confirm-Action "Do you want to migrate data from $OLD_INSTANCE to $NEW_INSTANCE?"

python migrate.py `
    --project $PROJECT_ID `
    --old-instance $OLD_INSTANCE `
    --skip-backup  # Already backed up

# Step 7: Update application deployment
Write-Host "`nStep 7: Updating application deployment..." -ForegroundColor Yellow
Set-Location ..
python scripts/deploy_to_gcp.py --project $PROJECT_ID --build-local --run-checks

# Step 8: Run tests
Write-Host "`nStep 8: Running integration tests..." -ForegroundColor Yellow
python unified_test_runner.py --level integration --env staging --fast-fail

# Step 9: Show summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✓ Migration completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

$publicIP = terraform output -raw database_public_ip
$connectionName = terraform output -raw database_connection_name

Write-Host "`nNew Infrastructure:"
Write-Host "  PostgreSQL Instance: $NEW_INSTANCE"
Write-Host "  PostgreSQL Version: 17"
Write-Host "  Public IP: $publicIP"
Write-Host "  Connection: $connectionName"
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Monitor application logs for any issues"
Write-Host "2. Verify all services are functioning correctly"
Write-Host "3. Once confirmed, delete old instance:"
Write-Host "   gcloud sql instances delete $OLD_INSTANCE --project $PROJECT_ID" -ForegroundColor Yellow
Write-Host "`nDocumentation: terraform-gcp-staging/README.md" -ForegroundColor Green