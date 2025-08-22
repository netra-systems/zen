# STAGING DEPLOYMENT VALIDATION CHECKLIST

## 🚨 CRITICAL ACTIONS REQUIRED BEFORE DEPLOYMENT

### 1. SECRETS SETUP (REQUIRED)
All secrets must be created in GCP Secret Manager before deployment:

```bash
# 1. Create database URL secret (CRITICAL - use correct IP and password)
echo -n "postgresql://netra_user:CORRECT_PASSWORD@34.132.142.103:5432/netra?sslmode=require" | \
gcloud secrets create database-url-staging --data-file=- --project=netra-staging

# 2. Create JWT secret key
echo -n "$(openssl rand -base64 32)" | \
gcloud secrets create jwt-secret-key-staging --data-file=- --project=netra-staging

# 3. Create session secret key  
echo -n "$(openssl rand -base64 32)" | \
gcloud secrets create session-secret-key-staging --data-file=- --project=netra-staging

# 4. Create Fernet encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" | \
gcloud secrets create fernet-key-staging --data-file=- --project=netra-staging

# 5. Create OpenAI API key (use real key or dummy for staging)
echo -n "sk-YOUR_REAL_OPENAI_API_KEY" | \
gcloud secrets create openai-api-key-staging --data-file=- --project=netra-staging

# 6. Create auth service JWT secret (must match backend)
echo -n "$(gcloud secrets versions access latest --secret=jwt-secret-key-staging --project=netra-staging)" | \
gcloud secrets create jwt-secret-staging --data-file=- --project=netra-staging
```

### 2. VALIDATE SECRETS EXIST
```bash
# Check all required secrets exist
gcloud secrets list --project=netra-staging --filter="name:(database-url-staging OR jwt-secret-key-staging OR session-secret-key-staging OR fernet-key-staging OR openai-api-key-staging OR jwt-secret-staging)"
```

### 3. STAGING URLS CONFIGURATION ✅
The following staging URLs are configured:
- Frontend: https://app.staging.netrasystems.ai
- Backend API: https://api.staging.netrasystems.ai  
- Auth Service: https://auth.staging.netrasystems.ai
- WebSocket: wss://api.staging.netrasystems.ai/ws

### 4. CORS CONFIGURATION ✅
CORS is properly configured for staging domains:
- *.staging.netrasystems.ai subdomains
- Cloud Run URLs
- Localhost development ports
- Service discovery integration

### 5. OAUTH CONFIGURATION ✅
OAuth is configured to handle staging environment variables:
- GOOGLE_OAUTH_CLIENT_ID_STAGING (optional)
- GOOGLE_OAUTH_CLIENT_SECRET_STAGING (optional)

### 6. DEPLOYMENT COMMAND
```bash
# Recommended deployment command with all checks
python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
```

## 🔍 POST-DEPLOYMENT VALIDATION

### 1. Health Check Endpoints
```bash
# Backend health
curl https://api.staging.netrasystems.ai/health

# Auth service health  
curl https://auth.staging.netrasystems.ai/health

# Frontend availability
curl https://app.staging.netrasystems.ai
```

### 2. Service URLs
Check Cloud Run service URLs:
```bash
gcloud run services list --platform managed --region us-central1 --project netra-staging
```

### 3. Secrets Verification
```bash
# Verify secrets are accessible to services
gcloud run services describe netra-backend --region us-central1 --project netra-staging --format="value(spec.template.spec.template.spec.containers[0].env[].valueFrom.secretKeyRef)"
```

### 4. Service Logs
```bash
# Check for startup errors
gcloud logs read "resource.type=cloud_run_revision" --project netra-staging --limit 50
```

## 🚨 KNOWN ISSUES TO FIX

1. **Database Connection**: Ensure DATABASE_URL uses correct Cloud SQL instance IP (34.132.142.103)
2. **Missing APIs**: Some GCP APIs may need to be enabled
3. **IAM Permissions**: Service account may need Secret Manager accessor role
4. **Custom Domains**: staging.netrasystems.ai domains need to be mapped to Cloud Run services

## 🔧 TROUBLESHOOTING

### Service Won't Start
1. Check secrets exist and are accessible
2. Verify service account has correct IAM roles
3. Check Cloud SQL instance is running and accessible
4. Review service logs for specific errors

### CORS Issues
1. Verify origin matches staging domain patterns
2. Check CORS_ORIGINS environment variable
3. Review CustomCORSMiddleware logs

### OAuth Issues  
1. Ensure OAuth client is configured for staging domain
2. Verify redirect URIs include staging URLs
3. Check OAuth secrets are properly set

## 📋 SUCCESS CRITERIA

✅ All services deploy without errors
✅ Health endpoints return 200 status
✅ Frontend loads and connects to backend
✅ WebSocket connections work
✅ Authentication flow works (if OAuth configured)
✅ Database connections established
✅ No startup errors in logs