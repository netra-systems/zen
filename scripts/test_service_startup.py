#!/usr/bin/env python3
"""
Simple test script to verify service startup orchestration.
Tests the core startup sequence without complex integration.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path

from dev_launcher.launcher import DevLauncher
from dev_launcher.config import LauncherConfig


async def test_service_startup():
    """Test basic service startup orchestration."""
    print("TESTING | Service startup orchestration...")
    
    # Create a minimal config for testing
    config = LauncherConfig(
        backend_port=None,  # Dynamic port
        frontend_port=3000,  # Use default
        dynamic_ports=True,
        no_browser=True,
        non_interactive=True,
        verbose=True,
        load_secrets=True,  # Load secrets for real connections
        startup_mode="standard"
    )
    
    launcher = DevLauncher(config)
    
    try:
        print("[U+1F4CB] PHASE 1 | Environment and pre-checks...")
        # Run environment checks
        env_ok = launcher.check_environment()
        if not env_ok:
            print(" FAIL:  FAILED | Environment check failed")
            return False
        
        print("[U+1F510] PHASE 2 | Loading secrets...")
        # Load secrets
        secrets_ok = launcher.load_secrets()
        if not secrets_ok:
            print(" WARNING: [U+FE0F] WARNING | Secrets loading had issues, continuing...")
        
        print("[U+1F4BE] PHASE 3 | Database validation...")
        # Validate databases
        db_ok = await launcher._validate_databases()
        if not db_ok:
            print(" FAIL:  FAILED | Database validation failed")
            return False
        
        print(" CYCLE:  PHASE 4 | Migration check...")
        # Check migrations
        migrations_ok = launcher.run_migrations()
        if not migrations_ok:
            print(" WARNING: [U+FE0F] WARNING | Migration issues, continuing...")
        
        print("[U+1F680] PHASE 5 | Starting services...")
        # Start core services (auth and backend only for this test)
        backend_success, auth_success = await launcher._start_core_services_with_cascade()
        
        if backend_success:
            print(" PASS:  SUCCESS | Backend service started")
        else:
            print(" FAIL:  FAILED | Backend service failed to start")
        
        if auth_success:
            print(" PASS:  SUCCESS | Auth service started")  
        else:
            print(" WARNING: [U+FE0F] WARNING | Auth service failed to start")
        
        if backend_success or auth_success:
            print(" TARGET:  PHASE 6 | Testing service readiness...")
            # Wait a moment for services to initialize
            await asyncio.sleep(3)
            
            # Test backend readiness
            if backend_success:
                backend_ready = launcher._wait_for_backend_readiness(timeout=15)
                if backend_ready:
                    print(" PASS:  SUCCESS | Backend is ready")
                else:
                    print(" WARNING: [U+FE0F] WARNING | Backend readiness check failed")
            
            # Test auth readiness
            if auth_success:
                auth_ready = launcher._verify_auth_system(timeout=10)
                if auth_ready:
                    print(" PASS:  SUCCESS | Auth system is ready")
                else:
                    print(" WARNING: [U+FE0F] WARNING | Auth system verification failed")
            
            print("[U+1F3C1] TESTING COMPLETE | Service startup orchestration test finished")
            
            # Keep services running for a moment to verify stability
            print("[U+23F1][U+FE0F] STABILITY | Keeping services running for 5 seconds...")
            await asyncio.sleep(5)
            
            return True
        else:
            print(" FAIL:  FAILED | No services started successfully")
            return False
            
    except Exception as e:
        print(f"[U+1F4A5] ERROR | Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("[U+1F9F9] CLEANUP | Shutting down services...")
        try:
            launcher._graceful_shutdown()
        except Exception as e:
            print(f" WARNING: [U+FE0F] WARNING | Cleanup error: {e}")
            launcher.emergency_cleanup()


def main():
    """Run the service startup test."""
    print("="*80)
    print("SERVICE STARTUP ORCHESTRATION TEST")
    print("="*80)
    print()
    
    start_time = time.time()
    success = asyncio.run(test_service_startup())
    elapsed = time.time() - start_time
    
    print()
    print("="*80)
    if success:
        print(f" PASS:  TEST PASSED | Service startup orchestration test completed successfully in {elapsed:.1f}s")
        exit_code = 0
    else:
        print(f" FAIL:  TEST FAILED | Service startup orchestration test failed after {elapsed:.1f}s")
        exit_code = 1
    
    print("="*80)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())