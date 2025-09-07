# Docker Volume Management Best Practices

## Overview

This guide addresses the critical issue of Docker Desktop instability caused by bind mounts on Windows and macOS, and provides best practices for stable Docker development.

## The Problem: Bind Mounts and Docker Desktop Crashes

### Why Bind Mounts Cause Crashes

On Windows and macOS, Docker Desktop runs a Linux VM. When you use bind mounts (e.g., `./src:/app/src`), Docker must synchronize files between your host OS and the Linux VM using complex networking protocols. This causes:

1. **I/O Overload**: Operations like `npm install` generate thousands of file operations, overwhelming the sync mechanism
2. **Memory Exhaustion**: The file-sharing layer can consume excessive memory, triggering OOM killers
3. **CPU Spikes**: Constant file synchronization causes high CPU usage
4. **Deadlocks**: The file-sharing drivers can freeze under heavy load, crashing the VM

### Most Problematic Scenarios

- **node_modules**: JavaScript projects with thousands of small files
- **Python venv**: Virtual environments with many dependencies
- **.git directories**: Large repositories with extensive history
- **Database files**: Constant high-velocity I/O operations
- **Build artifacts**: Compiled files, caches, and temporary files

## Solution: Named Volumes

Named volumes are stored entirely within the Docker VM, avoiding the host-VM synchronization overhead.

### Benefits of Named Volumes

- **10-100x faster** than bind mounts on Windows/macOS
- **No synchronization overhead** - files stay in the VM
- **No crashes** from I/O overload
- **Consistent permissions** - no Windows/Linux permission mismatches
- **Better isolation** - code runs in a true Linux environment

## Implementation Strategy

### 1. Default Configuration (Stable)

The main `docker-compose.yml` uses only named volumes:

```yaml
volumes:
  # Named volume - fast and stable
  - dev_backend_code:/app/netra_backend
  - dev_backend_logs:/app/logs
  # NOT bind mounts
  # - ./netra_backend:/app/netra_backend  # AVOID
```

### 2. Development Override (When Needed)

Use `docker-compose.override.yml` for bind mounts when you need real-time sync:

```yaml
# Only use when actively developing
volumes:
  - ./netra_backend:/app/netra_backend:delegated
  # Exclude problematic directories
  - /app/netra_backend/__pycache__
```

### 3. Hybrid Approach

Mix named volumes and selective bind mounts:

```yaml
volumes:
  # Source code - bind mount for editing
  - ./src:/app/src:delegated
  # Dependencies - named volume for stability
  - node_modules:/app/node_modules
  # Build artifacts - named volume
  - build_cache:/app/.next
```

## Usage Guide

### Starting Services

```bash
# Use named volumes only (most stable)
docker-compose --profile dev up

# Use with bind mounts (for active development)
# Ensure docker-compose.override.yml exists
docker-compose --profile dev up

# Disable bind mounts temporarily
mv docker-compose.override.yml docker-compose.override.yml.disabled
docker-compose --profile dev up
```

### Managing Volumes

```bash
# Windows
scripts\manage_docker_volumes.bat

# Linux/Mac
./scripts/manage_docker_volumes.sh

# Common operations
docker volume ls | grep netra           # List volumes
docker volume inspect netra-dev-backend-code  # Inspect volume
docker volume prune                     # Clean unused volumes
```

### Initial Setup

1. **First time setup**:
   ```bash
   # Initialize volumes with your code
   scripts/manage_docker_volumes.bat init  # Windows
   ./scripts/manage_docker_volumes.sh init  # Linux/Mac
   ```

2. **Start services**:
   ```bash
   docker-compose --profile dev up
   ```

3. **Access containers**:
   ```bash
   docker exec -it netra-dev-backend bash
   ```

### Syncing Code

When using named volumes, you need to sync code manually:

```bash
# Sync from host to volume (deploy your changes)
scripts/manage_docker_volumes.bat sync-to

# Sync from volume to host (retrieve changes)
scripts/manage_docker_volumes.bat sync-from

# Or use docker cp directly
docker cp ./netra_backend/. netra-dev-backend:/app/netra_backend/
```

## Performance Optimization

### 1. Volume Mount Options

- **`:delegated`** (macOS): Container's view is authoritative, better write performance
- **`:cached`** (macOS): Host's view is authoritative, better read performance
- **`:ro`** (read-only): For files that shouldn't be modified

### 2. Exclude Patterns

Always exclude build artifacts and dependencies:

```yaml
volumes:
  - ./src:/app/src
  - /app/node_modules        # Exclude
  - /app/.next               # Exclude
  - /app/__pycache__         # Exclude
```

### 3. Resource Limits

Prevent containers from consuming too many resources:

```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
```

## Troubleshooting

### Docker Desktop Crashes

1. **Immediate fix**: Switch to named volumes
   ```bash
   mv docker-compose.override.yml docker-compose.override.yml.disabled
   docker-compose down
   docker-compose --profile dev up
   ```

2. **Check resource usage**:
   ```bash
   docker stats
   docker system df
   ```

3. **Clean up**:
   ```bash
   docker system prune -a
   docker volume prune
   ```

### Slow Performance

1. **Use named volumes** for dependencies and build artifacts
2. **Limit bind mounts** to source code only
3. **Use `:delegated`** option on macOS
4. **Consider alternatives** like Mutagen or docker-sync

### Permission Issues

1. **Use named volumes** - permissions are handled correctly
2. **Set user in Dockerfile**:
   ```dockerfile
   RUN useradd -m -u 1000 appuser
   USER appuser
   ```

## Best Practices Summary

### DO:
- ✅ Use named volumes for databases, dependencies, and build artifacts
- ✅ Use `:delegated` or `:cached` mount options on macOS
- ✅ Exclude `node_modules`, `__pycache__`, `.next`, etc.
- ✅ Set resource limits to prevent container resource exhaustion
- ✅ Use the volume management scripts for setup and syncing
- ✅ Keep bind mounts to a minimum - only source code when needed

### DON'T:
- ❌ Mount `node_modules` or Python virtual environments
- ❌ Mount database data directories
- ❌ Mount your entire home directory
- ❌ Use bind mounts for production or CI/CD
- ❌ Mount large directories with thousands of files
- ❌ Ignore Docker Desktop memory/CPU warnings

## Alternative Solutions

If you must use extensive file sharing:

1. **WSL2 (Windows)**: Run Docker inside WSL2 and keep files in the Linux filesystem
2. **Mutagen**: Advanced file synchronization tool
3. **docker-sync**: Ruby-based sync solution
4. **Remote Development**: Use GitHub Codespaces or remote servers
5. **Native Linux**: Consider dual-boot or Linux VM for development

## Monitoring and Maintenance

### Regular Maintenance Tasks

```bash
# Weekly: Clean unused resources
docker system prune -a
docker volume prune

# Monthly: Backup important volumes
./scripts/manage_docker_volumes.sh backup netra-dev-postgres-data

# Before major updates: Full backup
for volume in $(docker volume ls -q | grep netra); do
    ./scripts/manage_docker_volumes.sh backup $volume
done
```

### Health Checks

```bash
# Check Docker Desktop resource usage
docker system df
docker stats --no-stream

# Check volume sizes
docker volume ls -q | grep netra | xargs -I {} sh -c 'echo -n "{}: " && docker run --rm -v {}:/data alpine du -sh /data'

# Monitor file sync issues (if using bind mounts)
# High CPU on com.docker.backend or Vmmem process indicates sync problems
```

## Conclusion

Named volumes are the key to stable Docker development on Windows and macOS. While bind mounts offer convenience for active development, they should be used sparingly and only for source code. Following these practices will prevent Docker Desktop crashes and provide a much better development experience.