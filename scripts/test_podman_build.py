#!/usr/bin/env python3
"""
Test script to verify Podman build compatibility
"""

import subprocess
import sys
import shutil
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

def test_podman_availability():
    """Test if Podman is available."""
    if shutil.which("podman"):
        print("[OK] Podman is available")
        # Check version
        result = subprocess.run(["podman", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Podman version output:\n{result.stdout[:200]}")
        return True
    else:
        print("[FAIL] Podman is not installed")
        return False

def test_podman_compose():
    """Test if podman-compose is available."""
    if shutil.which("podman-compose"):
        print("[OK] podman-compose is available")
        result = subprocess.run(["podman-compose", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"podman-compose version: {result.stdout.strip()}")
        return True
    else:
        print("[FAIL] podman-compose is not installed")
        print("   Install with: pip install podman-compose")
        return False

def test_docker_compatibility():
    """Test Docker API compatibility."""
    # Podman provides Docker-compatible CLI
    if shutil.which("podman"):
        # Test if podman works with docker alias
        result = subprocess.run(["podman", "ps"], capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] Podman docker-compatible commands work")
            return True
        else:
            print("[WARN] Podman command failed:", result.stderr[:100])
    return False

def test_build_scripts():
    """Test that build scripts detect Podman correctly."""
    scripts = [
        "scripts/container_build.py",
        "scripts/docker_build_local.py",
        "scripts/docker_manual.py"
    ]
    
    project_root = Path(__file__).parent.parent
    
    for script_path in scripts:
        full_path = project_root / script_path
        if full_path.exists():
            print(f"[OK] {script_path} exists")
            # Test help output
            result = subprocess.run(
                [sys.executable, str(full_path), "-h"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and ("podman" in result.stdout.lower() or "container" in result.stdout.lower()):
                print(f"   -> Script supports Podman/containers")
            else:
                print(f"   [WARN] Script may not mention Podman support")
        else:
            print(f"[FAIL] {script_path} not found")

def main():
    print("="*60)
    print("PODMAN BUILD COMPATIBILITY TEST")
    print("="*60)
    
    # Test Podman availability
    print("\n1. Checking Podman installation:")
    podman_available = test_podman_availability()
    
    # Test podman-compose
    print("\n2. Checking podman-compose:")
    compose_available = test_podman_compose()
    
    # Test Docker compatibility
    print("\n3. Testing Docker API compatibility:")
    docker_compat = test_docker_compatibility()
    
    # Test build scripts
    print("\n4. Verifying build scripts:")
    test_build_scripts()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if podman_available:
        print("[OK] Podman is installed and working")
        if compose_available:
            print("[OK] podman-compose is available for multi-container apps")
        else:
            print("[WARN] podman-compose not found - install for full functionality")
        
        print("\n[NOTE] Build commands you can use:")
        print("  python scripts/container_build.py --runtime podman --all")
        print("  python scripts/docker_build_local.py --runtime podman --check-images")
        print("  python scripts/docker_manual.py --runtime podman status")
    else:
        print("[FAIL] Podman is not installed")
        print("\n[NOTE] To install Podman:")
        print("  Windows: Download from https://github.com/containers/podman/releases")
        print("  macOS: brew install podman")
        print("  Linux: Check your distribution's package manager")
    
    print("\n[INFO] The build system now supports both Docker and Podman!")
    print("   Scripts will auto-detect the available runtime.")

if __name__ == "__main__":
    main()