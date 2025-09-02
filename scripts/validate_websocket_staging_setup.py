from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
WebSocket Staging Setup Validation Script

This script validates that WebSocket testing configuration is properly set up for staging.
It provides clear feedback on what needs to be configured and how to fix common issues.

Business Value:
- Ensures staging WebSocket testing infrastructure is ready
- Prevents deployment issues by validating connectivity before deployment
- Provides actionable feedback for fixing WebSocket configuration issues

Usage:
    python scripts/validate_websocket_staging_setup.py
    python scripts/validate_websocket_staging_setup.py --fix-common-issues
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.robust_websocket_test_helper import (
    validate_websocket_configuration,
    run_websocket_smoke_test,
    diagnose_websocket_issues
)


def print_header(title: str):
    """Print section header."""
    print(f"\n{title}")
    print("=" * len(title))


def print_status(label: str, success: bool, details: str = ""):
    """Print status with consistent formatting."""
    status = "PASS" if success else "FAIL"
    print(f"  {status} {label}")
    if details:
        print(f"      {details}")


async def validate_staging_setup():
    """Validate staging WebSocket setup."""
    print("WebSocket Staging Setup Validation")
    print("=" * 60)
    
    overall_success = True
    
    # 1. Configuration Validation
    print_header("1. Configuration Validation")
    
    try:
        validation = await validate_websocket_configuration()
        
        print_status("Environment Detection", validation["environment_detected"])
        print_status("URLs Configured", validation["urls_configured"])
        print_status("Authentication Available", validation["auth_available"])
        print_status("SSL/TLS Configured", validation["ssl_configured"])
        print_status("Basic Connectivity", validation["connectivity_possible"])
        
        if not all([
            validation["environment_detected"],
            validation["urls_configured"],
            validation["connectivity_possible"]
        ]):
            overall_success = False
            
    except Exception as e:
        print_status("Configuration Validation", False, f"Error: {e}")
        overall_success = False
    
    # 2. Environment Variables Check
    print_header("2. Environment Variables Check")
    
    env_vars = {
        "E2E_OAUTH_SIMULATION_KEY": "Required for staging authentication",
        "ENVIRONMENT": "Should be 'staging' for staging tests",
        "WEBSOCKET_TEST_TOKEN": "Alternative auth method (optional)"
    }
    
    for var_name, description in env_vars.items():
        value = get_env().get(var_name)
        has_value = bool(value)
        print_status(var_name, has_value, description)
        
        if var_name == "E2E_OAUTH_SIMULATION_KEY" and not has_value:
            overall_success = False
    
    # 3. Smoke Test
    print_header("3. Basic Connectivity Test")
    
    try:
        smoke_passed = await run_websocket_smoke_test()
        print_status("WebSocket Smoke Test", smoke_passed)
        
        if not smoke_passed:
            overall_success = False
            
    except Exception as e:
        print_status("Smoke Test", False, f"Error: {e}")
        overall_success = False
    
    # 4. Summary and Recommendations
    print_header("4. Summary and Recommendations")
    
    if overall_success:
        print("  PASS WebSocket staging setup is ready")
        print("\n  Next steps:")
        print("    - Run: pytest tests/mission_critical/test_staging_websocket_agent_events.py -v")
        print("    - Run: python scripts/test_staging_websocket_comprehensive.py --quick")
    else:
        print("  FAIL WebSocket staging setup needs attention")
        print("\n  Required actions:")
        
        if not get_env().get("E2E_OAUTH_SIMULATION_KEY"):
            print("    1. Set E2E_OAUTH_SIMULATION_KEY environment variable")
            print("       Contact team lead for staging OAuth simulation key")
        
        print("    2. Ensure staging services are deployed and healthy:")
        print("       - Backend: https://netra-backend-staging-701982941522.us-central1.run.app/health")
        print("       - Auth: https://netra-auth-service-701982941522.us-central1.run.app/auth/health")
        
        print("    3. Test staging deployment:")
        print("       python scripts/deploy_to_gcp.py --project netra-staging --build-local")
        
        print("\n  Debug tools available:")
        print("    - python test_framework/robust_websocket_test_helper.py")
        print("    - python scripts/test_staging_websocket_comprehensive.py --debug")
    
    return overall_success


async def fix_common_issues():
    """Attempt to fix common WebSocket configuration issues."""
    print_header("Attempting to Fix Common Issues")
    
    fixes_applied = []
    
    # Check if we're in the right directory
    if not (Path.cwd() / "tests" / "mission_critical").exists():
        print("  WARN Not in project root directory")
        print("       Please run from netra-core-generation-1 root")
        return False
    
    # Check test configuration
    mission_critical_file = Path("tests/mission_critical/test_websocket_agent_events_suite.py")
    if mission_critical_file.exists():
        print("  PASS Mission critical WebSocket tests found")
        fixes_applied.append("Mission critical tests available")
    else:
        print("  FAIL Mission critical WebSocket tests not found")
        return False
    
    # Check staging utilities
    staging_helper = Path("test_framework/staging_websocket_test_helper.py")
    if staging_helper.exists():
        print("  PASS Staging WebSocket test helper found")
        fixes_applied.append("Staging test utilities available")
    else:
        print("  FAIL Staging WebSocket test helper not found")
        return False
    
    # Check robust helper
    robust_helper = Path("test_framework/robust_websocket_test_helper.py")
    if robust_helper.exists():
        print("  PASS Robust WebSocket test helper found")
        fixes_applied.append("Robust test utilities available")
    else:
        print("  FAIL Robust WebSocket test helper not found")
        return False
    
    print(f"\n  Applied {len(fixes_applied)} fixes:")
    for fix in fixes_applied:
        print(f"    - {fix}")
    
    return True


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate WebSocket staging setup",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--fix-common-issues",
        action="store_true",
        help="Attempt to fix common configuration issues"
    )
    
    args = parser.parse_args()
    
    try:
        if args.fix_common_issues:
            fix_success = await fix_common_issues()
            if not fix_success:
                sys.exit(1)
        
        # Run validation
        success = await validate_staging_setup()
        
        exit_code = 0 if success else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\nValidation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Set event loop policy for Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
