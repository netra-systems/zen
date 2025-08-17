# deploy-staging-complete.ps1 - Complete staging deployment for Windows
# This script handles the full staging deployment including Docker image builds

# Exit on any error
$ErrorActionPreference = "Stop"

# Colors and formatting
function Write-Status {
    param($Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')]" -ForegroundColor Green -NoNewline
    Write-Host " $Message"
}

function Write-Error-Message {
    param($Message)
    Write-Host "[ERROR]" -ForegroundColor Red -NoNewline
    Write-Host " $Message"
}

function Write-Warning-Message {
    param($Message)
    Write-Host "[WARNING]" -ForegroundColor Yellow -NoNewline
    Write-Host " $Message"
}

function Write-Info {
    param($Message)
    Write-Host "[INFO]" -ForegroundColor Blue -NoNewline
    Write-Host " $Message"
}

# Banner
Write-Host "================================================" -ForegroundColor Blue
Write-Host "  NETRA COMPLETE STAGING DEPLOYMENT (WINDOWS)  " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$STAGING_API_URL = "https://api.staging.netrasystems.ai"
$STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"
$PROJECT_ID = "netra-staging"
$REGION = "us-central1"
$ZONE = "us-central1-a"
$ENVIRONMENT = "staging"

Write-Info "Staging Configuration:"
Write-Info "  Project ID: $PROJECT_ID"
Write-Info "  Region: $REGION"
Write-Info "  Environment: $ENVIRONMENT"
Write-Info "  API URL: $STAGING_API_URL"
Write-Info "  WebSocket URL: $STAGING_WS_URL"
Write-Host ""

# Step 1: Check prerequisites
Write-Status "Checking prerequisites..."

$commands = @("gcloud", "terraform", "docker")
foreach ($cmd in $commands) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error-Message "$cmd not found in PATH"
        exit 1
    }
}

# Step 2: Set GCP project
Write-Status "Setting GCP project to: $PROJECT_ID"
& gcloud config set project $PROJECT_ID

# Step 3: Configure Docker for Artifact Registry
Write-Status "Configuring Docker for Artifact Registry..."
& gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# Step 4: Build and push backend image
Write-Status "Building backend Docker image..."
Push-Location ..
try {
    & docker build -f Dockerfile.backend `
        -t "$REGION-docker.pkg.dev/$PROJECT_ID/netra-containers/backend:latest" .
    
    Write-Status "Pushing backend image..."
    & docker push "$REGION-docker.pkg.dev/$PROJECT_ID/netra-containers/backend:latest"
}
finally {
    Pop-Location
}

# Step 5: Build and push frontend image with staging API URLs
Write-Status "Building frontend Docker image with staging API configuration..."
Push-Location ..
try {
    & docker build -f Dockerfile.frontend.staging `
        --build-arg "NEXT_PUBLIC_API_URL=$STAGING_API_URL" `
        --build-arg "NEXT_PUBLIC_WS_URL=$STAGING_WS_URL" `
        -t "$REGION-docker.pkg.dev/$PROJECT_ID/netra-containers/frontend:latest" .
    
    Write-Status "Pushing frontend image..."
    & docker push "$REGION-docker.pkg.dev/$PROJECT_ID/netra-containers/frontend:latest"
}
finally {
    Pop-Location
}

# Step 6: Initialize Terraform
Write-Status "Initializing Terraform..."
$STAGING_STATE_BUCKET = "$PROJECT_ID-terraform-state"

# Check if state bucket exists
$bucketExists = & gsutil ls -b "gs://$STAGING_STATE_BUCKET" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Status "Creating Terraform state bucket: $STAGING_STATE_BUCKET"
    & gsutil mb -p $PROJECT_ID -l $REGION "gs://$STAGING_STATE_BUCKET"
    & gsutil versioning set on "gs://$STAGING_STATE_BUCKET"
}

& terraform init `
    -backend-config="bucket=$STAGING_STATE_BUCKET" `
    -backend-config="prefix=staging" `
    -reconfigure

# Step 7: Select workspace
Write-Status "Setting Terraform workspace to staging..."
$workspaceList = & terraform workspace list 2>$null
if ($workspaceList -match "staging") {
    & terraform workspace select staging
} else {
    & terraform workspace new staging
}

# Step 8: Plan deployment
Write-Status "Planning staging deployment..."
& terraform plan -var-file="terraform.staging.tfvars" -out="staging.tfplan"

# Step 9: Apply deployment
Write-Status "Applying Terraform configuration..."
& terraform apply "staging.tfplan"

# Step 10: Deploy services to Cloud Run
Write-Status "Deploying services to Cloud Run..."

$REGISTRY = "$REGION-docker.pkg.dev/$PROJECT_ID/netra-containers"

# Deploy backend
Write-Status "Deploying backend service..."
& gcloud run deploy netra-backend `
    --image "$REGISTRY/backend:latest" `
    --region $REGION `
    --platform managed `
    --port 8080 `
    --quiet

# Deploy frontend
Write-Status "Deploying frontend service..."
& gcloud run deploy netra-frontend `
    --image "$REGISTRY/frontend:latest" `
    --region $REGION `
    --platform managed `
    --port 3000 `
    --quiet

# Step 11: Get deployment URLs
Write-Status "Retrieving deployment information..."
Write-Host ""
Write-Host "=== STAGING Deployment Complete ===" -ForegroundColor Green
Write-Host ""

$BACKEND_URL = & gcloud run services describe netra-backend --region=$REGION --format='value(status.url)'
$FRONTEND_URL = & gcloud run services describe netra-frontend --region=$REGION --format='value(status.url)'

Write-Host "STAGING Environment URLs:" -ForegroundColor Blue
Write-Host "  Frontend: " -NoNewline
Write-Host $FRONTEND_URL -ForegroundColor Green
Write-Host "  Backend:  " -NoNewline
Write-Host $BACKEND_URL -ForegroundColor Green
Write-Host "  API Config: " -NoNewline
Write-Host $STAGING_API_URL -ForegroundColor Green
Write-Host ""

# Step 12: Verify deployment
Write-Status "Verifying deployment..."

# Check backend health
try {
    $response = Invoke-WebRequest -Uri "$BACKEND_URL/health" -Method Get -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Status "✓ Backend is healthy"
    }
} catch {
    Write-Warning-Message "Backend health check failed - service may still be starting"
}

# Check frontend
try {
    $response = Invoke-WebRequest -Uri $FRONTEND_URL -Method Get -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Status "✓ Frontend is accessible"
    }
} catch {
    Write-Warning-Message "Frontend check failed - service may still be starting"
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "   STAGING DEPLOYMENT COMPLETED SUCCESSFULLY   " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Info "Frontend configured to use: $STAGING_API_URL"
Write-Info "To destroy: terraform destroy -var-file=terraform.staging.tfvars"