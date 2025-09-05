# Build Failure Analysis - Backend Deployment

## Date: 2025-09-04

## Issue: Backend deployment failed with Podman connection error

### Error Details:
```
Cannot connect to Podman. 
Error: unable to connect to Podman socket: failed to connect: dial tcp 127.0.0.1:55491: 
connectex: No connection could be made because the target machine actively refused it.
```

## Five Whys Root Cause Analysis:

### 1. Why did the deployment fail?
- Podman couldn't connect to its socket on port 55491 - connection actively refused

### 2. Why couldn't Podman connect to the socket?  
- The Podman service/daemon is not running on the Windows machine

### 3. Why is Podman not running?
Possible reasons:
- Podman Desktop is not installed
- Podman machine hasn't been initialized (`podman machine init`)
- Podman machine hasn't been started (`podman machine start`)
- Docker Desktop is expected but Podman is being detected instead

### 4. Why is the script using Podman instead of Docker?
- The `_detect_container_runtime()` method in `deploy_to_gcp.py` found Podman in PATH
- Script assumes Podman is the preferred runtime when available

### 5. Why does the script assume Podman is ready when it's not?
- Detection logic only checks command existence via `which podman`
- Doesn't verify actual service availability or connectivity

## Root Cause:
**Incomplete container runtime detection** - The deployment script checks for command availability but doesn't verify the container service is actually running and connectable.

## Immediate Solutions:

### Option 1: Use Cloud Build (Recommended for CI/CD)
```bash
python scripts/deploy_to_gcp.py --project netra-staging --service backend --no-traffic --skip-post-tests
```
Note: Removes `--build-local` flag to use Google Cloud Build instead

### Option 2: Start Podman (If local builds needed)
```bash
podman machine init
podman machine start
podman system connection list
```

### Option 3: Force Docker usage (If Docker Desktop installed)
Modify the script to prefer Docker or add a `--force-docker` flag

## Long-term Fix Recommendations:

1. **Enhance Runtime Detection:**
   - Add connectivity check after detecting runtime
   - Try `podman version` or `docker version` to verify service is running
   - Fallback to Cloud Build if local runtime unavailable

2. **Add Runtime Override Flag:**
   ```python
   parser.add_argument("--container-runtime", 
                      choices=["docker", "podman", "auto"],
                      default="auto",
                      help="Container runtime to use")
   ```

3. **Improve Error Messages:**
   - Detect specific connection errors
   - Provide actionable remediation steps
   - Suggest Cloud Build as fallback

## Code Changes Made:
Added `--no-traffic` flag support to `deploy_to_gcp.py`:
- Modified `deploy_service()` method to accept `no_traffic` parameter
- Added `--no-traffic` to argparse arguments
- Updated `deploy_all()` to pass through the flag
- Skip traffic routing when flag is set

## Next Steps:
1. ✅ Retry deployment using Cloud Build (without --build-local) - COMPLETED
2. ✅ Monitor GCP Cloud Build logs for any compilation/build errors - COMPLETED
3. ✅ If build succeeds, verify revision deployed without traffic - COMPLETED
4. Test the revision manually before routing traffic

## Successful Deployment Results:

### Cloud Build Success:
- Build ID: `16a4ba75-b2d3-4e50-9500-e6eb057210f8`
- Docker image built successfully: `gcr.io/netra-staging/netra-backend-staging:latest`
- Image digest: `sha256:a17703e980987f89faecd98f346c7fd992c4662ec054ec89cd14f0a0ea9fd01d`
- No build errors encountered

### Cloud Run Deployment with No-Traffic:
- New revision created: `netra-backend-staging-00216-7vd` (Status: Ready)
- Traffic allocation: 0% (as intended with --no-traffic flag)
- Previous revision still serving: `netra-backend-staging-00215-tb5` (100% traffic)
- Deployment succeeded without routing any traffic to the new revision

### Key Learnings:
1. Local builds with Podman require the Podman service to be running
2. Cloud Build is a reliable fallback when local container runtime is unavailable
3. The `--no-traffic` flag successfully creates a revision without routing traffic
4. This allows for safe testing before promoting the revision to production traffic