#!/usr/bin/env python3
"""
Issue #964 Demo Mode Validation Script

This script validates that the SSOT fix for UserExecutionContext in demo mode works correctly.
"""

import os
import asyncio
import logging
from infrastructure.websocket_auth_remediation import WebSocketAuthManager

async def test_demo_mode_fix():
    """Test that demo mode works with the SSOT UserExecutionContext fix."""
    # Enable demo mode
    os.environ["DEMO_MODE"] = "1"

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Initialize auth manager
    auth_manager = WebSocketAuthManager()

    logger.info("=== Issue #964 Demo Mode Validation ===")
    logger.info(f"Demo mode enabled: {auth_manager.demo_mode}")

    # Test demo authentication (this would previously fail with TypeError)
    try:
        result = await auth_manager.authenticate_websocket_connection(
            token=None,
            connection_id="demo-validation-test-964"
        )

        logger.info(f"Demo auth result: success={result.success}")
        logger.info(f"Demo auth error: {result.error_message}")
        logger.info(f"User context created: {result.user_context is not None}")

        if result.success and result.user_context:
            context = result.user_context
            logger.info(f"User ID: {context.user_id}")
            logger.info(f"Thread ID: {context.thread_id}")
            logger.info(f"Run ID: {context.run_id}")
            logger.info(f"WebSocket connection ID: {context.websocket_connection_id}")
            logger.info(f"Metadata: {context.metadata}")

            # Validate SSOT factory method worked
            assert context.user_id == "demo-user", f"Expected 'demo-user', got {context.user_id}"
            assert context.websocket_connection_id == "demo-validation-test-964", f"Expected connection ID match"
            assert context.metadata.get("demo_mode") is True, f"Expected demo_mode=True in metadata"

            logger.info("✅ SUCCESS: Issue #964 fix validated - demo mode works with SSOT factory method!")
            return True
        else:
            logger.error("❌ FAILED: Demo auth did not succeed")
            return False

    except Exception as e:
        logger.error(f"❌ FAILED: Demo mode test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        return False

    finally:
        # Clean up environment
        if "DEMO_MODE" in os.environ:
            del os.environ["DEMO_MODE"]

if __name__ == "__main__":
    success = asyncio.run(test_demo_mode_fix())
    exit(0 if success else 1)