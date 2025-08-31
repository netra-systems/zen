# Docker Cleanup Process & Best Practices

## Problem Identified
Docker Desktop crashes were caused by:
1. **30+ named volumes** defined in docker-compose.yml
2. **3.4GB of old images** not being auto-deleted
3. **Bind mount overhead** from docker-compose.override.yml
4. **No automatic cleanup** of dev/test resources

## Immediate Fix Applied
```bash
# 1. Removed all containers
docker rm -f $(docker ps -aq)

# 2. Removed all volumes (1.3GB reclaimed)
docker volume prune -af

# 3. Removed all unused images (3.4GB reclaimed)
docker image prune -af

# Total space reclaimed: 4.7GB
```

## Systematic Cleanup Process

### Daily Cleanup (Add to development workflow)
```bash
# Clean up stopped containers
docker container prune -f

# Clean up unused images
docker image prune -f

# Clean up unused volumes
docker volume prune -f

# Check space usage
docker system df
```

### Weekly Deep Clean
```bash
# Complete system prune (WARNING: removes everything unused)
docker system prune -af --volumes

# Remove specific old images
docker images | grep "<none>" | awk '{print $3}' | xargs -r docker rmi
```

### Automated Cleanup Script
Create `scripts/docker_cleanup.py`:
```python
#!/usr/bin/env python3
"""Docker cleanup script for development environment."""

import subprocess
import sys

def run_command(cmd):
    """Run command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def main():
    print("🧹 Docker Cleanup Starting...")
    
    # 1. Remove stopped containers
    print("Removing stopped containers...")
    stdout, stderr, code = run_command("docker container prune -f")
    if code == 0:
        print(f"✅ {stdout}")
    
    # 2. Remove unused images
    print("Removing unused images...")
    stdout, stderr, code = run_command("docker image prune -af")
    if code == 0:
        print(f"✅ {stdout}")
    
    # 3. Remove unused volumes
    print("Removing unused volumes...")
    stdout, stderr, code = run_command("docker volume prune -f")
    if code == 0:
        print(f"✅ {stdout}")
    
    # 4. Show disk usage
    print("\n📊 Docker Disk Usage:")
    stdout, stderr, code = run_command("docker system df")
    print(stdout)
    
    print("\n✨ Cleanup complete!")

if __name__ == "__main__":
    main()
```

## Docker Compose Best Practices

### 1. Reduce Named Volumes
**BAD** (Current docker-compose.yml has 30+ volumes):
```yaml
services:
  dev-backend:
    volumes:
      - dev_backend_code:/app/netra_backend
      - dev_shared_code:/app/shared
      - dev_spec_data:/app/SPEC
      - dev_scripts:/app/scripts
      - dev_backend_logs:/app/logs
      - dev_backend_pycache:/app/.pycache
```

**GOOD** (Use minimal volumes):
```yaml
services:
  dev-backend:
    volumes:
      - backend_data:/app/data  # Only persist what's necessary
```

### 2. Add Resource Limits
```yaml
services:
  dev-postgres:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
```

### 3. Use Build Args for Auto-Cleanup
```yaml
services:
  dev-backend:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        BUILDKIT_INLINE_CACHE: 1  # Enable build cache
    image: netra-backend:dev  # Tag properly
    labels:
      - "environment=dev"
      - "auto-clean=true"
```

### 4. Add Health Checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Docker Configuration for Windows

### 1. Docker Desktop Settings
- **Memory:** 8GB minimum
- **CPUs:** 4-6 cores
- **Disk:** 100GB+
- **Enable:** WSL2 backend

### 2. .wslconfig (Create in %USERPROFILE%)
```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
```

### 3. Environment Variables for Dev
Add to `.env.development`:
```bash
# Docker build settings
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1
DOCKER_DEFAULT_PLATFORM=linux/amd64

# Auto-cleanup settings
DOCKER_PRUNE_IMAGES=true
DOCKER_PRUNE_VOLUMES=true
DOCKER_PRUNE_CONTAINERS=true
```

## Monitoring Docker Health

### Check Resource Usage
```bash
# Real-time stats
docker stats

# System disk usage
docker system df

# Check for issues
docker system events
```

### Windows Specific
```powershell
# Check Docker Desktop process
Get-Process "Docker Desktop" | Select-Object CPU, WS

# Check WSL2 memory
wsl --status
```

## Prevention Rules

1. **Never use bind mounts in production configs**
2. **Always set resource limits**
3. **Run cleanup before starting development**
4. **Use tagged images, not latest**
5. **Implement auto-cleanup in CI/CD**
6. **Monitor disk space regularly**

## Quick Recovery Commands

If Docker crashes:
```bash
# 1. Restart Docker Desktop
Stop-Process -Name "Docker Desktop" -Force
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 2. Wait for startup
Start-Sleep -Seconds 30

# 3. Clean everything
docker system prune -af --volumes

# 4. Start minimal services
docker-compose -f docker-compose.minimal.yml up -d
```

## Summary
- **Root cause:** Excessive volumes + old images not cleaned
- **Space reclaimed:** 4.7GB
- **Solution:** Regular cleanup + reduced volume usage
- **Prevention:** Automated cleanup scripts + better compose files