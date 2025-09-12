#!/usr/bin/env python3
"""
SSOT Compliance Redirect: docker_health_manager.py -> unified_docker_cli.py

This script redirects legacy docker_health_manager.py calls to the 
Unified Docker CLI for SSOT compliance.
"""
import sys
import subprocess
from pathlib import Path

def main():
    """Redirect to unified CLI with appropriate mapping."""
    
    # Get the script directory
    script_dir = Path(__file__).parent
    unified_cli = script_dir / "unified_docker_cli.py"
    
    print(" CYCLE:  Redirecting to Unified Docker CLI for SSOT compliance...")
    print("   (Legacy docker_health_manager.py -> unified_docker_cli.py)")
    
    # Map legacy arguments to unified CLI
    if len(sys.argv) < 2:
        print("Usage: docker_health_manager.py [start|stop|status|health] [services...]")
        print("Redirecting to: python unified_docker_cli.py health --auto-fix")
        # Default to health check
        cmd = [sys.executable, str(unified_cli), "health", "--auto-fix"]
    else:
        action = sys.argv[1].lower()
        services = sys.argv[2:] if len(sys.argv) > 2 else None
        
        # Map legacy actions to unified commands
        if action in ["start", "up"]:
            cmd = [sys.executable, str(unified_cli), "start", "--wait-healthy"]
            if services:
                cmd.extend(["--services"] + services)
        
        elif action in ["stop", "down"]:
            cmd = [sys.executable, str(unified_cli), "stop"]
            if services:
                cmd.extend(["--services"] + services)
        
        elif action in ["status", "ps"]:
            cmd = [sys.executable, str(unified_cli), "status", "--detailed"]
            if services:
                cmd.extend(["--services"] + services)
        
        elif action in ["health", "check"]:
            cmd = [sys.executable, str(unified_cli), "health", "--auto-fix"]
            if services:
                cmd.extend(["--services"] + services)
        
        else:
            # Default to status for unknown actions
            cmd = [sys.executable, str(unified_cli), "status"]
        
        print(f"Redirecting to: {' '.join(cmd[2:])}")  # Show the unified CLI command
    
    # Execute the unified CLI
    return subprocess.run(cmd).returncode

if __name__ == "__main__":
    sys.exit(main())