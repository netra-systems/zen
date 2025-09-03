#!/usr/bin/env python3
"""
Launch DEV Environment for Local Development - DEPRECATED

This script is now a lightweight wrapper around docker_manual.py which uses
UnifiedDockerManager as the SSOT for all Docker operations.

CRITICAL: All Docker operations now go through UnifiedDockerManager via docker_manual.py.
"""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """
    DEPRECATED: This script now delegates to docker_manual.py for SSOT Docker management.
    """
    print("=" * 70)
    print("DEPRECATION NOTICE: launch_dev_env.py is deprecated")
    print("=" * 70)
    print("This script now uses docker_manual.py with UnifiedDockerManager.")
    print("For full Docker management features, please use:")
    print("  python scripts/docker_manual.py start --environment dev")
    print("  python scripts/docker_manual.py stop --environment dev")
    print("  python scripts/docker_manual.py status")
    print("=" * 70)
    
    # Simple wrapper: start dev environment
    docker_manual_path = Path(__file__).parent / "docker_manual.py"
    
    try:
        print("Starting DEV environment via docker_manual.py...")
        result = subprocess.run([
            sys.executable, str(docker_manual_path),
            "start", "--environment", "dev"
        ])
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error: Failed to launch dev environment: {e}")
        print("Please run directly: python scripts/docker_manual.py start --environment dev")
        sys.exit(1)



if __name__ == "__main__":
    main()