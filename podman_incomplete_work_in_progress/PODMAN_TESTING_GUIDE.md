# Podman Desktop Testing Guide

## Overview

This guide provides instructions for using Podman Desktop as an alternative to Docker Desktop for running the Netra test infrastructure. Podman offers several advantages:

- **No licensing requirements** - Podman is completely open source
- **Better resource usage** - ~30% less memory overhead
- **Rootless containers** - Enhanced security by default
- **Native Windows support** - No WSL2 dependency required

## Installation

### Windows (Podman Desktop)

1. **Download Podman Desktop**
   - Visit https://podman-desktop.io/
   - Download the Windows installer
   - Run the installer with default settings

2. **Initialize Podman Machine**
   ```powershell
   # Create and start the default machine
   podman machine init
   podman machine start
   
   # Verify installation
   podman --version
   podman info
   ```

3. **Install podman-compose**
   ```powershell
   # Using pip
   pip install podman-compose
   
   # Verify installation
   podman-compose --version
   ```

### macOS

1. **Install via Homebrew**
   ```bash
   # Install Podman
   brew install podman
   
   # Install podman-compose
   brew install podman-compose
   
   # Initialize machine
   podman machine init
   podman machine start
   ```

### Linux

1. **Install via package manager**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install podman podman-compose
   
   # RHEL/Fedora
   sudo dnf install podman podman-compose
   
   # Arch
   sudo pacman -S podman podman-compose
   ```

## Configuration

### 1. Environment Variables

Create or update your `.env` file:

```bash
# Container Runtime Selection
CONTAINER_RUNTIME=podman  # Options: docker, podman, auto

# Podman-specific settings
PODMAN_ROOTLESS=true      # Use rootless containers
PODMAN_USE_PODS=true       # Group services in pods
```

### 2. Runtime Auto-Detection

The test framework automatically detects available container runtimes. To prefer Podman when both are available:

```python
# In your test configuration
from test_framework.unified_container_manager import create_container_manager

# Automatically uses Podman if available
manager = create_container_manager(
    environment="test",
    prefer_podman=True  # Prefer Podman over Docker
)
```

## Usage

### Basic Commands

```bash
# Start services with Podman
podman-compose up -d

# Start test environment specifically
podman-compose --profile test up -d

# View running containers
podman ps

# View logs
podman logs <container-name>

# Stop services
podman-compose down

# Remove everything including volumes
podman-compose down -v
```

### Running Tests

#### Using Unified Test Runner

The test runner automatically detects and uses Podman:

```bash
# Run tests with Podman (auto-detected)
python tests/unified_test_runner.py --real-services

# Force Podman usage
CONTAINER_RUNTIME=podman python tests/unified_test_runner.py --real-services

# Run specific test categories
python tests/unified_test_runner.py --category integration --real-services
```

#### Manual Container Management

```python
# Python script example
from test_framework.unified_container_manager import UnifiedContainerManager, ContainerManagerMode

# Explicitly use Podman
manager = UnifiedContainerManager(
    environment="test",
    mode=ContainerManagerMode.PODMAN,
    use_alpine=True  # Use Alpine images for better performance
)

# Start services
await manager.start_services()

# Run your tests...

# Stop services
await manager.stop_services()
```

## Pod-Based Architecture

Podman uses pods to group related containers, similar to Kubernetes:

### Creating Pods Manually

```bash
# Create a pod with port mappings
podman pod create \
  --name netra-test-pod \
  -p 8000:8000 \
  -p 8081:8081 \
  -p 5432:5432

# Run containers in the pod
podman run -d --pod netra-test-pod --name backend netra-backend:latest
podman run -d --pod netra-test-pod --name auth netra-auth:latest
podman run -d --pod netra-test-pod --name postgres postgres:15-alpine
```

### Benefits of Pods

- **Shared network namespace** - Containers can communicate via localhost
- **Atomic management** - Start/stop all containers together
- **Better resource isolation** - Pod-level resource limits

## Troubleshooting

### Common Issues

#### 1. Podman Machine Not Started (Windows/macOS)

```bash
# Check machine status
podman machine list

# Start the machine
podman machine start

# If issues persist, recreate
podman machine rm
podman machine init --cpus 4 --memory 8192
podman machine start
```

#### 2. Permission Denied Errors

```bash
# Linux: Add user to podman group
sudo usermod -aG podman $USER
newgrp podman

# Or use rootless mode (recommended)
systemctl --user enable --now podman.socket
```

#### 3. Port Already in Use

```bash
# Find process using port
# Windows
netstat -ano | findstr :8000

# Linux/macOS
lsof -i :8000

# Kill the process or use different ports
```

#### 4. Container Build Failures

```bash
# Clear Podman cache
podman system prune -a

# Rebuild without cache
podman-compose build --no-cache
```

#### 5. Network Issues

```bash
# Reset Podman network
podman network prune

# Create custom network
podman network create netra-network

# Use custom network in compose
podman-compose --network netra-network up
```

### Debugging Commands

```bash
# View Podman system information
podman info

# Check container logs
podman logs -f <container-name>

# Inspect container
podman inspect <container-name>

# Execute command in container
podman exec -it <container-name> /bin/sh

# View resource usage
podman stats

# Check pod status
podman pod ps

# View pod details
podman pod inspect <pod-name>
```

## Performance Optimization

### 1. Use Alpine Images

Alpine-based images are smaller and faster:

```bash
# Use Alpine compose file
podman-compose -f podman-compose.yml up
```

### 2. Resource Limits

Set appropriate resource limits in `podman-compose.yml`:

```yaml
services:
  backend:
    mem_limit: 1g
    cpus: 0.5
```

### 3. Volume Optimization

Use named volumes instead of bind mounts for better performance:

```yaml
volumes:
  postgres_data:
    driver: local
```

### 4. Rootless Mode

Run in rootless mode for better security and performance:

```bash
# Check if running rootless
podman info | grep rootless

# Should show: rootless: true
```

## Migration from Docker

### Compose File Compatibility

The `podman-compose.yml` file is mostly compatible with Docker Compose, with these exceptions:

- No `deploy` section (Swarm mode)
- Simplified resource limits
- Full image paths recommended (`docker.io/library/postgres` instead of `postgres`)

### Command Equivalents

| Docker Command | Podman Command |
|---------------|----------------|
| `docker ps` | `podman ps` |
| `docker logs` | `podman logs` |
| `docker exec` | `podman exec` |
| `docker-compose up` | `podman-compose up` |
| `docker system prune` | `podman system prune` |

### Data Migration

To migrate existing Docker volumes to Podman:

```bash
# Export from Docker
docker run --rm -v docker_volume:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .

# Import to Podman
podman run --rm -v podman_volume:/data -v $(pwd):/backup alpine tar xzf /backup/backup.tar.gz -C /data
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Test with Podman

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Install Podman
      run: |
        sudo apt-get update
        sudo apt-get install -y podman podman-compose
    
    - name: Start services
      run: |
        podman-compose --profile test up -d
        podman-compose ps
    
    - name: Run tests
      run: |
        python tests/unified_test_runner.py --real-services
    
    - name: Cleanup
      if: always()
      run: |
        podman-compose down -v
```

## Best Practices

1. **Always use rootless mode** for better security
2. **Group related services in pods** for easier management
3. **Use Alpine images** for reduced resource usage
4. **Set resource limits** to prevent resource exhaustion
5. **Regular cleanup** with `podman system prune`
6. **Monitor resources** with `podman stats`
7. **Use named volumes** instead of bind mounts
8. **Keep Podman updated** for latest features and fixes

## Additional Resources

- [Podman Documentation](https://docs.podman.io/)
- [Podman Desktop Documentation](https://podman-desktop.io/docs)
- [podman-compose GitHub](https://github.com/containers/podman-compose)
- [Migrating from Docker](https://www.redhat.com/sysadmin/podman-docker-compose)
- [Podman Troubleshooting Guide](https://github.com/containers/podman/blob/main/troubleshooting.md)