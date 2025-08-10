# deploy.ps1 - Automated deployment script for Windows
# Total deployment time: ~10 minutes

$ErrorActionPreference = "Stop"

# Colors for output
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

# Check if terraform.tfvars exists
if (-not (Test-Path "terraform.tfvars")) {
    Write-Error-Message "terraform.tfvars not found!"
    Write-Status "Creating terraform.tfvars from example..."
    Copy-Item "terraform.tfvars.example" "terraform.tfvars"
    Write-Warning-Message "Please edit terraform.tfvars with your project settings and run this script again."
    exit 1
}

# Read project_id and region from terraform.tfvars
$tfvars = Get-Content "terraform.tfvars"
$project_id = ($tfvars | Select-String 'project_id\s*=\s*"([^"]+)"').Matches.Groups[1].Value
$region = ($tfvars | Select-String 'region\s*=\s*"([^"]+)"').Matches.Groups[1].Value

Write-Status "Starting deployment for project: $project_id in region: $region"

# Step 1: Check prerequisites
Write-Status "Checking prerequisites..."

$prerequisites = @{
    "gcloud" = "Google Cloud SDK"
    "terraform" = "Terraform"
    "docker" = "Docker"
}

foreach ($cmd in $prerequisites.Keys) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error-Message "$cmd not found. Please install $($prerequisites[$cmd])."
        exit 1
    }
}

Write-Status "All prerequisites met!"

# Step 2: Configure GCP project
Write-Status "Configuring GCP project..."
gcloud config set project $project_id

# Enable required APIs
Write-Status "Enabling required GCP APIs..."
gcloud services enable `
    compute.googleapis.com `
    container.googleapis.com `
    sqladmin.googleapis.com `
    cloudrun.googleapis.com `
    artifactregistry.googleapis.com `
    secretmanager.googleapis.com `
    --project=$project_id

# Step 3: Initialize Terraform
Write-Status "Initializing Terraform..."
terraform init

# Step 4: Plan infrastructure
Write-Status "Planning infrastructure..."
terraform plan -out=tfplan

# Step 5: Apply infrastructure
Write-Status "Creating infrastructure (this may take 5-7 minutes)..."
terraform apply tfplan

# Step 6: Get outputs
Write-Status "Retrieving deployment information..."
terraform output -json | Out-File -FilePath "deployment-info.json"

# Extract values
$REGISTRY = terraform output -raw artifact_registry
$FRONTEND_URL = terraform output -raw frontend_url
$BACKEND_URL = terraform output -raw backend_url
$DB_IP = terraform output -raw database_ip

# Step 7: Configure Docker
Write-Status "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker "$region-docker.pkg.dev" --quiet

# Step 8: Build and push containers
Write-Status "Building and pushing Docker containers..."

# Build and push backend
Write-Status "Building backend Docker image..."
Set-Location ..
docker build -f Dockerfile.backend -t "$REGISTRY/backend:latest" .
Write-Status "Pushing backend image to registry..."
docker push "$REGISTRY/backend:latest"

# Build and push frontend
Write-Status "Building frontend Docker image..."
Set-Location frontend
docker build -t "$REGISTRY/frontend:latest" .
Write-Status "Pushing frontend image to registry..."
docker push "$REGISTRY/frontend:latest"

Set-Location ../terraform-gcp

# Step 9: Deploy to Cloud Run
Write-Status "Deploying services to Cloud Run..."

gcloud run deploy netra-backend `
    --image "$REGISTRY/backend:latest" `
    --region $region `
    --allow-unauthenticated `
    --port 8080 `
    --quiet

gcloud run deploy netra-frontend `
    --image "$REGISTRY/frontend:latest" `
    --region $region `
    --allow-unauthenticated `
    --port 8080 `
    --quiet

# Step 10: Verify deployment
Write-Status "Verifying deployment..."

# Test backend
try {
    $response = Invoke-WebRequest -Uri "$BACKEND_URL/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Status "✓ Backend is healthy"
    }
} catch {
    Write-Warning-Message "Backend health check failed"
}

# Test frontend
try {
    $response = Invoke-WebRequest -Uri $FRONTEND_URL -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Status "✓ Frontend is accessible"
    }
} catch {
    Write-Warning-Message "Frontend check failed"
}

# Step 11: Set up monitoring
Write-Status "Setting up budget alert..."

$BILLING_ACCOUNT = gcloud beta billing accounts list --format="value(name)" | Select-Object -First 1
if ($BILLING_ACCOUNT) {
    try {
        gcloud billing budgets create `
            --billing-account=$BILLING_ACCOUNT `
            --display-name="Netra Monthly Budget Alert" `
            --budget-amount=1000 `
            --threshold-rule=percent=0.5 `
            --threshold-rule=percent=0.9 `
            --threshold-rule=percent=1.0 `
            --quiet 2>$null
    } catch {
        Write-Warning-Message "Budget alert already exists or creation failed"
    }
}

# Print summary
Write-Status "==============================================="
Write-Status "DEPLOYMENT COMPLETE!"
Write-Status "==============================================="
Write-Host ""
Write-Host "Frontend URL: " -NoNewline
Write-Host $FRONTEND_URL -ForegroundColor Green
Write-Host "Backend URL:  " -NoNewline
Write-Host $BACKEND_URL -ForegroundColor Green
Write-Host "Database IP:  " -NoNewline
Write-Host $DB_IP -ForegroundColor Green
Write-Host ""
Write-Status "Estimated monthly cost: ~`$200 (base)"
Write-Status "Budget limit set: `$1,000/month"
Write-Host ""
Write-Status "Next steps:"
Write-Host "  1. Visit $FRONTEND_URL to access your application"
Write-Host "  2. Configure custom domain (optional)"
Write-Host "  3. Set up Redis separately if needed"
Write-Host "  4. Review security settings for production use"
Write-Host ""
Write-Status "To destroy all resources: terraform destroy"
Write-Status "Full deployment info saved to: deployment-info.json"