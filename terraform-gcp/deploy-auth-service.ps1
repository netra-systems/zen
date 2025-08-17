# deploy-auth-service.ps1 - Deploy Auth Service to GCP (Windows)

param(
    [string]$ProjectId = "netra-project",
    [string]$Region = "us-central1",
    [string]$Environment = "staging"
)

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Deploying Netra Auth Service" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

Write-Host "Project: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Environment: $Environment"

# Check if gcloud is installed
try {
    gcloud version | Out-Null
} catch {
    Write-Host "Error: gcloud CLI is not installed" -ForegroundColor Red
    exit 1
}

# Check if docker is installed
try {
    docker version | Out-Null
} catch {
    Write-Host "Error: Docker is not installed" -ForegroundColor Red
    exit 1
}

# Set project
Write-Host "Setting GCP project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable required APIs
Write-Host "Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    artifactregistry.googleapis.com `
    secretmanager.googleapis.com `
    compute.googleapis.com `
    certificatemanager.googleapis.com

# Build and push auth service image
Write-Host "Building Auth Service Docker image..." -ForegroundColor Yellow
Push-Location ..
docker build -f Dockerfile.auth -t auth-service:latest .

# Tag for Artifact Registry
Write-Host "Tagging image for Artifact Registry..." -ForegroundColor Yellow
docker tag auth-service:latest `
    "${Region}-docker.pkg.dev/${ProjectId}/netra-containers/auth-service:latest"

# Configure docker for Artifact Registry
Write-Host "Configuring Docker for Artifact Registry..." -ForegroundColor Yellow
gcloud auth configure-docker "${Region}-docker.pkg.dev"

# Push image
Write-Host "Pushing image to Artifact Registry..." -ForegroundColor Yellow
docker push "${Region}-docker.pkg.dev/${ProjectId}/netra-containers/auth-service:latest"

# Deploy with Terraform
Write-Host "Deploying infrastructure with Terraform..." -ForegroundColor Yellow
Pop-Location
Push-Location terraform-gcp

# Initialize Terraform
terraform init `
    -backend-config="bucket=netra-terraform-state-${ProjectId}" `
    -backend-config="prefix=terraform/state/${Environment}"

# Create/update infrastructure
Write-Host "Deploying Auth Service infrastructure..." -ForegroundColor Yellow
terraform apply `
    -var="project_id=${ProjectId}" `
    -var="region=${Region}" `
    -var="environment=${Environment}" `
    -target=google_cloud_run_service.auth `
    -target=google_service_account.auth_service `
    -target=google_project_iam_member.auth_service_sql `
    -target=google_project_iam_member.auth_service_secrets `
    -target=google_project_iam_member.auth_service_logging `
    -target=google_cloud_run_service_iam_member.auth_public `
    -target=google_secret_manager_secret.session_secret `
    -target=google_secret_manager_secret_version.session_secret `
    -auto-approve

# Deploy Load Balancer components
Write-Host "Deploying Load Balancer for Auth Service..." -ForegroundColor Yellow
terraform apply `
    -var="project_id=${ProjectId}" `
    -var="region=${Region}" `
    -var="environment=${Environment}" `
    -target=google_compute_region_network_endpoint_group.auth_neg `
    -target=google_compute_backend_service.auth `
    -target=google_compute_url_map.auth `
    -target=google_compute_managed_ssl_certificate.auth `
    -target=google_compute_target_https_proxy.auth `
    -target=google_compute_global_address.auth `
    -target=google_compute_global_forwarding_rule.auth `
    -target=google_compute_url_map.auth_http_redirect `
    -target=google_compute_target_http_proxy.auth_http `
    -target=google_compute_global_forwarding_rule.auth_http `
    -auto-approve

# Get outputs
Write-Host "===================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

terraform output -json | Out-File -FilePath auth-deployment-info.json

# Display URLs
$AuthServiceUrl = terraform output -raw auth_service_url
$AuthServiceDomain = terraform output -raw auth_service_domain
$AuthServiceIp = terraform output -raw auth_service_ip

Write-Host "Auth Service URL: $AuthServiceUrl" -ForegroundColor Cyan
Write-Host "Auth Service Domain: $AuthServiceDomain" -ForegroundColor Cyan
Write-Host "Auth Service IP: $AuthServiceIp" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update DNS records to point $AuthServiceDomain to $AuthServiceIp"
Write-Host "2. Update OAuth redirect URIs in Google Cloud Console:"
Write-Host "   - https://$AuthServiceDomain/api/auth/callback"
Write-Host "   - $AuthServiceUrl/api/auth/callback"
Write-Host "3. Update frontend configuration to use the auth service"
Write-Host "4. Test OAuth flow at https://$AuthServiceDomain/api/auth/login"

Pop-Location