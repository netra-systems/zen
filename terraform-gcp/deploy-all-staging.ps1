# deploy-all-staging.ps1 - Complete deployment of auth, backend, and frontend to GCP staging
# Windows PowerShell deployment script

param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectId = "netra-staging",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$false)]
    [string]$Zone = "us-central1-a",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "staging",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipDockerBuild,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTerraform,
    
    [Parameter(Mandatory=$false)]
    [switch]$ForceRecreate
)

# Exit on any error
$ErrorActionPreference = "Stop"

# Configuration
$REGISTRY = "$Region-docker.pkg.dev/$ProjectId/netra-containers"
$STAGING_API_URL = "https://api.staging.netrasystems.ai"
$STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"
$AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"
$STATE_BUCKET = "$ProjectId-terraform-state"

# Color functions
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

function Write-Success {
    param($Message)
    Write-Host "✓" -ForegroundColor Green -NoNewline
    Write-Host " $Message"
}

# Banner
Clear-Host
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   NETRA APEX - COMPLETE STAGING DEPLOYMENT (WINDOWS)      " -ForegroundColor Cyan
Write-Host "   Auth Service | Backend | Frontend                       " -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Display configuration
Write-Info "Deployment Configuration:"
Write-Host "  Project ID:    $ProjectId" -ForegroundColor White
Write-Host "  Region:        $Region" -ForegroundColor White
Write-Host "  Zone:          $Zone" -ForegroundColor White
Write-Host "  Environment:   $Environment" -ForegroundColor White
Write-Host "  Registry:      $REGISTRY" -ForegroundColor White
Write-Host "  API URL:       $STAGING_API_URL" -ForegroundColor White
Write-Host "  Auth URL:      $AUTH_SERVICE_URL" -ForegroundColor White
Write-Host ""

# Step 1: Check prerequisites
Write-Status "Checking prerequisites..."
$requiredCommands = @("gcloud", "terraform", "docker")
$missingCommands = @()

foreach ($cmd in $requiredCommands) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        $missingCommands += $cmd
    }
}

if ($missingCommands.Count -gt 0) {
    Write-Error-Message "Missing required commands: $($missingCommands -join ', ')"
    Write-Host "Please install the missing tools and try again." -ForegroundColor Red
    exit 1
}
Write-Success "All prerequisites installed"

# Step 2: Set GCP project and configure authentication
Write-Status "Configuring GCP project: $ProjectId"
& gcloud config set project $ProjectId 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error-Message "Failed to set GCP project. Please check project ID."
    exit 1
}

# Verify authentication
$account = & gcloud config get-value account 2>$null
if ([string]::IsNullOrEmpty($account)) {
    Write-Warning-Message "Not authenticated. Running gcloud auth login..."
    & gcloud auth login
}
Write-Success "GCP project configured"

# Step 3: Enable required APIs
Write-Status "Enabling required GCP APIs..."
$apis = @(
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com",
    "certificatemanager.googleapis.com",
    "sqladmin.googleapis.com",
    "servicenetworking.googleapis.com"
)

foreach ($api in $apis) {
    & gcloud services enable $api --quiet 2>$null
}
Write-Success "APIs enabled"

# Step 4: Configure Docker for Artifact Registry
Write-Status "Configuring Docker for Artifact Registry..."
& gcloud auth configure-docker "$Region-docker.pkg.dev" --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Error-Message "Failed to configure Docker"
    exit 1
}
Write-Success "Docker configured"

# Step 5: Create Artifact Registry repository if it doesn't exist
Write-Status "Checking Artifact Registry repository..."
$repoExists = & gcloud artifacts repositories describe netra-containers `
    --location=$Region --format="value(name)" 2>$null
    
if ([string]::IsNullOrEmpty($repoExists)) {
    Write-Status "Creating Artifact Registry repository..."
    & gcloud artifacts repositories create netra-containers `
        --repository-format=docker `
        --location=$Region `
        --description="Netra container images" `
        --quiet
    Write-Success "Repository created"
} else {
    Write-Success "Repository exists"
}

# Step 6: Build and push Docker images
if (-not $SkipDockerBuild) {
    Write-Host ""
    Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  Building and Pushing Docker Images" -ForegroundColor Yellow
    Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray
    
    Push-Location ..
    try {
        # Build Auth Service
        Write-Status "Building Auth Service image..."
        & docker build -f Dockerfile.auth `
            -t "$REGISTRY/auth-service:latest" `
            -t "$REGISTRY/auth-service:$Environment" .
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Message "Auth Service build failed"
            exit 1
        }
        Write-Success "Auth Service built"
        
        Write-Status "Pushing Auth Service image..."
        & docker push "$REGISTRY/auth-service:latest"
        & docker push "$REGISTRY/auth-service:$Environment"
        Write-Success "Auth Service pushed"
        
        # Build Backend
        Write-Status "Building Backend image..."
        & docker build -f Dockerfile.backend `
            -t "$REGISTRY/backend:latest" `
            -t "$REGISTRY/backend:$Environment" .
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Message "Backend build failed"
            exit 1
        }
        Write-Success "Backend built"
        
        Write-Status "Pushing Backend image..."
        & docker push "$REGISTRY/backend:latest"
        & docker push "$REGISTRY/backend:$Environment"
        Write-Success "Backend pushed"
        
        # Build Frontend with staging configuration
        Write-Status "Building Frontend image with staging configuration..."
        & docker build -f Dockerfile.frontend.staging `
            --build-arg "NEXT_PUBLIC_API_URL=$STAGING_API_URL" `
            --build-arg "NEXT_PUBLIC_WS_URL=$STAGING_WS_URL" `
            --build-arg "NEXT_PUBLIC_AUTH_URL=$AUTH_SERVICE_URL" `
            -t "$REGISTRY/frontend:latest" `
            -t "$REGISTRY/frontend:$Environment" .
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Message "Frontend build failed"
            exit 1
        }
        Write-Success "Frontend built"
        
        Write-Status "Pushing Frontend image..."
        & docker push "$REGISTRY/frontend:latest"
        & docker push "$REGISTRY/frontend:$Environment"
        Write-Success "Frontend pushed"
    }
    finally {
        Pop-Location
    }
} else {
    Write-Warning-Message "Skipping Docker builds (using existing images)"
}

# Step 7: Deploy with Terraform
if (-not $SkipTerraform) {
    Write-Host ""
    Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  Deploying Infrastructure with Terraform" -ForegroundColor Yellow
    Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray
    
    # Check if state bucket exists
    Write-Status "Checking Terraform state bucket..."
    $bucketExists = & gsutil ls -b "gs://$STATE_BUCKET" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Creating Terraform state bucket: $STATE_BUCKET"
        & gsutil mb -p $ProjectId -l $Region "gs://$STATE_BUCKET"
        & gsutil versioning set on "gs://$STATE_BUCKET"
        Write-Success "State bucket created"
    } else {
        Write-Success "State bucket exists"
    }
    
    # Initialize Terraform
    Write-Status "Initializing Terraform..."
    & terraform init `
        -backend-config="bucket=$STATE_BUCKET" `
        -backend-config="prefix=staging" `
        -reconfigure
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Terraform init failed"
        exit 1
    }
    Write-Success "Terraform initialized"
    
    # Select or create workspace
    Write-Status "Setting Terraform workspace to staging..."
    $workspaceList = & terraform workspace list 2>$null
    if ($workspaceList -match "staging") {
        & terraform workspace select staging
    } else {
        & terraform workspace new staging
    }
    Write-Success "Workspace set to staging"
    
    # Plan deployment
    Write-Status "Planning Terraform deployment..."
    & terraform plan -var-file="terraform.staging.tfvars" -out="staging-complete.tfplan"
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Terraform plan failed"
        exit 1
    }
    
    # Apply deployment
    Write-Status "Applying Terraform configuration..."
    & terraform apply "staging-complete.tfplan"
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Terraform apply failed"
        exit 1
    }
    Write-Success "Infrastructure deployed"
} else {
    Write-Warning-Message "Skipping Terraform deployment"
}

# Step 8: Deploy services to Cloud Run
Write-Host ""
Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Deploying Services to Cloud Run" -ForegroundColor Yellow
Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray

# Deploy Auth Service
Write-Status "Deploying Auth Service to Cloud Run..."
$authDeployCmd = @(
    "run", "deploy", "netra-auth",
    "--image", "$REGISTRY/auth-service:latest",
    "--region", $Region,
    "--platform", "managed",
    "--port", "8080",
    "--allow-unauthenticated",
    "--service-account", "auth-service@$ProjectId.iam.gserviceaccount.com",
    "--set-env-vars", "ENVIRONMENT=$Environment",
    "--set-env-vars", "PROJECT_ID=$ProjectId",
    "--set-env-vars", "REGION=$Region",
    "--cpu", "1",
    "--memory", "512Mi",
    "--min-instances", "1",
    "--max-instances", "10",
    "--quiet"
)

if ($ForceRecreate) {
    $authDeployCmd += "--force-override"
}

& gcloud @authDeployCmd
if ($LASTEXITCODE -ne 0) {
    Write-Error-Message "Auth Service deployment failed"
    exit 1
}
Write-Success "Auth Service deployed"

# Deploy Backend
Write-Status "Deploying Backend to Cloud Run..."
$backendDeployCmd = @(
    "run", "deploy", "netra-backend",
    "--image", "$REGISTRY/backend:latest",
    "--region", $Region,
    "--platform", "managed",
    "--port", "8080",
    "--allow-unauthenticated",
    "--service-account", "backend-service@$ProjectId.iam.gserviceaccount.com",
    "--set-env-vars", "ENVIRONMENT=$Environment",
    "--set-env-vars", "PROJECT_ID=$ProjectId",
    "--set-env-vars", "REGION=$Region",
    "--set-env-vars", "AUTH_SERVICE_URL=$AUTH_SERVICE_URL",
    "--cpu", "2",
    "--memory", "2Gi",
    "--min-instances", "1",
    "--max-instances", "20",
    "--quiet"
)

if ($ForceRecreate) {
    $backendDeployCmd += "--force-override"
}

& gcloud @backendDeployCmd
if ($LASTEXITCODE -ne 0) {
    Write-Error-Message "Backend deployment failed"
    exit 1
}
Write-Success "Backend deployed"

# Deploy Frontend
Write-Status "Deploying Frontend to Cloud Run..."
$frontendDeployCmd = @(
    "run", "deploy", "netra-frontend",
    "--image", "$REGISTRY/frontend:latest",
    "--region", $Region,
    "--platform", "managed",
    "--port", "3000",
    "--allow-unauthenticated",
    "--cpu", "1",
    "--memory", "512Mi",
    "--min-instances", "1",
    "--max-instances", "10",
    "--quiet"
)

if ($ForceRecreate) {
    $frontendDeployCmd += "--force-override"
}

& gcloud @frontendDeployCmd
if ($LASTEXITCODE -ne 0) {
    Write-Error-Message "Frontend deployment failed"
    exit 1
}
Write-Success "Frontend deployed"

# Step 9: Get deployment URLs
Write-Host ""
Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Retrieving Deployment Information" -ForegroundColor Yellow
Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray

$AUTH_URL = & gcloud run services describe netra-auth --region=$Region --format='value(status.url)'
$BACKEND_URL = & gcloud run services describe netra-backend --region=$Region --format='value(status.url)'
$FRONTEND_URL = & gcloud run services describe netra-frontend --region=$Region --format='value(status.url)'

# Step 10: Verify deployments
Write-Host ""
Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Verifying Deployments" -ForegroundColor Yellow
Write-Host "──────────────────────────────────────────────" -ForegroundColor DarkGray

# Check Auth Service
try {
    $response = Invoke-WebRequest -Uri "$AUTH_URL/health" -Method Get -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Success "Auth Service is healthy"
    }
} catch {
    Write-Warning-Message "Auth Service health check failed - service may still be starting"
}

# Check Backend
try {
    $response = Invoke-WebRequest -Uri "$BACKEND_URL/health" -Method Get -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Success "Backend is healthy"
    }
} catch {
    Write-Warning-Message "Backend health check failed - service may still be starting"
}

# Check Frontend
try {
    $response = Invoke-WebRequest -Uri $FRONTEND_URL -Method Get -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Success "Frontend is accessible"
    }
} catch {
    Write-Warning-Message "Frontend check failed - service may still be starting"
}

# Step 11: Save deployment information
$deploymentInfo = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    environment = $Environment
    project_id = $ProjectId
    region = $Region
    urls = @{
        auth = $AUTH_URL
        backend = $BACKEND_URL
        frontend = $FRONTEND_URL
        api_configured = $STAGING_API_URL
        auth_configured = $AUTH_SERVICE_URL
    }
    images = @{
        auth = "$REGISTRY/auth-service:latest"
        backend = "$REGISTRY/backend:latest"
        frontend = "$REGISTRY/frontend:latest"
    }
}

$deploymentInfo | ConvertTo-Json -Depth 3 | Out-File -FilePath "deployment-info-staging.json"
Write-Success "Deployment information saved to deployment-info-staging.json"

# Display summary
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "   STAGING DEPLOYMENT COMPLETED SUCCESSFULLY               " -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "  Auth Service:  " -NoNewline
Write-Host $AUTH_URL -ForegroundColor Green
Write-Host "  Backend:       " -NoNewline
Write-Host $BACKEND_URL -ForegroundColor Green
Write-Host "  Frontend:      " -NoNewline
Write-Host $FRONTEND_URL -ForegroundColor Green
Write-Host ""
Write-Host "Configured URLs:" -ForegroundColor Cyan
Write-Host "  API URL:       " -NoNewline
Write-Host $STAGING_API_URL -ForegroundColor Yellow
Write-Host "  Auth URL:      " -NoNewline
Write-Host $AUTH_SERVICE_URL -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Update DNS records if using custom domains"
Write-Host "2. Configure OAuth redirect URIs in Google Cloud Console:"
Write-Host "   - $AUTH_URL/api/auth/callback"
Write-Host "   - $AUTH_SERVICE_URL/api/auth/callback"
Write-Host "3. Test the deployment:"
Write-Host "   - Frontend: $FRONTEND_URL"
Write-Host "   - Auth: $AUTH_URL/health"
Write-Host "   - Backend: $BACKEND_URL/health"
Write-Host ""
Write-Host "To destroy this deployment:" -ForegroundColor Yellow
Write-Host "  terraform destroy -var-file=terraform.staging.tfvars"
Write-Host ""
Write-Host "Deployment completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray