#!/bin/bash
# update-oauth-config.sh - Update OAuth configuration for Auth Service

set -e

echo "==================================="
echo "Updating OAuth Configuration"
echo "==================================="

# Configuration
PROJECT_ID=${1:-"netra-project"}
ENVIRONMENT=${2:-"staging"}
AUTH_DOMAIN=${3:-"auth.staging.netrasystems.ai"}

echo "Project: $PROJECT_ID"
echo "Environment: $ENVIRONMENT"
echo "Auth Domain: $AUTH_DOMAIN"

# Get current auth service URL
AUTH_SERVICE_URL=$(gcloud run services describe netra-auth-service \
    --region=us-central1 \
    --format="value(status.url)")

echo "Auth Service URL: $AUTH_SERVICE_URL"

# OAuth Redirect URIs that need to be configured
echo ""
echo "==================================="
echo "OAuth Redirect URIs to Configure"
echo "==================================="
echo ""
echo "Add these redirect URIs to your Google OAuth 2.0 Client ID:"
echo ""
echo "1. https://${AUTH_DOMAIN}/api/auth/callback"
echo "2. ${AUTH_SERVICE_URL}/api/auth/callback"
echo "3. https://app.staging.netrasystems.ai/api/auth/callback"
echo "4. https://app.staging.netrasystems.ai/api/auth/callback"
echo ""
echo "For development:"
echo "5. http://localhost:3000/api/auth/callback"
echo "6. http://localhost:8080/api/auth/callback"
echo ""

# JavaScript Origins
echo "==================================="
echo "JavaScript Origins to Configure"
echo "==================================="
echo ""
echo "Add these JavaScript origins:"
echo ""
echo "1. https://${AUTH_DOMAIN}"
echo "2. ${AUTH_SERVICE_URL}"
echo "3. https://app.staging.netrasystems.ai"
echo "4. https://app.staging.netrasystems.ai"
echo ""
echo "For development:"
echo "5. http://localhost:3000"
echo "6. http://localhost:8080"
echo ""

# Update environment variables in Cloud Run
echo "==================================="
echo "Updating Cloud Run Environment Variables"
echo "==================================="

# Update auth service environment variables
gcloud run services update netra-auth-service \
    --region=us-central1 \
    --update-env-vars="GOOGLE_OAUTH_REDIRECT_URI=https://${AUTH_DOMAIN}/api/auth/callback" \
    --update-env-vars="GOOGLE_OAUTH_JAVASCRIPT_ORIGINS=https://${AUTH_DOMAIN},https://app.staging.netrasystems.ai" \
    --update-env-vars="AUTH_DOMAIN=${AUTH_DOMAIN}"

# Update backend service to use auth service
gcloud run services update netra-backend \
    --region=us-central1 \
    --update-env-vars="AUTH_SERVICE_URL=${AUTH_SERVICE_URL}" \
    --update-env-vars="AUTH_SERVICE_DOMAIN=${AUTH_DOMAIN}"

# Update frontend service
gcloud run services update netra-frontend \
    --region=us-central1 \
    --update-env-vars="NEXT_PUBLIC_AUTH_SERVICE_URL=https://${AUTH_DOMAIN}" \
    --update-env-vars="NEXT_PUBLIC_AUTH_API_URL=https://${AUTH_DOMAIN}/api/auth"

echo ""
echo "==================================="
echo "Configuration Updated!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Go to Google Cloud Console > APIs & Services > Credentials"
echo "2. Edit your OAuth 2.0 Client ID"
echo "3. Add the redirect URIs and JavaScript origins listed above"
echo "4. Save the changes"
echo "5. Test the OAuth flow at https://${AUTH_DOMAIN}/api/auth/login"
echo ""
echo "DNS Configuration:"
echo "Add a CNAME record:"
echo "  ${AUTH_DOMAIN} -> ${AUTH_SERVICE_URL#https://}"