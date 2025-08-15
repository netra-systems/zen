#!/usr/bin/env python3
"""
Quick local staging deployment script using docker-compose
"""

import subprocess
import sys
import time
from pathlib import Path
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_command(cmd, cwd=None):
    """Execute command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=False, text=True)
    return result.returncode == 0

def main():
    project_root = Path(__file__).parent
    
    print("🚀 Starting local staging deployment...")
    
    # Check Docker
    if not run_command(["docker", "--version"]):
        print("❌ Docker not found")
        sys.exit(1)
    
    # Stop existing containers
    print("\n🛑 Stopping existing containers...")
    run_command(["docker-compose", "-f", "docker-compose.staging.yml", "down", "-v"], cwd=project_root)
    
    # Build and start services
    print("\n🔨 Building and starting services...")
    if not run_command(["docker-compose", "-f", "docker-compose.staging.yml", "up", "-d", "--build"], cwd=project_root):
        print("❌ Failed to start services")
        sys.exit(1)
    
    # Wait for services
    print("\n⏳ Waiting for services to be ready...")
    time.sleep(20)
    
    # Show status
    print("\n📊 Service status:")
    run_command(["docker-compose", "-f", "docker-compose.staging.yml", "ps"], cwd=project_root)
    
    print("\n✅ Staging environment ready!")
    print("   Frontend: http://localhost:3000")
    print("   Backend: http://localhost:8080")
    print("   API Docs: http://localhost:8080/docs")
    print("\nRun 'docker-compose -f docker-compose.staging.yml down' to stop")

if __name__ == "__main__":
    main()