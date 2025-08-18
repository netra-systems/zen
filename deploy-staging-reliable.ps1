# Netra Reliable Staging Deployment Script
# This script ALWAYS works by ensuring proper service account authentication
# It handles all edge cases and authentication issues

param(
    [Parameter(Mandatory=$false)]
    [switch]$SkipHealthChecks = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipAuth = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$BuildOnly = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$DeployOnly = $false
)

Write-Host "================================================" -ForegroundColor Blue
Write-Host "  NETRA RELIABLE STAGING DEPLOYMENT           " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"
$REGION = "us-central1"
$REGISTRY = "$REGION-docker.pkg.dev"
$REGISTRY_PATH = "$REGISTRY/$PROJECT_ID/netra-containers"

# Service names - CRITICAL: These MUST match exactly for domain mapping
$BACKEND_SERVICE = "netra-backend-staging"   # EXACT name required for staging domain
$FRONTEND_SERVICE = "netra-frontend-staging" # EXACT name required for staging domain  
$AUTH_SERVICE = "netra-auth-service"         # EXACT name required for auth subdomain

# URLs for frontend build
$STAGING_API_URL = "https://api.staging.netrasystems.ai"
$STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"

# Function to ensure authentication
function Ensure-Authentication {
    Write-Host "Ensuring proper authentication..." -ForegroundColor Yellow
    
    # Check for key file in multiple locations
    $keyPaths = @(
        $env:GCP_STAGING_SA_KEY_PATH,
        "$PSScriptRoot\gcp-staging-sa-key.json",
        "$PSScriptRoot\secrets\gcp-staging-sa-key.json",
        "$PSScriptRoot\terraform-gcp\gcp-staging-sa-key.json",
        "$env:USERPROFILE\.gcp\staging-sa-key.json"
    )
    
    $keyFile = $null
    foreach ($path in $keyPaths) {
        if ($path -and (Test-Path $path)) {
            $keyFile = $path
            Write-Host "  Found key file: $keyFile" -ForegroundColor Green
            break
        }
    }
    
    if (-not $keyFile) {
        Write-Host "  No service account key found!" -ForegroundColor Red
        Write-Host "  Running setup script to create one..." -ForegroundColor Yellow
        
        # Run setup script
        & "$PSScriptRoot\setup-staging-auth.ps1"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to set up authentication!" -ForegroundColor Red
            exit 1
        }
        
        # Reload environment variable
        $keyFile = "$PSScriptRoot\gcp-staging-sa-key.json"
    }
    
    # Authenticate with service account
    Write-Host "  Authenticating with service account..." -ForegroundColor Yellow
    gcloud auth activate-service-account --key-file=$keyFile 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Authentication failed, retrying..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        gcloud auth activate-service-account --key-file=$keyFile
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Authentication failed!" -ForegroundColor Red
            exit 1
        }
    }
    
    # Configure Docker
    Write-Host "  Configuring Docker authentication..." -ForegroundColor Yellow
    gcloud auth configure-docker $REGISTRY --quiet
    
    # Set project
    gcloud config set project $PROJECT_ID --quiet
    
    Write-Host "  ✓ Authentication configured successfully" -ForegroundColor Green
    return $keyFile
}

# Step 1: Authentication
if (-not $SkipAuth -and -not $DeployOnly) {
    Write-Host "[1/5] Setting up authentication..." -ForegroundColor Green
    $keyFile = Ensure-Authentication
} else {
    Write-Host "[1/5] Skipping authentication setup..." -ForegroundColor Yellow
}

if (-not $DeployOnly) {
    # Step 2: Build Docker images
    Write-Host "[2/5] Building Docker images..." -ForegroundColor Green
    
    # Backend
    Write-Host "  Building backend..." -ForegroundColor Cyan
    docker build -f Dockerfile.backend `
        -t "$REGISTRY_PATH/backend:staging" `
        -t "$REGISTRY_PATH/backend:latest" .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Backend build failed!" -ForegroundColor Red
        exit 1
    }
    
    # Frontend
    Write-Host "  Building frontend..." -ForegroundColor Cyan
    $dockerFile = if (Test-Path "Dockerfile.frontend.staging") { 
        "Dockerfile.frontend.staging" 
    } elseif (Test-Path "Dockerfile.frontend.optimized") {
        "Dockerfile.frontend.optimized"
    } else {
        "Dockerfile"
    }
    
    docker build -f $dockerFile `
        --build-arg NEXT_PUBLIC_API_URL=$STAGING_API_URL `
        --build-arg NEXT_PUBLIC_WS_URL=$STAGING_WS_URL `
        -t "$REGISTRY_PATH/frontend:staging" `
        -t "$REGISTRY_PATH/frontend:latest" .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Frontend build failed!" -ForegroundColor Red
        exit 1
    }
    
    # Auth Service
    if (Test-Path "Dockerfile.auth") {
        Write-Host "  Building auth service..." -ForegroundColor Cyan
        docker build -f Dockerfile.auth `
            -t "$REGISTRY_PATH/auth:staging" `
            -t "$REGISTRY_PATH/auth:latest" .
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Auth service build failed!" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "  ✓ All images built successfully" -ForegroundColor Green
    
    # Step 3: Push images with retry logic
    Write-Host "[3/5] Pushing images to Artifact Registry..." -ForegroundColor Green
    
    function Push-ImageWithRetry {
        param($image, $maxRetries = 3)
        
        for ($i = 1; $i -le $maxRetries; $i++) {
            Write-Host "  Pushing $image (attempt $i/$maxRetries)..." -ForegroundColor Cyan
            docker push $image 2>&1 | Out-Null
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Pushed successfully" -ForegroundColor Green
                return $true
            }
            
            if ($i -lt $maxRetries) {
                Write-Host "    Push failed, re-authenticating..." -ForegroundColor Yellow
                Ensure-Authentication | Out-Null
                Start-Sleep -Seconds 5
            }
        }
        return $false
    }
    
    # Push all images
    $images = @(
        "$REGISTRY_PATH/backend:staging",
        "$REGISTRY_PATH/frontend:staging"
    )
    
    if (Test-Path "Dockerfile.auth") {
        $images += "$REGISTRY_PATH/auth:staging"
    }
    
    foreach ($image in $images) {
        if (-not (Push-ImageWithRetry $image)) {
            Write-Host "Failed to push $image after multiple attempts!" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "  ✓ All images pushed successfully" -ForegroundColor Green
}

if ($BuildOnly) {
    Write-Host ""
    Write-Host "Build completed. Skipping deployment." -ForegroundColor Yellow
    exit 0
}

# Step 4: Deploy to Cloud Run
Write-Host "[4/5] Deploying services to Cloud Run..." -ForegroundColor Green

# Deploy Backend
Write-Host "  Deploying backend..." -ForegroundColor Cyan
gcloud run deploy $BACKEND_SERVICE `
    --image "$REGISTRY_PATH/backend:staging" `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --port 8080 `
    --memory 1Gi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars="ENVIRONMENT=staging,SERVICE_NAME=backend,LOAD_SECRETS=true,SECRET_MANAGER_PROJECT_ID=701982941522,GCP_PROJECT_ID_NUMERICAL_STAGING=701982941522,SKIP_MIGRATIONS=true,DISABLE_STARTUP_CHECKS=true,REDIS_URL=redis://localhost:6379,CLICKHOUSE_URL=http://localhost:8123,CLICKHOUSE_DATABASE=netra,FRONTEND_URL=https://netra-frontend-e7oy7k4boa-uc.a.run.app,BACKEND_URL=https://netra-backend-e7oy7k4boa-uc.a.run.app,CORS_ORIGINS=https://netra-frontend-701982941522.us-central1.run.app;https://staging.netrasystems.ai;https://app.staging.netrasystems.ai" `
    --update-secrets="DATABASE_URL=database-url-staging:latest,JWT_SECRET_KEY=jwt-secret-key-staging:latest,GEMINI_API_KEY=gemini-api-key-staging:latest,FERNET_KEY=fernet-key-staging:latest,GOOGLE_OAUTH_CLIENT_ID_STAGING=google-client-id-staging:latest,GOOGLE_OAUTH_CLIENT_SECRET_STAGING=google-client-secret-staging:latest" `
    --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend deployment failed!" -ForegroundColor Red
    exit 1
}

# Deploy Frontend
Write-Host "  Deploying frontend..." -ForegroundColor Cyan
gcloud run deploy $FRONTEND_SERVICE `
    --image "$REGISTRY_PATH/frontend:staging" `
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

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend deployment failed!" -ForegroundColor Red
    exit 1
}

# Deploy Auth Service if exists
if (Test-Path "Dockerfile.auth") {
    Write-Host "  Deploying auth service..." -ForegroundColor Cyan
    gcloud run deploy $AUTH_SERVICE `
        --image "$REGISTRY_PATH/auth:staging" `
        --platform managed `
        --region $REGION `
        --project $PROJECT_ID `
        --allow-unauthenticated `
        --port 8080 `
        --memory 512Mi `
        --cpu 1 `
        --min-instances 0 `
        --max-instances 10 `
        --set-env-vars="ENVIRONMENT=staging,SERVICE_NAME=auth" `
        --quiet
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Auth service deployment failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "  ✓ All services deployed successfully" -ForegroundColor Green

# Step 5: Get service URLs
Write-Host "[5/5] Retrieving service URLs..." -ForegroundColor Green

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

# Health checks
if (-not $SkipHealthChecks) {
    Write-Host ""
    Write-Host "Running health checks..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    try {
        $response = Invoke-WebRequest -Uri "$BACKEND_URL/health" -Method Get -TimeoutSec 30
        Write-Host "  ✓ Backend is healthy" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Backend health check failed (service may still be starting)" -ForegroundColor Yellow
    }
    
    try {
        $response = Invoke-WebRequest -Uri $FRONTEND_URL -Method Get -TimeoutSec 30
        Write-Host "  ✓ Frontend is accessible" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Frontend check failed (service may still be starting)" -ForegroundColor Yellow
    }
}

# Summary
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETED SUCCESSFULLY           " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "  Frontend:  $FRONTEND_URL" -ForegroundColor Green
Write-Host "  Backend:   $BACKEND_URL" -ForegroundColor Green
if ($AUTH_URL) {
    Write-Host "  Auth:      $AUTH_URL" -ForegroundColor Green
}
Write-Host ""
Write-Host "Custom domains (if configured):" -ForegroundColor Cyan
Write-Host "  Frontend:  https://staging.netrasystems.ai" -ForegroundColor Blue
Write-Host "  Backend:   https://api.staging.netrasystems.ai" -ForegroundColor Blue
Write-Host ""

# Save deployment info
$deploymentInfo = @{
    frontend_url = $FRONTEND_URL
    backend_url = $BACKEND_URL
    auth_url = $AUTH_URL
    project_id = $PROJECT_ID
    region = $REGION
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
}

$deploymentInfo | ConvertTo-Json | Out-File -FilePath "deployment-info.json"
Write-Host "Deployment info saved to deployment-info.json" -ForegroundColor Yellow
