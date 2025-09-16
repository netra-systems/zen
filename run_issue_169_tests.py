#!/usr/bin/env python3
"""
Simple test runner for Issue #169 SessionMiddleware log spam tests.

This script runs the Issue #169 tests to demonstrate the current log spam issue
and validate the rate limiting solution when implemented.
"""
import sys
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run Issue #169 tests."""
    logger.info("Starting Issue #169 SessionMiddleware log spam test execution")

    # Test files to run
    test_files = [
        "tests/unit/middleware/test_session_middleware_log_spam_reproduction.py",
        "tests/integration/middleware/test_session_middleware_log_spam_prevention.py",
    ]

    results = {}

    for test_file in test_files:
        test_path = Path(test_file)
        if not test_path.exists():
            logger.error(f"Test file not found: {test_file}")
            results[test_file] = "NOT_FOUND"
            continue

        logger.info(f"Running test file: {test_file}")

        try:
            # Run the test using pytest
            cmd = [
                sys.executable, "-m", "pytest",
                test_file,
                "-v",
                "--tb=short",
                "--disable-warnings"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            logger.info(f"Test completed: {test_file}")
            logger.info(f"Return code: {result.returncode}")

            if result.stdout:
                logger.info(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                logger.info(f"STDERR:\n{result.stderr}")

            results[test_file] = "PASSED" if result.returncode == 0 else "FAILED"

        except subprocess.TimeoutExpired:
            logger.error(f"Test timed out: {test_file}")
            results[test_file] = "TIMEOUT"
        except Exception as e:
            logger.error(f"Error running test {test_file}: {e}")
            results[test_file] = "ERROR"

    # Summary
    logger.info("\n" + "="*60)
    logger.info("ISSUE #169 TEST EXECUTION SUMMARY")
    logger.info("="*60)

    for test_file, result in results.items():
        logger.info(f"{test_file}: {result}")

    # Overall result
    all_passed = all(result == "PASSED" for result in results.values())
    failed_count = sum(1 for result in results.values() if result == "FAILED")

    logger.info(f"\nTotal tests: {len(results)}")
    logger.info(f"Failed tests: {failed_count}")

    if failed_count > 0:
        logger.info("\nFAILED TESTS ARE EXPECTED - They demonstrate the log spam issue!")
        logger.info("Tests should fail until rate limiting is implemented.")

    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)