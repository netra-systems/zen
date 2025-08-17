# Deploy All Services to GCP Staging using Terraform
# PowerShell script for Windows deployment with Terraform

Write-Host "================================================" -ForegroundColor Blue
Write-Host "  NETRA STAGING DEPLOYMENT - TERRAFORM        " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"
$REGION = "us-central1"
$ENVIRONMENT = "staging"
$TF_VAR_FILE = "terraform.staging.tfvars"

Write-Host "Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  Project: $PROJECT_ID"
Write-Host "  Region: $REGION"
Write-Host "  Environment: $ENVIRONMENT"
Write-Host "  Terraform vars: $TF_VAR_FILE"
Write-Host ""

# Step 1: Authenticate with GCP
Write-Host "[1/8] Authenticating with GCP..." -ForegroundColor Green
Write-Host "Please complete authentication in your browser when prompted"
gcloud auth login
if ($LASTEXITCODE -ne 0) {
    Write-Host "Authentication failed!" -ForegroundColor Red
    exit 1
}

# Authenticate for application default credentials (needed for Terraform)
gcloud auth application-default login
if ($LASTEXITCODE -ne 0) {
    Write-Host "Application default authentication failed!" -ForegroundColor Red
    exit 1
}

# Step 2: Set project
Write-Host "[2/8] Setting GCP project..." -ForegroundColor Green
gcloud config set project $PROJECT_ID

# Step 3: Enable required APIs
Write-Host "[3/8] Enabling required GCP APIs..." -ForegroundColor Green
$APIs = @(
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
    "sqladmin.googleapis.com"
)

foreach ($api in $APIs) {
    Write-Host "  Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID
}

# Step 4: Create state bucket if not exists
Write-Host "[4/8] Setting up Terraform state bucket..." -ForegroundColor Green
$STATE_BUCKET = "$PROJECT_ID-terraform-state"

# Check if bucket exists
$bucketExists = gsutil ls -b "gs://$STATE_BUCKET" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating state bucket: $STATE_BUCKET"
    gsutil mb -p $PROJECT_ID -l $REGION "gs://$STATE_BUCKET"
    gsutil versioning set on "gs://$STATE_BUCKET"
} else {
    Write-Host "  State bucket already exists: $STATE_BUCKET"
}

# Step 5: Navigate to terraform directory
Write-Host "[5/8] Navigating to Terraform directory..." -ForegroundColor Green
Set-Location -Path "terraform-gcp"

# Step 6: Initialize Terraform
Write-Host "[6/8] Initializing Terraform..." -ForegroundColor Green
terraform init `
    -backend-config="bucket=$STATE_BUCKET" `
    -backend-config="prefix=staging" `
    -reconfigure

if ($LASTEXITCODE -ne 0) {
    Write-Host "Terraform init failed!" -ForegroundColor Red
    Set-Location -Path ".."
    exit 1
}

# Select or create staging workspace
terraform workspace select staging 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating staging workspace..."
    terraform workspace new staging
}

# Step 7: Set up secrets in Secret Manager
Write-Host "[7/8] Setting up secrets in Secret Manager..." -ForegroundColor Green

# Check and create JWT secret
$secrets = gcloud secrets list --project=$PROJECT_ID --format="value(name)" 2>$null

if ($secrets -notcontains "jwt-secret") {
    Write-Host "  Creating jwt-secret..."
    $JWT_SECRET = [System.Guid]::NewGuid().ToString() + [System.Guid]::NewGuid().ToString()
    echo $JWT_SECRET | gcloud secrets create jwt-secret --data-file=- --project=$PROJECT_ID
    
    # Set Terraform variable
    $env:TF_VAR_jwt_secret = $JWT_SECRET
} else {
    Write-Host "  jwt-secret already exists"
    # Retrieve the secret for Terraform
    $JWT_SECRET = gcloud secrets versions access latest --secret="jwt-secret" --project=$PROJECT_ID
    $env:TF_VAR_jwt_secret = $JWT_SECRET
}

if ($secrets -notcontains "auth-database-url") {
    Write-Host "  Creating auth-database-url..."
    # This would typically point to a Cloud SQL instance
    $DB_URL = "postgresql://auth_user:staging_pass@10.0.0.5:5432/auth_db"
    echo $DB_URL | gcloud secrets create auth-database-url --data-file=- --project=$PROJECT_ID
    
    $env:TF_VAR_auth_database_url = $DB_URL
} else {
    Write-Host "  auth-database-url already exists"
    $DB_URL = gcloud secrets versions access latest --secret="auth-database-url" --project=$PROJECT_ID
    $env:TF_VAR_auth_database_url = $DB_URL
}

if ($secrets -notcontains "redis-url") {
    Write-Host "  Creating redis-url..."
    $REDIS_URL = "redis://10.0.0.6:6379/0"
    echo $REDIS_URL | gcloud secrets create redis-url --data-file=- --project=$PROJECT_ID
} else {
    Write-Host "  redis-url already exists"
}

# Set additional Terraform variables
$env:TF_VAR_project_id = $PROJECT_ID
$env:TF_VAR_project_id_numerical = "701982941522"
$env:TF_VAR_region = $REGION
$env:TF_VAR_environment = $ENVIRONMENT

# Step 8: Run Terraform deployment
Write-Host "[8/8] Running Terraform deployment..." -ForegroundColor Green

# Plan the deployment
Write-Host "  Planning deployment..."
terraform plan -var-file="$TF_VAR_FILE" -out="staging-complete.tfplan"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Terraform plan failed!" -ForegroundColor Red
    Set-Location -Path ".."
    exit 1
}

# Show the plan summary
Write-Host ""
Write-Host "Terraform will perform the following actions:" -ForegroundColor Yellow
terraform show -no-color staging-complete.tfplan | Select-String -Pattern "will be" | Select-Object -First 10

Write-Host ""
$confirmation = Read-Host "Do you want to proceed with the deployment? (yes/no)"

if ($confirmation -eq "yes") {
    Write-Host "  Applying Terraform configuration..."
    terraform apply staging-complete.tfplan
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Terraform apply failed!" -ForegroundColor Red
        Set-Location -Path ".."
        exit 1
    }
    
    # Get outputs
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "   STAGING DEPLOYMENT COMPLETED SUCCESSFULLY   " -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "Deployment Outputs:" -ForegroundColor Cyan
    
    # Try to get outputs
    $outputs = @(
        "frontend_url",
        "backend_url",
        "auth_service_url",
        "load_balancer_ip",
        "artifact_registry"
    )
    
    foreach ($output in $outputs) {
        try {
            $value = terraform output -raw $output 2>$null
            if ($LASTEXITCODE -eq 0 -and $value) {
                Write-Host "  ${output}: $value" -ForegroundColor Green
            }
        } catch {
            # Output doesn't exist, skip
        }
    }
    
    Write-Host ""
    Write-Host "Services Information:" -ForegroundColor Yellow
    
    # Get Cloud Run services
    Write-Host "  Cloud Run Services:"
    gcloud run services list --platform=managed --region=$REGION --project=$PROJECT_ID --format="table(SERVICE,REGION,URL)"
    
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Verify services are running: terraform output"
    Write-Host "  2. Check service health endpoints"
    Write-Host "  3. Update DNS records if needed"
    Write-Host "  4. Run integration tests"
    Write-Host ""
    Write-Host "To destroy this deployment:" -ForegroundColor Yellow
    Write-Host "  terraform destroy -var-file=$TF_VAR_FILE"
    
} else {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
}

# Return to original directory
Set-Location -Path ".."

Write-Host ""
Write-Host "Script completed." -ForegroundColor Green