#!/usr/bin/env python
"""
CRITICAL TEST: WebSocket Agent Events - FOCUSED ON STAGING ISSUE
Test specifically for fixing WebSocket event transmission in staging environment.
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

class WebSocketEventTester:
    """Test WebSocket event transmission specifically for staging issues."""
    
    def __init__(self):
        self.received_events = []
        self.event_counts = {event: 0 for event in REQUIRED_EVENTS}
    
    async def test_agent_websocket_bridge_creation(self):
        """Test that AgentWebSocketBridge can create user emitters."""
        logger.info("🔍 Testing AgentWebSocketBridge factory pattern")
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.models.user_execution_context import UserExecutionContext
            
            # Create user context using constructor (models version doesn't have from_request)
            user_context = UserExecutionContext(
                user_id="test_user_12345",
                thread_id="test_thread_12345", 
                run_id="test_run_12345",
                request_id="test_request_12345",  # Required field for models version
                websocket_connection_id="test_ws_12345"
            )
            
            # Create isolated bridge
            bridge = create_agent_websocket_bridge(user_context)
            logger.info(f"✅ Created AgentWebSocketBridge: {type(bridge)}")
            
            # Test emitter creation
            emitter = await bridge.create_user_emitter(user_context)
            logger.info(f"✅ Created user emitter: {type(emitter)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ AgentWebSocketBridge test failed: {e}")
            return False
    
    async def test_websocket_dependencies_available(self):
        """Test that WebSocket route dependencies are available."""
        logger.info("🔍 Testing WebSocket route dependencies")
        
        try:
            # Test supervisor creation (the way WebSocket route does it)
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
            
            # Create minimal dependencies (like WebSocket route does)
            websocket_bridge = create_agent_websocket_bridge()
            llm_manager = LLMManager()
            
            # Create supervisor 
            supervisor = SupervisorAgent(
                llm_manager=llm_manager,
                websocket_bridge=websocket_bridge
            )
            logger.info(f"✅ SupervisorAgent created: {type(supervisor)}")
            
            # Test thread service availability
            from netra_backend.app.services.thread_service import ThreadService
            thread_service = ThreadService()
            logger.info(f"✅ ThreadService available: {type(thread_service)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Dependency test failed: {e}")
            return False
    
    async def test_websocket_manager_factory(self):
        """Test WebSocket manager factory creation."""
        logger.info("🔍 Testing WebSocket manager factory")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
            
            # Create user context using constructor (models version doesn't have from_request)
            user_context = UserExecutionContext(
                user_id="test_user_12345",
                thread_id="test_thread_12345", 
                run_id="test_run_12345",
                request_id="test_request_12345",  # Required field for models version
                websocket_connection_id="test_ws_12345"
            )
            
            # Create isolated WebSocket manager
            ws_manager = create_websocket_manager(user_context)
            logger.info(f"✅ Created WebSocket manager: {type(ws_manager)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ WebSocket manager factory test failed: {e}")
            return False
    
    async def test_event_emission_pipeline(self):
        """Test the complete event emission pipeline."""
        logger.info("🔍 Testing event emission pipeline")
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.models.user_execution_context import UserExecutionContext
            
            # Create user context using constructor (models version doesn't have from_request)
            user_context = UserExecutionContext(
                user_id="test_user_12345",
                thread_id="test_thread_12345", 
                run_id="test_run_12345",
                request_id="test_request_12345",  # Required field for models version
                websocket_connection_id="test_ws_12345"
            )
            
            # Create bridge and emitter
            bridge = create_agent_websocket_bridge(user_context)
            emitter = await bridge.create_user_emitter(user_context)
            
            # Test each critical event
            for event_name in REQUIRED_EVENTS:
                method_name = f'emit_{event_name}'
                if hasattr(emitter, method_name):
                    method = getattr(emitter, method_name)
                    test_data = {"test": f"{event_name}_data", "timestamp": time.time()}
                    
                    try:
                        await method(test_data)
                        logger.info(f"✅ Successfully called {method_name}")
                        self.event_counts[event_name] = 1
                    except Exception as e:
                        logger.error(f"❌ Failed to call {method_name}: {e}")
                else:
                    logger.error(f"❌ Method {method_name} not found on emitter")
            
            # Check results
            successful_events = sum(self.event_counts.values())
            logger.info(f"Event emission results: {successful_events}/{len(REQUIRED_EVENTS)} events succeeded")
            
            return successful_events == len(REQUIRED_EVENTS)
            
        except Exception as e:
            logger.error(f"❌ Event emission pipeline test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all critical tests."""
        logger.info("🚀 Starting CRITICAL WebSocket Event Tests")
        
        tests = [
            ("AgentWebSocketBridge Creation", self.test_agent_websocket_bridge_creation),
            ("WebSocket Dependencies", self.test_websocket_dependencies_available),
            ("WebSocket Manager Factory", self.test_websocket_manager_factory),
            ("Event Emission Pipeline", self.test_event_emission_pipeline),
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
        logger.info(f"\n📊 TEST SUMMARY: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED - WebSocket events should work!")
        else:
            logger.error("💥 SOME TESTS FAILED - WebSocket events will not work properly")
            for test_name, result in results.items():
                if not result:
                    logger.error(f"   ❌ Failed: {test_name}")
        
        return results

async def main():
    """Run the critical WebSocket event tests."""
    tester = WebSocketEventTester()
    results = await tester.run_all_tests()
    
    # Return appropriate exit code
    all_passed = all(results.values())
    if not all_passed:
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    asyncio.run(main())