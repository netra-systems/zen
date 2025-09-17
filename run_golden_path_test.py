#!/usr/bin/env python3
"""
Direct execution script for Golden Path E2E tests.
This bypasses pytest subprocess issues and runs tests directly.
"""

import os
import sys
import asyncio
from pathlib import Path

# Set up the project path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Set staging environment variables
os.environ["ENVIRONMENT"] = "staging"
os.environ["STAGING_ENV"] = "true"
os.environ["TEST_MODE"] = "true"
os.environ["USE_STAGING_SERVICES"] = "true"
os.environ["INTEGRATION_TEST_MODE"] = "staging"

def run_simplified_golden_path_test():
    """Run the simplified golden path test directly."""
    print("🚀 Starting Golden Path E2E Test Execution Against Staging")
    print("=" * 60)

    try:
        # Import the test class
        from tests.e2e.golden_path.test_simplified_golden_path_e2e import SimplifiedGoldenPathE2ETests

        # Create test instance
        test_instance = SimplifiedGoldenPathE2ETests()

        # Set up the test method
        test_instance.setup_method(test_instance.test_simplified_golden_path_validation)

        print("✅ Test instance created and setup complete")

        # Run the main test
        print("\n📋 Executing: test_simplified_golden_path_validation")
        print("-" * 50)

        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(test_instance.test_simplified_golden_path_validation())
            print("\n✅ test_simplified_golden_path_validation PASSED")
        except Exception as e:
            print(f"\n❌ test_simplified_golden_path_validation FAILED")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            loop.close()

        # Run the auth components test
        print("\n📋 Executing: test_golden_path_authentication_components")
        print("-" * 50)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(test_instance.test_golden_path_authentication_components())
            print("\n✅ test_golden_path_authentication_components PASSED")
        except Exception as e:
            print(f"\n❌ test_golden_path_authentication_components FAILED")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            loop.close()

        print("\n🎉 ALL SIMPLIFIED GOLDEN PATH TESTS PASSED!")
        return True

    except ImportError as e:
        print(f"❌ Failed to import test class: {e}")
        print("This indicates missing dependencies or import path issues.")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error during test execution: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_staging_validation_test():
    """Run the staging validation test directly."""
    print("\n🚀 Starting Staging Validation E2E Test Execution")
    print("=" * 60)

    try:
        # Import the test class
        from tests.e2e.staging.test_golden_path_end_to_end_staging_validation import GoldenPathEndToEndStagingValidationTests

        # Create test instance
        test_instance = GoldenPathEndToEndStagingValidationTests()

        # Set up the test method
        test_instance.setup_method(test_instance.test_staging_environment_health_check)

        print("✅ Staging test instance created and setup complete")

        # Run environment health check first
        print("\n📋 Executing: test_staging_environment_health_check")
        print("-" * 50)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(test_instance.test_staging_environment_health_check())
            print("\n✅ test_staging_environment_health_check PASSED")
        except Exception as e:
            print(f"\n❌ test_staging_environment_health_check FAILED")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            loop.close()

        print("\n🎉 STAGING ENVIRONMENT HEALTH CHECK PASSED!")
        return True

    except ImportError as e:
        print(f"❌ Failed to import staging test class: {e}")
        print("This indicates missing dependencies or import path issues.")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error during staging test execution: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🌟 NETRA APEX GOLDEN PATH E2E TEST EXECUTION")
    print("Testing against GCP staging environment")
    print("Environment: staging")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[0]}")

    # Run tests in sequence
    success1 = run_simplified_golden_path_test()

    if success1:
        success2 = run_staging_validation_test()

        if success1 and success2:
            print("\n🎉 ALL GOLDEN PATH TESTS COMPLETED SUCCESSFULLY!")
            print("✅ Simplified Golden Path validation: PASSED")
            print("✅ Staging environment health check: PASSED")
            sys.exit(0)
        else:
            print("\n❌ SOME TESTS FAILED")
            sys.exit(1)
    else:
        print("\n❌ SIMPLIFIED GOLDEN PATH TESTS FAILED")
        sys.exit(1)