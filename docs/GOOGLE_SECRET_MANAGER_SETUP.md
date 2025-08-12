# Google Secret Manager Setup for Netra Staging

This document lists all the secrets that need to be created in Google Secret Manager for the staging environment to function properly.

## Important: Staging Secret Naming Convention

**In the staging environment, all secrets MUST have a `-staging` suffix appended to their names.**

For example:
- Configuration expects: `gemini-api-key`
- Staging secret name: `gemini-api-key-staging`

The application automatically appends `-staging` when fetching secrets in the staging environment.

## Project Information
- **Staging Project Name**: `netra-staging`
- **Staging Project Number**: (Get with `gcloud projects describe netra-staging --format="value(projectNumber)"`)
- **Production Project Number**: `304612253870`

**Important**: Google Secret Manager API requires the numerical project ID, not the project name.

## Required Secrets (MUST have for deployment to work)

These secrets are critical and must be present for the application to start.

**Note**: In staging, append `-staging` to all secret names!

| Config Name | Staging Secret Name | Description | Example/Format |
|------------|-------------------|-------------|----------------|
| `gemini-api-key` | `gemini-api-key-staging` | **REQUIRED** - Gemini API key for all default LLM operations | `AIza...` |
| `jwt-secret-key` | `jwt-secret-key-staging` | **REQUIRED** - JWT token signing key (min 32 chars) | Random 64-char string |
| `fernet-key` | `fernet-key-staging` | **REQUIRED** - Encryption key for sensitive data | Use `cryptography.fernet.Fernet.generate_key()` |
| `google-client-id` | `google-client-id-staging` | **REQUIRED** - Google OAuth client ID | `xxx.apps.googleusercontent.com` |
| `google-client-secret` | `google-client-secret-staging` | **REQUIRED** - Google OAuth client secret | OAuth client secret |

## Optional LLM API Keys

These are for branded LLM providers. If not provided, those specific providers will be skipped during initialization.

**Note**: In staging, append `-staging` to all secret names!

| Config Name | Staging Secret Name | Description | Provider |
|------------|-------------------|-------------|----------|
| `anthropic-api-key` | `anthropic-api-key-staging` | Anthropic Claude API key | Optional - Anthropic models |
| `openai-api-key` | `openai-api-key-staging` | OpenAI API key | Optional - GPT models |
| `cohere-api-key` | `cohere-api-key-staging` | Cohere API key | Optional - Cohere models |
| `mistral-api-key` | `mistral-api-key-staging` | Mistral API key | Optional - Mistral models |

## Database and Cache Secrets

**Note**: In staging, append `-staging` to all secret names!

| Config Name | Staging Secret Name | Description | Required for |
|------------|-------------------|-------------|--------------|
| `clickhouse-default-password` | `clickhouse-default-password-staging` | ClickHouse password | Analytics features |
| `clickhouse-development-password` | `clickhouse-development-password-staging` | ClickHouse password for dev | Analytics features |
| `redis-default` | `redis-default-staging` | Redis password | Caching features |

## Observability and Monitoring

**Note**: In staging, append `-staging` to all secret names!

| Config Name | Staging Secret Name | Description | Used for |
|------------|-------------------|-------------|----------|
| `langfuse-secret-key` | `langfuse-secret-key-staging` | LangFuse secret key | LLM monitoring |
| `langfuse-public-key` | `langfuse-public-key-staging` | LangFuse public key | LLM monitoring |
| `sentry-dsn` | `sentry-dsn-staging` | Sentry DSN for error tracking | Error reporting |

## Communication and Notifications

**Note**: In staging, append `-staging` to all secret names!

| Config Name | Staging Secret Name | Description | Used for |
|------------|-------------------|-------------|----------|
| `slack-webhook-url` | `slack-webhook-url-staging` | Slack webhook for notifications | Alert notifications |
| `sendgrid-api-key` | `sendgrid-api-key-staging` | SendGrid API key for emails | Email notifications |

## How to Create Secrets

### Using gcloud CLI:

```bash
# Set the project
gcloud config set project netra-staging

# Create a secret (example with gemini-api-key-staging for staging environment)
echo -n "YOUR_API_KEY_HERE" | gcloud secrets create gemini-api-key-staging \
    --data-file=- \
    --replication-policy="automatic"

# Grant access to the service account
gcloud secrets add-iam-policy-binding gemini-api-key-staging \
    --member="serviceAccount:staging-environments@netra-staging.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Using Google Cloud Console:

1. Go to [Secret Manager](https://console.cloud.google.com/security/secret-manager) in the staging project
2. Click "Create Secret"
3. Enter the secret name (must match exactly from the table above)
4. Enter the secret value
5. Click "Create"
6. Grant access to the service account `staging-environments@netra-staging.iam.gserviceaccount.com`

## Batch Creation Script

Save this as `create-secrets.sh` and run it:

```bash
#!/bin/bash

PROJECT_NAME="netra-staging"
# Get the numerical project ID required by Secret Manager
PROJECT_ID=$(gcloud projects describe $PROJECT_NAME --format="value(projectNumber)")
SERVICE_ACCOUNT="staging-environments@netra-staging.iam.gserviceaccount.com"

echo "Using project: $PROJECT_NAME (ID: $PROJECT_ID)"

# Function to create a secret with -staging suffix
create_secret() {
    CONFIG_NAME=$1
    SECRET_VALUE=$2
    SECRET_NAME="${CONFIG_NAME}-staging"  # Append -staging suffix
    
    echo "Creating secret: $SECRET_NAME"
    echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --data-file=- \
        --replication-policy="automatic" 2>/dev/null || \
    echo "Secret $SECRET_NAME already exists, updating..."
    
    echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --data-file=-
    
    gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor"
}

# Required secrets (will be created with -staging suffix)
create_secret "gemini-api-key" "YOUR_GEMINI_API_KEY"
create_secret "jwt-secret-key" "$(openssl rand -hex 32)"
create_secret "fernet-key" "$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
create_secret "google-client-id" "YOUR_OAUTH_CLIENT_ID"
create_secret "google-client-secret" "YOUR_OAUTH_CLIENT_SECRET"

# Optional LLM keys (will be created with -staging suffix)
# create_secret "anthropic-api-key" "YOUR_ANTHROPIC_KEY"
# create_secret "openai-api-key" "YOUR_OPENAI_KEY"
# create_secret "cohere-api-key" "YOUR_COHERE_KEY"
# create_secret "mistral-api-key" "YOUR_MISTRAL_KEY"

echo "Secrets creation complete!"
```

## Verification

To verify secrets are properly created:

```bash
# List all secrets
gcloud secrets list --project=netra-staging

# Read a secret value (for testing)
gcloud secrets versions access latest --secret="gemini-api-key-staging" --project=netra-staging

# Check IAM bindings
gcloud secrets get-iam-policy gemini-api-key-staging --project=netra-staging
```

## Important Notes

1. **Gemini API Key is Required**: The application will fail to start without the `gemini-api-key-staging` secret in staging
2. **Other LLM keys are optional**: If not provided, those specific providers will be skipped
3. **Service Account**: Ensure the Cloud Run service account has access to read these secrets
4. **Secret Names**: Must match exactly as listed in the tables above
5. **Rotation**: Secrets can be rotated by adding new versions through the console or CLI

## Troubleshooting

If secrets are not loading:

1. Check Cloud Run logs for secret loading errors
2. Verify the service account has `roles/secretmanager.secretAccessor` role
3. Ensure the `LOAD_SECRETS=true` and `GCP_PROJECT_ID=netra-staging` environment variables are set
4. Check that secret names match exactly (case-sensitive)
5. Verify the secrets exist in the correct project

## Environment Variable Fallback

If Secret Manager fails, the system will fall back to environment variables with these mappings:
- `gemini-api-key` → `GEMINI_API_KEY`
- `jwt-secret-key` → `JWT_SECRET_KEY`
- `fernet-key` → `FERNET_KEY`
- etc.

This is primarily for local development and should not be relied upon in staging/production.