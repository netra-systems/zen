# Netra Staging Authentication Setup Script
# This script ensures GCP authentication always works for staging deployments

param(
    [Parameter(Mandatory=$false)]
    [switch]$ForceNewKey = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectId = 'netra-staging'
)

Write-Host '================================================' -ForegroundColor Blue
Write-Host '  NETRA STAGING AUTHENTICATION SETUP          ' -ForegroundColor Blue
Write-Host '================================================' -ForegroundColor Blue
Write-Host ''

# Configuration
$SERVICE_ACCOUNT_NAME = 'netra-staging-deploy'
$SERVICE_ACCOUNT_EMAIL = "$SERVICE_ACCOUNT_NAME@$ProjectId.iam.gserviceaccount.com"
$KEY_FILE_PATH = "$PSScriptRoot\gcp-staging-sa-key.json"
$ENV_FILE_PATH = "$PSScriptRoot\.env.staging.local"

# Step 1: Check if we can access the project
Write-Host '[1/7] Checking GCP project access...' -ForegroundColor Green
$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $ProjectId) {
    Write-Host "  Setting project to $ProjectId..."
    gcloud config set project $ProjectId 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Error: Cannot access project $ProjectId" -ForegroundColor Red
        Write-Host '  Please ensure you have access to this project' -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "  OK: Project set to: $ProjectId" -ForegroundColor Green

# Step 2: Check if service account exists
Write-Host '[2/7] Checking service account...' -ForegroundColor Green
$accountExists = gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL --project=$ProjectId 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating service account: $SERVICE_ACCOUNT_NAME..."
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME `
        --display-name='Netra Staging Deployment Account' `
        --project=$ProjectId
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host '  Error: Failed to create service account' -ForegroundColor Red
        exit 1
    }
    Write-Host '  OK: Service account created' -ForegroundColor Green
} else {
    Write-Host "  OK: Service account exists: $SERVICE_ACCOUNT_EMAIL" -ForegroundColor Green
}

# Step 3: Grant necessary roles
Write-Host '[3/7] Granting IAM roles...' -ForegroundColor Green
$roles = @(
    'roles/artifactregistry.writer',
    'roles/run.developer',
    'roles/storage.admin',
    'roles/secretmanager.admin',
    'roles/cloudbuild.builds.editor'
)

foreach ($role in $roles) {
    Write-Host "  Granting $role..."
    gcloud projects add-iam-policy-binding $ProjectId `
        --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" `
        --role="$role" `
        --quiet 2>$null
}
Write-Host '  OK: IAM roles granted' -ForegroundColor Green

# Step 4: Check if key file exists or force new key
Write-Host '[4/7] Managing service account key...' -ForegroundColor Green
if ((Test-Path $KEY_FILE_PATH) -and -not $ForceNewKey) {
    Write-Host "  OK: Key file exists: $KEY_FILE_PATH" -ForegroundColor Green
} else {
    if (Test-Path $KEY_FILE_PATH) {
        Write-Host '  Removing old key file...'
        Remove-Item $KEY_FILE_PATH -Force
    }
    
    Write-Host '  Creating new key file...'
    gcloud iam service-accounts keys create $KEY_FILE_PATH `
        --iam-account=$SERVICE_ACCOUNT_EMAIL `
        --project=$ProjectId
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host '  Error: Failed to create key file' -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK: Key file created: $KEY_FILE_PATH" -ForegroundColor Green
}

# Step 5: Set environment variables
Write-Host '[5/7] Setting environment variables...' -ForegroundColor Green

# Set for current session
$env:GCP_STAGING_SA_KEY_PATH = $KEY_FILE_PATH
$env:GOOGLE_APPLICATION_CREDENTIALS = $KEY_FILE_PATH

# Set for current user (persistent)
[System.Environment]::SetEnvironmentVariable('GCP_STAGING_SA_KEY_PATH', $KEY_FILE_PATH, 'User')
[System.Environment]::SetEnvironmentVariable('GOOGLE_APPLICATION_CREDENTIALS', $KEY_FILE_PATH, 'User')

Write-Host '  OK: Environment variables set' -ForegroundColor Green
Write-Host "    GCP_STAGING_SA_KEY_PATH=$KEY_FILE_PATH" -ForegroundColor Cyan
Write-Host "    GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE_PATH" -ForegroundColor Cyan

# Step 6: Authenticate with service account
Write-Host '[6/7] Authenticating with service account...' -ForegroundColor Green
gcloud auth activate-service-account --key-file=$KEY_FILE_PATH
if ($LASTEXITCODE -ne 0) {
    Write-Host '  Error: Failed to authenticate' -ForegroundColor Red
    exit 1
}

# Configure Docker
gcloud auth configure-docker 'us-central1-docker.pkg.dev' --quiet
Write-Host '  OK: Authenticated and Docker configured' -ForegroundColor Green

# Step 7: Create/Update .env.staging.local file
Write-Host '[7/7] Creating .env.staging.local file...' -ForegroundColor Green
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$envContent = @"
# Staging Environment Service Account Configuration
# Generated by setup-staging-auth.ps1
# Last updated: $timestamp

# GCP Service Account Key Path
GCP_STAGING_SA_KEY_PATH=$KEY_FILE_PATH
GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE_PATH

# GCP Project Configuration
GCP_PROJECT_ID=$ProjectId
GCP_REGION=us-central1
GCP_ZONE=us-central1-a

# Service Account Details
SERVICE_ACCOUNT_EMAIL=$SERVICE_ACCOUNT_EMAIL
"@

$envContent | Out-File -FilePath $ENV_FILE_PATH -Encoding UTF8
Write-Host "  OK: Created $ENV_FILE_PATH" -ForegroundColor Green

# Verification
Write-Host ''
Write-Host '================================================' -ForegroundColor Green
Write-Host '  AUTHENTICATION SETUP COMPLETED              ' -ForegroundColor Green
Write-Host '================================================' -ForegroundColor Green
Write-Host ''
Write-Host 'Verification:' -ForegroundColor Yellow
$activeAccount = gcloud auth list --filter=status:ACTIVE --format='value(account)'
$currentProject = gcloud config get-value project
Write-Host "  Active account: $activeAccount" -ForegroundColor Cyan
Write-Host "  Project: $currentProject" -ForegroundColor Cyan
Write-Host "  Key file: $KEY_FILE_PATH" -ForegroundColor Cyan
Write-Host ''
Write-Host 'You can now run deployments with:' -ForegroundColor Yellow
Write-Host '  .\deploy-staging-reliable.ps1' -ForegroundColor Green
Write-Host ''