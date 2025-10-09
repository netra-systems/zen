#!/usr/bin/env python3
"""
Test script for CLI Thread Resolution improvements.
This script verifies that the zen agent_cli properly accepts backend-provided thread IDs.
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# Add parent directory to path to import agent_cli
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from agent_cli import WebSocketClient, Config, DebugManager, DebugLevel, Environment

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ThreadResolutionTester:
    """Test harness for thread resolution validation."""

    def __init__(self):
        self.config = Config(
            environment=Environment.LOCAL,
            debug_level=DebugLevel.TRACE,
            enable_websocket_diagnostics=True,
            stream_logs=True,
            use_backend_threads=True  # Enable backend thread management
        )
        self.debug = DebugManager(
            debug_level=DebugLevel.TRACE,
            enable_websocket_diagnostics=True
        )

    async def test_handshake_protocol(self):
        """Test that handshake properly receives and uses backend thread_id."""
        logger.info("=" * 60)
        logger.info("TEST 1: Handshake Protocol")
        logger.info("=" * 60)

        # Create WebSocket client
        client = WebSocketClient(
            config=self.config,
            token="test_token",
            debug_manager=self.debug,
            send_logs=True
        )

        try:
            # Connect and perform handshake
            logger.info("Connecting to WebSocket...")
            connected = await client.connect()

            if connected:
                logger.info(f"✅ Connection established")
                logger.info(f"Thread ID from handshake: {client.current_thread_id}")

                # Verify thread_id format
                if client.current_thread_id:
                    if client.current_thread_id.startswith("thread_"):
                        logger.info(f"✅ Backend-provided thread_id accepted: {client.current_thread_id}")
                    elif client.current_thread_id.startswith("cli_thread_"):
                        logger.warning(f"⚠️ Using local fallback thread_id: {client.current_thread_id}")
                    else:
                        logger.info(f"ℹ️ Thread ID format: {client.current_thread_id}")
                else:
                    logger.error("❌ No thread_id set after connection")

                # Close connection
                await client.close()
            else:
                logger.error("❌ Failed to connect to WebSocket")

        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")

    async def test_message_with_backend_thread(self):
        """Test sending a message using backend-provided thread_id."""
        logger.info("=" * 60)
        logger.info("TEST 2: Message with Backend Thread ID")
        logger.info("=" * 60)

        client = WebSocketClient(
            config=self.config,
            token="test_token",
            debug_manager=self.debug,
            send_logs=True
        )

        try:
            # Connect
            connected = await client.connect()
            if not connected:
                logger.error("❌ Failed to connect")
                return

            initial_thread_id = client.current_thread_id
            logger.info(f"Initial thread_id: {initial_thread_id}")

            # Send a test message
            test_message = "Test message for thread resolution"
            logger.info(f"Sending message: {test_message}")

            # Start receiving events in background
            receive_task = asyncio.create_task(client.receive_events())

            # Send message
            await client.send_message(test_message)

            # Wait a bit for events
            await asyncio.sleep(2)

            # Check if thread_id remained consistent
            final_thread_id = client.current_thread_id
            logger.info(f"Final thread_id: {final_thread_id}")

            if initial_thread_id == final_thread_id:
                logger.info(f"✅ Thread ID consistent: {final_thread_id}")
            else:
                logger.warning(f"⚠️ Thread ID changed from {initial_thread_id} to {final_thread_id}")

            # Cancel receive task and close
            receive_task.cancel()
            await client.close()

        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")

    async def test_log_filtering_with_thread_id(self):
        """Test that log filtering properly uses backend thread_id."""
        logger.info("=" * 60)
        logger.info("TEST 3: Log Filtering with Thread ID")
        logger.info("=" * 60)

        client = WebSocketClient(
            config=self.config,
            token="test_token",
            debug_manager=self.debug,
            send_logs=True,
            logs_count=10
        )

        try:
            # Connect
            connected = await client.connect()
            if not connected:
                logger.error("❌ Failed to connect")
                return

            thread_id = client.current_thread_id
            logger.info(f"Using thread_id for filtering: {thread_id}")

            # Create a mock backend_log event to test filtering
            mock_log_event = {
                "type": "backend_log",
                "messages": [
                    {
                        "thread_id": thread_id,
                        "level": "INFO",
                        "message": f"Test log for thread {thread_id}",
                        "timestamp": "2025-01-08T10:00:00"
                    },
                    {
                        "thread_id": "different_thread_123",
                        "level": "INFO",
                        "message": "Log for different thread",
                        "timestamp": "2025-01-08T10:00:01"
                    },
                    {
                        "thread_id": None,
                        "level": "SYSTEM",
                        "message": "System log without thread_id",
                        "timestamp": "2025-01-08T10:00:02"
                    }
                ],
                "total_count": 3
            }

            # Test the filtering logic
            logger.info("Testing log filtering...")
            await client._handle_backend_log(mock_log_event)

            logger.info(f"✅ Log filtering tested with thread_id: {thread_id}")

            await client.close()

        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")

    async def run_all_tests(self):
        """Run all thread resolution tests."""
        logger.info("Starting Thread Resolution Tests")
        logger.info("=" * 60)

        # Test 1: Handshake protocol
        await self.test_handshake_protocol()
        await asyncio.sleep(1)

        # Test 2: Message with backend thread
        await self.test_message_with_backend_thread()
        await asyncio.sleep(1)

        # Test 3: Log filtering
        await self.test_log_filtering_with_thread_id()

        logger.info("=" * 60)
        logger.info("Thread Resolution Tests Complete")


async def main():
    """Main test runner."""
    tester = ThreadResolutionTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # Run tests
    asyncio.run(main())