# Auth Service Deployment Guide

## Overview
This guide covers the deployment of the Netra Auth Service as a standalone microservice on Google Cloud Platform.

## Architecture

The Auth Service is deployed as:
- **Cloud Run Service**: Containerized auth service
- **Load Balancer**: Global HTTP(S) load balancer with SSL
- **Cloud Armor**: Optional security policies
- **Secret Manager**: Secure storage for OAuth credentials

## Files Created

### Terraform Infrastructure
- `auth-service.tf` - Cloud Run service definition for auth
- `auth-load-balancer.tf` - Load balancer and routing configuration
- `api-gateway.tf` - API gateway for service routing
- `variables.tf` - Updated with auth service variables

### Docker Configuration
- `Dockerfile.auth` - Container definition for auth service
- `auth_service_main.py` - FastAPI application for auth service

### Deployment Scripts
- `deploy-auth-service.sh` - Linux/Mac deployment script
- `deploy-auth-service.ps1` - Windows PowerShell deployment script
- `update-oauth-config.sh` - OAuth configuration updater

### Frontend Integration
- `frontend/lib/auth-service-config.ts` - Auth service client library
- `frontend/.env.staging` - Updated environment variables

## Deployment Steps

### 1. Prerequisites
- GCP Project with billing enabled
- gcloud CLI installed and configured
- Docker installed
- Terraform installed
- Domain configured (auth.staging.netrasystems.ai)

### 2. Deploy Infrastructure

#### Linux/Mac:
```bash
cd terraform-gcp
chmod +x deploy-auth-service.sh
./deploy-auth-service.sh <PROJECT_ID> <REGION> <ENVIRONMENT>
```

#### Windows:
```powershell
cd terraform-gcp
.\deploy-auth-service.ps1 -ProjectId <PROJECT_ID> -Region <REGION> -Environment <ENVIRONMENT>
```

### 3. Configure OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Select your project
3. Edit your OAuth 2.0 Client ID
4. Add Authorized JavaScript origins:
   - `https://auth.staging.netrasystems.ai`
   - `https://app.staging.netrasystems.ai`
   - `http://localhost:3000` (for development)

5. Add Authorized redirect URIs:
   - `https://auth.staging.netrasystems.ai/api/auth/callback`
   - `https://app.staging.netrasystems.ai/api/auth/callback`
   - `http://localhost:3000/api/auth/callback` (for development)

### 4. Update DNS Records

Add CNAME record:
```
auth.staging.netrasystems.ai -> netra-auth-service-<PROJECT_ID>.us-central1.run.app
```

Or A record pointing to the Load Balancer IP:
```
auth.staging.netrasystems.ai -> <LOAD_BALANCER_IP>
```

### 5. Update Environment Variables

Run the OAuth configuration update script:
```bash
./update-oauth-config.sh <PROJECT_ID> staging auth.staging.netrasystems.ai
```

## Service Endpoints

### Auth Service
- Base URL: `https://auth.staging.netrasystems.ai`
- Health Check: `/health`
- API Docs: `/api/docs`

### Authentication Endpoints
- Login: `/api/auth/login`
- Callback: `/api/auth/callback`
- Logout: `/api/auth/logout`
- Token: `/api/auth/token`
- Refresh: `/api/auth/refresh`
- Validate: `/api/auth/validate`
- Config: `/api/auth/config`
- Session: `/api/auth/session`
- Current User: `/api/auth/me`

## Environment Variables

### Auth Service
```env
SERVICE_NAME=auth-service
ENVIRONMENT=staging
DATABASE_URL=<postgres_connection_string>
REDIS_URL=<redis_connection_string>
JWT_SECRET=<from_secret_manager>
GOOGLE_OAUTH_CLIENT_ID_STAGING=<from_secret_manager>
GOOGLE_OAUTH_CLIENT_SECRET_STAGING=<from_secret_manager>
AUTH_SERVICE_URL=https://auth.staging.netrasystems.ai
FRONTEND_URL=https://app.staging.netrasystems.ai
CORS_ORIGINS=<allowed_origins>
```

### Backend Service Updates
```env
AUTH_SERVICE_URL=https://auth.staging.netrasystems.ai
AUTH_SERVICE_INTERNAL_URL=http://netra-auth-service.us-central1.run.app
```

### Frontend Updates
```env
NEXT_PUBLIC_AUTH_SERVICE_URL=https://auth.staging.netrasystems.ai
NEXT_PUBLIC_AUTH_API_URL=https://auth.staging.netrasystems.ai
```

## Testing

### 1. Health Check
```bash
curl https://auth.staging.netrasystems.ai/health
```

### 2. Configuration Endpoint
```bash
curl https://auth.staging.netrasystems.ai/api/auth/config
```

### 3. OAuth Flow
1. Navigate to `https://auth.staging.netrasystems.ai/api/auth/login`
2. Should redirect to Google OAuth
3. After authorization, should redirect back to callback
4. Session should be established

### 4. Frontend Integration
```javascript
import { authService } from '@/lib/auth-service-config';

// Initiate login
authService.initiateLogin('google');

// Get current user
const user = await authService.getCurrentUser();

// Logout
await authService.logout();
```

## Monitoring

### Cloud Run Metrics
- View in Cloud Console: Cloud Run > netra-auth-service > Metrics
- Key metrics: Request count, latency, error rate

### Load Balancer Logs
- View in Cloud Console: Network Services > Load Balancing > Logs
- Monitor traffic patterns and errors

### Application Logs
- View in Cloud Console: Logging > Logs Explorer
- Filter by: `resource.type="cloud_run_revision" AND resource.labels.service_name="netra-auth-service"`

## Troubleshooting

### OAuth Redirect Mismatch
- Verify redirect URIs in Google Cloud Console match exactly
- Check environment variables in Cloud Run service
- Ensure HTTPS is used for production/staging

### CORS Issues
- Check CORS_ORIGINS environment variable
- Verify frontend URL is in allowed origins
- Check browser console for specific CORS errors

### Database Connection
- Verify DATABASE_URL is correct
- Check Cloud SQL proxy if using private IP
- Ensure service account has cloudsql.client role

### SSL Certificate Issues
- Wait 10-15 minutes for certificate provisioning
- Verify domain DNS is pointing correctly
- Check certificate status in Load Balancing console

## Security Considerations

1. **Secrets Management**
   - All sensitive data in Secret Manager
   - Service account with minimal permissions
   - Encrypted environment variables

2. **Network Security**
   - HTTPS only for production/staging
   - Cloud Armor for DDoS protection (optional)
   - Session cookies with secure flags

3. **Authentication Flow**
   - OAuth 2.0 with PKCE (recommended)
   - JWT tokens with expiration
   - Secure session management

## Rollback Procedure

If issues occur, rollback to previous version:

```bash
# Rollback Cloud Run service
gcloud run services update-traffic netra-auth-service \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1

# Or use Terraform
terraform apply -target=google_cloud_run_service.auth \
  -var="auth_service_image_tag=previous-tag"
```

## Support

For issues or questions:
1. Check application logs in Cloud Console
2. Review this documentation
3. Contact the DevOps team

## Next Steps

1. Set up monitoring alerts
2. Configure backup and disaster recovery
3. Implement rate limiting
4. Add comprehensive logging
5. Set up CI/CD pipeline for auth service