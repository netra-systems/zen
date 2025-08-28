# Windows Port 8000 Permission Error Fix

## Problem
The backend service fails to bind to port 8000 on Windows with the error:
```
ERROR: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
```

This error prevents the backend container from starting and makes the service inaccessible.

## Root Causes
1. **Process already using port 8000** (most common)
2. Windows firewall blocking port access
3. Orphaned processes from previous dev launcher runs
4. Insufficient privileges (rare)
5. Antivirus software blocking socket operations

## Quick Solution

### Option 1: Automated Fix Script
```bash
# Check current status
python scripts/fix_port_8000_windows.py

# Kill processes using port 8000
python scripts/fix_port_8000_windows.py --kill-processes

# Create firewall rule if needed
python scripts/fix_port_8000_windows.py --create-firewall-rule

# Force fix everything
python scripts/fix_port_8000_windows.py --force
```

### Option 2: Test Port Binding
```bash
# Test if the backend can bind to port 8000
python scripts/test_backend_port_binding.py
```

### Option 3: Manual Commands
```cmd
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill a specific process (replace PID)
taskkill /F /T /PID [pid]

# Check Windows firewall rules
netsh advfirewall firewall show rule name=all | findstr 8000
```

## Detailed Diagnosis

### Step 1: Check Port Usage
```bash
python scripts/fix_port_8000_windows.py
```

This will show:
- ✅ Port 8000 appears to be free
- ⚠️  Port 8000 is being used by X process(es)

### Step 2: Identify Processes
If processes are found, they will be listed with:
- Process name (e.g., python.exe, uvicorn.exe)
- Process ID (PID)
- Connection info (TCP, state)

### Step 3: Kill Blocking Processes
```bash
python scripts/fix_port_8000_windows.py --kill-processes
```

This will:
- Skip system processes (safe)
- Try graceful termination first
- Force kill if needed with `--force` flag
- Verify port is freed after cleanup

### Step 4: Test Backend Binding
```bash
python scripts/test_backend_port_binding.py
```

This runs comprehensive tests:
- Basic socket binding to port 8000
- Backend main module import
- Uvicorn server startup test

## Prevention

1. **Use Graceful Shutdown**: Always stop dev launcher with Ctrl+C
2. **Avoid Force Killing**: Don't use Task Manager to kill dev launcher
3. **Regular Cleanup**: Run port cleanup script if developing frequently
4. **Use Dynamic Ports**: If conflicts persist, use `python scripts/dev_launcher.py --dynamic`

## Fallback Solutions

If the automated fix doesn't work:

### Alternative Ports
```bash
# Use different backend port
python scripts/dev_launcher.py --backend-port 8001
```

### Run as Administrator
```bash
# Right-click Command Prompt -> "Run as administrator"
# Then run the fix script
```

### Computer Restart
```bash
# Restart computer to clear all stuck processes
# This is a last resort but very effective
```

### Check Antivirus
- Add project folder to Windows Defender exclusions
- Check if antivirus is blocking socket operations
- Temporarily disable real-time protection for testing

## Files Created

### Scripts
- `scripts/fix_port_8000_windows.py` - Main Windows port fix script
- `scripts/test_backend_port_binding.py` - Backend port binding test script

### Documentation  
- `SPEC/learnings/windows_development.xml` - Detailed Windows development learnings
- `docs/WINDOWS_PORT_8000_FIX.md` - This file

## Success Verification

After applying the fix, you should see:
```
✅ SUCCESS: Port 8000 is now available for the backend service!
   You can now run the dev launcher:
   python scripts/dev_launcher.py
```

Then test the dev launcher:
```bash
python scripts/dev_launcher.py --no-browser --verbose
```

## Common Scenarios

### Scenario 1: Previous Dev Session Not Properly Closed
- **Symptoms**: uvicorn or python processes still running
- **Fix**: `python scripts/fix_port_8000_windows.py --kill-processes`

### Scenario 2: Windows Firewall Blocking
- **Symptoms**: Port appears free but binding fails
- **Fix**: `python scripts/fix_port_8000_windows.py --create-firewall-rule`

### Scenario 3: Antivirus Interference
- **Symptoms**: Intermittent binding failures
- **Fix**: Add project folder to antivirus exclusions

### Scenario 4: System Process Using Port
- **Symptoms**: System process shown in port usage
- **Fix**: Use alternative port with `--backend-port 8001`

## Technical Details

### Windows-Specific Process Management
The dev launcher now includes enhanced Windows process management:
- Uses `taskkill /F /T` for proper process tree termination
- Includes zombie process cleanup
- Port cleanup verification with retry logic
- Windows console event handlers for graceful shutdown

### Port Range Safety
- Port 8000 is safely outside Windows dynamic port range (49152-65535)
- No conflicts with well-known service ports
- Backend, frontend (3000), and auth service (8081) ports are all safe

### Implementation Files
- `dev_launcher/windows_process_manager.py` - Enhanced Windows process management
- `dev_launcher/launcher.py` - Windows-specific port cleanup methods
- `dev_launcher/port_manager.py` - Windows port availability checking

---

This solution has been tested and verified to resolve Windows socket permission errors on port 8000. The automated scripts provide a comprehensive fix for the most common causes of this issue.