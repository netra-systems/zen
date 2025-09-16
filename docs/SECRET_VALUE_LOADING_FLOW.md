# Secret Value Loading Flow - Complete Timeline

**CRITICAL UNDERSTANDING:** Secrets go through multiple stages, and failures can occur silently at each stage.

## Timeline of Secret Loading

### Stage 1: Secret Creation (One-time setup)
**When:** Before first deployment
**Where:** Developer machine or CI/CD pipeline
**What happens:**
```bash
# Secret is created in Google Secret Manager
gcloud secrets create jwt-secret-staging --data-file=- <<< "actual-secret-value-here"
```
**Can fail if:**
- Secret name already exists
- User lacks permission to create secrets
- Value is empty or invalid

---

### Stage 2: IAM Permission Grant (One-time setup)
**When:** After secret creation, before deployment
**Where:** Developer machine or CI/CD pipeline
**What happens:**
```bash
# Grant service account access to the secret
gcloud secrets add-iam-policy-binding jwt-secret-staging \
  --member="serviceAccount:netra-staging-deploy@netra-staging.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```
**Can fail if:**
- Service account doesn't exist
- User lacks permission to modify IAM policies
- **SILENT FAILURE:** If skipped, deployment succeeds but runtime fails

---

### Stage 3: Deployment Configuration (Every deployment)
**When:** During `gcloud run deploy` command
**Where:** Deployment script (`deploy_to_gcp_actual.py`)
**What happens:**
```python
# Script creates environment variable mappings
env_vars = [
    {
        "name": "JWT_SECRET_STAGING",
        "valueFrom": {
            "secretKeyRef": {
                "name": "jwt-secret-staging",
                "key": "latest"
            }
        }
    }
]
# These are passed to gcloud run deploy --set-env-vars
```
**Result:** Cloud Run service YAML contains references to secrets, NOT the actual values
**Can fail if:**
- Secret name is misspelled
- **DOES NOT FAIL if service account lacks access!**

---

### Stage 4: Container Startup - Secret Injection (Every container start)
**When:** When Cloud Run starts a new container instance
**Where:** Cloud Run infrastructure (Google-managed)
**What happens:**

1. Cloud Run reads the service configuration YAML
2. For each `secretKeyRef`, Cloud Run:
   - Uses the service account identity
   - Attempts to read the secret from Secret Manager
   - If successful, injects value as environment variable
   - **If fails, SILENTLY sets variable to empty/undefined**

**THIS IS THE CRITICAL SILENT FAILURE POINT**

```
If service account has access:
  JWT_SECRET_STAGING = "actual-secret-value-here"

If service account lacks access:
  JWT_SECRET_STAGING = undefined  # Variable doesn't exist at all!
```

**Can fail if:**
- Service account lacks `secretAccessor` role
- Secret was deleted after deployment
- Secret version is disabled
- **SILENT FAILURE:** No error is reported by Cloud Run

---

### Stage 5: Application Startup - Environment Loading (Every container start)
**When:** Python application starts
**Where:** Application code (e.g., `shared/isolated_environment.py`)
**What happens:**
```python
# Application tries to read environment variables
import os
jwt_secret = os.environ.get('JWT_SECRET_STAGING')  # Returns None if not set

# IsolatedEnvironment wraps this
env = get_env()
jwt_secret = env.get('JWT_SECRET_STAGING')  # Also returns None if not set
```
**Result:** Application has either the actual value or None
**Can fail if:**
- Variable wasn't injected by Cloud Run (Stage 4 failed)
- Variable name mismatch

---

### Stage 6: Application Validation (Every container start)
**When:** During application initialization
**Where:** `shared/configuration/central_config_validator.py`
**What happens:**
```python
def validate_all_requirements(self):
    jwt_secret = self.env_getter("JWT_SECRET_STAGING")
    if not jwt_secret:
        raise ValueError("JWT_SECRET_STAGING is required in staging")
```
**Result:** Application crashes if required variables are missing
**Can fail if:**
- Any previous stage failed
- Value exists but doesn't meet requirements (too short, placeholder, etc.)

---

## The Actual Values Flow

### Where values physically exist:

1. **Secret Manager Storage:** The ONLY place actual secret values are stored
   ```
   Project: netra-staging
   Secret: jwt-secret-staging
   Value: "actual-secret-value-here"
   ```

2. **In Transit (Brief):** When Cloud Run reads from Secret Manager
   - Uses service account credentials
   - TLS-encrypted API call
   - Value briefly in Cloud Run's memory

3. **Container Environment:** After successful injection
   - Value exists as Linux environment variable
   - Accessible via `os.environ` in Python
   - Persists for container lifetime

4. **Application Memory:** After application reads environment
   - Stored in Python variables
   - May be cached by application
   - Used for actual operations (JWT signing, etc.)

### Where values NEVER exist:

1. **Cloud Run Service YAML:** Only contains references, never values
2. **Deployment Scripts:** Only handle secret names, not values
3. **Git Repository:** Should never contain actual secret values
4. **Container Image:** Built without secrets, injected at runtime
5. **Logs:** Should be filtered to prevent secret exposure

---

## Common Failure Patterns

### Pattern 1: Service Account Mismatch
```
Secret Manager: Grants access to serviceAccount:netra-cloudrun@...
Cloud Run: Runs as serviceAccount:netra-staging-deploy@...
Result: Secrets fail to load, variables are undefined
```

### Pattern 2: Deployment vs Runtime Confusion
```
Deployment: SUCCESS (references are valid)
Runtime: FAILURE (can't actually access secrets)
Developer: Confused because "deployment succeeded"
```

### Pattern 3: Silent Undefined Variables
```python
# This doesn't error, just returns None
jwt_secret = os.environ.get('JWT_SECRET_STAGING')

# Later code assumes it has a value
jwt.encode(payload, jwt_secret, ...)  # Crashes here, not earlier
```

---

## Validation Points

### ✅ GOOD: Validate at deployment time
```python
def deploy():
    # Check secret exists
    secret_exists = check_secret_exists("jwt-secret-staging")

    # Check service account has access
    has_access = check_secret_access("jwt-secret-staging", service_account)

    # Check secret has valid value
    secret_value = read_secret("jwt-secret-staging")
    is_valid = validate_secret_value(secret_value)

    if not (secret_exists and has_access and is_valid):
        raise DeploymentError("Secret validation failed")
```

### ❌ BAD: Only validate at runtime
```python
def startup():
    # Too late! Container is already running
    jwt_secret = os.environ.get('JWT_SECRET_STAGING')
    if not jwt_secret:
        raise ValueError("JWT_SECRET_STAGING missing")
```

---

## Testing Commands

### Check if secret exists:
```bash
gcloud secrets describe jwt-secret-staging --project=netra-staging
```

### Check if service account has access:
```bash
gcloud secrets get-iam-policy jwt-secret-staging --project=netra-staging \
  --format=json | grep netra-staging-deploy
```

### Test read as service account:
```bash
gcloud secrets versions access latest \
  --secret=jwt-secret-staging \
  --impersonate-service-account=netra-staging-deploy@netra-staging.iam.gserviceaccount.com \
  --project=netra-staging
```

### Check what Cloud Run sees:
```bash
gcloud run services describe netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging \
  --format="yaml" | grep -A5 "secretKeyRef"
```

### Check actual runtime values:
```bash
# SSH into container (if enabled) or add debug endpoint
gcloud run services proxy netra-backend-staging \
  --region=us-central1 \
  --project=netra-staging
# Then curl a debug endpoint that prints env vars (NEVER in production!)
```

---

## Key Learnings

1. **Deployment success ≠ Runtime success**
   - Deployment only validates that secret NAMES are correct
   - Runtime is when actual VALUES are loaded

2. **Service account access is critical**
   - Must be validated BEFORE deployment
   - Silent failure if not properly configured

3. **Three-layer validation needed**
   - Existence: Does the secret exist?
   - Access: Can the service account read it?
   - Quality: Is the value valid (not empty/placeholder)?

4. **Environment variables can be undefined**
   - Not just empty strings, but completely missing
   - `os.environ['KEY']` raises KeyError
   - `os.environ.get('KEY')` returns None

5. **Cloud Run doesn't report secret loading failures**
   - No error in Cloud Run logs
   - No deployment failure
   - Only discovered when application tries to use the value

---

## Recommended Implementation

```python
class SecretValidator:
    @staticmethod
    def validate_before_deployment(project_id: str, service_account: str):
        """Run this BEFORE deploying to Cloud Run"""

        required_secrets = [
            'jwt-secret-staging',
            'fernet-key-staging',
            'gemini-api-key-staging',
            # ... all other secrets
        ]

        for secret_name in required_secrets:
            # 1. Check existence
            if not secret_exists(secret_name):
                raise DeploymentError(f"Secret {secret_name} does not exist")

            # 2. Check access
            if not has_secret_access(secret_name, service_account):
                raise DeploymentError(
                    f"Service account {service_account} lacks access to {secret_name}\n"
                    f"Run: gcloud secrets add-iam-policy-binding {secret_name} "
                    f"--member=serviceAccount:{service_account} "
                    f"--role=roles/secretmanager.secretAccessor"
                )

            # 3. Check value (optional but recommended)
            value = read_secret_value(secret_name)
            if not value or is_placeholder(value):
                raise DeploymentError(f"Secret {secret_name} has invalid value")

        print("✅ All secrets validated successfully")
        return True
```

This validation MUST run before `gcloud run deploy` to prevent the confusing situation where deployment succeeds but the application fails at runtime due to missing secrets.