# E2E OAuth Simulation Key Deployment Commands

## Critical P0 Fix: Deploy E2E_OAUTH_SIMULATION_KEY to GCP Secret Manager

This is one of the three critical P0 fixes required for Data Helper Agent functionality.

### Problem
- Missing `E2E_OAUTH_SIMULATION_KEY` in GCP Secret Manager
- Prevents authentication flow validation
- Required for staging environment functionality

### Solution Commands

Execute these commands in your GCP environment (where gcloud CLI is available):

```bash
# 1. Set project context
gcloud config set project netra-staging

# 2. Create the E2E OAuth simulation key secret
gcloud secrets create E2E_OAUTH_SIMULATION_KEY \
    --project=netra-staging

# 3. Add the secret value
echo "e0e9c5d29e7aea3942f47855b4870d3e0272e061c2de22827e71b893071d777e" | \
    gcloud secrets versions add E2E_OAUTH_SIMULATION_KEY \
    --project=netra-staging \
    --data-file=-

# 4. Verify the secret was created
gcloud secrets describe E2E_OAUTH_SIMULATION_KEY \
    --project=netra-staging

# 5. Test secret access (optional)
gcloud secrets versions access latest \
    --secret=E2E_OAUTH_SIMULATION_KEY \
    --project=netra-staging
```

### Alternative: Using GCP Console

1. Go to GCP Console → Security → Secret Manager
2. Click "Create Secret"
3. Name: `E2E_OAUTH_SIMULATION_KEY`
4. Secret value: `e0e9c5d29e7aea3942f47855b4870d3e0272e061c2de22827e71b893071d777e`
5. Select project: `netra-staging`
6. Click "Create"

### Verification

After deployment, verify the key is accessible:

```bash
# Check if secret exists and is accessible
gcloud secrets versions access latest \
    --secret=E2E_OAUTH_SIMULATION_KEY \
    --project=netra-staging
```

Expected output: `e0e9c5d29e7aea3942f47855b4870d3e0272e061c2de22827e71b893071d777e`

### Impact

✅ **Resolves**: Authentication flow validation failures  
✅ **Enables**: E2E OAuth simulation in staging  
✅ **Protects**: $1.5M+ ARR dependent on Data Helper Agent functionality  

### Security Notes

- This is a simulation key for E2E testing, not production OAuth credentials
- Key is 256-bit hex string suitable for cryptographic operations
- Access is restricted to staging environment only
- Key rotation can be performed by adding new secret versions