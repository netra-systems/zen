# deploy-staging-clean.ps1 - Clean deployment script for GCP staging
param(
    [string]$ProjectId = "netra-staging",
    [string]$Region = "us-central1",
    [string]$Zone = "us-central1-a",
    [string]$Environment = "staging",
    [switch]$SkipDockerBuild,
    [switch]$SkipTerraform,
    [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"

# Configuration
$REGISTRY = "$Region-docker.pkg.dev/$ProjectId/netra-containers"
$STAGING_API_URL = "https://api.staging.netrasystems.ai"
$STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"
$AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"
$STATE_BUCKET = "$ProjectId-terraform-state"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NETRA STAGING DEPLOYMENT (WINDOWS)   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Environment: $Environment"
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow
$missing = @()
@("gcloud", "terraform", "docker") | ForEach-Object {
    if (-not (Get-Command $_ -ErrorAction SilentlyContinue)) {
        $missing += $_
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing tools: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host "All prerequisites installed" -ForegroundColor Green

# Set GCP project
Write-Host "Setting GCP project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable APIs
Write-Host "Enabling required APIs..." -ForegroundColor Yellow
@(
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com"
) | ForEach-Object {
    gcloud services enable $_ --quiet
}

# Configure Docker
Write-Host "Configuring Docker..." -ForegroundColor Yellow
gcloud auth configure-docker "$Region-docker.pkg.dev" --quiet

# Check Artifact Registry
$repoExists = gcloud artifacts repositories describe netra-containers --location=$Region --format="value(name)" 2>$null
if ([string]::IsNullOrEmpty($repoExists)) {
    Write-Host "Creating Artifact Registry repository..." -ForegroundColor Yellow
    gcloud artifacts repositories create netra-containers --repository-format=docker --location=$Region --quiet
}

if (-not $SkipDockerBuild) {
    Write-Host "Building and pushing Docker images..." -ForegroundColor Yellow
    Push-Location ..
    
    # Build Auth Service
    docker build -f Dockerfile.auth -t "$REGISTRY/auth-service:latest" .
    docker push "$REGISTRY/auth-service:latest"
    
    # Build Backend
    docker build -f Dockerfile.backend -t "$REGISTRY/backend:latest" .
    docker push "$REGISTRY/backend:latest"
    
    # Build Frontend
    docker build -f Dockerfile.frontend.staging --build-arg "NEXT_PUBLIC_API_URL=$STAGING_API_URL" --build-arg "NEXT_PUBLIC_WS_URL=$STAGING_WS_URL" -t "$REGISTRY/frontend:latest" .
    docker push "$REGISTRY/frontend:latest"
    
    Pop-Location
}

if (-not $SkipTerraform) {
    Write-Host "Deploying with Terraform..." -ForegroundColor Yellow
    
    # Check state bucket
    $bucketExists = gsutil ls -b "gs://$STATE_BUCKET" 2>$null
    if ($LASTEXITCODE -ne 0) {
        gsutil mb -p $ProjectId -l $Region "gs://$STATE_BUCKET"
        gsutil versioning set on "gs://$STATE_BUCKET"
    }
    
    terraform init -backend-config="bucket=$STATE_BUCKET" -backend-config="prefix=staging" -reconfigure
    
    $workspaceList = terraform workspace list 2>$null
    if ($workspaceList -match "staging") {
        terraform workspace select staging
    } else {
        terraform workspace new staging
    }
    
    terraform plan -var-file="terraform.staging.tfvars" -out="staging.tfplan"
    terraform apply "staging.tfplan"
}

# Deploy to Cloud Run
Write-Host "Deploying services to Cloud Run..." -ForegroundColor Yellow

gcloud run deploy netra-auth --image "$REGISTRY/auth-service:latest" --region $Region --platform managed --port 8080 --allow-unauthenticated --quiet
gcloud run deploy netra-backend --image "$REGISTRY/backend:latest" --region $Region --platform managed --port 8080 --allow-unauthenticated --quiet
gcloud run deploy netra-frontend --image "$REGISTRY/frontend:latest" --region $Region --platform managed --port 3000 --allow-unauthenticated --quiet

# Get URLs
$AUTH_URL = gcloud run services describe netra-auth --region=$Region --format='value(status.url)'
$BACKEND_URL = gcloud run services describe netra-backend --region=$Region --format='value(status.url)'
$FRONTEND_URL = gcloud run services describe netra-frontend --region=$Region --format='value(status.url)'

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETED SUCCESSFULLY    " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "  Auth:     $AUTH_URL"
Write-Host "  Backend:  $BACKEND_URL"
Write-Host "  Frontend: $FRONTEND_URL"
Write-Host ""
Write-Host "Deployment completed!" -ForegroundColor Green