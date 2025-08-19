# Creating Gemini API Key for Staging Environment

## Quick Setup Script

Save this as `setup-gemini-staging.sh` and run it:

```bash
#!/bin/bash

# Configuration
PROJECT_NAME="netra-staging"
SECRET_NAME="gemini-api-key-staging"  # Note the -staging suffix!
SERVICE_ACCOUNT="staging-environments@netra-staging.iam.gserviceaccount.com"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== Gemini API Key Setup for Staging ===${NC}"
echo -e "${YELLOW}Project: $PROJECT_NAME${NC}"
echo -e "${YELLOW}Secret Name: $SECRET_NAME${NC}"
echo ""

# Step 1: Set project
echo -e "${GREEN}Step 1: Setting GCP project...${NC}"
gcloud config set project $PROJECT_NAME

# Step 2: Enable API
echo -e "${GREEN}Step 2: Enabling Generative Language API...${NC}"
gcloud services enable generativelanguage.googleapis.com

# Step 3: Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_NAME --format="value(projectNumber)")
echo -e "${GREEN}Project Number: $PROJECT_NUMBER${NC}"

# Step 4: Create API Key
echo -e "${YELLOW}Step 3: Create your Gemini API Key${NC}"
echo -e "${YELLOW}Please visit: https://aistudio.google.com/app/apikey${NC}"
echo -e "${YELLOW}Instructions:${NC}"
echo "  1. Click 'Create API key'"
echo "  2. Select 'Create API key in existing project'"
echo "  3. Choose project: $PROJECT_NAME"
echo "  4. Copy the generated key (starts with AIza...)"
echo ""
read -sp "Paste your Gemini API key here: " API_KEY
echo ""

# Step 5: Create secret with -staging suffix
echo -e "${GREEN}Step 4: Creating secret in Secret Manager...${NC}"
echo -n "$API_KEY" | gcloud secrets create $SECRET_NAME \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$PROJECT_NAME 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Secret created successfully${NC}"
else
    echo -e "${YELLOW}Secret already exists, updating to new version...${NC}"
    echo -n "$API_KEY" | gcloud secrets versions add $SECRET_NAME \
        --data-file=- \
        --project=$PROJECT_NAME
    echo -e "${GREEN}✅ Secret updated successfully${NC}"
fi

# Step 6: Grant access
echo -e "${GREEN}Step 5: Granting access to service account...${NC}"
gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_NAME \
    --quiet

# Step 7: Verify
echo -e "${GREEN}Step 6: Verifying secret...${NC}"
gcloud secrets describe $SECRET_NAME --project=$PROJECT_NAME

# Test the secret can be accessed
echo -e "${GREEN}Step 7: Testing secret access...${NC}"
SECRET_VALUE=$(gcloud secrets versions access latest --secret=$SECRET_NAME --project=$PROJECT_NAME 2>/dev/null)
if [ -n "$SECRET_VALUE" ]; then
    echo -e "${GREEN}✅ Secret is accessible (value hidden for security)${NC}"
else
    echo -e "${RED}❌ Failed to access secret${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Important Notes:${NC}"
echo "• Secret name in Secret Manager: $SECRET_NAME"
echo "• Config expects: gemini-api-key (without suffix)"
echo "• The app automatically adds -staging suffix when running in staging"
echo "• This key will be loaded when ENVIRONMENT=staging or K_SERVICE is set"
echo ""
echo -e "${YELLOW}To manually verify the secret:${NC}"
echo "gcloud secrets versions access latest --secret=$SECRET_NAME --project=$PROJECT_NAME"
```

## Manual Steps

### 1. Create the Gemini API Key

Visit https://aistudio.google.com/app/apikey and:
1. Click "Create API key"
2. Select "Create API key in existing project"
3. Choose `netra-staging`
4. Copy the generated key

### 2. Add to Secret Manager with -staging Suffix

```bash
# Set project
gcloud config set project netra-staging

# Create the secret WITH -staging suffix
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key-staging \
    --data-file=- \
    --replication-policy="automatic"

# Grant access to service account
gcloud secrets add-iam-policy-binding gemini-api-key-staging \
    --member="serviceAccount:staging-environments@netra-staging.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Verify the Setup

```bash
# List all secrets (should show gemini-api-key-staging)
gcloud secrets list --project=netra-staging

# Test reading the secret
gcloud secrets versions access latest --secret=gemini-api-key-staging --project=netra-staging
```

## All Required Staging Secrets

Here's a complete list of secrets needed for staging (all with -staging suffix):

```bash
# Required secrets
gemini-api-key-staging
jwt-secret-key-staging
fernet-key-staging
google-client-id-staging
google-client-secret-staging

# Optional (if you have them)
anthropic-api-key-staging
openai-api-key-staging
cohere-api-key-staging
mistral-api-key-staging
langfuse-secret-key-staging
langfuse-public-key-staging
sentry-dsn-staging
slack-webhook-url-staging
```

## How the Staging Suffix Works

1. **Configuration expects**: `gemini-api-key` (no suffix)
2. **Secret Manager stores**: `gemini-api-key-staging` (with suffix)
3. **App behavior**: When `ENVIRONMENT=staging` or running in Cloud Run, the app automatically appends `-staging` when fetching secrets
4. **Result**: Complete isolation between production and staging secrets

## Troubleshooting

### Secret not found
```bash
# Check if secret exists with correct name
gcloud secrets list --project=netra-staging | grep gemini

# Should show: gemini-api-key-staging (NOT gemini-api-key)
```

### Permission denied
```bash
# Check IAM bindings
gcloud secrets get-iam-policy gemini-api-key-staging --project=netra-staging

# Should show staging-environments@netra-staging.iam.gserviceaccount.com with secretAccessor role
```

### App not loading secret
Check logs for:
- "Fetching secret: gemini-api-key-staging (original: gemini-api-key)"
- Confirm ENVIRONMENT=staging or K_SERVICE is set
- Verify GCP_PROJECT_ID_NUMERICAL_STAGING is set to the numerical project ID

## Testing the API Key

```bash
# Test the key directly
API_KEY=$(gcloud secrets versions access latest --secret=gemini-api-key-staging --project=netra-staging)

curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Say hello"}]}]}'
```

Should return a valid response if the key is working.