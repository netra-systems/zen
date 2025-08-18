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

Write-Host '' -ForegroundColor Blue
Write-Host '' -ForegroundColor Blue
Write-Host '' -ForegroundColor Blue
Write-Host ''

# Configuration
$PROJECT_ID = ''
$REGION = ''
$ZONE = ''
$ENVIRONMENT = ''

# Service configurations
$BACKEND_SERVICE = ''
$FRONTEND_SERVICE = ''
$AUTH_SERVICE = ''
$REGISTRY_NAME = ''

Write-Host '' -ForegroundColor Yellow
Write-Host ''
Write-Host ''
Write-Host ''
Write-Host ''

# Step 1: Authenticate with Service Account
Write-Host '' -ForegroundColor Green

if (-not $ServiceAccountKeyPath) {
    # Check common locations for staging service account key
    $possiblePaths = @(
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $ServiceAccountKeyPath = $path
            Write-Host ''
            break
        }
    }
}

if (-not $ServiceAccountKeyPath -or -not (Test-Path $ServiceAccountKeyPath)) {
    Write-Host '' -ForegroundColor Red
    Write-Host '' -ForegroundColor Yellow
    exit 1
}

# Authenticate using service account
gcloud auth activate-service-account --key-file=$ServiceAccountKeyPath
if ($LASTEXITCODE -ne 0) {
    Write-Host '' -ForegroundColor Red
    exit 1
}

# Step 2: Set project
Write-Host '' -ForegroundColor Green
gcloud config set project $PROJECT_ID

# Step 3: Enable required APIs
Write-Host '' -ForegroundColor Green
$APIs = @(
    '',
    '',
    '',
    '',
    '',
    '',
    ''
)

foreach ($api in $APIs) {
    Write-Host ''
    gcloud services enable $api --project=$PROJECT_ID --quiet
}

# Step 4: Configure Docker for Artifact Registry
Write-Host '' -ForegroundColor Green
gcloud auth configure-docker '' --quiet

# Step 5: Pre-create resources if requested
if ($PreCreateResources) {
    Write-Host '' -ForegroundColor Green
    
    # Create Artifact Registry
    Write-Host ''
    gcloud artifacts repositories create $REGISTRY_NAME `
        --repository-format=docker `
        --location=$REGION `
        --project=$PROJECT_ID `
        --quiet 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ''
    } else {
        Write-Host ''
    }
    
    # Create secrets if they don't exist
    Write-Host ''
    $secrets = gcloud secrets list --project=$PROJECT_ID --format='' 2>$null
    
    if ($secrets -notcontains '') {
        Write-Host ''
        $JWT_SECRET = [System.Guid]::NewGuid().ToString() + [System.Guid]::NewGuid().ToString()
        echo $JWT_SECRET | gcloud secrets create jwt-secret --data-file=- --project=$PROJECT_ID
    }
    
    if ($secrets -notcontains '') {
        Write-Host ''
        $DB_URL = ''
        echo $DB_URL | gcloud secrets create auth-database-url --data-file=- --project=$PROJECT_ID
    }
} else {
    Write-Host '' -ForegroundColor Green
    gcloud artifacts repositories describe $REGISTRY_NAME `
        --location=$REGION `
        --project=$PROJECT_ID 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        gcloud artifacts repositories create $REGISTRY_NAME `
            --repository-format=docker `
            --location=$REGION `
            --project=$PROJECT_ID `
            --quiet
    } else {
        Write-Host ''
    }
}

# Step 6: Build and push Docker images
Write-Host '' -ForegroundColor Green

# Backend
Write-Host ''
docker build -f Dockerfile.backend `
    -t '' `
    -t '' .

if ($LASTEXITCODE -ne 0) {
    Write-Host '' -ForegroundColor Red
    exit 1
}

# Frontend
Write-Host ''
$STAGING_API_URL = ''
$STAGING_WS_URL = ''

# Check if staging-specific Dockerfile exists
if (Test-Path '') {
    docker build -f Dockerfile.frontend.staging `
        --build-arg NEXT_PUBLIC_API_URL=$STAGING_API_URL `
        --build-arg NEXT_PUBLIC_WS_URL=$STAGING_WS_URL `
        -t '' `
        -t '' .
} else {
    docker build -f Dockerfile.frontend `
        --build-arg NEXT_PUBLIC_API_URL=$STAGING_API_URL `
        --build-arg NEXT_PUBLIC_WS_URL=$STAGING_WS_URL `
        -t '' `
        -t '' .
}

if ($LASTEXITCODE -ne 0) {
    Write-Host '' -ForegroundColor Red
    exit 1
}

# Auth Service
Write-Host ''
if (Test-Path '') {
    docker build -f Dockerfile.auth `
        -t '' `
        -t '' .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host '' -ForegroundColor Red
        exit 1
    }
}

# Step 7: Push images to Artifact Registry
Write-Host '' -ForegroundColor Green

Write-Host ''
docker push ''
docker push ''

Write-Host ''
docker push ''
docker push ''

if (Test-Path '') {
    Write-Host ''
    docker push ''
    docker push ''
}

# Step 8: Deploy services to Cloud Run
Write-Host '' -ForegroundColor Green

# Deploy Backend
Write-Host ''
gcloud run deploy $BACKEND_SERVICE `
    --image '' `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --port 8080 `
    --memory 1Gi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars='' `
    --quiet

# Deploy Frontend
Write-Host ''
gcloud run deploy $FRONTEND_SERVICE `
    --image '' `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --allow-unauthenticated `
    --port 3000 `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars='' `
    --quiet

# Deploy Auth Service if image exists
if (Test-Path '') {
    Write-Host ''
    
    # Ensure secrets exist
    $secrets = gcloud secrets list --project=$PROJECT_ID --format='' 2>$null
    
    if ($secrets -notcontains '') {
        Write-Host ''
        $JWT_SECRET = [System.Guid]::NewGuid().ToString() + [System.Guid]::NewGuid().ToString()
        echo $JWT_SECRET | gcloud secrets create jwt-secret --data-file=- --project=$PROJECT_ID
    }
    
    if ($secrets -notcontains '') {
        Write-Host ''
        $DB_URL = ''
        echo $DB_URL | gcloud secrets create auth-database-url --data-file=- --project=$PROJECT_ID
    }
    
    gcloud run deploy $AUTH_SERVICE `
        --image '' `
        --platform managed `
        --region $REGION `
        --project $PROJECT_ID `
        --allow-unauthenticated `
        --port 8080 `
        --memory 512Mi `
        --cpu 1 `
        --min-instances 0 `
        --max-instances 10 `
        --set-secrets='' `
        --set-env-vars='' `
        --quiet
}

# Step 9: Get service URLs
Write-Host '' -ForegroundColor Green

$BACKEND_URL = gcloud run services describe $BACKEND_SERVICE `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --format ''

$FRONTEND_URL = gcloud run services describe $FRONTEND_SERVICE `
    --platform managed `
    --region $REGION `
    --project $PROJECT_ID `
    --format ''

$AUTH_URL = ''
if (Test-Path '') {
    $AUTH_URL = gcloud run services describe $AUTH_SERVICE `
        --platform managed `
        --region $REGION `
        --project $PROJECT_ID `
        --format ''
}

# Step 10: Health checks
if (-not $SkipHealthChecks) {
    Write-Host '' -ForegroundColor Green
    
    Start-Sleep -Seconds 10  # Give services time to start
    
    # Backend health check
    try {
        $response = Invoke-WebRequest -Uri '' -Method Get -TimeoutSec 30
        if ($response.StatusCode -eq 200) {
            Write-Host '' -ForegroundColor Green
        }
    } catch {
        Write-Host '' -ForegroundColor Red
        exit 1
    }
    
    # Frontend check
    try {
        $response = Invoke-WebRequest -Uri $FRONTEND_URL -Method Get -TimeoutSec 30
        if ($response.StatusCode -eq 200) {
            Write-Host '' -ForegroundColor Green
        }
    } catch {
        Write-Host '' -ForegroundColor Red
        exit 1
    }
    
    # Auth service check
    if ($AUTH_URL) {
        try {
            $response = Invoke-WebRequest -Uri '' -Method Get -TimeoutSec 30
            if ($response.StatusCode -eq 200) {
                Write-Host '' -ForegroundColor Green
            }
        } catch {
            Write-Host '' -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host '' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '' -ForegroundColor Green
Write-Host '' -ForegroundColor Green
Write-Host '' -ForegroundColor Green
Write-Host ''
Write-Host '' -ForegroundColor Cyan
Write-Host '' -ForegroundColor Green
Write-Host '' -ForegroundColor Green
if ($AUTH_URL) {
    Write-Host '' -ForegroundColor Green
}
Write-Host ''

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
