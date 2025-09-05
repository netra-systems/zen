# Refresh Dev Guide - The ONE Way to Refresh Development Environment

## Overview

The `refresh_dev` command provides the official, standardized way for developers to refresh their local development environment. It eliminates confusion and ensures consistent, reliable environment management.

## Quick Start

```bash
# The most common usage - refresh everything
python scripts/refresh_dev.py

# Just refresh backend service
python scripts/refresh_dev.py backend

# Force clean rebuild when things get weird  
python scripts/refresh_dev.py --clean
```

## Command Overview

The `refresh_dev` command:

1. **Stops** existing development containers gracefully
2. **Rebuilds** images with latest code changes 
3. **Starts** services with health monitoring
4. **Verifies** all services are healthy and ready
5. **Reports** service URLs for immediate use

**Typical execution time:** 15-30 seconds (smart build) or 60-90 seconds (clean build)

## Usage Patterns

### Full Environment Refresh (Most Common)
```bash
python scripts/refresh_dev.py
```
- Refreshes all development services
- Uses smart caching (fresh code, cached dependencies)
- Recommended for daily development workflow

### Service-Specific Refresh
```bash
python scripts/refresh_dev.py backend      # Just backend
python scripts/refresh_dev.py auth         # Just auth service  
python scripts/refresh_dev.py frontend     # Just frontend
python scripts/refresh_dev.py backend auth # Multiple services
```
- Faster than full refresh
- Useful when working on specific services
- Dependencies are automatically handled

### Clean Rebuild
```bash
python scripts/refresh_dev.py --clean
```
- Forces complete rebuild from scratch
- Slower but guaranteed to be 100% fresh
- Use when debugging mysterious issues
- Recommended after major dependency changes

## Command Features

### ✅ Smart Defaults
- **No options required** - just works out of the box
- **Opinionated workflow** - eliminates decision fatigue
- **Clear feedback** - shows exactly what's happening

### ⚡ Performance Optimized
- **Smart caching** - rebuilds code, reuses dependencies
- **Parallel builds** - builds multiple services simultaneously  
- **Health monitoring** - only reports success when services are actually ready

### 🛡️ Error Handling
- **Graceful cleanup** - stops containers properly
- **Clear error messages** - tells you exactly what went wrong
- **Health reporting** - shows container status on failures

### 🌐 Service Discovery
- **Automatic port detection** - shows actual service URLs
- **Health verification** - confirms services are responsive
- **Quick access** - URLs ready to copy/paste

## Integration with UnifiedDockerManager

The `refresh_dev` command is built on top of the `UnifiedDockerManager` and provides:

### Programmatic Access
```python
from test_framework.unified_docker_manager import refresh_dev

# Use in scripts or tests
success = refresh_dev()                    # All services
success = refresh_dev(['backend'])        # Specific services
success = refresh_dev(clean=True)         # Clean rebuild
```

### Class-based Usage
```python
from scripts.refresh_dev import DevEnvironmentRefresher

refresher = DevEnvironmentRefresher(clean=False)
success = refresher.refresh_dev(['backend', 'auth'])
```

## Service URLs After Refresh

After successful refresh, the command shows active service URLs:

```
🌐 Service URLs:
   • Frontend      : http://localhost:3000
   • Backend API   : http://localhost:8000
   • Auth Service  : http://localhost:8081
   • PostgreSQL    : localhost:5433
   • Redis         : localhost:6380
   • ClickHouse HTTP: http://localhost:8124
```

## Shell Aliases (Recommended)

Add these to your shell profile (`.bashrc`, `.zshrc`, etc.) for convenience:

```bash
# Copy from .aliases file
source .aliases

# Or add manually:
alias refresh-dev="python scripts/refresh_dev.py"
alias refresh-backend="python scripts/refresh_dev.py backend"  
alias refresh-clean="python scripts/refresh_dev.py --clean"
```

Then use simply:
```bash
refresh-dev           # Full refresh
refresh-backend       # Backend only
refresh-clean         # Clean rebuild
```

## Troubleshooting

### Common Issues

**Build Fails:**
```bash
# Try clean rebuild
python scripts/refresh_dev.py --clean

# Check Docker daemon
docker version
```

**Services Don't Start:**
```bash
# Check port conflicts
netstat -an | findstr ":3000\|:8000\|:8081"

# Check container status  
docker ps -a --filter name=netra-dev
```

**Health Checks Fail:**
```bash
# Check logs
docker-compose -f docker-compose.yml logs --tail=50

# Manual health check
curl http://localhost:8000/health
curl http://localhost:8081/health
```

### Debug Mode

For debugging issues, the command provides detailed output:
- Container stopping process
- Build progress (shown in real-time)  
- Service startup monitoring
- Health check results
- Failure diagnostics

### When to Use Clean Rebuild

Use `--clean` when:
- Dependency versions changed (package.json, requirements.txt, etc.)
- Docker images seem stale or inconsistent  
- Mysterious build or runtime issues
- After major codebase changes
- First setup on new machine

## Architecture Integration

### Docker Compose Integration
- Uses `docker-compose.yml` (SSOT for development)
- Handles service dependencies automatically
- Manages networks and volumes correctly

### UnifiedDockerManager Features
- Cross-platform locking (prevents concurrent operations)
- Resource optimization (prevents Docker crashes)
- Health monitoring (comprehensive status reporting) 
- Environment isolation (development vs test vs production)

### SSOT Compliance
- Single compose file source (`docker-compose.yml`)
- Consistent service naming (`dev-*` prefixes)  
- Centralized port management
- Unified logging and monitoring

## Business Value

### Developer Productivity
- **Saves 5-10 minutes** per environment refresh
- **Eliminates confusion** about refresh procedures  
- **Prevents "works on my machine"** issues
- **Standardizes workflow** across team

### System Reliability  
- **Graceful container management** (no orphaned processes)
- **Health verification** (services actually work, not just running)
- **Error reporting** (clear feedback on failures)
- **Resource optimization** (prevents Docker daemon crashes)

### Team Velocity
- **Onboarding acceleration** (one command to learn)
- **Reduced support overhead** (standardized troubleshooting)
- **Deployment confidence** (local environment matches staging/prod)
- **Focus on code** (not infrastructure management)

## Related Commands

### Docker Management
```bash
python scripts/docker_manual.py status    # Check container status
python scripts/docker_manual.py clean     # Full cleanup
```

### Testing  
```bash
python tests/unified_test_runner.py --real-services  # Integration tests
```

### Monitoring
```bash
docker-compose -f docker-compose.yml logs -f         # Follow logs
docker stats                                          # Resource usage
```

## Future Enhancements

Planned improvements:
- **Auto-detection** of code changes (skip rebuild if no changes)
- **Selective rebuilds** (only rebuild changed services)  
- **Health benchmarking** (track startup time improvements)
- **IDE integration** (VS Code extension, etc.)
- **Notification support** (desktop notifications on completion)

---

**Remember:** `refresh_dev` is THE way to refresh your development environment. No other method is officially supported or recommended.