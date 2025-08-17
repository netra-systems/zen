# deploy-staging.ps1 - Automated deployment script for STAGING environment on Windows
# This script ensures staging deployments use staging resources only

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

function Write-Info {
    param($Message)
    Write-Host "[INFO]" -ForegroundColor Blue -NoNewline
    Write-Host " $Message"
}

# Staging environment banner
Write-Host "================================================" -ForegroundColor Blue
Write-Host "     NETRA STAGING ENVIRONMENT DEPLOYMENT      " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Force use of staging configuration
$TF_VAR_FILE = "terraform.staging.tfvars"

# Check if staging tfvars exists
if (-not (Test-Path $TF_VAR_FILE)) {
    Write-Error-Message "$TF_VAR_FILE not found!"
    Write-Status "Please ensure terraform.staging.tfvars exists with staging configuration."
    exit 1
}

# Read variables from terraform.staging.tfvars
$tfvars = Get-Content $TF_VAR_FILE
$project_id = ($tfvars | Select-String 'project_id\s*=\s*"([^"]+)"').Matches.Groups[1].Value
$project_id_numerical = ($tfvars | Select-String 'project_id_numerical\s*=\s*"([^"]+)"').Matches.Groups[1].Value
$region = ($tfvars | Select-String 'region\s*=\s*"([^"]+)"').Matches.Groups[1].Value
$environment = ($tfvars | Select-String 'environment\s*=\s*"([^"]+)"').Matches.Groups[1].Value

# Verify this is staging
if ($environment -ne "staging") {
    Write-Error-Message "Environment is not set to 'staging' in $TF_VAR_FILE"
    Write-Error-Message "Current environment: $environment"
    exit 1
}

if ($project_id -like "*production*") {
    Write-Error-Message "Project ID contains 'production': $project_id"
    Write-Error-Message "This appears to be a production project. Aborting staging deployment."
    exit 1
}

Write-Info "Deploying to STAGING environment"
Write-Info "Project: $project_id"
Write-Info "Project ID (numerical): $project_id_numerical"
Write-Info "Region: $region"
Write-Info "Environment: $environment"
Write-Host ""

# Step 1: Check prerequisites
Write-Status "Checking prerequisites..."

$prerequisites = @{
    "gcloud" = "Google Cloud SDK"
    "terraform" = "Terraform"
}

foreach ($cmd in $prerequisites.Keys) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error-Message "$cmd not found. Please install $($prerequisites[$cmd])."
        exit 1
    }
}

# Step 2: Set the correct GCP project
Write-Status "Setting GCP project to staging: $project_id"
gcloud config set project $project_id

# Verify we're using the right project
$CURRENT_PROJECT = gcloud config get-value project
if ($CURRENT_PROJECT -ne $project_id) {
    Write-Error-Message "Failed to set project to $project_id"
    exit 1
}

# Step 3: Check authentication
Write-Status "Checking GCP authentication..."
try {
    $null = gcloud auth application-default print-access-token 2>$null
} catch {
    Write-Warning-Message "Not authenticated. Please run: gcloud auth application-default login"
    Write-Info "After authenticating, run this script again."
    exit 1
}

# Step 4: Enable required APIs for staging
Write-Status "Enabling required APIs for staging project..."
$APIS = @(
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "redis.googleapis.com",
    "dns.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudkms.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
)

foreach ($api in $APIS) {
    Write-Status "  Enabling $api..."
    gcloud services enable $api --project=$project_id --quiet
}

# Step 5: Initialize Terraform with staging backend
Write-Status "Initializing Terraform for staging..."

# Use staging-specific state bucket
$STAGING_STATE_BUCKET = "$project_id-terraform-state"

# Check if state bucket exists, create if not
try {
    gsutil ls -b "gs://$STAGING_STATE_BUCKET" 2>$null
} catch {
    Write-Status "Creating Terraform state bucket for staging: $STAGING_STATE_BUCKET"
    gsutil mb -p $project_id -l $region "gs://$STAGING_STATE_BUCKET"
    gsutil versioning set on "gs://$STAGING_STATE_BUCKET"
}

# Initialize with staging backend
terraform init `
    -backend-config="bucket=$STAGING_STATE_BUCKET" `
    -backend-config="prefix=staging" `
    -reconfigure

# Step 6: Create workspace for staging
Write-Status "Setting Terraform workspace to staging..."
$workspaces = terraform workspace list
if ($workspaces -like "*staging*") {
    terraform workspace select staging
} else {
    terraform workspace new staging
}

# Step 7: Validate configuration
Write-Status "Validating Terraform configuration..."
terraform validate

# Step 8: Plan deployment with staging variables
Write-Status "Planning staging deployment..."
terraform plan -var-file="$TF_VAR_FILE" -out="staging.tfplan"

# Step 9: Confirm deployment
Write-Host ""
Write-Warning-Message "About to deploy to STAGING environment: $project_id"
$response = Read-Host "Do you want to proceed with the staging deployment? (yes/no)"
Write-Host ""

if ($response -ne "yes") {
    Write-Warning-Message "Deployment cancelled."
    exit 0
}

# Step 10: Apply Terraform configuration
Write-Status "Applying Terraform configuration for staging..."
terraform apply staging.tfplan

# Step 11: Get outputs
Write-Status "Retrieving deployment outputs..."
Write-Host ""
Write-Host "=== STAGING Deployment Complete ===" -ForegroundColor Green
Write-Host ""

# Display staging URLs
try {
    $BACKEND_URL = terraform output -raw backend_url 2>$null
} catch {
    $BACKEND_URL = "Not available"
}

try {
    $FRONTEND_URL = terraform output -raw frontend_url 2>$null
} catch {
    $FRONTEND_URL = "Not available"
}

try {
    $DB_CONNECTION = terraform output -raw database_connection_name 2>$null
} catch {
    $DB_CONNECTION = "Not available"
}

Write-Host "STAGING Environment URLs:" -ForegroundColor Blue
Write-Host "  Frontend: " -NoNewline
Write-Host $FRONTEND_URL -ForegroundColor Green
Write-Host "  Backend:  " -NoNewline
Write-Host $BACKEND_URL -ForegroundColor Green
Write-Host "  Database: " -NoNewline
Write-Host $DB_CONNECTION -ForegroundColor Green
Write-Host ""

# Step 12: Post-deployment verification
Write-Status "Running post-deployment checks..."

# Check if backend is responding
if ($BACKEND_URL -ne "Not available") {
    Write-Status "Checking backend health..."
    try {
        $response = Invoke-WebRequest -Uri "$BACKEND_URL/health" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Status "Backend is responding"
        }
    } catch {
        Write-Warning-Message "Backend health check failed - this is normal if the service is still starting"
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "   STAGING DEPLOYMENT COMPLETED SUCCESSFULLY   " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Info "Environment: STAGING"
Write-Info "Project: $project_id"
Write-Info "To destroy this staging deployment, run: terraform destroy -var-file=$TF_VAR_FILE"