# Automated Deploy Script for GCP Staging with Service Account Auth
# PowerShell script for CI/CD deployment

param(
    [Parameter(Mandatory=$false)]
    [string]$ServiceAccountKeyPath = $env:GCP_STAGING_SA_KEY_PATH,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipHealthChecks = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$PreCreateResources = $false
)

# Fall back to general key path if staging-specific not set
if (-not $ServiceAccountKeyPath) {
    $ServiceAccountKeyPath = $env:GCP_SA_KEY_PATH
}

Write-Host "================================================" -ForegroundColor Blue
Write-Host "  NETRA STAGING DEPLOYMENT - AUTOMATED        " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"
$REGION = "us-central1"
$ZONE = "us-central1-a"
$ENVIRONMENT = "staging"

# Service configurations
$BACKEND_SERVICE = "netra-backend"
$FRONTEND_SERVICE = "netra-frontend"
$AUTH_SERVICE = "netra-auth-service"
$REGISTRY_NAME = "netra-containers"

Write-Host "Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  Project: $PROJECT_ID"
Write-Host "  Region: $REGION"
Write-Host "  Environment: $ENVIRONMENT"
Write-Host ""

# Step 1: Authenticate with Service Account
Write-Host "[1/10] Authenticating with GCP Service Account..." -ForegroundColor Green

if (-not $ServiceAccountKeyPath) {
    # Check common locations for staging service account key
    $possiblePaths = @(
        ".\gcp-staging-sa-key.json",
        ".\secrets\gcp-staging-sa-key.json",
        ".\terraform-gcp\gcp-staging-sa-key.json",
        "$env:USERPROFILE\.gcp\staging-sa-key.json",
        ".\gcp-sa-key.json",
        ".\terraform-gcp\gcp-sa-key.json",
        ".\secrets\gcp-sa-key.json"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $ServiceAccountKeyPath = $path
            Write-Host "  Found service account key at: $path"
            break
        }
    }
}

if (-not $ServiceAccountKeyPath -or -not (Test-Path $ServiceAccountKeyPath)) {
    Write-Host "Service account key file not found!" -ForegroundColor Red
    Write-Host "Please provide path via -ServiceAccountKeyPath parameter or GCP_SA_KEY_PATH env var" -ForegroundColor Yellow
    exit 1
}

# Authenticate using service account
gcloud auth activate-service-account --key-file=$ServiceAccountKeyPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "Service account authentication failed!" -ForegroundColor Red
    exit 1
}

# Step 2: Set project
Write-Host "[2/10] Setting GCP project..." -ForegroundColor Green
gcloud config set project $PROJECT_ID

# Step 3: Enable required APIs
Write-Host "[3/10] Enabling required GCP APIs..." -ForegroundColor Green
$APIs = @(
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com"
)

foreach ($api in $APIs) {
    Write-Host "  Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID --quiet
}

# Step 4: Configure Docker for Artifact Registry
Write-Host "[4/10] Configuring Docker for Artifact Registry..." -ForegroundColor Green
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# Step 5: Pre-create resources if requested
if ($PreCreateResources) {
    Write-Host "[5/10] Pre-creating GCP resources..." -ForegroundColor Green
    
    # Create Artifact Registry
    Write-Host "  Creating Artifact Registry..."
    gcloud artifacts repositories create $REGISTRY_NAME `
        --repository-format=docker `
        --location=$REGION `
        --project=$PROJECT_ID `
        --quiet 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    Created Artifact Registry: $REGISTRY_NAME"
    } else {
        Write-Host "    Artifact Registry already exists or error occurred"
    }
    
    # Create secrets if they don't exist
    Write-Host "  Checking/Creating secrets..."
    $secrets = gcloud secrets list --project=$PROJECT_ID --format="value(name)" 2>$null
    
    if ($secrets -notcontains "jwt-secret") {
        Write-Host "    Creating jwt-secret..."
        $JWT_SECRET = [System.Guid]::NewGuid().ToString() + [System.Guid]::NewGuid().ToString()
        echo $JWT_SECRET | gcloud secrets create jwt-secret --data-file=- --project=$PROJECT_ID
    }
    
    if ($secrets -notcontains "auth-database-url") {
        Write-Host "    Creating auth-database-url..."
        $DB_URL = "postgresql://user:pass@localhost:5432/auth_db"
        echo $DB_URL | gcloud secrets create auth-database-url --data-file=- --project=$PROJECT_ID
    }
} else {
    Write-Host "[5/10] Ensuring Artifact Registry exists..." -ForegroundColor Green
    gcloud artifacts repositories describe $REGISTRY_NAME `
        --location=$REGION `
        --project=$PROJECT_ID 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Creating Artifact Registry..."
        gcloud artifacts repositories create $REGISTRY_NAME `
            --repository-format=docker `
            --location=$REGION `
            --project=$PROJECT_ID `
            --quiet
    } else {
        Write-Host "  Artifact Registry already exists"
    }
}

# Step 6: Build and push Docker images
Write-Host "[6/10] Building Docker images..." -ForegroundColor Green

# Backend
Write-Host "  Building backend image..."
docker build -f Dockerfile.backend `
    -t "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/backend:latest" `
    -t "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/backend:staging" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend build failed!" -ForegroundColor Red
    exit 1
}

# Frontend
Write-Host "  Building frontend image..."
$STAGING_API_URL = "https://api.staging.netrasystems.ai"
$STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"

# Check if staging-specific Dockerfile exists
if (Test-Path "Dockerfile.frontend.staging") {
    docker build -f Dockerfile.frontend.staging `
        --build-arg NEXT_PUBLIC_API_URL=$STAGING_API_URL `
        --build-arg NEXT_PUBLIC_WS_URL=$STAGING_WS_URL `
        -t "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/frontend:latest" `
        -t "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/frontend:staging" .
} else {
    docker build -f Dockerfile.frontend `
        --build-arg NEXT_PUBLIC_API_URL=$STAGING_API_URL `
        --build-arg NEXT_PUBLIC_WS_URL=$STAGING_WS_URL `
        -t "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/frontend:latest" `
        -t "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/frontend:staging" .
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit 1
}

# Auth Service
Write-Host "  Building auth service image..."
if (Test-Path "Dockerfile.auth") {
    docker build -f Dockerfile.auth `
        -t "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/auth:latest" `
        -t "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/auth:staging" .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Auth service build failed!" -ForegroundColor Red
        exit 1
    }
}

# Step 7: Push images to Artifact Registry
Write-Host "[7/10] Pushing images to Artifact Registry..." -ForegroundColor Green

Write-Host "  Pushing backend..."
docker push "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/backend:latest"
docker push "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/backend:staging"

Write-Host "  Pushing frontend..."
docker push "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/frontend:latest"
docker push "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/frontend:staging"

if (Test-Path "Dockerfile.auth") {
    Write-Host "  Pushing auth service..."
    docker push "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/auth:latest"
    docker push "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/auth:staging"
}

# Step 8: Deploy services to Cloud Run
Write-Host "[8/10] Deploying services to Cloud Run..." -ForegroundColor Green

# Deploy Backend
Write-Host "  Deploying backend service..."
gcloud run deploy $BACKEND_SERVICE `
    --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/backend:staging" `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --port 8080 `
    --memory 1Gi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars="ENVIRONMENT=staging,SERVICE_NAME=backend,LOG_LEVEL=INFO" `
    --quiet

# Deploy Frontend
Write-Host "  Deploying frontend service..."
gcloud run deploy $FRONTEND_SERVICE `
    --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/frontend:staging" `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --port 3000 `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars="NODE_ENV=production,NEXT_PUBLIC_API_URL=$STAGING_API_URL,NEXT_PUBLIC_WS_URL=$STAGING_WS_URL" `
    --quiet

# Deploy Auth Service if image exists
if (Test-Path "Dockerfile.auth") {
    Write-Host "  Deploying auth service..."
    
    # Ensure secrets exist
    $secrets = gcloud secrets list --project=$PROJECT_ID --format="value(name)" 2>$null
    
    if ($secrets -notcontains "jwt-secret") {
        Write-Host "    Creating jwt-secret..."
        $JWT_SECRET = [System.Guid]::NewGuid().ToString() + [System.Guid]::NewGuid().ToString()
        echo $JWT_SECRET | gcloud secrets create jwt-secret --data-file=- --project=$PROJECT_ID
    }
    
    if ($secrets -notcontains "auth-database-url") {
        Write-Host "    Creating auth-database-url..."
        $DB_URL = "postgresql://user:pass@localhost:5432/auth_db"
        echo $DB_URL | gcloud secrets create auth-database-url --data-file=- --project=$PROJECT_ID
    }
    
    gcloud run deploy $AUTH_SERVICE `
        --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME/auth:staging" `
        --platform managed `
        --region $REGION `
        --project $PROJECT_ID `
        --allow-unauthenticated `
        --port 8080 `
        --memory 512Mi `
        --cpu 1 `
        --min-instances 0 `
        --max-instances 10 `
        --set-secrets="JWT_SECRET=jwt-secret:latest,DATABASE_URL=auth-database-url:latest" `
        --set-env-vars="ENVIRONMENT=staging,SERVICE_NAME=auth-service,LOG_LEVEL=INFO,CORS_ORIGINS=https://staging.netrasystems.ai" `
        --quiet
}

# Step 9: Get service URLs
Write-Host "[9/10] Retrieving service URLs..." -ForegroundColor Green

$BACKEND_URL = gcloud run services describe $BACKEND_SERVICE `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --format "value(status.url)"

$FRONTEND_URL = gcloud run services describe $FRONTEND_SERVICE `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --format "value(status.url)"

$AUTH_URL = ""
if (Test-Path "Dockerfile.auth") {
    $AUTH_URL = gcloud run services describe $AUTH_SERVICE `
        --platform managed `
        --region $REGION `
        --project $PROJECT_ID `
        --format "value(status.url)"
}

# Step 10: Health checks
if (-not $SkipHealthChecks) {
    Write-Host "[10/10] Running health checks..." -ForegroundColor Green
    
    Start-Sleep -Seconds 10  # Give services time to start
    
    # Backend health check
    try {
        $response = Invoke-WebRequest -Uri "$BACKEND_URL/health" -Method Get -TimeoutSec 30
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✓ Backend is healthy" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ✗ Backend health check failed: $_" -ForegroundColor Red
        exit 1
    }
    
    # Frontend check
    try {
        $response = Invoke-WebRequest -Uri $FRONTEND_URL -Method Get -TimeoutSec 30
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✓ Frontend is accessible" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ✗ Frontend check failed: $_" -ForegroundColor Red
        exit 1
    }
    
    # Auth service check
    if ($AUTH_URL) {
        try {
            $response = Invoke-WebRequest -Uri "$AUTH_URL/health" -Method Get -TimeoutSec 30
            if ($response.StatusCode -eq 200) {
                Write-Host "  ✓ Auth service is healthy" -ForegroundColor Green
            }
        } catch {
            Write-Host "  ✗ Auth service health check failed: $_" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "[10/10] Skipping health checks (SkipHealthChecks flag set)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "   STAGING DEPLOYMENT COMPLETED SUCCESSFULLY   " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "  Frontend: $FRONTEND_URL" -ForegroundColor Green
Write-Host "  Backend:  $BACKEND_URL" -ForegroundColor Green
if ($AUTH_URL) {
    Write-Host "  Auth:     $AUTH_URL" -ForegroundColor Green
}
Write-Host ""

# Output for CI/CD systems
$deploymentInfo = @{
    frontend_url = $FRONTEND_URL
    backend_url = $BACKEND_URL
    auth_url = $AUTH_URL
    project_id = $PROJECT_ID
    region = $REGION
    timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
}

$deploymentInfo | ConvertTo-Json | Out-File -FilePath 'deployment-info.json'
Write-Host 'Deployment info saved to deployment-info.json' -ForegroundColor Yellow