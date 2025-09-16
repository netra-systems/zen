#!/usr/bin/env python3
"""
Simple demonstration script for Issue #169 SessionMiddleware log spam.

This script reproduces the exact log spam scenario without requiring complex test infrastructure.
"""
import sys
import logging
import time
from unittest.mock import Mock
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Demonstrate Issue #169 log spam."""
    print("Issue #169 SessionMiddleware Log Spam Demonstration")
    print("=" * 60)

    # Set up logging to capture warnings
    log_messages = []

    class LogCapture(logging.Handler):
        def emit(self, record):
            log_messages.append(record)

    # Configure logging
    logger = logging.getLogger('netra_backend.app.middleware.gcp_auth_context_middleware')
    handler = LogCapture()
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)

    try:
        # Import the middleware
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        from fastapi import Request

        # Create middleware instance
        middleware = GCPAuthContextMiddleware(app=Mock())

        # Create mock request that will fail session access (reproduces production issue)
        mock_request = Mock(spec=Request)
        mock_request.session = Mock(side_effect=RuntimeError("SessionMiddleware must be installed"))
        mock_request.cookies = {}
        mock_request.state = Mock()

        print("\nSimulating 100 session access attempts (typical production load)...")
        start_time = time.time()

        # Simulate 100 session access attempts
        for i in range(100):
            try:
                session_data = middleware._safe_extract_session_data(mock_request)
                if i % 20 == 0:  # Progress indicator
                    print(f"Progress: {i}/100 requests processed")
            except Exception as e:
                print(f"Unexpected error at request {i}: {e}")

        end_time = time.time()
        duration = end_time - start_time

        # Analyze results
        warning_messages = [msg for msg in log_messages
                           if msg.levelno == logging.WARNING
                           and "Session access failed" in msg.getMessage()]

        warnings_count = len(warning_messages)
        warnings_per_hour = (warnings_count / duration) * 3600 if duration > 0 else warnings_count

        print(f"\nRESULTS:")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Warnings generated: {warnings_count}")
        print(f"Warnings per hour: {warnings_per_hour:.1f}")

        # Demonstrate the issue
        print(f"\nISSUE #169 DEMONSTRATION:")
        if warnings_count >= 90:  # Allow some tolerance
            print(f"✓ LOG SPAM REPRODUCED: {warnings_count} warnings from 100 requests")
            print(f"✓ Projected rate: {warnings_per_hour:.1f} warnings per hour")

            if warnings_per_hour > 100:
                print(f"✓ EXCEEDS TARGET: {warnings_per_hour:.1f}/hour > 100/hour threshold")

            print(f"\nTARGET BEHAVIOR:")
            print(f"- Current: {warnings_count} warnings")
            print(f"- Target: ≤1 warning per time window (with rate limiting)")
            print(f"- Reduction needed: {warnings_count - 1} fewer warnings")

            return 0  # Success in demonstrating the issue
        else:
            print(f"✗ ISSUE NOT REPRODUCED: Only {warnings_count} warnings generated")
            return 1

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running from the project root directory.")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Clean up logging handler
        logger.removeHandler(handler)

if __name__ == "__main__":
    exit_code = main()
    print(f"\nSimulation complete. Check output above for Issue #169 reproduction.")
    sys.exit(exit_code)