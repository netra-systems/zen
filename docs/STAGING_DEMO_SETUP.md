# Staging Demo Setup Guide

## Overview

The Netra Apex platform provides a streamlined way to set up and launch the staging demo environment. This guide covers both the automated `/run-demo` command and manual setup options.

## Prerequisites

- **Python 3.8+** installed
- **gcloud CLI** installed and configured
- **Node.js 18+** and npm (for localhost frontend mode)
- Access to the **netra-staging** GCP project
- Modern web browser (Chrome, Firefox, Safari, or Edge)

## Quick Start with `/run-demo` Command

### Using Claude Code (Recommended)

If you're using Claude Code, simply run:

```bash
/run-demo
```

You'll be prompted to choose between:
- **GCP Cloud Run deployment**: Uses the deployed frontend-staging service
- **Local development server**: Runs frontend locally on port 3000

### Using Python Script Directly

```bash
# Use GCP-deployed frontend
python scripts/staging_demo_setup.py --frontend gcp

# Use local frontend (for development)
python scripts/staging_demo_setup.py --frontend localhost
```

## What the Script Does

The staging demo setup script automates the entire process:

### 1. Authentication & Configuration
- Authenticates with gcloud (prompts for login if needed)
- Sets the GCP project to `netra-staging`
- Configures all required environment variables

### 2. Environment Variables Set
```bash
ENVIRONMENT=staging
GCP_PROJECT=netra-staging
BACKEND_URL=https://backend-staging-906714043974.us-central1.run.app
NEXT_PUBLIC_API_URL=https://backend-staging-906714043974.us-central1.run.app
NEXT_PUBLIC_WS_URL=wss://backend-staging-906714043974.us-central1.run.app
NEXT_PUBLIC_ENVIRONMENT=staging
NEXT_PUBLIC_GCP_PROJECT=netra-staging
NODE_ENV=production  # or 'development' for localhost mode
```

### 3. Secret Manager Access Verification
Checks access to critical secrets:
- `jwt-secret-key` - Authentication token signing
- `openai-api-key` - AI model access
- `database-url` - PostgreSQL connection
- `redis-url` - Cache connection

### 4. Service Health Checks
Validates that Cloud Run services are deployed and running:
- **backend-staging**: Backend API service
- **frontend-staging**: Frontend web application (if using GCP mode)

### 5. Frontend Setup (Localhost Mode)
If localhost mode is selected:
- Checks for `node_modules` and runs `npm install` if needed
- Starts the Next.js development server on port 3000
- Configures it to connect to the staging backend

### 6. Browser Launch
Automatically opens your default browser to the appropriate URL:
- **GCP Mode**: https://frontend-staging-906714043974.us-central1.run.app
- **Localhost Mode**: http://localhost:3000

## Service URLs

| Service | URL |
|---------|-----|
| Backend API | https://backend-staging-906714043974.us-central1.run.app |
| Frontend (GCP) | https://frontend-staging-906714043974.us-central1.run.app |
| Frontend (Local) | http://localhost:3000 |

## Frontend Modes Explained

### GCP Cloud Run Mode
- **Use Case**: Testing the full production-like environment
- **Benefits**: 
  - No local setup required
  - Tests actual deployment configuration
  - Consistent with production environment
- **Requirements**: Services must be deployed to Cloud Run

### Localhost Mode
- **Use Case**: Frontend development with hot-reload
- **Benefits**:
  - Instant code changes without deployment
  - Better debugging capabilities
  - Faster iteration cycles
- **Requirements**: Node.js and npm installed locally

## Manual Setup (Alternative)

If you prefer manual setup or need to customize the process:

### 1. Authenticate with GCP
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project netra-staging
```

### 2. Set Environment Variables
```bash
export ENVIRONMENT=staging
export GCP_PROJECT=netra-staging
export BACKEND_URL=https://backend-staging-906714043974.us-central1.run.app
export NEXT_PUBLIC_API_URL=$BACKEND_URL
export NEXT_PUBLIC_WS_URL=${BACKEND_URL/https:/wss:}
export NEXT_PUBLIC_ENVIRONMENT=staging
export NEXT_PUBLIC_GCP_PROJECT=netra-staging
```

### 3. Verify Services (Optional)
```bash
# Check backend service
gcloud run services describe backend-staging \
  --region=us-central1 \
  --project=netra-staging

# Check frontend service
gcloud run services describe frontend-staging \
  --region=us-central1 \
  --project=netra-staging
```

### 4. Deploy Services (If Needed)
```bash
# Deploy backend
python scripts/deploy_to_gcp.py \
  --project netra-staging \
  --service backend \
  --build-local

# Deploy frontend
python scripts/deploy_to_gcp.py \
  --project netra-staging \
  --service frontend \
  --build-local
```

### 5. Launch Frontend

**For GCP Mode:**
```bash
open https://frontend-staging-906714043974.us-central1.run.app
```

**For Localhost Mode:**
```bash
cd frontend
npm install
npm run dev
# Then open http://localhost:3000
```

## Testing the Demo

Once the demo is running:

1. **Login**: Use your Google account to authenticate
2. **Chat Interface**: Test the AI chat functionality
3. **Agent Responses**: Verify you receive substantive AI-powered responses
4. **WebSocket Events**: Check real-time updates during agent execution
5. **Tool Execution**: Observe tool usage transparency in responses

## Troubleshooting

### Authentication Issues
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login

# Verify active account
gcloud auth list
```

### Service Not Running
```bash
# Check service status
gcloud run services list --project=netra-staging

# View service logs
gcloud run services logs read backend-staging \
  --project=netra-staging \
  --region=us-central1
```

### Frontend Connection Issues
- Verify backend URL is correct in environment variables
- Check browser console for errors
- Ensure CORS is properly configured
- Try clearing browser cache and cookies

### Local Frontend Issues
```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check for port conflicts
lsof -i :3000  # Should be empty before starting
```

### Secret Access Issues
```bash
# List available secrets
gcloud secrets list --project=netra-staging

# Check specific secret access
gcloud secrets versions access latest \
  --secret=jwt-secret-key \
  --project=netra-staging
```

## Security Considerations

- **Authentication**: Always use proper authentication when accessing staging
- **Secrets**: Never expose secret values in logs or commits
- **CORS**: Frontend must be on approved CORS origin list
- **SSL/TLS**: All connections use HTTPS/WSS for security

## Performance Tips

- **GCP Mode**: May have cold starts; first request might be slower
- **Localhost Mode**: Hot-reload may consume resources; restart if slow
- **Browser**: Use Chrome DevTools Network tab to monitor requests
- **Caching**: Clear browser cache if seeing stale data

## Common Use Cases

### Demo to Stakeholders
Use GCP mode for stable, production-like demonstrations:
```bash
python scripts/staging_demo_setup.py --frontend gcp
```

### Frontend Development
Use localhost mode for rapid iteration:
```bash
python scripts/staging_demo_setup.py --frontend localhost
```

### Testing WebSocket Events
1. Open browser developer console
2. Navigate to Network tab
3. Filter by WS (WebSocket)
4. Send a chat message
5. Observe real-time events

### Debugging Backend Issues
```bash
# View backend logs
gcloud run services logs read backend-staging \
  --project=netra-staging \
  --region=us-central1 \
  --limit=100
```

## Related Documentation

- [Golden Path User Flow](./GOLDEN_PATH_USER_FLOW_COMPLETE.md) - Complete user journey analysis
- [Command Index](./COMMAND_INDEX.md) - All available Claude Code commands
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Full deployment documentation
- [WebSocket Architecture](./WEBSOCKET_MODERNIZATION_REPORT.md) - WebSocket implementation details

## Support

If you encounter issues not covered in this guide:
1. Check the [GitHub Issues](https://github.com/netra/netra-apex/issues)
2. Review recent deployment logs in GCP Console
3. Contact the development team via Slack

---

*Last Updated: 2025-01-12*