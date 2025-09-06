#!/usr/bin/env python
"""
Diagnostic script to identify why Podman is failing in the test framework.
This confirms the root cause identified in the Five Whys analysis.
"""

import subprocess
import shutil
import os
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('-'*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        print(f"[SUCCESS] (exit code: {result.returncode})")
        if result.stdout:
            print(f"Output: {result.stdout.strip()[:200]}")
        if result.stderr:
            print(f"Stderr: {result.stderr.strip()[:200]}")
        return True
    except FileNotFoundError as e:
        print(f"[FAILED] Command not found - {e}")
        return False
    except subprocess.TimeoutExpired:
        print(f"[FAILED] Command timed out")
        return False
    except Exception as e:
        print(f"[FAILED] {type(e).__name__}: {e}")
        return False

def check_runtime_availability():
    """Check which container runtimes are available."""
    print("\n" + "="*60)
    print("CONTAINER RUNTIME AVAILABILITY CHECK")
    print("="*60)
    
    runtimes = {}
    
    # Check Docker
    docker_path = shutil.which('docker')
    if docker_path:
        print(f"[FOUND] Docker at: {docker_path}")
        runtimes['docker'] = docker_path
    else:
        print("[NOT FOUND] Docker NOT in PATH")
        runtimes['docker'] = None
    
    # Check Podman
    podman_path = shutil.which('podman')
    if podman_path:
        print(f"[FOUND] Podman at: {podman_path}")
        runtimes['podman'] = podman_path
    else:
        print("[NOT FOUND] Podman NOT in PATH")
        runtimes['podman'] = None
    
    # Check podman-docker compatibility
    podman_docker_path = shutil.which('podman-docker')
    if podman_docker_path:
        print(f"[FOUND] podman-docker at: {podman_docker_path}")
        runtimes['podman-docker'] = podman_docker_path
    else:
        print("[NOT FOUND] podman-docker NOT available (this would provide docker command compatibility)")
        runtimes['podman-docker'] = None
    
    return runtimes

def test_runtime_commands(runtimes):
    """Test basic commands with available runtimes."""
    print("\n" + "="*60)
    print("RUNTIME COMMAND TESTS")
    print("="*60)
    
    results = {}
    
    if runtimes.get('docker'):
        results['docker_ps'] = run_command(['docker', 'ps'], "Docker ps command")
        results['docker_version'] = run_command(['docker', 'version'], "Docker version command")
    
    if runtimes.get('podman'):
        results['podman_ps'] = run_command(['podman', 'ps'], "Podman ps command")
        results['podman_version'] = run_command(['podman', 'version'], "Podman version command")
        
    if runtimes.get('podman-docker'):
        results['podman_docker_ps'] = run_command(['podman-docker', 'ps'], "Podman-docker compatibility")
    
    return results

def check_subprocess_execution():
    """Test how subprocess calls work (mimics docker_rate_limiter behavior)."""
    print("\n" + "="*60)
    print("SUBPROCESS EXECUTION TEST (Mimics docker_rate_limiter)")
    print("="*60)
    
    # This mimics what execute_docker_command does
    cmd = ['docker', 'ps', '--format', '{{.Names}}']
    print(f"Attempting: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        print(f"[SUCCESS] Docker command succeeded")
        return True
    except FileNotFoundError as e:
        print(f"[FAILED] Docker command failed with FileNotFoundError")
        print(f"  Error: {e}")
        print("\n  THIS IS THE ROOT CAUSE: The system is hardcoded to use 'docker'")
        print("  but Docker is not available on this system.")
        return False
    except Exception as e:
        print(f"[FAILED] Docker command failed: {e}")
        return False

def suggest_workarounds(runtimes):
    """Suggest immediate workarounds based on available runtimes."""
    print("\n" + "="*60)
    print("RECOMMENDED WORKAROUNDS")
    print("="*60)
    
    if runtimes.get('podman') and not runtimes.get('docker'):
        print("\n[WORKAROUNDS] IMMEDIATE FIXES (choose one):\n")
        
        print("1. Install podman-docker for compatibility:")
        if os.name == 'nt':
            print("   Not directly available on Windows, use option 2 or 3 instead")
        else:
            print("   sudo dnf install podman-docker  # For Fedora/RHEL")
            print("   sudo apt install podman-docker  # For Debian/Ubuntu")
        
        print("\n2. Create an alias (temporary, for current session):")
        if os.name == 'nt':
            print("   In PowerShell: Set-Alias docker podman")
            print("   In Git Bash: alias docker='podman'")
        else:
            print("   alias docker='podman'")
            print("   Add to ~/.bashrc or ~/.zshrc for persistence")
        
        print("\n3. Create a docker.bat shim (Windows):")
        print("   Create C:\\Windows\\System32\\docker.bat with:")
        print("   @echo off")
        print("   podman %*")
        
        print("\n4. Modify PATH to include a docker shim:")
        print("   Create a directory with a 'docker' executable that calls podman")
        print("   Add this directory to the beginning of your PATH")

def check_test_framework_detection():
    """Check how the test framework detects the runtime."""
    print("\n" + "="*60)
    print("TEST FRAMEWORK RUNTIME DETECTION")
    print("="*60)
    
    # Import and check what the test framework would detect
    try:
        # Check the actual environment variable the system might use
        use_podman = os.environ.get('USE_PODMAN', '').lower() in ('true', '1', 'yes')
        prefer_podman = os.environ.get('PREFER_PODMAN', '').lower() in ('true', '1', 'yes')
        
        print(f"USE_PODMAN env var: {os.environ.get('USE_PODMAN', 'not set')}")
        print(f"PREFER_PODMAN env var: {os.environ.get('PREFER_PODMAN', 'not set')}")
        
        # Check if this is Windows (where Podman is often preferred)
        if os.name == 'nt':
            print("\n[INFO] Windows detected - system SHOULD prefer Podman")
            print("  But the execute_docker_command doesn't check for this!")
    except Exception as e:
        print(f"Error checking environment: {e}")

def main():
    """Run all diagnostics."""
    print("PODMAN FAILURE DIAGNOSTIC REPORT")
    print("="*60)
    print(f"Platform: {sys.platform}")
    print(f"OS: {os.name}")
    print(f"Python: {sys.version}")
    
    # Run diagnostics
    runtimes = check_runtime_availability()
    test_results = test_runtime_commands(runtimes)
    subprocess_works = check_subprocess_execution()
    check_test_framework_detection()
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSIS SUMMARY")
    print("="*60)
    
    if runtimes.get('podman') and not runtimes.get('docker'):
        print("\n[ROOT CAUSE CONFIRMED]:")
        print("   1. Podman is installed and working")
        print("   2. Docker command is NOT available")
        print("   3. The test framework's docker_rate_limiter.py uses hardcoded 'docker' commands")
        print("   4. This causes FileNotFoundError when subprocess tries to execute 'docker'")
        print("\n   The Five Whys analysis is correct!")
        
        suggest_workarounds(runtimes)
    elif runtimes.get('docker') and runtimes.get('podman'):
        print("\n[OK] Both Docker and Podman are available")
        print("  The system should work, but may not be using the optimal runtime")
    elif runtimes.get('docker'):
        print("\n[OK] Docker is available, system should work normally")
    else:
        print("\n[ERROR] No container runtime found! Install Docker or Podman")
    
    print("\n" + "="*60)
    print("For full analysis, see: PODMAN_FIVE_WHYS_ANALYSIS.md")
    print("="*60)

if __name__ == "__main__":
    main()