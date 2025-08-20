# Netra Reliable Staging Deployment Script
# This script aims for reliability by ensuring proper service account authentication,
# implementing robust error handling, and adhering to PowerShell best practices.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [switch]$SkipHealthChecks,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipAuth,
    
    [Parameter(Mandatory=$false)]
    [switch]$BuildOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$DeployOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipErrorMonitoring,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipMigrations
)

# Enforce strict coding standards and stop on PowerShell errors
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Blue
Write-Host "    NETRA RELIABLE STAGING DEPLOYMENT           " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"
$REGION = "us-central1"
$REGISTRY = "$REGION-docker.pkg.dev"
$REGISTRY_PATH = "$REGISTRY/$PROJECT_ID/netra-containers"
$BUILD_CONTEXT = "." # Assuming the script is run from the project root

# Service names (MUST match Cloud Run service names exactly)
$BACKEND_SERVICE = "netra-backend-staging"
$FRONTEND_SERVICE = "netra-frontend-staging"
$AUTH_SERVICE = "netra-auth-service"

# Determine if optional Auth Service exists (based on Dockerfile presence)
# We use $PSScriptRoot to ensure paths are relative to the script location
$AuthServiceExists = Test-Path (Join-Path $PSScriptRoot "Dockerfile.auth")

# URLs for frontend build
$STAGING_API_URL = "https://api.staging.netrasystems.ai"
$STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"

# --- Helper Functions ---

# Function to check prerequisites
function Check-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Yellow
    $missingTools = @()
    if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
        $missingTools += "gcloud (Google Cloud SDK)"
    }
    if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
        $missingTools += "docker"
    }
    
    if ($missingTools.Count -gt 0) {
        Write-Host "Error: Missing required tools: $($missingTools -join ', ')" -ForegroundColor Red
        Write-Host "Please install the missing tools and ensure they are in your system's PATH." -ForegroundColor Red
        exit 1
    }
    
    # Check if Docker daemon is running
    try {
        # Use try/catch here to catch connection errors, not just exit codes
        docker info > $null 2>&1
    } catch {
        Write-Host "Error: Docker daemon is not running or not responding. Please start Docker." -ForegroundColor Red
        exit 1
    }

    Write-Host "  ✓ Prerequisites met" -ForegroundColor Green
}

# Function to ensure authentication
function Ensure-Authentication {
    Write-Host "Ensuring proper authentication..." -ForegroundColor Yellow
    
    # Check for key file in multiple locations using Join-Path for safety
    $keyPaths = @(
        $env:GCP_STAGING_SA_KEY_PATH,
        (Join-Path $PSScriptRoot "gcp-staging-sa-key.json"),
        (Join-Path $PSScriptRoot "secrets/gcp-staging-sa-key.json"),
        (Join-Path $PSScriptRoot "terraform-gcp/gcp-staging-sa-key.json"),
        (Join-Path $env:USERPROFILE ".gcp/staging-sa-key.json")
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
        $setupScriptPath = Join-Path $PSScriptRoot "setup-staging-auth.ps1"
        if (Test-Path $setupScriptPath) {
            try {
                 & $setupScriptPath
            } catch {
                Write-Host "Failed to execute setup script: $_" -ForegroundColor Red
                exit 1
            }
           
            # Define keyfile location after setup and verify
            $keyFile = Join-Path $PSScriptRoot "gcp-staging-sa-key.json"
            if (-not (Test-Path $keyFile)) {
                Write-Host "Setup script ran, but key file was not created at $keyFile!" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "Setup script not found at $setupScriptPath!" -ForegroundColor Red
            exit 1
        }
    }
    
    # Authenticate with service account
    # For native executables, we must check $LASTEXITCODE explicitly.
    Write-Host "  Authenticating with service account..." -ForegroundColor Yellow
    gcloud auth activate-service-account --key-file=$keyFile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Authentication failed (Exit Code $LASTEXITCODE), retrying..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        gcloud auth activate-service-account --key-file=$keyFile
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Authentication failed after retry!" -ForegroundColor Red
            exit 1
        }
    }
    
    # Configure Docker
    Write-Host "  Configuring Docker authentication..." -ForegroundColor Yellow
    gcloud auth configure-docker $REGISTRY --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to configure Docker authentication!" -ForegroundColor Red
        exit 1
    }
    
    # Set project
    gcloud config set project $PROJECT_ID --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to set GCP project!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  ✓ Authentication configured successfully" -ForegroundColor Green
    return $keyFile
}

# Function to push Docker images with retry logic
function Push-ImageWithRetry {
    param($image, $maxRetries = 3)
    
    for ($i = 1; $i -le $maxRetries; $i++) {
        Write-Host "  Pushing $image (attempt $i/$maxRetries)..." -ForegroundColor Cyan
        
        # Allow Docker output to be visible for diagnostics and progress
        docker push $image
        
        # Check exit code for success/failure
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ Pushed successfully" -ForegroundColor Green
            return $true
        }
        
        if ($i -lt $maxRetries) {
            Write-Host "    Push failed (Exit Code $LASTEXITCODE). Review the error above." -ForegroundColor Yellow
            if (-not $SkipAuth) {
                Write-Host "    Re-authenticating and retrying..." -ForegroundColor Yellow
                # Use try/catch around the re-auth function in case it fails
                try {
                    Ensure-Authentication | Out-Null
                } catch {
                    Write-Host "Re-authentication failed during retry!" -ForegroundColor Red
                }
            } else {
                Write-Host "    Cannot re-authenticate because -SkipAuth was used." -ForegroundColor Yellow
            }
            Start-Sleep -Seconds 5
        }
    }
    return $false
}

# Helper function to get Cloud Run URL
function Get-CloudRunUrl {
    param($serviceName)
    # Use splatting for gcloud commands
    $urlArgs = @(
        "run", "services", "describe", $serviceName,
        "--platform", "managed",
        "--region", $REGION,
        "--project", $PROJECT_ID,
        "--format", "value(status.url)"
    )
    $url = (gcloud @urlArgs).Trim()
    # Check both the exit code and if the output is empty
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($url)) {
        Write-Host "Failed to retrieve URL for $serviceName." -ForegroundColor Red
        return $null
    }
    return $url
}

# --- Execution Start ---

# Pre-Step: Check Prerequisites
Check-Prerequisites

# Step 1: Authentication
# Authentication is required for pushing images and deploying.
if (-not $SkipAuth) {
    Write-Host "[1/5] Setting up authentication..." -ForegroundColor Green
    $keyFile = Ensure-Authentication
} else {
    Write-Host "[1/5] Skipping authentication setup (Warning: Deployment or Push may fail if not already authenticated)..." -ForegroundColor Yellow
}

if (-not $DeployOnly) {
    # Step 2: Build Docker images
    Write-Host "[2/5] Building Docker images..." -ForegroundColor Green
    
    # Backend
    Write-Host "  Building backend..." -ForegroundColor Cyan
    # Use Splatting instead of backticks for readability and reliability
    $backendBuildArgs = @(
        "build",
        "-f", "Dockerfile.backend",
        "-t", "$REGISTRY_PATH/backend:staging",
        "-t", "$REGISTRY_PATH/backend:latest",
        $BUILD_CONTEXT
    )
    docker @backendBuildArgs
    
    # Explicitly check exit code for external commands
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Backend build failed!" -ForegroundColor Red
        exit 1
    }
    
    # Frontend
    Write-Host "  Building frontend..." -ForegroundColor Cyan
    # Check paths relative to the script root if the build context is the script root
    if (Test-Path (Join-Path $PSScriptRoot "Dockerfile.frontend.staging")) { 
        $dockerFile = "Dockerfile.frontend.staging" 
    } elseif (Test-Path (Join-Path $PSScriptRoot "Dockerfile.frontend.optimized")) {
        $dockerFile = "Dockerfile.frontend.optimized"
    } else {
        $dockerFile = "Dockerfile" # Fallback
    }
    Write-Host "  Using Dockerfile: $dockerFile" -ForegroundColor Cyan
    
    $frontendBuildArgs = @(
        "build",
        "-f", $dockerFile,
        "--build-arg", "NEXT_PUBLIC_API_URL=$STAGING_API_URL",
        "--build-arg", "NEXT_PUBLIC_WS_URL=$STAGING_WS_URL",
        "-t", "$REGISTRY_PATH/frontend:staging",
        "-t", "$REGISTRY_PATH/frontend:latest",
        $BUILD_CONTEXT
    )
    docker @frontendBuildArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Frontend build failed!" -ForegroundColor Red
        exit 1
    }
    
    # Auth Service
    if ($AuthServiceExists) {
        Write-Host "  Building auth service..." -ForegroundColor Cyan
        $authBuildArgs = @(
            "build",
            "-f", "Dockerfile.auth",
            "-t", "$REGISTRY_PATH/auth:staging",
            "-t", "$REGISTRY_PATH/auth:latest",
            $BUILD_CONTEXT
        )
        docker @authBuildArgs
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Auth service build failed!" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "  ✓ All images built successfully" -ForegroundColor Green
    
    # Step 3: Push images
    Write-Host "[3/5] Pushing images to Artifact Registry..." -ForegroundColor Green
    
    $images = @(
        "$REGISTRY_PATH/backend:staging",
        "$REGISTRY_PATH/frontend:staging"
    )
    
    if ($AuthServiceExists) {
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

# Step 3.5: Run Database Migrations
if (-not $SkipMigrations) {
    Write-Host "[3.5/5] Running database migrations..." -ForegroundColor Green

    # Check if migration script exists
    $migrationScriptPath = Join-Path $PSScriptRoot "run-staging-migrations.ps1"
    if (Test-Path $migrationScriptPath) {
        Write-Host "  Checking and running migrations if needed..." -ForegroundColor Cyan
        
        # Run the migration script
        & $migrationScriptPath
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  Warning: Migration check returned non-zero exit code" -ForegroundColor Yellow
            Write-Host "  Continuing with deployment (migrations may have already been applied)" -ForegroundColor Yellow
        } else {
            Write-Host "  Migrations completed successfully" -ForegroundColor Green
        }
    } else {
        Write-Host "  Migration script not found, skipping migrations" -ForegroundColor Yellow
        Write-Host "  Expected at: $migrationScriptPath" -ForegroundColor Gray
    }
} else {
    Write-Host "[3.5/5] Skipping database migrations (SkipMigrations flag)" -ForegroundColor Yellow
}

# Step 4: Deploy to Cloud Run
Write-Host "[4/5] Deploying services to Cloud Run..." -ForegroundColor Green

# Deploy Backend
Write-Host "  Deploying backend..." -ForegroundColor Cyan
$backendDeployArgs = @(
    "run", "deploy", $BACKEND_SERVICE,
    "--image", "$REGISTRY_PATH/backend:staging",
    "--platform", "managed",
    "--region", $REGION,
    "--project", $PROJECT_ID,
    "--allow-unauthenticated",
    "--port", "8080",
    "--memory", "1Gi",
    "--cpu", "1",
    "--min-instances", "0",
    "--max-instances", "10",
    "--set-env-vars=ENVIRONMENT=staging,SERVICE_NAME=backend",
    "--add-cloudsql-instances=netra-staging:us-central1:staging-shared-postgres",
    "--set-secrets=DATABASE_URL=database-url-staging:latest,GEMINI_API_KEY=gemini-api-key-staging:latest,JWT_SECRET_KEY=jwt-secret-staging:latest,FERNET_KEY=fernet-key-staging:latest",
    "--quiet"
)
gcloud @backendDeployArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend deployment failed!" -ForegroundColor Red
    exit 1
}

# Deploy Frontend
Write-Host "  Deploying frontend..." -ForegroundColor Cyan
$frontendDeployArgs = @(
    "run", "deploy", $FRONTEND_SERVICE,
    "--image", "$REGISTRY_PATH/frontend:staging",
    "--platform", "managed",
    "--region", $REGION,
    "--project", $PROJECT_ID,
    "--allow-unauthenticated",
    "--port", "3000",
    "--memory", "512Mi",
    "--cpu", "1",
    "--min-instances", "0",
    "--max-instances", "10",
    "--set-env-vars=NODE_ENV=production,NEXT_PUBLIC_API_URL=$STAGING_API_URL,NEXT_PUBLIC_WS_URL=$STAGING_WS_URL",
    "--quiet"
)
gcloud @frontendDeployArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend deployment failed!" -ForegroundColor Red
    exit 1
}

# Deploy Auth Service if exists
# If running DeployOnly, we rely on the $AuthServiceExists check done at the start.
if ($AuthServiceExists) {
    Write-Host "  Deploying auth service..." -ForegroundColor Cyan
    $authDeployArgs = @(
        "run", "deploy", $AUTH_SERVICE,
        "--image", "$REGISTRY_PATH/auth:staging",
        "--platform", "managed",
        "--region", $REGION,
        "--project", $PROJECT_ID,
        "--allow-unauthenticated",
        "--port", "8001",
        "--memory", "1Gi",
        "--cpu", "1",
        "--min-instances", "1",
        "--max-instances", "2",
        "--set-env-vars=ENVIRONMENT=staging,SERVICE_NAME=auth",
        "--add-cloudsql-instances=netra-staging:us-central1:staging-shared-postgres",
        "--set-secrets=DATABASE_URL=database-url-staging:latest,JWT_SECRET_KEY=jwt-secret-staging:latest,FERNET_KEY=fernet-key-staging:latest,GOOGLE_CLIENT_ID=google-client-id-staging:latest,GOOGLE_CLIENT_SECRET=google-client-secret-staging:latest",
        "--quiet"
    )
    gcloud @authDeployArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Auth service deployment failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "  ✓ All services deployed successfully" -ForegroundColor Green

# Step 5: Get service URLs and Post-Deployment Checks
Write-Host "[5/5] Retrieving service URLs and running checks..." -ForegroundColor Green

$BACKEND_URL = Get-CloudRunUrl $BACKEND_SERVICE
$FRONTEND_URL = Get-CloudRunUrl $FRONTEND_SERVICE

$AUTH_URL = ""
if ($AuthServiceExists) {
    $AUTH_URL = Get-CloudRunUrl $AUTH_SERVICE
}

# Health checks
if (-not $SkipHealthChecks) {
    Write-Host ""
    Write-Host "Running health checks (waiting 10s for services to stabilize)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    if ($BACKEND_URL) {
        try {
            # Use -UseBasicParsing when content parsing isn't needed (optimization)
            $response = Invoke-WebRequest -Uri "$BACKEND_URL/health" -Method Get -TimeoutSec 30 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "  ✓ Backend is healthy" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ Backend returned status code $($response.StatusCode)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  ⚠ Backend health check failed (service may still be starting): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    
    if ($FRONTEND_URL) {
        try {
            $response = Invoke-WebRequest -Uri $FRONTEND_URL -Method Get -TimeoutSec 30 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "  ✓ Frontend is accessible" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ Frontend returned status code $($response.StatusCode)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  ⚠ Frontend check failed (service may still be starting): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

# Error monitoring check
if (-not $SkipErrorMonitoring) {
    Write-Host ""
    Write-Host "Running post-deployment error monitoring..." -ForegroundColor Yellow

    # Record deployment time for error analysis
    # Ensure UTC format for consistency with GCP logs
    $deploymentTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")

    # Wait a moment for any immediate errors to appear in GCP Error Reporting
    Write-Host "  Waiting 15s for logs to propagate..." -ForegroundColor Cyan
    Start-Sleep -Seconds 15

    # Run the error monitoring script
    $errorMonitorPath = Join-Path $PSScriptRoot "scripts/staging_error_monitor.py"
    
    if (Test-Path $errorMonitorPath) {
        Write-Host "  Checking for deployment-related errors..." -ForegroundColor Cyan
        
        # Check if python/python3 is available
        $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue
        if (-not $pythonCmd) {
            $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
        }

        if ($pythonCmd) {
            # Run error monitor with deployment time. We rely on the Python script's exit code.
            & $pythonCmd $errorMonitorPath --deployment-time $deploymentTime --project-id $PROJECT_ID --service netra-backend
            $pythonExit = $LASTEXITCODE
            
            if ($pythonExit -eq 0) {
                Write-Host "  ✓ No critical deployment errors detected" -ForegroundColor Green
            } elseif ($pythonExit -eq 1) {
                Write-Host "  ❌ Critical deployment errors detected!" -ForegroundColor Red
                Write-Host "  Consider rolling back the deployment." -ForegroundColor Yellow
                
                # Check if the session is interactive (e.g., local development vs CI/CD)
                if ($Host.UI.IsInteractive) {
                    $continue = Read-Host "Continue despite errors? (y/N)"
                    if ($continue -ne "y" -and $continue -ne "Y") {
                        Write-Host "Deployment marked as failed by user due to critical errors." -ForegroundColor Red
                        exit 1
                    }
                } else {
                    # If non-interactive (CI/CD), fail the deployment automatically
                    Write-Host "Deployment failed automatically due to critical errors detected in non-interactive mode." -ForegroundColor Red
                    exit 1
                }
            } else {
                Write-Host "  ⚠ Error monitoring script failed unexpectedly (Exit Code: $pythonExit)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ⚠ Python executable (python or python3) not found. Cannot run error monitoring." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⚠ Error monitoring script not found at $errorMonitorPath" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Skipping error monitoring check..." -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "    DEPLOYMENT COMPLETED SUCCESSFULLY           " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
if ($FRONTEND_URL) { Write-Host "  Frontend:  $FRONTEND_URL" -ForegroundColor Green }
if ($BACKEND_URL) { Write-Host "  Backend:   $BACKEND_URL" -ForegroundColor Green }
if ($AUTH_URL) { Write-Host "  Auth:      $AUTH_URL" -ForegroundColor Green }

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

try {
    $jsonPath = Join-Path $PSScriptRoot "deployment-info.json"
    $deploymentInfo | ConvertTo-Json | Out-File -FilePath $jsonPath -Encoding utf8
    Write-Host "Deployment info saved to deployment-info.json" -ForegroundColor Yellow
} catch {
    Write-Host "Warning: Failed to save deployment-info.json" -ForegroundColor Yellow
}