# Cross-Platform Compatibility Guide for Zen

## Overview
This document explains how the zen package works across different operating systems and what considerations are needed for true cross-platform compatibility.

## Current Compatibility Status

### ✅ Fully Compatible
- **Linux** (Ubuntu, Debian, CentOS, Fedora, etc.)
- **macOS** (10.15+)
- **WSL/WSL2** (Windows Subsystem for Linux)

### ✅ Full Compatibility (with automatic adjustments)
- **Windows** (Native) - Automatic permission mode detection as of Issue #1320

### 🐳 Universal Compatibility
- **Docker** - Works on all platforms that support Docker

## Platform-Specific Behavior

### Linux
```bash
# Installation
pip install zen-orchestrator
# or
pipx install zen-orchestrator

# Script location
~/.local/bin/zen

# PATH configuration
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**Status:** ✅ Full compatibility
- Shebang `#!/usr/bin/env python3` works perfectly
- File permissions handled correctly
- PATH integration standard

### macOS
```bash
# Installation
pip3 install zen-orchestrator
# or
pipx install zen-orchestrator
# or
brew install zen  # If Homebrew formula created

# Script location
~/.local/bin/zen  # pip/pipx
/opt/homebrew/bin/zen  # Homebrew on Apple Silicon
/usr/local/bin/zen  # Homebrew on Intel

# PATH configuration
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

**Status:** ✅ Full compatibility
- Works with both zsh (default) and bash
- Handles both Intel and Apple Silicon architectures
- Homebrew provides additional distribution option

### Windows (Native)

Windows requires special considerations due to different path handling and executable mechanisms.

#### Current Issues
1. **Path separators**: Windows uses `\` instead of `/`
2. **Executable format**: Windows doesn't use shebang lines
3. **File permissions**: Different permission model
4. **Shell differences**: CMD/PowerShell vs Unix shells

#### Windows Permission Mode (Issue #1320 Fix)
As of Issue #1320, Zen automatically detects Windows and adjusts the Claude CLI permission mode:

```python
# Automatic platform detection in zen_orchestrator.py
if platform.system() == "Windows":
    self.permission_mode = "bypassPermissions"  # Prevents approval prompts
else:
    self.permission_mode = "bypassPermissions"  # Standard mode for Unix-like systems
```

**Why this is needed:** Windows Claude CLI doesn't properly respect `bypassPermissions` mode and requires manual approval for commands, causing silent failures.

**Solution:** Zen now:
- Detects Windows automatically
- Uses `bypassPermissions` mode to avoid approval prompts
- Provides clear error messages if permission issues occur
- Works without any manual configuration

For full details, see [Issue #1320 Documentation](../../docs/issues/ISSUE_1320_ZEN_PERMISSION_ERROR_FIX.md).

#### Windows Installation
```powershell
# PowerShell
pip install zen-orchestrator

# Script locations
%LOCALAPPDATA%\Programs\Python\Python3X\Scripts\zen.exe
%LOCALAPPDATA%\Programs\Python\Python3X\Scripts\zen-script.py

# PATH configuration (PowerShell)
$env:Path += ";$env:LOCALAPPDATA\Programs\Python\Python3X\Scripts"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::User)
```

#### Windows Compatibility Fixes Needed

**1. Path Handling in zen_orchestrator.py:**
```python
import os
from pathlib import Path

# Instead of:
workspace = args.workspace or os.getcwd()

# Use:
workspace = Path(args.workspace or os.getcwd()).resolve()

# Instead of:
claude_dir = os.path.join(workspace, '.claude')

# Use:
claude_dir = Path(workspace) / '.claude'
```

**2. Subprocess Handling:**
```python
import subprocess
import sys
import platform

def run_command(cmd):
    """Cross-platform command execution."""
    if platform.system() == 'Windows':
        # Windows-specific handling
        shell = True
        if isinstance(cmd, list):
            cmd = ' '.join(cmd)
    else:
        # Unix-like systems
        shell = False
        if isinstance(cmd, str):
            cmd = cmd.split()
    
    return subprocess.run(
        cmd,
        shell=shell,
        capture_output=True,
        text=True
    )
```

**3. File Permissions:**
```python
import stat
import platform

def make_executable(path):
    """Make a file executable (Unix-only operation)."""
    if platform.system() != 'Windows':
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)
```

## Required Code Changes for Full Windows Support

### 1. Update zen_orchestrator.py
```python
# Add at the top of the file
import platform
from pathlib import Path

# Replace os.path operations with pathlib
def get_workspace_path(workspace_arg):
    """Get cross-platform workspace path."""
    if workspace_arg:
        return Path(workspace_arg).resolve()
    return Path.cwd()

# Handle file paths consistently
def get_config_path(config_file):
    """Get cross-platform config file path."""
    config_path = Path(config_file)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
    return config_path

# Platform-specific command execution
async def run_claude_instance(instance_config):
    """Run Claude instance with platform-specific handling."""
    if platform.system() == 'Windows':
        # Windows-specific subprocess creation
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace_path)
        )
    else:
        # Unix-like subprocess creation
        process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace_path)
        )
```

### 2. Update setup.py for Windows
```python
import platform

setup(
    name="zen-orchestrator",
    # ... other config ...
    entry_points={
        "console_scripts": [
            "zen=zen_orchestrator:run",
        ],
    },
    # Platform-specific dependencies
    install_requires=[
        "PyYAML>=6.0",
        "python-dateutil>=2.8.2",
        "colorama>=0.4.4;platform_system=='Windows'",  # Windows color support
    ],
)
```

### 3. Create Windows Batch Wrapper (Optional)
Create `zen.bat` for Windows users who prefer traditional batch files:
```batch
@echo off
python -m zen_orchestrator %*
```

## Docker as Universal Solution

For guaranteed cross-platform compatibility, Docker provides the best solution:

### Dockerfile (Multi-Platform)
```dockerfile
# Multi-platform base image
FROM --platform=$BUILDPLATFORM python:3.11-slim

# Install zen
WORKDIR /app
COPY . .
RUN pip install .

# Create non-root user (works on all platforms)
RUN useradd -m -u 1000 zen || adduser -D -u 1000 zen

USER zen
ENTRYPOINT ["zen"]
```

### Build for Multiple Platforms
```bash
# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64,windows/amd64 \
  -t netrasystems/zen:latest \
  --push .
```

### Run on Any Platform
```bash
# Linux/macOS
docker run --rm -v $(pwd):/workspace netrasystems/zen --help

# Windows PowerShell
docker run --rm -v ${PWD}:/workspace netrasystems/zen --help

# Windows CMD
docker run --rm -v %cd%:/workspace netrasystems/zen --help
```

## Testing Cross-Platform Compatibility

### Automated Testing Matrix
```yaml
# .github/workflows/cross-platform.yml
name: Cross-Platform Tests

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']
    
    runs-on: ${{ matrix.os }}
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install package
      run: |
        pip install -e .
    
    - name: Test command
      run: |
        zen --help
    
    - name: Run tests
      run: |
        pytest tests/
```

### Manual Testing Checklist

#### Linux Testing
- [ ] Install via pip
- [ ] Install via pipx
- [ ] Verify PATH setup
- [ ] Test all command options
- [ ] Test with different Python versions

#### macOS Testing
- [ ] Install via pip3
- [ ] Install via pipx
- [ ] Install via Homebrew (if available)
- [ ] Test on Intel Mac
- [ ] Test on Apple Silicon Mac
- [ ] Verify with both bash and zsh

#### Windows Testing
- [ ] Install via pip in PowerShell
- [ ] Install via pip in CMD
- [ ] Test PATH configuration
- [ ] Test in Git Bash
- [ ] Test in WSL
- [ ] Verify .exe wrapper works
- [ ] Test with spaces in paths

## Platform-Specific Features

### Unix-Only Features
```python
if platform.system() in ['Linux', 'Darwin']:
    # Unix-specific features
    # - Signal handling
    # - Process groups
    # - File permissions
    pass
```

### Windows-Only Features
```python
if platform.system() == 'Windows':
    # Windows-specific features
    # - Registry access
    # - COM objects
    # - Windows services
    import colorama
    colorama.init()  # Enable ANSI colors
```

## Best Practices for Cross-Platform Code

### 1. Always Use pathlib
```python
from pathlib import Path

# Good - works everywhere
config_file = Path.home() / '.config' / 'zen' / 'config.json'

# Bad - assumes Unix paths
config_file = os.path.expanduser('~/.config/zen/config.json')
```

### 2. Handle Line Endings
```python
# Open files with universal newlines
with open(file_path, 'r', newline='') as f:
    content = f.read()

# Write with consistent line endings
with open(file_path, 'w', newline='') as f:
    f.write(content)
```

### 3. Environment Variables
```python
import os

# Cross-platform home directory
home = Path.home()

# Cross-platform temp directory
import tempfile
temp_dir = tempfile.gettempdir()

# Cross-platform config directory
if platform.system() == 'Windows':
    config_dir = Path(os.environ.get('APPDATA', Path.home()))
else:
    config_dir = Path.home() / '.config'
```

### 4. Command Execution
```python
import shutil

# Find executables cross-platform
python_exe = shutil.which('python') or shutil.which('python3')
```

## Summary

### Current Status
- ✅ **Linux**: Fully compatible
- ✅ **macOS**: Fully compatible
- ⚠️ **Windows**: Needs path handling adjustments
- ✅ **Docker**: Universal compatibility

### Required Changes for Full Windows Support
1. Replace `os.path` with `pathlib.Path`
2. Handle subprocess creation differently per platform
3. Add Windows-specific dependencies (colorama)
4. Test thoroughly on all platforms

### Recommendation
For immediate cross-platform distribution:
1. **Primary**: Use Docker for guaranteed compatibility
2. **Secondary**: Document platform-specific installation
3. **Long-term**: Implement full Windows native support

The package structure and distribution mechanism (pip, PyPI) work on all platforms. The main compatibility issues are in the runtime code's path handling and subprocess management, which can be addressed with the changes outlined above.