# Simple Netra Staging Deployment Script
# This script deploys all three services to GCP staging

Write-Host "================================================" -ForegroundColor Blue
Write-Host "  NETRA STAGING DEPLOYMENT                    " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"
$REGION = "us-central1"
$REGISTRY = "$REGION-docker.pkg.dev"
$REGISTRY_PATH = "$REGISTRY/$PROJECT_ID/netra-staging"

# Service names - CRITICAL: Use exact names from learnings XML
$BACKEND_SERVICE = "netra-backend-staging"
$FRONTEND_SERVICE = "netra-frontend-staging"
$AUTH_SERVICE = "netra-auth-service"

# Step 1: Authenticate
Write-Host "[1/5] Authenticating..." -ForegroundColor Green
$keyFile = "$PSScriptRoot\gcp-staging-sa-key.json"
if (Test-Path $keyFile) {
    gcloud auth activate-service-account --key-file=$keyFile
    gcloud config set project $PROJECT_ID --quiet
    gcloud auth configure-docker $REGISTRY --quiet
    Write-Host "  ✓ Authentication successful" -ForegroundColor Green
} else {
    Write-Host "  ❌ Key file not found: $keyFile" -ForegroundColor Red
    Write-Host "  Run setup-staging-auth.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Step 2: Build images
Write-Host "[2/5] Building Docker images..." -ForegroundColor Green

# Backend
Write-Host "  Building backend..." -ForegroundColor Cyan
docker build -f Dockerfile.backend -t "$REGISTRY_PATH/$BACKEND_SERVICE:latest" .
if ($LASTEXITCODE -ne 0) { exit 1 }

# Frontend
Write-Host "  Building frontend..." -ForegroundColor Cyan
docker build -f Dockerfile.frontend.staging -t "$REGISTRY_PATH/$FRONTEND_SERVICE:latest" .
if ($LASTEXITCODE -ne 0) { exit 1 }

# Auth
Write-Host "  Building auth service..." -ForegroundColor Cyan
docker build -f Dockerfile.auth -t "$REGISTRY_PATH/$AUTH_SERVICE:latest" .
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "  ✓ All images built" -ForegroundColor Green

# Step 3: Push images
Write-Host "[3/5] Pushing images..." -ForegroundColor Green

docker push "$REGISTRY_PATH/$BACKEND_SERVICE:latest"
if ($LASTEXITCODE -ne 0) { exit 1 }

docker push "$REGISTRY_PATH/$FRONTEND_SERVICE:latest"
if ($LASTEXITCODE -ne 0) { exit 1 }

docker push "$REGISTRY_PATH/$AUTH_SERVICE:latest"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "  ✓ All images pushed" -ForegroundColor Green

# Step 4: Deploy to Cloud Run
Write-Host "[4/5] Deploying to Cloud Run..." -ForegroundColor Green

# Backend
Write-Host "  Deploying backend..." -ForegroundColor Cyan
gcloud run deploy $BACKEND_SERVICE `
    --image "$REGISTRY_PATH/$BACKEND_SERVICE:latest" `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --quiet

# Frontend
Write-Host "  Deploying frontend..." -ForegroundColor Cyan
gcloud run deploy $FRONTEND_SERVICE `
    --image "$REGISTRY_PATH/$FRONTEND_SERVICE:latest" `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --quiet

# Auth
Write-Host "  Deploying auth service..." -ForegroundColor Cyan
gcloud run deploy $AUTH_SERVICE `
    --image "$REGISTRY_PATH/$AUTH_SERVICE:latest" `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --quiet

Write-Host "  ✓ All services deployed" -ForegroundColor Green

# Step 5: Get URLs
Write-Host "[5/5] Service URLs:" -ForegroundColor Green

$BACKEND_URL = gcloud run services describe $BACKEND_SERVICE --region $REGION --format "value(status.url)"
$FRONTEND_URL = gcloud run services describe $FRONTEND_SERVICE --region $REGION --format "value(status.url)"
$AUTH_URL = gcloud run services describe $AUTH_SERVICE --region $REGION --format "value(status.url)"

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETE                         " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend:  $FRONTEND_URL" -ForegroundColor Cyan
Write-Host "Backend:   $BACKEND_URL" -ForegroundColor Cyan
Write-Host "Auth:      $AUTH_URL" -ForegroundColor Cyan