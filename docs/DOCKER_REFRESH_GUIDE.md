# Docker Container Refresh Guide

## Critical Understanding: File Updates vs Container Rebuilds

### What Updates Automatically (Live Changes)
**Files mounted as volumes update immediately without rebuild:**
- Frontend source code (when using development mode with volume mounts)
- Configuration files explicitly mounted as volumes
- Static assets mounted via volumes
- Any file/directory listed in `docker-compose.yml` under `volumes:` section

**Example Volume Mount:**
```yaml
volumes:
  - ./frontend:/app/frontend  # Changes to ./frontend reflect immediately
  - ./config.json:/app/config.json  # Config changes apply immediately
```

### What Requires Container Rebuild
**Files copied during image build require rebuild:**
- Backend Python code (copied via Dockerfile COPY commands)
- Dependencies (requirements.txt, package.json)
- System packages
- Any file that's part of the Docker image layers

**Identifying COPY Commands in Dockerfile:**
```dockerfile
COPY requirements.txt /app/  # Requires rebuild to update
COPY netra_backend /app/netra_backend  # Requires rebuild to update
```

## Standard Docker Refresh Process

### Level 1: Quick Restart (No Code Changes)
```bash
# Just restart containers to apply config changes
docker-compose restart backend
```

### Level 2: Standard Rebuild (Code Changes)
```bash
# Stop containers
docker-compose down

# Rebuild with latest code
docker-compose build backend

# Start containers
docker-compose up -d
```

### Level 3: Clean Rebuild (Major Changes or Issues)
```bash
# Complete cleanup and rebuild
docker-compose down -v  # -v removes volumes (careful with data!)

# Force rebuild without cache
docker-compose build --no-cache backend

# Start fresh
docker-compose up -d
```

### Level 4: Nuclear Option (System Issues)
```bash
# Stop everything
docker-compose down -v

# Remove all images related to the project
docker rmi $(docker images | grep netra | awk '{print $3}')

# Prune system
docker system prune -a --volumes

# Fresh build
docker-compose build --no-cache

# Start
docker-compose up -d
```

## Verification Commands

### Check if Fix is Present in Container
```bash
# Verify specific code changes are in the container
docker exec netra-backend grep -A5 "CRITICAL FIX" /app/netra_backend/app/db/database_manager.py

# Check file modification time inside container
docker exec netra-backend stat /app/netra_backend/app/db/database_manager.py

# Compare file between host and container
diff netra_backend/app/db/database_manager.py <(docker exec netra-backend cat /app/netra_backend/app/db/database_manager.py)
```

### Check Image Build Time
```bash
# See when image was built
docker images | grep netra-backend

# Detailed image history
docker history netra-backend:latest

# Inspect image metadata
docker inspect netra-backend:latest | grep Created
```

## Common Pitfalls and Solutions

### Pitfall 1: Old Image Still Running
**Symptom:** Fixed bug still occurring despite code changes
**Solution:** Image predates the fix - rebuild required
```bash
docker-compose build --no-cache backend && docker-compose up -d
```

### Pitfall 2: Cache Using Old Layers
**Symptom:** Rebuild doesn't pick up changes
**Solution:** Force no-cache build
```bash
docker-compose build --no-cache backend
```

### Pitfall 3: Volume Mounting Overrides
**Symptom:** Local changes not reflected even with volume mounts
**Solution:** Check docker-compose.yml for correct mount paths
```yaml
# Ensure paths are correct and not overriding each other
volumes:
  - ./netra_backend:/app/netra_backend  # Good for development
  # NOT: - ./netra_backend:/app  # This would override the entire /app
```

### Pitfall 4: Multiple Compose Files
**Symptom:** Wrong configuration being used
**Solution:** Specify compose file explicitly
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Quick Decision Tree

```
Code changed?
├─ No → docker-compose restart
└─ Yes → Is it in a volume-mounted directory?
    ├─ Yes → Changes apply immediately (maybe restart for safety)
    └─ No → Is it backend/image code?
        ├─ Yes → docker-compose build && docker-compose up -d
        └─ Cache issues? → docker-compose build --no-cache
```

## Timeline Issue Resolution

### Specific Issue Encountered
- **08:59 AM**: SQLAlchemy session fix committed (a1a8a0300)
- **12:01 PM**: Docker image built (WITHOUT the fix) 
- **Later**: Container running old code, experiencing the fixed bug

### Root Cause
Docker image was built from an older commit, before the fix was applied. The container was running stale code.

### Resolution Applied
```bash
# Stop current containers
docker-compose down

# Rebuild with latest code (force no-cache to ensure fresh build)
docker-compose build --no-cache backend

# Start fresh containers
docker-compose up -d

# Verify the fix is present
docker exec netra-backend grep -A5 "CRITICAL FIX" /app/netra_backend/app/db/database_manager.py
```

## Best Practices

1. **Always verify after rebuild:**
   ```bash
   docker exec [container] cat [critical_file] | grep [expected_change]
   ```

2. **Use tags for production:**
   ```bash
   docker build -t netra-backend:v1.2.3 .
   ```

3. **Check logs after restart:**
   ```bash
   docker-compose logs -f backend | grep -i error
   ```

4. **Document rebuild in commits:**
   ```bash
   git commit -m "fix: [issue] - requires Docker rebuild"
   ```

5. **For CI/CD: Always rebuild on deploy:**
   ```yaml
   deploy:
     steps:
       - docker-compose build --no-cache
       - docker-compose up -d
   ```