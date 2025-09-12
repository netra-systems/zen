---
name: run-demo
description: Setup and launch the Netra Apex staging demo with flexible frontend deployment
command: python
args:
  - ${WORKING_DIR}/scripts/staging_demo_setup.py
  - --frontend
  - ${frontend|select|"Choose frontend deployment mode"|gcp:"GCP Cloud Run deployment"|localhost:"Local development server"}
---

# run-demo

Sets up and launches the Netra Apex staging demo environment. This command handles all necessary configuration including GCP authentication, environment variables, secret manager access, service deployment checks, and automatically opens the frontend in your browser.

## Features

- **Automatic GCP Authentication**: Handles gcloud authentication if needed
- **Environment Configuration**: Sets up all required environment variables for staging
- **Secret Manager Access**: Verifies access to required secrets (JWT, OpenAI API key, database, Redis)
- **Service Health Checks**: Validates backend and frontend Cloud Run services are running
- **Flexible Frontend**: Choose between GCP deployment or local development server
- **Browser Launch**: Automatically opens the frontend in your default browser
- **Connectivity Testing**: Verifies services are accessible before launching

## Usage

```bash
/run-demo
```

You'll be prompted to choose the frontend mode:
- **GCP Cloud Run deployment**: Uses the deployed frontend-staging service
- **Local development server**: Runs frontend locally on port 3000 (useful for development)

## What It Does

1. **Authentication & Setup**
   - Authenticates with gcloud if not already authenticated
   - Sets the GCP project to `netra-staging`
   - Configures all required environment variables

2. **Service Validation**
   - Checks if backend-staging service is running
   - Checks if frontend-staging service is running (if using GCP mode)
   - Deploys services if they're not running (using existing deploy scripts)

3. **Local Frontend (if selected)**
   - Installs npm dependencies if needed
   - Starts the Next.js development server
   - Configures it to connect to staging backend

4. **Launch Demo**
   - Tests connectivity to both services
   - Opens the frontend in your default browser
   - Provides URLs and usage tips

## Environment Variables Set

- `ENVIRONMENT=staging`
- `GCP_PROJECT=netra-staging`
- `BACKEND_URL=https://backend-staging-906714043974.us-central1.run.app`
- `NEXT_PUBLIC_API_URL` (backend URL)
- `NEXT_PUBLIC_WS_URL` (WebSocket URL)
- `NEXT_PUBLIC_ENVIRONMENT=staging`
- `NEXT_PUBLIC_GCP_PROJECT=netra-staging`
- `NODE_ENV` (production for GCP, development for localhost)

## Service URLs

- **Backend**: https://backend-staging-906714043974.us-central1.run.app
- **Frontend (GCP)**: https://frontend-staging-906714043974.us-central1.run.app
- **Frontend (Local)**: http://localhost:3000

## Requirements

- Python 3.8+
- gcloud CLI installed and configured
- Node.js and npm (for localhost mode)
- Access to netra-staging GCP project
- Browser for viewing the demo

## Tips

- Use **GCP mode** for testing the full production-like environment
- Use **localhost mode** for frontend development with hot-reload
- The script handles all authentication and configuration automatically
- Keep the terminal open when using localhost mode (Ctrl+C to stop)

## Troubleshooting

If you encounter issues:
1. Ensure you have access to the netra-staging project
2. Check that gcloud CLI is installed: `gcloud version`
3. For localhost mode, ensure Node.js is installed: `node --version`
4. Check the console output for specific error messages

## Example Output

```
🚀 Netra Apex Staging Demo Setup
📍 Frontend Mode: gcp
==================================================
✅ Authenticated as: user@example.com
🎯 Setting project to netra-staging...
✅ Environment variables configured
🔑 Checking Secret Manager access...
  ✅ jwt-secret-key: Accessible
  ✅ openai-api-key: Accessible
🔍 Checking Cloud Run services...
  ✅ Backend service (backend-staging): Running
  ✅ Frontend service (frontend-staging): Running
🧪 Testing service connectivity...
  ✅ Backend health check: OK
  ✅ Frontend (gcp): OK
🌐 Opening browser to https://frontend-staging-906714043974.us-central1.run.app...
✨ Demo setup complete!
```