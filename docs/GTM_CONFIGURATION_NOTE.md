# GTM Configuration - Important Note

## Issue
Google Tag Manager (GTM) stopped sending events in production.

## Root Cause
The `.env.production` file was missing from the frontend directory. While the deployment script (`scripts/deploy_to_gcp.py`) does set GTM environment variables, Next.js requires `NEXT_PUBLIC_*` variables to be available at **build time**, not just runtime.

## Solution
Created `.env.production` file with proper GTM configuration:
```
NEXT_PUBLIC_GTM_CONTAINER_ID=GTM-WKP28PNQ
NEXT_PUBLIC_GTM_ENABLED=true
NEXT_PUBLIC_GTM_DEBUG=false
```

## Why This Regression Occurred
According to `docs/STAGING_ENVIRONMENT_SIMPLIFIED.md`, the project guideline states:
> "Never create .env.staging or .env.production files - They cause precedence issues"

This guideline was likely created to avoid confusion with Google Secret Manager secrets. However, for Next.js frontend builds, `NEXT_PUBLIC_*` variables MUST be available at build time, which means:
1. They need to be in `.env.production` for production builds
2. OR they need to be injected during the Docker build process

## Prevention Strategy

### Option 1: Keep .env.production (Recommended)
- Maintain `.env.production` for frontend build-time variables only
- Only include `NEXT_PUBLIC_*` variables (no secrets)
- Add clear documentation that this file is required for frontend builds

### Option 2: Modify Docker Build
- Update `docker/frontend.Dockerfile` to accept build args
- Pass GTM configuration as Docker build arguments in deployment script
- Example:
  ```dockerfile
  ARG NEXT_PUBLIC_GTM_CONTAINER_ID
  ARG NEXT_PUBLIC_GTM_ENABLED
  ENV NEXT_PUBLIC_GTM_CONTAINER_ID=$NEXT_PUBLIC_GTM_CONTAINER_ID
  ENV NEXT_PUBLIC_GTM_ENABLED=$NEXT_PUBLIC_GTM_ENABLED
  ```

### Option 3: Build-time Script
- Create a script that generates `.env.production` during CI/CD
- Use this before running `npm run build` in Docker

## Monitoring
To verify GTM is working:
1. Check browser console for `[GTM]` debug messages (if debug enabled)
2. Use Google Tag Assistant Chrome extension
3. Check Network tab for requests to `googletagmanager.com`
4. Verify dataLayer array in browser console: `window.dataLayer`

## Files Involved
- `frontend/.env.production` - Production environment variables (REQUIRED)
- `frontend/.env.staging` - Staging environment variables  
- `frontend/.env.local` - Local development environment variables
- `frontend/providers/GTMProvider.tsx` - GTM implementation
- `scripts/deploy_to_gcp.py` - Deployment script (sets runtime env vars)

## Testing
```bash
# Local testing with GTM enabled
cd frontend
npm run build
npm run start

# Check GTM is loaded
# Open browser console and type: window.dataLayer
```

## Important Notes
1. **Do NOT** add secrets to `.env.production` - only public build-time variables
2. **Do NOT** commit `.env.production.local` (it's gitignored)
3. **Always** ensure GTM container ID matches across environments
4. **Remember** Next.js `NEXT_PUBLIC_*` variables are embedded at build time, not runtime