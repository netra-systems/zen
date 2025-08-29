# Docker Hot Reload Guide for Backend Services

## Overview
This guide explains the hot reload configuration for Netra's backend services in Docker, with special considerations for Mac and Windows developers.

## Quick Start

### Starting Services with Hot Reload
```bash
# Standard approach (uses docker-compose.dev.yml + docker-compose.override.yml)
docker-compose -f docker-compose.dev.yml up backend auth

# Without override file (if you want to disable extra optimizations)
docker-compose -f docker-compose.dev.yml up backend auth --no-deps
```

### Testing Hot Reload
1. Start the services: `docker-compose -f docker-compose.dev.yml up backend auth`
2. Edit any Python file in `netra_backend/` or `auth_service/`
3. Watch the console - you should see: `WARNING: Detected file change in 'path/to/file.py'. Reloading...`
4. Changes should reflect within 1-2 seconds

## Configuration Details

### What Changed
1. **Removed read-only volume mounts** - Allows uvicorn to monitor file changes
2. **Added explicit reload directories** - Monitors both service and shared directories
3. **Created docker-compose.override.yml** - Platform-specific optimizations
4. **Added auth service hot reload** - Previously missing

### Volume Mount Strategies

#### Linux (Native Docker)
- Best performance, no special configuration needed
- File system events work natively

#### Mac (Docker Desktop)
- **Issue**: File system events don't propagate properly from host to container
- **Solution**: Enable polling mode with `WATCHDOG_USE_POLLING=true`
- **Performance**: Use volume mount flags:
  - `:delegated` - For frequently changing code (best write performance)
  - `:cached` - For read-heavy files like configs
  - No flag - Consistent but slower

#### Windows (Docker Desktop/WSL2)
- **WSL2**: Best performance, similar to Linux
- **Docker Desktop**: Similar issues to Mac, use polling mode
- **Tip**: Keep code in WSL2 filesystem for best performance

## Common Issues and Solutions

### Issue: Changes Not Detected on Mac/Windows
**Solution**: Ensure polling is enabled in docker-compose.override.yml:
```yaml
environment:
  WATCHDOG_USE_POLLING: "true"
  WATCHDOG_POLL_INTERVAL: "1"
```

### Issue: High CPU Usage from Polling
**Solution**: Increase poll interval or use docker-sync/Mutagen:
```yaml
environment:
  WATCHDOG_POLL_INTERVAL: "2"  # Check every 2 seconds instead of 1
```

### Issue: Permission Errors
**Solution**: Ensure Docker has proper permissions:
```bash
# Mac/Linux
chmod -R 755 ./netra_backend ./auth_service

# Windows (Run as Administrator)
icacls . /grant Everyone:F /T
```

### Issue: Slow Reload on Large Codebases
**Solution**: Use more specific reload patterns:
```yaml
command: uvicorn app.main:app --reload-include "app/**/*.py" --reload-exclude "tests/*"
```

## Advanced Optimizations

### Option 1: Docker Sync (Mac)
For large codebases with performance issues:
```bash
# Install docker-sync
gem install docker-sync

# Create docker-sync.yml
syncs:
  backend-sync:
    src: './netra_backend'
    sync_excludes: ['__pycache__', '*.pyc', '.pytest_cache']

# Start sync
docker-sync start
```

### Option 2: Mutagen (Cross-platform)
Alternative to docker-sync with better cross-platform support:
```bash
# Install mutagen
brew install mutagen-io/mutagen/mutagen

# Create mutagen.yml
sync:
  backend:
    alpha: "./netra_backend"
    beta: "docker://netra-backend/app/netra_backend"
    mode: "two-way-resolved"
```

### Option 3: Development-Only Dockerfile
Create a minimal Dockerfile without COPY commands:
```dockerfile
# docker/backend.dev.Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
ENV PYTHONPATH=/app
# No COPY of source - relies entirely on volumes
```

## Performance Benchmarks

| Platform | Method | Reload Time | CPU Usage |
|----------|--------|-------------|-----------|
| Linux | Native | <1s | Low |
| Mac | Default | 2-3s | Medium |
| Mac | Polling | 1-2s | High |
| Mac | Docker-sync | <1s | Low |
| Windows WSL2 | Native | <1s | Low |
| Windows | Polling | 2-3s | High |

## Disabling Hot Reload

To disable hot reload temporarily:
1. Rename `docker-compose.override.yml` to `docker-compose.override.yml.disabled`
2. Or set environment variable: `RELOAD=false`

## File Patterns Monitored

Current configuration monitors:
- `*.py` - Python source files
- `*.json` - Configuration files
- `*.yaml`, `*.yml` - Configuration files

Excluded:
- `__pycache__` directories
- `*.pyc` compiled files
- `.pytest_cache` directories

## Troubleshooting Commands

```bash
# Check if file watching is working
docker exec netra-backend ls -la /app/netra_backend

# Monitor file system events (Linux/Mac)
docker exec netra-backend inotifywait -r -m /app/netra_backend

# Check uvicorn reload status
docker logs netra-backend --tail 50 | grep -i reload

# Force restart if stuck
docker-compose -f docker-compose.dev.yml restart backend
```

## Best Practices

1. **Use .dockerignore** - Exclude unnecessary files from context
2. **Keep containers running** - Don't stop/start, let hot reload handle changes
3. **Monitor logs** - Watch for reload messages to confirm it's working
4. **Clean regularly** - Remove `__pycache__` if reload seems stuck:
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} +
   ```

## Integration with IDEs

### VS Code
Add to `.vscode/settings.json`:
```json
{
  "files.watcherExclude": {
    "**/__pycache__/**": true,
    "**/node_modules/**": true
  }
}
```

### PyCharm
- Go to Settings → Build, Execution, Deployment → Docker
- Enable "Use Docker Compose V2"
- Set file watchers to exclude `__pycache__`

## Summary

The hot reload setup enables:
- ✅ Instant code updates without container restart
- ✅ Cross-platform compatibility (Linux, Mac, Windows)
- ✅ Monitoring of both service and shared directories
- ✅ Configurable performance optimizations
- ✅ Easy disable/enable via override file

For most developers, the default configuration will work well. Mac users may experience slightly slower reloads due to file system limitations, but the polling mode ensures changes are still detected reliably.