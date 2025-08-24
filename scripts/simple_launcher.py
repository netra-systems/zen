#!/usr/bin/env python3
"""
Simple launcher script to test basic functionality.

This bypasses complex dependencies and tests core launcher functionality.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path

def test_imports():
    """Test critical imports."""
    try:
        from dev_launcher.config import LauncherConfig
        print("[OK] Config module imported successfully")
        
        # Test basic configuration
        config = LauncherConfig()
        print(f"[OK] Config created successfully: project_root={config.project_root}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False

def test_basic_launcher():
    """Test basic launcher functionality."""
    try:
        from dev_launcher.config import LauncherConfig
        from dev_launcher.launcher import DevLauncher
        
        print("[OK] Launcher module imported successfully")
        
        # Create a minimal config for testing
        config = LauncherConfig(
            verbose=True,
            no_browser=True,
            load_secrets=False  # Skip secrets for now
        )
        
        # Create launcher instance
        launcher = DevLauncher(config)
        print("[OK] Launcher instance created successfully")
        
        # Test environment check only
        if launcher.check_environment():
            print("[OK] Environment check passed")
        else:
            print("[WARN] Environment check failed")
        
        return True
    except Exception as e:
        print(f"[ERROR] Launcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("Testing startup components...")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        return 1
    
    print()
    
    # Test basic launcher
    if not test_basic_launcher():
        return 1
    
    print()
    print("All basic tests passed!")
    print("Try running: python -m dev_launcher --help")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())