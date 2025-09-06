# How to Allocate More Memory to Docker

## Windows with Docker Desktop

### Method 1: Docker Desktop Settings (GUI)

1. **Open Docker Desktop**
   - Right-click the Docker icon in the system tray
   - Click "Settings" or "Preferences"

2. **Navigate to Resources**
   - Click on "Settings" → "Resources" → "Advanced"
   - Or in newer versions: "Settings" → "Resources" → "WSL Integration"

3. **Adjust Memory Allocation**
   - Find the "Memory" slider
   - Increase the memory allocation (e.g., from 8GB to 12GB)
   - The maximum depends on your system's total RAM

4. **Apply Changes**
   - Click "Apply & Restart"
   - Docker will restart with the new memory allocation

### Method 2: WSL2 Configuration File (.wslconfig)

For Docker Desktop using WSL2 backend (most common on Windows):

1. **Create/Edit .wslconfig file**
   ```powershell
   notepad "$env:USERPROFILE\.wslconfig"
   ```

2. **Add memory configuration**
   ```ini
   [wsl2]
   memory=12GB   # Allocate 12GB to WSL2 (and thus Docker)
   processors=6  # Number of processors (optional)
   swap=8GB      # Swap size (optional)
   swapfile=%USERPROFILE%\AppData\Local\Temp\swap.vhdx  # Swap location (optional)
   
   # Additional performance settings
   localhostForwarding=true
   nestedVirtualization=true
   ```

3. **Save and restart WSL**
   ```powershell
   wsl --shutdown
   ```
   Then restart Docker Desktop

### Method 3: Command Line Check

To verify current Docker memory allocation:

```powershell
# Check Docker system info
docker system info | findstr "Total Memory"

# Or use docker info
docker info | findstr "Memory"

# Check WSL2 memory
wsl -d docker-desktop -e sh -c "free -h"
```

## Current System Status

Based on your crash analysis, your current Docker configuration shows:
- **Total Memory**: 8,329,089,024 bytes (≈8GB)
- **Platform**: Docker Desktop on Windows with WSL2
- **Kernel**: 6.6.87.2-microsoft-standard-WSL2

## Recommendations for Netra Project

For the Netra project with multiple services (backend, auth, postgres, redis, clickhouse), consider:

### Development Environment
- **Minimum**: 8GB (current)
- **Recommended**: 12-16GB
- **Optimal**: 16-24GB

### Memory Distribution Example (16GB total):
```yaml
# docker-compose.yml memory limits
services:
  backend:
    mem_limit: 4g
    mem_reservation: 2g
    
  auth:
    mem_limit: 2g
    mem_reservation: 1g
    
  postgres:
    mem_limit: 2g
    mem_reservation: 1g
    
  redis:
    mem_limit: 1g
    mem_reservation: 512m
    
  clickhouse:
    mem_limit: 2g
    mem_reservation: 1g
    
  frontend:
    mem_limit: 2g
    mem_reservation: 1g
```

## Verification Script

Create a script to check Docker memory allocation: