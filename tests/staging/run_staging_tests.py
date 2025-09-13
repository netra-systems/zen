#!/usr/bin/env python3

"""

DEPRECATED TEST RUNNER - LEGACY COMPATIBILITY ONLY

=====================================================

This script is DEPRECATED and will be removed in a future version.

Please use the unified test runner instead:



    python tests/unified_test_runner.py --env staging [your args]



This script now redirects to the unified test runner for backward compatibility.

"""



import sys

import subprocess

from pathlib import Path



def show_deprecation_warning():

    """Show deprecation warning."""

    print("="*80)

    print("[DEPRECATION WARNING] This script is deprecated!")

    print("="*80)

    print("The staging test runner has been consolidated into unified_test_runner.py")

    print("Please update your scripts and CI/CD to use:")

    print()

    print("    python tests/unified_test_runner.py --env staging [your args]")

    print()

    print("The unified test runner now handles all staging test scenarios.")

    print()

    print("This legacy wrapper will be removed in a future version.")

    print("="*80)

    print()



def convert_args_to_unified(args):

    """Convert legacy staging args to unified test runner args."""

    unified_args = ["python", "tests/unified_test_runner.py", "--env", "staging"]

    

    # Skip the script name

    args = args[1:]

    

    # Convert specific staging arguments

    i = 0

    while i < len(args):

        arg = args[i]

        

        # Convert specific test selection

        if arg == "--test":

            if i + 1 < len(args):

                test_name = args[i + 1]

                # Map staging tests to categories

                test_category_mapping = {

                    "jwt_cross_service_auth": "auth",

                    "websocket_agent_events": "websocket",

                    "e2e_user_auth_flow": "e2e",

                    "api_endpoints": "api",

                    "service_health": "smoke",

                    "database_connectivity": "database",

                    "token_validation": "auth",

                    "configuration": "smoke",

                    "agent_execution": "agent",

                    "frontend_backend_integration": "integration"

                }

                category = test_category_mapping.get(test_name, "integration")

                unified_args.extend(["--category", category])

                i += 1

        

        # Pass through other supported arguments

        elif arg in ["--parallel", "--verbose", "--json", "--fail-fast", "--timeout"]:

            unified_args.append(arg)

            if arg == "--timeout" and i + 1 < len(args):

                unified_args.append(args[i + 1])

                i += 1

        

        i += 1

    

    return unified_args



def main():

    """Main entry point - redirect to unified test runner."""

    show_deprecation_warning()

    

    # Convert arguments

    unified_command = convert_args_to_unified(sys.argv)

    

    # Show what we're running

    print("Redirecting to:", " ".join(unified_command))

    print("-" * 80)

    

    # Execute the unified test runner

    try:

        exit_code = subprocess.run(unified_command, cwd=Path(__file__).parent.parent.parent).returncode

        sys.exit(exit_code)

    except Exception as e:

        print(f"Failed to run unified test runner: {e}")

        sys.exit(1)



if __name__ == "__main__":

    main()

