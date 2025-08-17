#!/bin/bash
# deploy-auth-staging.sh - Complete Auth Service Deployment for Staging

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}    AUTH SERVICE STAGING DEPLOYMENT            ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Load staging configuration
PROJECT_ID="netra-staging"
PROJECT_ID_NUMERICAL="701982941522"
REGION="us-central1"
ENVIRONMENT="staging"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/netra-containers"

print_info "Configuration:"
print_info "  Project: $PROJECT_ID"
print_info "  Project ID (Numerical): $PROJECT_ID_NUMERICAL"
print_info "  Region: $REGION"
print_info "  Environment: $ENVIRONMENT"
print_info "  Registry: $REGISTRY"
echo ""

# Step 1: Set project
print_status "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Step 2: Enable required APIs
print_status "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    compute.googleapis.com

# Step 3: Configure Docker
print_status "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Step 4: Check if secrets exist
print_status "Checking required secrets..."
MISSING_SECRETS=()

REQUIRED_SECRETS=(
    "jwt-secret-key-staging"
    "fernet-key-staging"
    "session-secret-key-staging"
    "google-client-id-staging"
    "google-client-secret-staging"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! gcloud secrets describe $secret --project=$PROJECT_ID &>/dev/null; then
        MISSING_SECRETS+=($secret)
    fi
done

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    print_warning "Missing secrets: ${MISSING_SECRETS[@]}"
    print_info "Running secret setup script..."
    ./setup-auth-secrets.sh $PROJECT_ID $PROJECT_ID_NUMERICAL $ENVIRONMENT
fi

# Step 5: Build auth service Docker image
print_status "Building Auth Service Docker image..."
cd ..  # Move to project root

# Check if Dockerfile.auth exists
if [ ! -f "Dockerfile.auth" ]; then
    print_error "Dockerfile.auth not found!"
    exit 1
fi

# Build the image
docker build -f Dockerfile.auth \
    --build-arg ENVIRONMENT=$ENVIRONMENT \
    -t auth-service:latest \
    -t ${REGISTRY}/auth-service:latest \
    -t ${REGISTRY}/auth-service:${ENVIRONMENT} \
    .

# Step 6: Push image to registry
print_status "Pushing Auth Service image to registry..."
docker push ${REGISTRY}/auth-service:latest
docker push ${REGISTRY}/auth-service:${ENVIRONMENT}

# Step 7: Create/update service account
print_status "Setting up service account..."
cd terraform-gcp

# Check if service account exists
SA_NAME="netra-auth-service"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    print_info "Creating service account: $SA_NAME"
    gcloud iam service-accounts create $SA_NAME \
        --display-name="Netra Auth Service Account" \
        --project=$PROJECT_ID
fi

# Grant necessary roles
print_status "Granting IAM roles to service account..."
ROLES=(
    "roles/secretmanager.secretAccessor"
    "roles/cloudsql.client"
    "roles/logging.logWriter"
    "roles/monitoring.metricWriter"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$role" \
        --quiet
done

# Step 8: Get database connection info from existing deployment
print_status "Getting database connection information..."

# Check if database exists
DB_INSTANCE=$(gcloud sql instances list --project=$PROJECT_ID --format="value(name)" | grep -E "netra-postgres" | head -1)

if [ -z "$DB_INSTANCE" ]; then
    print_error "No PostgreSQL instance found. Please deploy the main infrastructure first."
    exit 1
fi

DB_IP=$(gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format="value(ipAddresses[0].ipAddress)")
print_info "Database IP: $DB_IP"

# Step 9: Deploy Auth Service to Cloud Run
print_status "Deploying Auth Service to Cloud Run..."

# Build the gcloud run deploy command with all environment variables
gcloud run deploy netra-auth-service \
    --image=${REGISTRY}/auth-service:latest \
    --region=${REGION} \
    --platform=managed \
    --port=8080 \
    --cpu=1 \
    --memory=512Mi \
    --min-instances=1 \
    --max-instances=10 \
    --concurrency=100 \
    --timeout=60 \
    --service-account=$SA_EMAIL \
    --allow-unauthenticated \
    --set-env-vars="SERVICE_NAME=auth-service" \
    --set-env-vars="ENVIRONMENT=$ENVIRONMENT" \
    --set-env-vars="LOG_LEVEL=INFO" \
    --set-env-vars="DATABASE_URL=postgresql://netra_user@${DB_IP}:5432/netra" \
    --set-env-vars="REDIS_URL=redis://localhost:6379" \
    --set-env-vars="JWT_ALGORITHM=HS256" \
    --set-env-vars="JWT_EXPIRATION_MINUTES=1440" \
    --set-env-vars="CORS_ORIGINS=https://staging.netrasystems.ai,https://app.staging.netrasystems.ai,https://auth.staging.netrasystems.ai,http://localhost:3000" \
    --set-env-vars="FRONTEND_URL=https://staging.netrasystems.ai" \
    --set-env-vars="BACKEND_URL=https://netra-backend-${PROJECT_ID_NUMERICAL}.${REGION}.run.app" \
    --set-env-vars="AUTH_SERVICE_URL=https://netra-auth-service-${PROJECT_ID_NUMERICAL}.${REGION}.run.app" \
    --set-env-vars="GCP_PROJECT_ID_NUMERICAL_STAGING=$PROJECT_ID_NUMERICAL" \
    --set-env-vars="SECRET_MANAGER_PROJECT_ID=$PROJECT_ID_NUMERICAL" \
    --set-env-vars="LOAD_SECRETS=true" \
    --set-env-vars="SECURE_HEADERS_ENABLED=true" \
    --set-env-vars="SESSION_COOKIE_NAME=netra_auth_session" \
    --set-env-vars="SESSION_COOKIE_SECURE=true" \
    --set-env-vars="SESSION_COOKIE_HTTPONLY=true" \
    --set-env-vars="SESSION_COOKIE_SAMESITE=lax" \
    --set-secrets="JWT_SECRET=jwt-secret-key-staging:latest" \
    --set-secrets="FERNET_KEY=fernet-key-staging:latest" \
    --set-secrets="SESSION_SECRET_KEY=session-secret-key-staging:latest" \
    --set-secrets="GOOGLE_OAUTH_CLIENT_ID_STAGING=google-client-id-staging:latest" \
    --set-secrets="GOOGLE_OAUTH_CLIENT_SECRET_STAGING=google-client-secret-staging:latest" \
    --quiet

# Step 10: Get service URL
print_status "Getting Auth Service URL..."
AUTH_SERVICE_URL=$(gcloud run services describe netra-auth-service \
    --region=${REGION} \
    --format='value(status.url)')

print_info "Auth Service URL: $AUTH_SERVICE_URL"

# Step 11: Test the service
print_status "Testing Auth Service endpoints..."

# Test health endpoint
if curl -s -o /dev/null -w "%{http_code}" "$AUTH_SERVICE_URL/health" | grep -q "200"; then
    print_status "✓ Health check passed"
else
    print_warning "Health check failed - service may still be starting"
fi

# Test API health endpoint
if curl -s -o /dev/null -w "%{http_code}" "$AUTH_SERVICE_URL/api/health" | grep -q "200"; then
    print_status "✓ API health check passed"
else
    print_warning "API health check failed"
fi

# Step 12: Update OAuth redirect URIs reminder
echo ""
echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}         IMPORTANT: OAuth Configuration         ${NC}"
echo -e "${YELLOW}================================================${NC}"
echo ""
print_info "Please update your Google OAuth application with these redirect URIs:"
echo "  1. ${AUTH_SERVICE_URL}/api/auth/callback"
echo "  2. https://auth.staging.netrasystems.ai/api/auth/callback"
echo "  3. http://localhost:8080/api/auth/callback (for local testing)"
echo ""
print_info "Go to: https://console.cloud.google.com/apis/credentials"
echo ""

# Step 13: Output summary
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}    AUTH SERVICE DEPLOYMENT COMPLETE           ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
print_info "Service Details:"
echo "  - URL: $AUTH_SERVICE_URL"
echo "  - Environment: $ENVIRONMENT"
echo "  - Project: $PROJECT_ID"
echo "  - Region: $REGION"
echo ""
print_info "Test the OAuth flow:"
echo "  curl ${AUTH_SERVICE_URL}/api/auth/login"
echo ""
print_info "View logs:"
echo "  gcloud run logs read netra-auth-service --region=$REGION"
echo ""
print_info "To update the service:"
echo "  ./deploy-auth-staging.sh"