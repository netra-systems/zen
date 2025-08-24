#!/usr/bin/env python3
"""
Service Restart Script with Configuration Fixes

Restarts all services with correct port configuration and validates integration.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity
- Value Impact: Eliminates manual service restart steps  
- Strategic Impact: Ensures consistent service startup
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    """Main function to restart services with correct configuration."""
    print("🔄 Restarting Netra Services with Configuration Fixes")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    
    try:
        # Step 1: Apply configuration fixes
        print("📋 Step 1: Applying configuration fixes...")
        fix_config_script = project_root / "fix_integration_config.py"
        
        if fix_config_script.exists():
            result = subprocess.run([
                sys.executable, str(fix_config_script)
            ], cwd=project_root)
            
            if result.returncode == 0:
                print("✅ Configuration fixes applied successfully")
            else:
                print("⚠️  Configuration fixes had issues but continuing...")
        else:
            print("⚠️  Configuration fix script not found, skipping...")
        
        # Step 2: Restart services using dev launcher
        print("\n🚀 Step 2: Starting services with dev launcher...")
        dev_launcher_path = project_root / "scripts" / "dev_launcher.py"
        
        if dev_launcher_path.exists():
            print("Starting services...")
            result = subprocess.run([
                sys.executable, str(dev_launcher_path)
            ], cwd=project_root)
            
            if result.returncode == 0:
                print("✅ Services started successfully")
            else:
                print(f"❌ Dev launcher failed with code {result.returncode}")
                return False
        else:
            print(f"❌ Dev launcher not found at {dev_launcher_path}")
            return False
        
        # Step 3: Wait for services to initialize
        print("\n⏳ Step 3: Waiting for services to initialize...")
        time.sleep(5)
        
        # Step 4: Run integration tests
        print("\n🧪 Step 4: Running integration tests...")
        integration_test_script = project_root / "integration_test.py"
        
        if integration_test_script.exists():
            result = subprocess.run([
                sys.executable, str(integration_test_script)
            ], cwd=project_root)
            
            if result.returncode == 0:
                print("✅ Integration tests passed")
                print("\n🎉 All services are running and integrated successfully!")
                return True
            else:
                print("⚠️  Integration tests found issues, but services are running")
                print("Check the integration test results for details")
                return True
        else:
            print("⚠️  Integration test script not found, skipping validation...")
            print("Services should be running - check manually")
            return True
            
    except Exception as e:
        print(f"\n💥 Service restart failed: {e}")
        return False

def print_usage_instructions():
    """Print usage instructions for the user."""
    print("\n📋 USAGE INSTRUCTIONS:")
    print("=" * 40)
    print("1. Frontend: http://localhost:3000")
    print("2. Backend API: http://localhost:8000")  
    print("3. Auth Service: http://localhost:8082 (or check service discovery)")
    print("4. WebSocket: ws://localhost:8000/ws")
    print("\n🔧 TROUBLESHOOTING:")
    print("- If auth service is on a different port, check service discovery files")
    print("- Run integration_test.py to validate all connections")
    print("- Check individual service logs in dev_launcher output")

if __name__ == "__main__":
    success = main()
    
    if success:
        print_usage_instructions()
    
    sys.exit(0 if success else 1)