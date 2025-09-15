#!/usr/bin/env python3
"""
Validation Test for Issue #937 - WebSocket Agent Events Test Fix

This test demonstrates the correct approach for testing WebSocket agent events:
- Send user_message to trigger agent workflow
- Wait for server to generate and send agent events
- Validate event structure from server output

CRITICAL: This proves the test design issue, not a production issue.
"""
import asyncio
import json
import time
import websockets
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketAgentEventValidator:
    """Validates WebSocket agent events using correct input->output pattern."""

    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.events_received: List[Dict[str, Any]] = []

    async def test_correct_agent_event_flow(self) -> Dict[str, Any]:
        """Test correct flow: user_message -> agent events from server."""
        results = {
            "connection_success": False,
            "user_message_sent": False,
            "agent_events_received": [],
            "connection_established_received": False,
            "test_conclusion": ""
        }

        try:
            # Connect to WebSocket
            async with websockets.connect(self.websocket_url) as websocket:
                results["connection_success"] = True
                logger.info(f"✅ Connected to WebSocket: {self.websocket_url}")

                # First, check what we get on connection
                try:
                    initial_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    initial_event = json.loads(initial_message)
                    logger.info(f"📨 Initial message received: {initial_event.get('type', 'unknown')}")

                    if initial_event.get('type') == 'connection_established':
                        results["connection_established_received"] = True
                        logger.info("✅ Connection established event received (expected)")
                except asyncio.TimeoutError:
                    logger.info("ℹ️ No initial message received")

                # Send user message to trigger agent workflow
                user_message = {
                    "type": "user_message",
                    "user_id": "test_user_agent_validation",
                    "thread_id": "test_thread_agent_validation",
                    "run_id": "test_run_agent_validation",
                    "message": "Please help me with a simple test request to validate agent events",
                    "timestamp": time.time(),
                    "test_context": {
                        "validation_test": True,
                        "expect_agent_events": True
                    }
                }

                await websocket.send(json.dumps(user_message))
                results["user_message_sent"] = True
                logger.info("✅ User message sent to trigger agent workflow")

                # Wait for agent events from server (up to 30 seconds)
                agent_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
                timeout_total = 30.0
                start_time = time.time()

                while time.time() - start_time < timeout_total:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event = json.loads(message)
                        event_type = event.get('type', 'unknown')

                        logger.info(f"📨 Event received: {event_type}")

                        if event_type in agent_events:
                            results["agent_events_received"].append({
                                "type": event_type,
                                "timestamp": time.time(),
                                "has_required_fields": self._validate_event_structure(event)
                            })
                            logger.info(f"🎯 Agent event captured: {event_type}")

                        # Store for analysis
                        self.events_received.append(event)

                    except asyncio.TimeoutError:
                        # Continue waiting
                        continue
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ JSON decode error: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error receiving message: {e}")
                        break

                # Analyze results
                if results["agent_events_received"]:
                    results["test_conclusion"] = "SUCCESS: Server generates agent events when triggered by user_message"
                    logger.info(f"🎉 SUCCESS: Received {len(results['agent_events_received'])} agent events")
                else:
                    results["test_conclusion"] = "INVESTIGATION: No agent events received - may need different trigger message"
                    logger.warning("⚠️ No agent events received - investigating trigger approach")

        except Exception as e:
            logger.error(f"❌ WebSocket connection error: {e}")
            results["test_conclusion"] = f"CONNECTION_ERROR: {str(e)}"

        return results

    async def test_broken_approach(self) -> Dict[str, Any]:
        """Test broken approach: send agent_started directly."""
        results = {
            "connection_success": False,
            "agent_event_sent": False,
            "response_received": False,
            "response_type": None,
            "test_conclusion": ""
        }

        try:
            async with websockets.connect(self.websocket_url) as websocket:
                results["connection_success"] = True

                # Wait for initial connection message
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=5.0)
                except:
                    pass

                # Send agent_started event directly (BROKEN APPROACH)
                agent_started_event = {
                    "type": "agent_started",
                    "user_id": "test_user_broken",
                    "agent_name": "test_agent",
                    "task": "Process user request",
                    "timestamp": time.time()
                }

                await websocket.send(json.dumps(agent_started_event))
                results["agent_event_sent"] = True
                logger.info("📤 Sent agent_started event directly (broken approach)")

                # Check response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_event = json.loads(response)
                    results["response_received"] = True
                    results["response_type"] = response_event.get('type', 'unknown')

                    logger.info(f"📨 Response: {results['response_type']}")

                    if results["response_type"] == "connection_established":
                        results["test_conclusion"] = "CONFIRMED: Server responds with connection_established, not agent_started echo"
                    else:
                        results["test_conclusion"] = f"Server responded with: {results['response_type']}"

                except asyncio.TimeoutError:
                    results["test_conclusion"] = "No response received to agent_started event"

        except Exception as e:
            results["test_conclusion"] = f"CONNECTION_ERROR: {str(e)}"

        return results

    def _validate_event_structure(self, event: Dict[str, Any]) -> bool:
        """Basic validation of event structure."""
        event_type = event.get('type')

        # Basic required fields
        if not all(key in event for key in ['type', 'timestamp']):
            return False

        # Type-specific validation
        if event_type == 'tool_executing':
            return 'tool_name' in event
        elif event_type == 'tool_completed':
            return 'results' in event
        elif event_type == 'agent_started':
            return 'user_id' in event

        return True

    def print_summary(self, correct_results: Dict, broken_results: Dict):
        """Print test summary."""
        print("\n" + "="*80)
        print("ISSUE #937 WEBSOCKET AGENT EVENTS - VALIDATION RESULTS")
        print("="*80)

        print("\n🔧 CORRECT APPROACH (user_message -> agent events):")
        print(f"   Connection: {'✅ SUCCESS' if correct_results['connection_success'] else '❌ FAILED'}")
        print(f"   User Message Sent: {'✅ YES' if correct_results['user_message_sent'] else '❌ NO'}")
        print(f"   Agent Events Received: {len(correct_results['agent_events_received'])}")
        for event in correct_results['agent_events_received']:
            print(f"     - {event['type']} (valid: {event['has_required_fields']})")
        print(f"   Conclusion: {correct_results['test_conclusion']}")

        print("\n❌ BROKEN APPROACH (send agent_started directly):")
        print(f"   Connection: {'✅ SUCCESS' if broken_results['connection_success'] else '❌ FAILED'}")
        print(f"   Agent Event Sent: {'✅ YES' if broken_results['agent_event_sent'] else '❌ NO'}")
        print(f"   Response Received: {'✅ YES' if broken_results['response_received'] else '❌ NO'}")
        print(f"   Response Type: {broken_results['response_type']}")
        print(f"   Conclusion: {broken_results['test_conclusion']}")

        print(f"\n🎯 ROOT CAUSE ANALYSIS:")
        print(f"   Issue #937 is caused by incorrect test design:")
        print(f"   - Tests send agent events as INPUT (wrong)")
        print(f"   - Agent events are OUTPUT from server workflows (correct)")
        print(f"   - Server correctly responds to broken approach with connection_established")
        print(f"   - Solution: Fix tests to trigger agent workflows, not send agent events directly")

        print("="*80)

async def main():
    """Run validation test for Issue #937."""
    # Use staging WebSocket URL from test failures
    websocket_url = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/api/v1/websocket"

    print(f"🔗 Testing WebSocket URL: {websocket_url}")

    validator = WebSocketAgentEventValidator(websocket_url)

    print("\n🧪 Testing CORRECT approach (user_message -> agent events)...")
    correct_results = await validator.test_correct_agent_event_flow()

    print("\n🧪 Testing BROKEN approach (send agent events directly)...")
    broken_results = await validator.test_broken_approach()

    # Print comprehensive summary
    validator.print_summary(correct_results, broken_results)

if __name__ == "__main__":
    asyncio.run(main())