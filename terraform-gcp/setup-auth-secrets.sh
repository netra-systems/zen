#!/bin/bash
# setup-auth-secrets.sh - Set up all required secrets for Auth Service

set -e

# Colors for output
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

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Configuration
PROJECT_ID=${1:-"netra-staging"}
PROJECT_ID_NUMERICAL=${2:-"701982941522"}
ENVIRONMENT=${3:-"staging"}

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}       AUTH SERVICE SECRET SETUP                ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

print_info "Project: $PROJECT_ID"
print_info "Project ID (Numerical): $PROJECT_ID_NUMERICAL"
print_info "Environment: $ENVIRONMENT"
echo ""

# Set project
print_status "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable Secret Manager API
print_status "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# Function to create or update a secret
create_or_update_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    local DESCRIPTION=$3
    
    print_status "Setting up secret: $SECRET_NAME"
    
    # Check if secret exists
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        print_info "Secret $SECRET_NAME exists, updating..."
        echo -n "$SECRET_VALUE" | gcloud secrets versions add $SECRET_NAME --data-file=-
    else
        print_info "Creating new secret: $SECRET_NAME"
        echo -n "$SECRET_VALUE" | gcloud secrets create $SECRET_NAME \
            --data-file=- \
            --replication-policy="automatic" \
            --labels="environment=$ENVIRONMENT,service=auth"
    fi
}

# Generate random keys if they don't exist
print_status "Generating secure random keys..."

# JWT Secret Key
JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')
create_or_update_secret "jwt-secret-key-$ENVIRONMENT" "$JWT_SECRET" "JWT signing key"

# Fernet Key for encryption
FERNET_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 2>/dev/null || openssl rand -base64 32)
create_or_update_secret "fernet-key-$ENVIRONMENT" "$FERNET_KEY" "Fernet encryption key"

# Session Secret Key
SESSION_SECRET=$(openssl rand -base64 64 | tr -d '\n')
create_or_update_secret "session-secret-key-$ENVIRONMENT" "$SESSION_SECRET" "Session secret key"

# Google OAuth Credentials (you need to provide these)
print_status "Setting up OAuth credentials..."
echo ""
echo -e "${YELLOW}Please provide Google OAuth credentials:${NC}"
echo "You can get these from: https://console.cloud.google.com/apis/credentials"
echo ""

read -p "Enter Google OAuth Client ID for $ENVIRONMENT: " GOOGLE_CLIENT_ID
read -p "Enter Google OAuth Client Secret for $ENVIRONMENT: " GOOGLE_CLIENT_SECRET

if [ -n "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ]; then
    create_or_update_secret "google-client-id-$ENVIRONMENT" "$GOOGLE_CLIENT_ID" "Google OAuth Client ID"
    create_or_update_secret "google-client-secret-$ENVIRONMENT" "$GOOGLE_CLIENT_SECRET" "Google OAuth Client Secret"
else
    print_error "OAuth credentials not provided. Please add them manually later."
fi

# API Keys (optional - can be added later)
print_status "Setting up API keys..."
echo ""
echo -e "${YELLOW}Optional: Provide API keys (press Enter to skip):${NC}"

read -p "Enter Gemini API Key (or press Enter to skip): " GEMINI_API_KEY
if [ -n "$GEMINI_API_KEY" ]; then
    create_or_update_secret "gemini-api-key-$ENVIRONMENT" "$GEMINI_API_KEY" "Gemini API Key"
fi

read -p "Enter OpenAI API Key (or press Enter to skip): " OPENAI_API_KEY
if [ -n "$OPENAI_API_KEY" ]; then
    create_or_update_secret "openai-api-key-$ENVIRONMENT" "$OPENAI_API_KEY" "OpenAI API Key"
fi

read -p "Enter Anthropic API Key (or press Enter to skip): " ANTHROPIC_API_KEY
if [ -n "$ANTHROPIC_API_KEY" ]; then
    create_or_update_secret "anthropic-api-key-$ENVIRONMENT" "$ANTHROPIC_API_KEY" "Anthropic API Key"
fi

# Grant permissions to service accounts
print_status "Granting permissions to service accounts..."

# Auth service account
AUTH_SA="netra-auth-service@$PROJECT_ID.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $AUTH_SA --project=$PROJECT_ID &>/dev/null; then
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$AUTH_SA" \
        --role="roles/secretmanager.secretAccessor"
fi

# Cloud Run service account
CLOUDRUN_SA="netra-cloudrun@$PROJECT_ID.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $CLOUDRUN_SA --project=$PROJECT_ID &>/dev/null; then
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$CLOUDRUN_SA" \
        --role="roles/secretmanager.secretAccessor"
fi

# List all secrets
print_status "Listing all configured secrets:"
echo ""
gcloud secrets list --filter="labels.environment=$ENVIRONMENT" --format="table(name,created)"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}       SECRET SETUP COMPLETED                   ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
print_info "Next steps:"
echo "1. Ensure OAuth redirect URIs are configured in Google Cloud Console:"
echo "   - https://auth.staging.netrasystems.ai/api/auth/callback"
echo "   - https://netra-auth-service-$PROJECT_ID_NUMERICAL.us-central1.run.app/api/auth/callback"
echo "   - http://localhost:8080/api/auth/callback (for local testing)"
echo ""
echo "2. Deploy the auth service:"
echo "   ./deploy-auth-service.sh $PROJECT_ID us-central1 $ENVIRONMENT"
echo ""
echo "3. Update frontend configuration to use auth service endpoints"