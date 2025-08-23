# Secure OAuth Deployment Guide

## Overview
This guide ensures OAuth implementation is deployed securely without any secrets in source control.

## Security Changes Implemented

### 1. Removed Hardcoded Secrets
- **Redis Password**: Removed hardcoded Redis cloud password from `dev_launcher/service_config.py`
- **Environment Variables**: All secrets now loaded from environment variables

### 2. Environment Variable Configuration

#### Required OAuth Variables
```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# JWT Configuration (must match between services)
JWT_SECRET_KEY=your-jwt-secret-at-least-32-chars
JWT_SECRET=${JWT_SECRET_KEY}  # For compatibility

# Redis Cloud (Production/Staging)
REDIS_CLOUD_HOST=redis-xxxx.ec2.redns.redis-cloud.com
REDIS_CLOUD_PORT=17593
REDIS_CLOUD_PASSWORD=your-redis-password

# Service Authentication
SERVICE_ID=backend
SERVICE_SECRET=your-service-secret
```

## Deployment Steps

### Local Development

1. **Create .env file** from template:
   ```bash
   cp .env.unified.template .env
   ```

2. **Configure secrets** in .env:
   - Set `JWT_SECRET_KEY` (min 32 characters)
   - Set Google OAuth credentials
   - Set Redis Cloud password if using shared Redis

3. **Run services**:
   ```bash
   # Start all services
   python scripts/dev_launcher.py
   
   # Or start individually
   python -m auth_service.auth_core.main  # Auth service
   python -m netra_backend.app.main       # Backend
   ```

### GCP Deployment

1. **Set environment variables** in GCP:
   ```bash
   gcloud run services update auth-service \
     --set-env-vars="JWT_SECRET_KEY=$JWT_SECRET,GOOGLE_CLIENT_ID=$CLIENT_ID,GOOGLE_CLIENT_SECRET=$CLIENT_SECRET"
   
   gcloud run services update backend \
     --set-env-vars="JWT_SECRET_KEY=$JWT_SECRET,REDIS_CLOUD_PASSWORD=$REDIS_PWD"
   ```

2. **Use Secret Manager** (recommended):
   ```bash
   # Create secrets
   echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret --data-file=-
   echo -n "$GOOGLE_CLIENT_SECRET" | gcloud secrets create google-oauth-secret --data-file=-
   echo -n "$REDIS_PASSWORD" | gcloud secrets create redis-password --data-file=-
   
   # Grant access
   gcloud secrets add-iam-policy-binding jwt-secret \
     --member="serviceAccount:SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

3. **Deploy with secrets**:
   ```bash
   python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
   ```

## Security Tools

### Secrets Scanner
Run before commits to detect hardcoded secrets:
```bash
python scripts/scan_for_secrets.py --fail-on-critical
```

### Pre-commit Hook
Automatically scans for secrets before allowing commits:
```bash
# Install hook
cp .githooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

### OAuth Testing Tools

1. **Test local OAuth**:
   ```bash
   python scripts/test_oauth_local.py
   ```

2. **Audit GCP OAuth logs**:
   ```bash
   python scripts/audit_oauth_gcp_logs.py --project netra-staging --hours 24
   ```

## OAuth Flow Architecture

```
User → Frontend (localhost:3000)
         ↓
      Backend (/api/auth/login)
         ↓
      Auth Service (/auth/login)
         ↓
      Google OAuth
         ↓
      Callback → Auth Service
         ↓
      Generate JWT Token
         ↓
      Return to Frontend
```

## Security Best Practices

### DO:
- Use environment variables for all secrets
- Use GCP Secret Manager in production
- Rotate secrets regularly
- Use different secrets per environment
- Enable audit logging for OAuth events
- Use HTTPS in production
- Validate redirect URIs

### DON'T:
- Commit secrets to source control
- Use the same JWT secret across environments
- Log sensitive tokens or passwords
- Store secrets in plain text files
- Share service account keys

## Troubleshooting

### OAuth Login Fails
1. Check environment variables are set
2. Verify JWT secrets match between services
3. Check redirect URIs in Google Console
4. Review logs: `python scripts/audit_oauth_gcp_logs.py`

### Token Validation Errors
1. Ensure JWT_SECRET_KEY matches in both services
2. Check token expiry settings
3. Verify service-to-service authentication

### Redis Connection Issues
1. Verify REDIS_CLOUD_PASSWORD is set
2. Check network connectivity
3. Confirm Redis Cloud instance is running

## Monitoring

### Key Metrics
- OAuth success/failure rate
- Token generation latency
- JWT validation errors
- Redis connection pool status

### Logs to Monitor
```python
# Auth service logs
"OAuth login initiated"
"Token generated successfully"
"JWT validation failed"

# Backend logs  
"Auth service communication error"
"Redis connection failed"
```

## Compliance

This implementation follows:
- OWASP OAuth 2.0 Security Best Practices
- Google OAuth 2.0 Guidelines
- JWT Best Current Practices (RFC 8725)
- PCI DSS requirements for secret management

## Emergency Procedures

### Compromised Secret
1. Immediately rotate the compromised secret
2. Update all services with new secret
3. Audit logs for unauthorized access
4. Notify security team

### Service Outage
1. Check environment variables are set
2. Verify services can reach external OAuth providers
3. Review error logs for configuration issues
4. Fall back to dev login if needed (dev only)

## Contact

For OAuth issues or security concerns:
- Create issue: https://github.com/netra-systems/netra-core-generation-1/issues
- Security email: security@netra.systems