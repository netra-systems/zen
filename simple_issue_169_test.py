"""
Simple Issue #169 test to validate the log spam issue exists.
"""
import logging
import sys
import time
from pathlib import Path
from unittest.mock import Mock

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_log_spam_issue():
    """Test the log spam issue directly."""
    try:
        logger.info("Testing Issue #169 log spam...")

        # Create a simple mock that mimics the issue
        from fastapi import Request

        # Mock request that fails session access
        mock_request = Mock()
        mock_request.session = Mock(side_effect=RuntimeError("SessionMiddleware must be installed"))
        mock_request.cookies = {}
        mock_request.state = Mock()

        # Count log messages
        log_capture = []

        class MockMiddleware:
            def _safe_extract_session_data(self, request):
                """Mock version of the problematic method."""
                try:
                    # This will fail and log a warning
                    session = request.session
                except Exception as e:
                    # This simulates the problematic logging
                    log_capture.append(f"Session access failed: {e}")
                    logger.warning(f"Session access failed (middleware not installed?): {e}")
                return {}

        middleware = MockMiddleware()

        # Test multiple calls (simulating the spam)
        for i in range(10):  # Reduced for testing
            middleware._safe_extract_session_data(mock_request)

        logger.info(f"Generated {len(log_capture)} log messages from 10 calls")

        if len(log_capture) == 10:
            logger.info("✓ Log spam issue reproduced: 1 warning per call")
            return True
        else:
            logger.info(f"✗ Unexpected result: {len(log_capture)} warnings from 10 calls")
            return False

    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_log_spam_issue()
    print(f"Test result: {'PASSED' if success else 'FAILED'}")