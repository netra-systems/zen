# Deploy All Staging Script for Netra Apex
# This script deploys all components to GCP staging environment

param(
    [switch]$SkipTerraform,
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Info "==========================================="
Write-Info "   Netra Apex - Staging Deployment"
Write-Info "==========================================="
Write-Host ""

# Check prerequisites
Write-Info "Checking prerequisites..."

# Check for Google Cloud SDK
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Error "Google Cloud SDK is not installed. Please install it first."
    exit 1
}

# Check for Terraform
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
    Write-Error "Terraform is not installed. Please install it first."
    exit 1
}

# Check for Node.js and npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js/npm is not installed. Please install it first."
    exit 1
}

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed. Please install it first."
    exit 1
}

Write-Success "✓ All prerequisites met"
Write-Host ""

# Set GCP project
$GCP_PROJECT = "netra-staging"
Write-Info "Setting GCP project to: $GCP_PROJECT"
gcloud config set project $GCP_PROJECT

# Authenticate with GCP if needed
Write-Info "Checking GCP authentication..."
$authList = gcloud auth list --format=json | ConvertFrom-Json
if ($authList.Count -eq 0) {
    Write-Info "No active GCP authentication found. Please authenticate..."
    gcloud auth login
    gcloud auth application-default login
} else {
    Write-Success "✓ GCP authentication active"
}

Write-Host ""

# Deploy Terraform infrastructure
if (-not $SkipTerraform) {
    Write-Info "==========================================="
    Write-Info "   Deploying Terraform Infrastructure"
    Write-Info "==========================================="
    Write-Host ""
    
    Push-Location terraform-gcp
    
    try {
        # Initialize Terraform
        Write-Info "Initializing Terraform..."
        terraform init
        
        # Plan deployment
        Write-Info "Planning Terraform deployment..."
        terraform plan -var-file="terraform.staging.tfvars" -out=staging.tfplan
        
        if (-not $Force) {
            Write-Warning "Review the plan above. Deploy? (Y/N)"
            $response = Read-Host
            if ($response -ne 'Y' -and $response -ne 'y') {
                Write-Warning "Deployment cancelled by user"
                Pop-Location
                exit 0
            }
        }
        
        # Apply deployment
        Write-Info "Applying Terraform configuration..."
        terraform apply staging.tfplan
        
        # Get outputs
        Write-Info "Getting deployment outputs..."
        $outputs = terraform output -json | ConvertFrom-Json
        
        # Store outputs for later use
        $BACKEND_URL = $outputs.backend_url.value
        $FRONTEND_URL = $outputs.frontend_url.value
        $DB_HOST = $outputs.database_host.value
        $AUTH_URL = $outputs.auth_service_url.value
        
        Write-Success "✓ Terraform infrastructure deployed"
        Write-Info "Backend URL: $BACKEND_URL"
        Write-Info "Frontend URL: $FRONTEND_URL"
        Write-Info "Database Host: $DB_HOST"
        Write-Info "Auth Service URL: $AUTH_URL"
        
    } catch {
        Write-Error "Terraform deployment failed: $_"
        Pop-Location
        exit 1
    }
    
    Pop-Location
    Write-Host ""
} else {
    Write-Warning "Skipping Terraform deployment"
    
    # Try to get existing outputs
    Push-Location terraform-gcp
    $outputs = terraform output -json 2>$null | ConvertFrom-Json
    if ($outputs) {
        $BACKEND_URL = $outputs.backend_url.value
        $FRONTEND_URL = $outputs.frontend_url.value
        $DB_HOST = $outputs.database_host.value
        $AUTH_URL = $outputs.auth_service_url.value
    }
    Pop-Location
}

# Deploy Backend
if (-not $SkipBackend) {
    Write-Info "==========================================="
    Write-Info "   Deploying Backend Application"
    Write-Info "==========================================="
    Write-Host ""
    
    try {
        # Create requirements file for Cloud Run
        Write-Info "Preparing backend deployment..."
        
        # Create app.yaml for App Engine or Dockerfile for Cloud Run
        $dockerfileContent = @"
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY .env.staging .env

# Set environment variables
ENV PORT=8080
ENV ENVIRONMENT=staging

# Run migrations and start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080
"@
        
        $dockerfileContent | Out-File -FilePath Dockerfile -Encoding UTF8
        
        # Build and deploy to Cloud Run
        Write-Info "Building and deploying backend to Cloud Run..."
        
        $serviceName = "netra-backend-staging"
        $region = "us-central1"
        
        # Build container
        Write-Info "Building container image..."
        gcloud builds submit --tag gcr.io/$GCP_PROJECT/$serviceName .
        
        # Deploy to Cloud Run
        Write-Info "Deploying to Cloud Run..."
        gcloud run deploy $serviceName `
            --image gcr.io/$GCP_PROJECT/$serviceName `
            --platform managed `
            --region $region `
            --allow-unauthenticated `
            --set-env-vars "DATABASE_URL=$DB_HOST,ENVIRONMENT=staging" `
            --memory 2Gi `
            --cpu 2 `
            --timeout 60 `
            --max-instances 10
        
        Write-Success "✓ Backend deployed successfully"
        
    } catch {
        Write-Error "Backend deployment failed: $_"
        exit 1
    }
    
    Write-Host ""
} else {
    Write-Warning "Skipping backend deployment"
}

# Deploy Frontend
if (-not $SkipFrontend) {
    Write-Info "==========================================="
    Write-Info "   Deploying Frontend Application"
    Write-Info "==========================================="
    Write-Host ""
    
    Push-Location frontend
    
    try {
        # Install dependencies
        Write-Info "Installing frontend dependencies..."
        npm ci
        
        # Build frontend
        Write-Info "Building frontend application..."
        $env:NEXT_PUBLIC_API_URL = $BACKEND_URL
        $env:NEXT_PUBLIC_WS_URL = $BACKEND_URL.Replace("https://", "wss://")
        $env:NEXT_PUBLIC_AUTH_URL = $AUTH_URL
        npm run build
        
        # Deploy to Cloud Run or Firebase Hosting
        Write-Info "Deploying frontend..."
        
        # Option 1: Deploy to Firebase Hosting
        if (Get-Command firebase -ErrorAction SilentlyContinue) {
            firebase deploy --only hosting --project $GCP_PROJECT
        }
        # Option 2: Deploy to Cloud Run
        else {
            # Create Dockerfile for Next.js
            $nextDockerfile = @"
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
RUN npm ci --only=production

ENV PORT=3000
ENV NODE_ENV=production

EXPOSE 3000
CMD ["npm", "start"]
"@
            
            $nextDockerfile | Out-File -FilePath Dockerfile -Encoding UTF8
            
            # Build and deploy
            gcloud builds submit --tag gcr.io/$GCP_PROJECT/netra-frontend-staging .
            gcloud run deploy netra-frontend-staging `
                --image gcr.io/$GCP_PROJECT/netra-frontend-staging `
                --platform managed `
                --region us-central1 `
                --allow-unauthenticated `
                --memory 1Gi `
                --cpu 1
        }
        
        Write-Success "✓ Frontend deployed successfully"
        
    } catch {
        Write-Error "Frontend deployment failed: $_"
        Pop-Location
        exit 1
    }
    
    Pop-Location
    Write-Host ""
} else {
    Write-Warning "Skipping frontend deployment"
}

# Run post-deployment checks
Write-Info "==========================================="
Write-Info "   Running Post-Deployment Checks"
Write-Info "==========================================="
Write-Host ""

# Backend health check
if ($BACKEND_URL) {
    try {
        $response = Invoke-WebRequest -Uri "$BACKEND_URL/health" -Method Get -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ Backend service is healthy"
        }
    } catch {
        Write-Warning "✗ Backend health check failed"
    }
}

# Frontend check
if ($FRONTEND_URL) {
    try {
        $response = Invoke-WebRequest -Uri $FRONTEND_URL -Method Get -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ Frontend is accessible"
        }
    } catch {
        Write-Warning "✗ Frontend check failed"
    }
}

# Auth service check
if ($AUTH_URL) {
    try {
        $response = Invoke-WebRequest -Uri "$AUTH_URL/health" -Method Get -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ Auth service is healthy"
        }
    } catch {
        Write-Warning "✗ Auth service health check failed"
    }
}

Write-Host ""
Write-Success "Deployment complete! Services may take a few minutes to fully start."
Write-Host ""
Write-Info "Next steps:"
Write-Info "  1. Update DNS records to point to the new service URLs"
Write-Info "  2. Configure load balancing if needed"
Write-Info "  3. Set up monitoring and alerting"
Write-Info "  4. Run integration tests"
Write-Host ""
Write-Warning "To destroy this deployment, run:"
Write-Info "  cd terraform-gcp"
Write-Info "  terraform destroy -var-file=terraform.staging.tfvars"