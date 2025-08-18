# Setup GCP Staging Resources
# Pre-creates all required GCP resources for staging deployment

param(
    [Parameter(Mandatory=$false)]
    [string]$ServiceAccountKeyPath = $env:GCP_SA_KEY_PATH,
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceAccountEmail = "netra-staging-deploy@netra-staging.iam.gserviceaccount.com"
)

Write-Host "================================================" -ForegroundColor Blue
Write-Host "  GCP STAGING RESOURCES SETUP                 " -ForegroundColor Blue
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"
$REGION = "us-central1"
$ZONE = "us-central1-a"

# Authenticate
if ($ServiceAccountKeyPath -and (Test-Path $ServiceAccountKeyPath)) {
    Write-Host "Using service account authentication..." -ForegroundColor Green
    gcloud auth activate-service-account --key-file=$ServiceAccountKeyPath
} else {
    Write-Host "Using default authentication..." -ForegroundColor Yellow
    $currentUser = gcloud config get-value account
    if (-not $currentUser) {
        gcloud auth login
    }
}

# Set project
Write-Host "Setting project to $PROJECT_ID..." -ForegroundColor Green
gcloud config set project $PROJECT_ID

# Enable APIs
Write-Host ""
Write-Host "Enabling required APIs..." -ForegroundColor Green
$APIs = @(
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com"
)

foreach ($api in $APIs) {
    Write-Host "  Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID --quiet
}

# Create Service Account if needed
Write-Host ""
Write-Host "Setting up service account..." -ForegroundColor Green

$saExists = gcloud iam service-accounts describe $ServiceAccountEmail --project=$PROJECT_ID 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating service account..."
    gcloud iam service-accounts create netra-staging-deploy `
        --display-name="Netra Staging Deployment Account" `
        --project=$PROJECT_ID
    
    # Grant necessary roles
    Write-Host "  Granting roles to service account..."
    $roles = @(
        "roles/run.admin",
        "roles/artifactregistry.admin",
        "roles/secretmanager.admin",
        "roles/iam.serviceAccountUser",
        "roles/cloudbuild.builds.editor",
        "roles/storage.admin"
    )
    
    foreach ($role in $roles) {
        gcloud projects add-iam-policy-binding $PROJECT_ID `
            --member="serviceAccount:$ServiceAccountEmail" `
            --role="$role" `
            --quiet
    }
    
    Write-Host "  Service account created and configured"
} else {
    Write-Host "  Service account already exists"
}

# Create Artifact Registry
Write-Host ""
Write-Host "Creating Artifact Registry..." -ForegroundColor Green
$REGISTRY_NAME = "netra-containers"

$registryExists = gcloud artifacts repositories describe $REGISTRY_NAME `
    --location=$REGION `
    --project=$PROJECT_ID 2>$null

if ($LASTEXITCODE -ne 0) {
    gcloud artifacts repositories create $REGISTRY_NAME `
        --repository-format=docker `
        --location=$REGION `
        --description="Container images for Netra staging deployment" `
        --project=$PROJECT_ID
    Write-Host "  Artifact Registry created: $REGISTRY_NAME"
} else {
    Write-Host "  Artifact Registry already exists: $REGISTRY_NAME"
}

# Create secrets
Write-Host ""
Write-Host "Creating secrets..." -ForegroundColor Green

$secretsToCreate = @{
    "jwt-secret" = [System.Guid]::NewGuid().ToString() + [System.Guid]::NewGuid().ToString()
    "auth-database-url" = "postgresql://user:pass@localhost:5432/auth_db"
    "openai-api-key" = "sk-placeholder-replace-with-real-key"
    "anthropic-api-key" = "sk-ant-placeholder-replace-with-real-key"
    "gemini-api-key" = "placeholder-replace-with-real-key"
}

$existingSecrets = gcloud secrets list --project=$PROJECT_ID --format="value(name)" 2>$null

foreach ($secret in $secretsToCreate.Keys) {
    if ($existingSecrets -notcontains $secret) {
        Write-Host "  Creating secret: $secret"
        echo $secretsToCreate[$secret] | gcloud secrets create $secret `
            --data-file=- `
            --project=$PROJECT_ID `
            --replication-policy="automatic"
    } else {
        Write-Host "  Secret already exists: $secret"
    }
}

# Create Cloud Storage bucket for backups
Write-Host ""
Write-Host "Creating Cloud Storage bucket..." -ForegroundColor Green
$BUCKET_NAME = "$PROJECT_ID-backups"

$bucketExists = gsutil ls -b gs://$BUCKET_NAME 2>$null
if ($LASTEXITCODE -ne 0) {
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME
    Write-Host "  Bucket created: $BUCKET_NAME"
} else {
    Write-Host "  Bucket already exists: $BUCKET_NAME"
}

# Setup monitoring workspace
Write-Host ""
Write-Host "Setting up monitoring..." -ForegroundColor Green
# Note: Monitoring workspace creation via CLI is limited
Write-Host "  Please visit https://console.cloud.google.com/monitoring to complete monitoring setup"

# Create firewall rules for Cloud Run
Write-Host ""
Write-Host "Configuring networking..." -ForegroundColor Green
# Cloud Run is serverless and doesn't need firewall rules, but we'll ensure VPC is configured
Write-Host "  Cloud Run networking is automatically configured"

# Generate service account key if needed
Write-Host ""
Write-Host "Service Account Key Management..." -ForegroundColor Green

if (-not $ServiceAccountKeyPath) {
    $keyPath = ".\gcp-sa-key.json"
    Write-Host "  Do you want to generate a service account key? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    
    if ($response -eq "Y" -or $response -eq "y") {
        gcloud iam service-accounts keys create $keyPath `
            --iam-account=$ServiceAccountEmail `
            --project=$PROJECT_ID
        
        Write-Host "  Service account key saved to: $keyPath" -ForegroundColor Green
        Write-Host "  IMPORTANT: Keep this key secure and add to .gitignore!" -ForegroundColor Red
    }
}

# Summary
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  RESOURCE SETUP COMPLETED                    " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Resources created/verified:" -ForegroundColor Cyan
Write-Host "  ✓ APIs enabled"
Write-Host "  ✓ Service account: $ServiceAccountEmail"
Write-Host "  ✓ Artifact Registry: $REGISTRY_NAME"
Write-Host "  ✓ Secrets created"
Write-Host "  ✓ Storage bucket: $BUCKET_NAME"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Update secret values with real API keys"
Write-Host "  2. Run deployment script: .\deploy-staging-automated.ps1"
Write-Host "  3. Configure monitoring dashboards"
Write-Host ""

# Export configuration
$config = @{
    project_id = $PROJECT_ID
    region = $REGION
    zone = $ZONE
    registry_name = $REGISTRY_NAME
    bucket_name = $BUCKET_NAME
    service_account = $ServiceAccountEmail
}

$config | ConvertTo-Json | Out-File -FilePath "gcp-staging-config.json"
Write-Host "Configuration saved to gcp-staging-config.json" -ForegroundColor Yellow