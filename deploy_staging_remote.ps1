# Deploy to Remote GCP Staging Environment from Local Machine
# This script mimics the GitHub Actions staging workflow but runs locally

param(
    [Parameter(Position=0)]
    [ValidateSet("deploy", "destroy", "restart", "status", "rebuild")]
    [string]$Action = "deploy",
    
    [string]$PrNumber = "",
    [string]$Branch = "",
    [switch]$Force = $false,
    [switch]$SkipBuild = $false,
    [switch]$SkipTests = $false
)

# Configuration
$ProjectName = "netra-staging"
$GcpRegion = "us-central1"
$TerraformVersion = "1.5.0"

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Main deployment function
function Deploy-Staging {
    Write-Info "Starting Remote Staging Deployment"
    Write-Info "========================================"
    Write-Info "Action: $Action"
    Write-Info "PR Number: $PrNumber"
    Write-Info "Branch: $Branch"
    Write-Info ""
    
    # Step 1: Environment Setup
    $envConfig = Setup-Environment
    
    # Step 2: Authenticate with GCP
    if (-not (Test-GcpAuth)) {
        Write-Error "GCP authentication failed. Please run: gcloud auth login"
        exit 1
    }
    
    if ($Action -eq "deploy" -or $Action -eq "rebuild") {
        # Step 3: Build and Push Docker Images
        if (-not $SkipBuild) {
            $images = Build-DockerImages -Config $envConfig
            $envConfig.BackendImage = $images.Backend
            $envConfig.FrontendImage = $images.Frontend
        }
        
        # Step 4: Deploy Infrastructure with Terraform
        Deploy-Infrastructure -Config $envConfig
        
        # Step 5: Run Smoke Tests
        if (-not $SkipTests) {
            Test-Deployment -Config $envConfig
        }
    }
    elseif ($Action -eq "destroy") {
        Destroy-Infrastructure -Config $envConfig
    }
    elseif ($Action -eq "status") {
        Get-DeploymentStatus -Config $envConfig
    }
    elseif ($Action -eq "restart") {
        Restart-Services -Config $envConfig
    }
    
    Write-Success "Deployment Complete!"
}

function Setup-Environment {
    $config = @{}
    
    # Determine environment name and PR number
    if ($PrNumber) {
        $config.PrNumber = $PrNumber
    } else {
        # Get from current git branch
        $currentBranch = git rev-parse --abbrev-ref HEAD
        $config.PrNumber = "branch-$($currentBranch -replace '[^a-zA-Z0-9-]', '-')"
    }
    
    if ($Branch) {
        $config.Branch = $Branch
    } else {
        $config.Branch = git rev-parse --abbrev-ref HEAD
    }
    
    # Get commit SHA
    $config.CommitSha = git rev-parse HEAD
    $config.ShortSha = $config.CommitSha.Substring(0, 7)
    
    # Sanitize environment name
    $envName = "$ProjectName-$($config.PrNumber)" -replace '[^a-zA-Z0-9-]', '-'
    $envName = $envName.ToLower()
    if ($envName.Length -gt 63) {
        $envName = $envName.Substring(0, 63)
    }
    $config.EnvironmentName = $envName
    
    # Get GCP project ID
    $config.ProjectId = $env:GCP_STAGING_PROJECT_ID
    if (-not $config.ProjectId) {
        $config.ProjectId = $env:GCP_PROJECT_ID
    }
    if (-not $config.ProjectId) {
        $config.ProjectId = gcloud config get-value project
    }
    
    Write-Info "Environment Configuration:"
    Write-Info "  Environment Name: $($config.EnvironmentName)"
    Write-Info "  PR Number: $($config.PrNumber)"
    Write-Info "  Branch: $($config.Branch)"
    Write-Info "  Commit SHA: $($config.ShortSha)"
    Write-Info "  GCP Project: $($config.ProjectId)"
    Write-Info ""
    
    return $config
}

function Test-GcpAuth {
    try {
        $account = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
        if ($account) {
            Write-Success "Authenticated as: $account"
            
            # Set project
            $projectId = $env:GCP_STAGING_PROJECT_ID
            if (-not $projectId) { $projectId = $env:GCP_PROJECT_ID }
            if ($projectId) {
                gcloud config set project $projectId 2>$null
                Write-Success "Project set to: $projectId"
            }
            
            # Configure Docker for GCR
            Write-Info "Configuring Docker for GCR..."
            gcloud auth configure-docker gcr.io --quiet
            
            return $true
        }
    }
    catch {
        Write-Warning "GCP authentication check failed: $_"
    }
    return $false
}

function Build-DockerImages {
    param($Config)
    
    Write-Info "Building Docker Images..."
    $startTime = Get-Date
    
    $images = @{}
    $projectId = $Config.ProjectId
    $tag = $Config.CommitSha
    
    # Enable BuildKit
    $env:DOCKER_BUILDKIT = "1"
    $env:BUILDKIT_PROGRESS = "plain"
    
    # Build Backend
    Write-Info "Building backend image..."
    $backendImage = "gcr.io/$projectId/backend:$tag"
    $backendLatest = "gcr.io/$projectId/backend:latest"
    
    # Check if image already exists
    $imageExists = $false
    try {
        gcloud container images describe $backendImage 2>$null | Out-Null
        $imageExists = $true
        Write-Info "Backend image already exists, skipping build"
    } catch {
        # Image doesn't exist, need to build
    }
    
    if (-not $imageExists) {
        $buildDate = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
        $buildArgs = @(
            "build",
            "--platform", "linux/amd64",
            "--build-arg", "COMMIT_SHA=$($Config.CommitSha)",
            "--build-arg", "BUILD_DATE=$buildDate",
            "-t", $backendImage,
            "-t", $backendLatest,
            "-f", "Dockerfile.backend",
            "."
        )
        
        docker $buildArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Backend build failed!"
            exit 1
        }
        
        # Push to GCR
        Write-Info "Pushing backend image to GCR..."
        docker push $backendImage
        docker push $backendLatest
    }
    
    $images.Backend = $backendImage
    
    # Build Frontend
    Write-Info "Building frontend image..."
    $frontendImage = "gcr.io/$projectId/frontend:$tag"
    $frontendLatest = "gcr.io/$projectId/frontend:latest"
    
    # Check if image already exists
    $imageExists = $false
    try {
        gcloud container images describe $frontendImage 2>$null | Out-Null
        $imageExists = $true
        Write-Info "Frontend image already exists, skipping build"
    } catch {
        # Image doesn't exist, need to build
    }
    
    if (-not $imageExists) {
        $buildDate = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
        $buildArgs = @(
            "build",
            "--platform", "linux/amd64",
            "--build-arg", "COMMIT_SHA=$($Config.CommitSha)",
            "--build-arg", "BUILD_DATE=$buildDate",
            "-t", $frontendImage,
            "-t", $frontendLatest,
            "-f", "Dockerfile.frontend.staging",
            "."
        )
        
        docker $buildArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Frontend build failed!"
            exit 1
        }
        
        # Push to GCR
        Write-Info "Pushing frontend image to GCR..."
        docker push $frontendImage
        docker push $frontendLatest
    }
    
    $images.Frontend = $frontendImage
    
    $duration = (Get-Date) - $startTime
    Write-Success "Images built and pushed in $([int]$duration.TotalSeconds) seconds"
    
    return $images
}

function Deploy-Infrastructure {
    param($Config)
    
    Write-Info "Deploying Infrastructure with Terraform..."
    $startTime = Get-Date
    
    # Change to terraform directory
    Push-Location "terraform/staging"
    try {
        # Setup state bucket
        $bucket = $env:TF_STAGING_STATE_BUCKET
        if (-not $bucket) { $bucket = $env:TF_STATE_BUCKET }
        if (-not $bucket) { $bucket = "netra-staging-terraform-state" }
        
        # Create bucket if it doesn't exist
        try {
            gsutil ls "gs://$bucket" 2>$null | Out-Null
        } catch {
            Write-Info "Creating Terraform state bucket..."
            gsutil mb -p $($Config.ProjectId) -l $GcpRegion "gs://$bucket"
        }
        
        # Initialize Terraform
        Write-Info "Initializing Terraform..."
        terraform init `
            -backend-config="bucket=$bucket" `
            -backend-config="prefix=$($Config.EnvironmentName)" `
            -upgrade=false `
            -reconfigure `
            -input=false
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Terraform init failed!"
            exit 1
        }
        
        # Create tfvars file
        Write-Info "Creating terraform.tfvars..."
        $tfvars = @"
environment_name = "$($Config.EnvironmentName)"
pr_number = "$($Config.PrNumber)"
branch_name = "$($Config.Branch)"
commit_sha = "$($Config.CommitSha)"
project_id = "$($Config.ProjectId)"
backend_image = "$($Config.BackendImage)"
frontend_image = "$($Config.FrontendImage)"
postgres_password = "$(if ($env:POSTGRES_PASSWORD_STAGING) { $env:POSTGRES_PASSWORD_STAGING } else { 'staging-password' })"
clickhouse_password = "$(if ($env:CLICKHOUSE_PASSWORD_STAGING) { $env:CLICKHOUSE_PASSWORD_STAGING } else { 'staging-clickhouse' })"
jwt_secret_key = "$(if ($env:JWT_SECRET_KEY_STAGING) { $env:JWT_SECRET_KEY_STAGING } else { '' })"
fernet_key = "$(if ($env:FERNET_KEY_STAGING) { $env:FERNET_KEY_STAGING } else { '' })"
gemini_api_key = "$(if ($env:GEMINI_API_KEY_STAGING) { $env:GEMINI_API_KEY_STAGING } else { '' })"
"@
        $tfvars | Out-File -FilePath "terraform.tfvars" -Encoding utf8
        
        # Plan deployment
        Write-Info "Planning deployment..."
        terraform plan -out=tfplan
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Terraform plan failed!"
            exit 1
        }
        
        # Apply deployment
        Write-Info "Applying deployment..."
        terraform apply -auto-approve tfplan
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Terraform apply failed!"
            exit 1
        }
        
        # Get outputs
        $Config.BackendUrl = terraform output -raw backend_url 2>$null
        $Config.FrontendUrl = terraform output -raw frontend_url 2>$null
        
        $duration = (Get-Date) - $startTime
        Write-Success "Infrastructure deployed in $([int]$duration.TotalSeconds) seconds"
        Write-Success "Frontend URL: $($Config.FrontendUrl)"
        Write-Success "Backend URL: $($Config.BackendUrl)"
    }
    finally {
        Pop-Location
    }
}

function Destroy-Infrastructure {
    param($Config)
    
    Write-Warning "Destroying Infrastructure..."
    
    Push-Location "terraform/staging"
    try {
        # Setup state bucket
        $bucket = $env:TF_STAGING_STATE_BUCKET
        if (-not $bucket) { $bucket = $env:TF_STATE_BUCKET }
        if (-not $bucket) { $bucket = "netra-staging-terraform-state" }
        
        # Initialize Terraform
        terraform init `
            -backend-config="bucket=$bucket" `
            -backend-config="prefix=$($Config.EnvironmentName)" `
            -upgrade=false `
            -reconfigure `
            -input=false
        
        # Destroy
        terraform destroy `
            -auto-approve `
            -var="environment_name=$($Config.EnvironmentName)" `
            -var="pr_number=$($Config.PrNumber)" `
            -var="project_id=$($Config.ProjectId)"
        
        Write-Success "Infrastructure destroyed"
    }
    finally {
        Pop-Location
    }
}

function Test-Deployment {
    param($Config)
    
    Write-Info "Running Smoke Tests..."
    
    # Wait for services to stabilize
    Start-Sleep -Seconds 15
    
    # Test backend health
    Write-Info "Testing backend health..."
    $maxRetries = 10
    $retryCount = 0
    
    while ($retryCount -lt $maxRetries) {
        try {
            $response = Invoke-WebRequest -Uri "$($Config.BackendUrl)/health" -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Success "Backend is healthy"
                break
            }
        } catch {
            $retryCount++
            Write-Warning "Backend not ready, retry $retryCount/$maxRetries"
            Start-Sleep -Seconds 5
        }
    }
    
    if ($retryCount -eq $maxRetries) {
        Write-Error "Backend health check failed after $maxRetries retries"
        exit 1
    }
    
    # Test frontend
    Write-Info "Testing frontend..."
    try {
        $response = Invoke-WebRequest -Uri $Config.FrontendUrl -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Success "Frontend is accessible"
        }
    } catch {
        Write-Warning "Frontend may not be fully ready yet"
    }
}

function Get-DeploymentStatus {
    param($Config)
    
    Write-Info "Getting Deployment Status..."
    
    Push-Location "terraform/staging"
    try {
        # Setup state bucket
        $bucket = $env:TF_STAGING_STATE_BUCKET
        if (-not $bucket) { $bucket = $env:TF_STATE_BUCKET }
        if (-not $bucket) { $bucket = "netra-staging-terraform-state" }
        
        # Initialize Terraform
        terraform init `
            -backend-config="bucket=$bucket" `
            -backend-config="prefix=$($Config.EnvironmentName)" `
            -upgrade=false `
            -reconfigure `
            -input=false 2>$null
        
        # Get outputs
        $backendUrl = terraform output -raw backend_url 2>$null
        $frontendUrl = terraform output -raw frontend_url 2>$null
        
        if ($backendUrl -and $frontendUrl) {
            Write-Success "Deployment is active"
            Write-Info "Frontend URL: $frontendUrl"
            Write-Info "Backend URL: $backendUrl"
            
            # Test health
            try {
                $response = Invoke-WebRequest -Uri "$backendUrl/health" -TimeoutSec 5
                Write-Success "Backend: Healthy"
            } catch {
                Write-Warning "Backend: Not responding"
            }
            
            try {
                $response = Invoke-WebRequest -Uri $frontendUrl -TimeoutSec 5
                Write-Success "Frontend: Accessible"
            } catch {
                Write-Warning "Frontend: Not responding"
            }
        } else {
            Write-Warning "No active deployment found for $($Config.EnvironmentName)"
        }
    }
    finally {
        Pop-Location
    }
}

function Restart-Services {
    param($Config)
    
    Write-Info "Restarting Services..."
    
    # In GCP Cloud Run, we restart by updating the service
    $projectId = $Config.ProjectId
    
    # Restart backend
    Write-Info "Restarting backend service..."
    $restartTime = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    gcloud run services update "backend-$($Config.PrNumber)" `
        --region=$GcpRegion `
        --project=$projectId `
        --update-env-vars="RESTART_TIME=$restartTime"
    
    # Restart frontend
    Write-Info "Restarting frontend service..."
    gcloud run services update "frontend-$($Config.PrNumber)" `
        --region=$GcpRegion `
        --project=$projectId `
        --update-env-vars="RESTART_TIME=$restartTime"
    
    Write-Success "Services restarted"
}

# Check prerequisites
function Test-Prerequisites {
    $missing = @()
    
    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        $missing += "Docker"
    } else {
        try {
            docker info 2>$null | Out-Null
        } catch {
            Write-Error "Docker is not running. Please start Docker Desktop."
            exit 1
        }
    }
    
    # Check gcloud
    if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
        $missing += "Google Cloud SDK (gcloud)"
    }
    
    # Check Terraform
    if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
        $missing += "Terraform"
    }
    
    # Check git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        $missing += "Git"
    }
    
    if ($missing.Count -gt 0) {
        $missingList = $missing -join ", "
        Write-Error "Missing prerequisites: $missingList"
        Write-Info "Please install the missing tools and try again."
        exit 1
    }
    
    Write-Success "All prerequisites met"
}

# Main execution
Test-Prerequisites
Deploy-Staging