#!/usr/bin/env python
"""
STAGING FIX VALIDATION: Test WebSocket Event Transmission
Tests the specific fixes for WebSocket event transmission in staging environment.
"""

import asyncio
import json
import time
from typing import Dict, List, Any

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# REQUIRED WEBSOCKET EVENTS FOR CHAT VALUE
REQUIRED_EVENTS = [
    'agent_started',
    'agent_thinking', 
    'tool_executing',
    'tool_completed',
    'agent_completed'
]

class WebSocketStagingFixValidator:
    """Validates that our WebSocket staging fixes work correctly."""
    
    def __init__(self):
        self.received_events = []
        self.event_counts = {event: 0 for event in REQUIRED_EVENTS}
    
    async def test_websocket_route_fallback(self):
        """Test that the WebSocket route fallback works correctly."""
        logger.info("🔍 Testing WebSocket route fallback functionality")
        
        try:
            # Import the fallback agent handler function directly
            from netra_backend.app.routes.websocket import _create_fallback_agent_handler
            
            # Create a mock WebSocket object for testing
            class MockWebSocket:
                def __init__(self):
                    self.sent_messages = []
                
                async def send_json(self, message):
                    self.sent_messages.append(message)
                    logger.info(f"Mock WebSocket received: {message['type']}")
            
            mock_websocket = MockWebSocket()
            
            # Create fallback handler
            fallback_handler = _create_fallback_agent_handler(mock_websocket)
            
            # Test message handling
            from netra_backend.app.websocket_core.types import WebSocketMessage
            
            test_message = WebSocketMessage(
                type="CHAT",
                payload={"content": "Hello, test message!"},
                thread_id="test_thread_123",
                timestamp=time.time()
            )
            
            # Handle the message
            result = await fallback_handler.handle_message(
                user_id="test_user_123",
                websocket=mock_websocket,
                message=test_message
            )
            
            logger.info(f"Handler result: {result}")
            logger.info(f"Messages sent: {len(mock_websocket.sent_messages)}")
            
            # Verify all 5 events were sent
            event_types = [msg['type'] for msg in mock_websocket.sent_messages]
            logger.info(f"Event types sent: {event_types}")
            
            for required_event in REQUIRED_EVENTS:
                if required_event in event_types:
                    logger.info(f"✅ {required_event} event sent successfully")
                    self.event_counts[required_event] = 1
                else:
                    logger.error(f"❌ {required_event} event missing")
            
            # Check if all events were sent
            events_sent = sum(self.event_counts.values())
            logger.info(f"Events sent: {events_sent}/{len(REQUIRED_EVENTS)}")
            
            return events_sent == len(REQUIRED_EVENTS)
            
        except Exception as e:
            logger.error(f"❌ Fallback test failed: {e}")
            return False
    
    async def test_dependency_creation_staging(self):
        """Test that dependencies are created correctly in staging environment."""
        logger.info("🔍 Testing staging dependency creation")
        
        try:
            # Mock the staging environment
            import os
            original_env = os.environ.get("ENVIRONMENT", "")
            os.environ["ENVIRONMENT"] = "staging"
            
            # Test that our supervisor creation logic works
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
            
            # Create minimal dependencies for staging (like our WebSocket route does)
            websocket_bridge = create_agent_websocket_bridge()
            llm_manager = LLMManager()
            
            # Create supervisor 
            supervisor = SupervisorAgent(
                llm_manager=llm_manager,
                websocket_bridge=websocket_bridge
            )
            
            logger.info(f"✅ Successfully created SupervisorAgent: {type(supervisor)}")
            
            # Test thread service creation
            from netra_backend.app.services.thread_service import ThreadService
            thread_service = ThreadService()
            logger.info(f"✅ Successfully created ThreadService: {type(thread_service)}")
            
            # Restore original environment
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            else:
                del os.environ["ENVIRONMENT"]
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Dependency creation test failed: {e}")
            return False
    
    async def test_websocket_route_logging(self):
        """Test that our WebSocket route improvements log correctly."""
        logger.info("🔍 Testing WebSocket route logging")
        
        try:
            # Import the logging functions to make sure they work
            from netra_backend.app.routes.websocket import WEBSOCKET_CONFIG
            logger.info(f"✅ WebSocket config loaded: timeout={WEBSOCKET_CONFIG.connection_timeout_seconds}s")
            
            # Test the environment-specific timeout configuration
            from netra_backend.app.routes.websocket import _get_staging_optimized_timeouts
            timeout_config = _get_staging_optimized_timeouts()
            logger.info(f"✅ Staging timeout config: {timeout_config}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Route logging test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all staging fix validation tests."""
        logger.info("🚀 Starting STAGING FIX validation tests")
        
        tests = [
            ("WebSocket Route Fallback", self.test_websocket_route_fallback),
            ("Staging Dependency Creation", self.test_dependency_creation_staging),
            ("WebSocket Route Logging", self.test_websocket_route_logging),
        ]
        
        results = {}
        for test_name, test_func in tests:
            logger.info(f"Running test: {test_name}")
            try:
                result = await test_func()
                results[test_name] = result
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"{status} - {test_name}")
            except Exception as e:
                results[test_name] = False
                logger.error(f"❌ FAIL - {test_name}: {e}")
        
        # Summary
        passed = sum(results.values())
        total = len(results)
        logger.info(f"\n📊 STAGING FIX VALIDATION: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL STAGING FIXES WORKING - WebSocket events should work in staging!")
        else:
            logger.error("💥 SOME STAGING FIXES FAILED - Events may not work properly in staging")
            for test_name, result in results.items():
                if not result:
                    logger.error(f"   ❌ Failed: {test_name}")
        
        # Log the critical events status
        events_working = sum(self.event_counts.values())
        logger.info(f"🎯 CRITICAL EVENTS STATUS: {events_working}/{len(REQUIRED_EVENTS)} events working")
        for event_name, count in self.event_counts.items():
            status = "✅" if count > 0 else "❌"
            logger.info(f"   {status} {event_name}")
        
        return results

async def main():
    """Run the staging fix validation tests."""
    validator = WebSocketStagingFixValidator()
    results = await validator.run_all_tests()
    
    # Return appropriate exit code
    all_passed = all(results.values())
    if not all_passed:
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    asyncio.run(main())