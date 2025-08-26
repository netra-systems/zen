# Docker Requirements Refresh Runbook

## Purpose
This runbook documents the process for refreshing Docker containers after requirements.txt changes to ensure all dependencies are properly updated.

## When to Use
- After updating requirements.txt in any service
- When dependency conflicts arise
- When switching branches with different dependencies
- After pulling changes with dependency updates

## Process Steps

### 1. Stop All Running Containers
```bash
docker compose down
```
**Purpose:** Cleanly stops all running containers and removes the default network.

### 2. Remove Containers and Volumes (Optional - for clean slate)
```bash
docker compose down -v
```
**Purpose:** Removes containers AND volumes. Use when you need a completely fresh database state.

### 3. Remove Docker Images (Force Rebuild)
```bash
docker compose down --rmi local
```
**Purpose:** Removes locally built images to force a complete rebuild.

### 4. Rebuild Images Without Cache
```bash
docker compose build --no-cache
```
**Purpose:** Rebuilds all images from scratch, ensuring new requirements are installed fresh without using cached layers.

### 5. Start Services
```bash
docker compose up -d
```
**Purpose:** Starts all services in detached mode.

### 6. Verify Services
```bash
docker compose ps
docker compose logs --tail=50
```
**Purpose:** Check that all services are running and review recent logs for errors.

## Quick Commands

### Standard Refresh (Preserves Data)
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose ps
```

### Full Reset (Removes Everything)
```bash
docker compose down -v --rmi local
docker compose build --no-cache
docker compose up -d
docker compose ps
```

## Service-Specific Notes

### Backend Service
- Main requirements: `/netra_backend/requirements.txt`
- Test requirements: `/netra_backend/requirements-test.txt`
- Container name: `netra-backend`

### Auth Service
- Main requirements: `/auth_service/requirements.txt`
- Test requirements: `/auth_service/tests/requirements-test.txt`
- Container name: `netra-auth`

### Frontend Service
- Dependencies: `/frontend/package.json`
- Container name: `netra-frontend`
- Note: For frontend, you may need to also clear node_modules

## Troubleshooting

### Issue: Old dependencies still present
**Solution:** Use `--no-cache` flag with build command

### Issue: Permission errors
**Solution:** On Windows, ensure Docker Desktop is running with appropriate permissions

### Issue: Port conflicts
**Solution:** Check for other services using the same ports:
- Backend: 8000
- Auth: 8001  
- Frontend: 3000
- PostgreSQL: 5432
- Redis: 6379

### Issue: Database connection errors after refresh
**Solution:** Wait 10-15 seconds for PostgreSQL to fully initialize, or check logs:
```bash
docker compose logs postgres
```

## Verification Checklist

- [ ] All containers show as "Up" in `docker compose ps`
- [ ] No error messages in last 50 lines of logs
- [ ] Can access frontend at http://localhost:3000
- [ ] Can access backend health at http://localhost:8000/health
- [ ] Can access auth service health at http://localhost:8001/health
- [ ] Database migrations completed successfully (check logs)

## Common Issues After Requirements Update

### Missing Module: fastmcp
**Issue:** Backend fails with `ModuleNotFoundError: No module named 'fastmcp'`
**Solution:** Add `fastmcp` to `/netra_backend/requirements.txt` and rebuild

## Notes

- Always commit your code before doing a full reset
- Document any additional service-specific requirements in this runbook
- Keep this runbook updated as the system evolves
- After requirements.txt updates, ensure all new dependencies are included