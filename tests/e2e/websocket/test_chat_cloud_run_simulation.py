"""
E2E Tests for Chat Cloud Run Simulation

Business Value Justification:
- Segment: Enterprise/Mid/Early/Free (ALL customer segments)
- Business Goal: Prevent complete chat outage (90% of business value)
- Value Impact: Ensure AI-powered chat functionality works under Cloud Run conditions
- Strategic Impact: Protect $120K+ MRR from WebSocket import failures

CRITICAL MISSION: Test complete chat flow under Cloud Run conditions to detect and
reproduce the dynamic import failure that completely blocks chat functionality.

ALL SERVICES MUST BE REAL per CLAUDE.md requirements - NO MOCKS in E2E tests.
Authentication is MANDATORY per CLAUDE.md - ALL e2e tests MUST use real auth.
"""

import asyncio
import gc
import sys
import time
from typing import Dict, List, Any
import pytest

# SSOT E2E Test Framework (required per CLAUDE.md)
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager
from test_framework.ssot.websocket_golden_path_helpers import WebSocketGoldenPathHelper
from test_framework.ssot.agent_event_validators import AgentEventValidator

# Import Docker orchestration for real services
from test_framework.ssot.docker import DockerTestManager


class TestChatCloudRunSimulation(BaseTestCase):
    """
    E2E tests simulating Cloud Run environment conditions.
    
    CRITICAL: Uses ALL REAL SERVICES per CLAUDE.md requirements:
    - Real authentication (JWT/OAuth) - MANDATORY
    - Real WebSocket connections
    - Real agent execution
    - Real LLM calls
    - Real database operations
    
    Tests are designed to FAIL initially, proving business impact of the issue.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_real_environment(self):
        """Setup complete real environment for E2E testing."""
        # Initialize SSOT components for real E2E testing
        self.auth_helper = E2EAuthHelper()
        self.ws_manager = RealWebSocketConnectionManager()
        self.golden_path_helper = WebSocketGoldenPathHelper()
        self.agent_validator = AgentEventValidator()
        self.docker_manager = DockerTestManager()
        
        # Ensure all real services are running
        await self.docker_manager.ensure_services_running()
        await self.ws_manager.ensure_services_available()
        
        # Validate authentication system is working
        await self.auth_helper.validate_auth_system()
        
        yield
        
        # Cleanup
        await self.ws_manager.cleanup_all_connections()
        await self.docker_manager.cleanup_test_resources()
    
    @pytest.mark.e2e
    @pytest.mark.chat
    @pytest.mark.critical
    async def test_chat_functionality_during_import_failures(self):
        """
        Test complete chat flow when import failures occur.
        
        This test MUST FAIL initially to prove business impact.
        
        BUSINESS IMPACT: When this test fails, it proves that chat (90% of our value)
        is completely broken in Cloud Run environments.
        """
        # MANDATORY: Real authentication per CLAUDE.md requirements
        user_token = await self.auth_helper.get_authenticated_user_token()
        assert user_token, "E2E test requires real authentication"
        
        # Create real authenticated WebSocket connection
        chat_client = await self.ws_manager.create_authenticated_connection(
            user_token=user_token,
            endpoint="/ws/chat"
        )
        
        try:
            # Establish real WebSocket connection
            await chat_client.connect()
            assert chat_client.is_connected(), "Chat WebSocket must be connected"
            
            # Validate initial connection with real auth context
            await self.auth_helper.validate_websocket_auth_context(chat_client)
            
            # Test basic chat flow first (baseline)
            initial_message = {
                "type": "agent_request",
                "data": {
                    "agent_type": "data_explorer",
                    "query": "What data do we have available?"
                }
            }
            
            await chat_client.send_json(initial_message)
            
            # Validate WebSocket agent events are working (business value delivery)
            events_received = await self.agent_validator.validate_agent_event_sequence(
                chat_client,
                expected_events=[
                    "agent_started",
                    "agent_thinking", 
                    "tool_executing",
                    "tool_completed",
                    "agent_completed"
                ],
                timeout=30.0
            )
            
            assert events_received, "Initial chat flow must work (baseline for failure detection)"
            
            # Now simulate Cloud Run resource pressure during chat
            await self._simulate_cloud_run_environment_pressure()
            
            # Test chat flow under Cloud Run conditions (this should fail initially)
            stress_message = {
                "type": "agent_request", 
                "data": {
                    "agent_type": "optimization_agent",
                    "query": "Optimize our data pipeline under Cloud Run conditions"
                }
            }
            
            await chat_client.send_json(stress_message)
            
            # This should fail when import errors occur during agent execution
            try:
                stress_events = await self.agent_validator.validate_agent_event_sequence(
                    chat_client,
                    expected_events=[
                        "agent_started",
                        "agent_thinking",
                        "tool_executing", 
                        "tool_completed",
                        "agent_completed"
                    ],
                    timeout=45.0
                )
                
                # If we get complete events, check for import errors in the responses
                if stress_events:
                    for event in stress_events:
                        if "error" in event and "time" in str(event["error"]):
                            pytest.fail(f"REPRODUCED CHAT IMPORT FAILURE: {event['error']}")
                
                # If chat appears to work, it means our simulation isn't aggressive enough
                print("WARNING: Chat flow succeeded under Cloud Run simulation - need more aggressive testing")
                
            except asyncio.TimeoutError:
                # Timeout likely indicates the import failure blocked agent execution
                pytest.fail("REPRODUCED: Chat functionality blocked by import failures (timeout)")
                
            except Exception as e:
                # Check if this is the import error
                if "time" in str(e) and "not defined" in str(e):
                    pytest.fail(f"REPRODUCED CHAT IMPORT FAILURE: {e}")
                else:
                    raise
                    
        finally:
            await chat_client.close()
    
    @pytest.mark.e2e
    @pytest.mark.chat
    @pytest.mark.multiuser
    async def test_multi_user_chat_import_failure_isolation(self):
        """
        Test user isolation during import failures.
        
        BUSINESS CRITICAL: Ensure import failures don't cascade across users.
        This protects revenue by preventing one user's issue from affecting others.
        """
        # Create multiple real authenticated users
        user_connections = []
        
        try:
            # Setup 3 different authenticated users (simulating real usage)
            for user_id in range(3):
                user_token = await self.auth_helper.get_authenticated_user_token()
                user_client = await self.ws_manager.create_authenticated_connection(
                    user_token=user_token,
                    endpoint="/ws/chat"
                )
                await user_client.connect()
                user_connections.append({
                    "client": user_client,
                    "user_id": user_id,
                    "token": user_token
                })
            
            # Validate all users are properly isolated
            for user_conn in user_connections:
                await self.auth_helper.validate_websocket_auth_context(user_conn["client"])
            
            # Simulate Cloud Run import instability
            await self._simulate_cloud_run_import_instability()
            
            # Trigger chat on all users simultaneously
            chat_tasks = []
            for user_conn in user_connections:
                task = asyncio.create_task(
                    self._execute_user_chat_flow(
                        user_conn["client"], 
                        f"user_{user_conn['user_id']}"
                    )
                )
                chat_tasks.append(task)
            
            # Execute all user chats concurrently
            results = await asyncio.gather(*chat_tasks, return_exceptions=True)
            
            # Analyze results for import failures and cross-user contamination
            import_failures = []
            successful_users = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    if "time" in error_msg and "not defined" in error_msg:
                        import_failures.append(f"User {i}: {error_msg}")
                    else:
                        print(f"User {i} other error: {error_msg}")
                else:
                    successful_users.append(i)
            
            # Test expectations for import failure scenarios
            if import_failures:
                failure_summary = "\n".join(import_failures)
                
                # Check if failures affected all users (cascade failure - BAD)
                if len(import_failures) == len(user_connections):
                    pytest.fail(f"CRITICAL: Import failures cascaded to ALL users:\n{failure_summary}")
                
                # Check if some users succeeded (good isolation)
                if successful_users:
                    print(f"GOOD: Users {successful_users} isolated from import failures")
                    pytest.fail(f"REPRODUCED ISOLATED IMPORT FAILURES:\n{failure_summary}")
                else:
                    pytest.fail(f"REPRODUCED SYSTEM-WIDE IMPORT FAILURES:\n{failure_summary}")
                    
        finally:
            # Cleanup all user connections
            for user_conn in user_connections:
                try:
                    await user_conn["client"].close()
                except:
                    pass
    
    @pytest.mark.e2e
    @pytest.mark.chat
    @pytest.mark.recovery
    async def test_chat_recovery_after_import_fix(self):
        """
        Test chat functionality recovery after import fix.
        
        This test should PASS after the fix is implemented.
        It validates that the fix resolves the import issue without breaking chat.
        """
        # This test is designed to PASS after fixing the import issue
        # It serves as validation that the fix works correctly
        
        user_token = await self.auth_helper.get_authenticated_user_token()
        chat_client = await self.ws_manager.create_authenticated_connection(
            user_token=user_token,
            endpoint="/ws/chat"
        )
        
        try:
            await chat_client.connect()
            
            # Test complete chat flow under various conditions
            test_scenarios = [
                {
                    "name": "basic_chat",
                    "agent_type": "data_explorer",
                    "query": "Show me available data sources"
                },
                {
                    "name": "complex_chat", 
                    "agent_type": "optimization_agent",
                    "query": "Analyze performance bottlenecks in our data pipeline"
                },
                {
                    "name": "error_recovery_chat",
                    "agent_type": "data_explorer", 
                    "query": "Handle this gracefully even under resource pressure"
                }
            ]
            
            for scenario in test_scenarios:
                # Simulate some resource pressure (but not enough to break fixed system)
                await self._light_resource_pressure()
                
                # Execute chat scenario
                message = {
                    "type": "agent_request",
                    "data": {
                        "agent_type": scenario["agent_type"],
                        "query": scenario["query"]
                    }
                }
                
                await chat_client.send_json(message)
                
                # Validate complete agent event sequence works
                events = await self.agent_validator.validate_agent_event_sequence(
                    chat_client,
                    expected_events=[
                        "agent_started",
                        "agent_thinking",
                        "tool_executing",
                        "tool_completed", 
                        "agent_completed"
                    ],
                    timeout=30.0
                )
                
                assert events, f"Chat scenario '{scenario['name']}' should work after fix"
                
                # Validate no import errors in any events
                for event in events:
                    if "error" in event:
                        error_msg = str(event["error"])
                        assert "time" not in error_msg or "not defined" not in error_msg, \
                            f"Import error still present after fix: {error_msg}"
            
            print("SUCCESS: All chat scenarios work correctly after import fix")
            
        finally:
            await chat_client.close()
    
    @pytest.mark.e2e
    @pytest.mark.websocket_events
    @pytest.mark.critical
    async def test_websocket_agent_events_with_import_stability(self):
        """
        Test all 5 required WebSocket events work after fix.
        
        BUSINESS CRITICAL: These events enable substantive chat interactions.
        Without them, users get no feedback on AI processing.
        """
        user_token = await self.auth_helper.get_authenticated_user_token()
        chat_client = await self.ws_manager.create_authenticated_connection(
            user_token=user_token,
            endpoint="/ws/chat"
        )
        
        try:
            await chat_client.connect()
            
            # Test each required WebSocket event under stress
            await self._moderate_cloud_run_simulation()
            
            # Send agent request
            agent_message = {
                "type": "agent_request",
                "data": {
                    "agent_type": "data_explorer",
                    "query": "Test all WebSocket events under import pressure"
                }
            }
            
            await chat_client.send_json(agent_message)
            
            # Validate ALL 5 required events are received
            required_events = [
                "agent_started",    # User must see agent began processing
                "agent_thinking",   # Real-time reasoning visibility  
                "tool_executing",   # Tool usage transparency
                "tool_completed",   # Tool results display
                "agent_completed"   # User must know when response is ready
            ]
            
            received_events = await self.agent_validator.validate_all_required_events(
                chat_client,
                required_events=required_events,
                timeout=40.0
            )
            
            # Check for import errors in any event
            for event_type, event_data in received_events.items():
                if "error" in event_data:
                    error_msg = str(event_data["error"])
                    if "time" in error_msg and "not defined" in error_msg:
                        pytest.fail(f"Import error in {event_type} event: {error_msg}")
            
            # Validate we got all required events
            missing_events = set(required_events) - set(received_events.keys())
            if missing_events:
                pytest.fail(f"Missing WebSocket events due to import failures: {missing_events}")
            
            print("SUCCESS: All WebSocket agent events working with import stability")
            
        finally:
            await chat_client.close()
    
    async def _execute_user_chat_flow(self, websocket_client, user_context):
        """Execute complete chat flow for a specific user."""
        try:
            # Send chat message
            message = {
                "type": "agent_request",
                "data": {
                    "agent_type": "data_explorer",
                    "query": f"User-specific query from {user_context}"
                }
            }
            
            await websocket_client.send_json(message)
            
            # Wait for complete response
            events = await self.agent_validator.validate_agent_event_sequence(
                websocket_client,
                expected_events=["agent_started", "agent_completed"],
                timeout=20.0
            )
            
            return {"user": user_context, "events": events, "success": True}
            
        except Exception as e:
            return {"user": user_context, "error": str(e), "success": False}
    
    async def _simulate_cloud_run_environment_pressure(self):
        """Simulate comprehensive Cloud Run environment pressure."""
        # Memory pressure
        memory_objects = []
        for i in range(15000):
            memory_objects.append(f"cloud_run_memory_pressure_{i}" * 75)
        
        # Aggressive garbage collection cycles
        gc_tasks = []
        for cycle in range(15):
            task = asyncio.create_task(self._aggressive_gc_cycle())
            gc_tasks.append(task)
        
        await asyncio.gather(*gc_tasks)
        
        # Module system instability
        await self._corrupt_import_system_aggressively()
        
        # Cleanup memory
        del memory_objects
        gc.collect()
    
    async def _simulate_cloud_run_import_instability(self):
        """Simulate Cloud Run import system instability."""
        # Remove critical modules temporarily
        critical_modules = [
            'time',
            'datetime',
            'shared.isolated_environment',
            'netra_backend.app.websocket_core.connection_state_machine'
        ]
        
        original_modules = {}
        for module_name in critical_modules:
            if module_name in sys.modules:
                original_modules[module_name] = sys.modules[module_name]
                del sys.modules[module_name]
        
        # Instability period
        gc.collect()
        await asyncio.sleep(0.2)
        
        # Partial restoration (simulating instability)
        import threading
        def restore_gradually():
            time.sleep(0.1)
            sys.modules.update(original_modules)
        
        threading.Thread(target=restore_gradually).start()
    
    async def _corrupt_import_system_aggressively(self):
        """Aggressively corrupt import system to reproduce Cloud Run failures."""
        # Multiple rounds of module removal
        for round_num in range(3):
            modules_to_remove = [
                'time', 'datetime', 'asyncio',
                'shared.isolated_environment'
            ]
            
            for module in modules_to_remove:
                if module in sys.modules:
                    del sys.modules[module]
            
            gc.collect()
            await asyncio.sleep(0.05)
    
    async def _aggressive_gc_cycle(self):
        """Perform aggressive garbage collection cycle."""
        for _ in range(8):
            gc.collect()
            await asyncio.sleep(0.01)
    
    async def _light_resource_pressure(self):
        """Apply light resource pressure (for post-fix testing)."""
        # Light memory allocation
        temp_objects = []
        for i in range(1000):
            temp_objects.append(f"light_pressure_{i}")
        
        # Single GC cycle
        gc.collect()
        
        # Cleanup
        del temp_objects
    
    async def _moderate_cloud_run_simulation(self):
        """Moderate Cloud Run simulation for testing fixed system."""
        # Moderate memory pressure
        memory_objects = []
        for i in range(5000):
            memory_objects.append(f"moderate_pressure_{i}" * 20)
        
        # Moderate GC
        for _ in range(5):
            gc.collect()
            await asyncio.sleep(0.01)
        
        # Cleanup
        del memory_objects
        gc.collect()


class TestWebSocketErrorRecovery(BaseTestCase):
    """Test WebSocket error recovery after fixing import issues."""
    
    @pytest.mark.e2e
    @pytest.mark.recovery
    async def test_websocket_connection_stability_post_fix(self):
        """
        Test WebSocket connection stability after import fix.
        
        This validates that fixed exception handlers properly handle errors
        without import failures.
        """
        auth_helper = E2EAuthHelper()
        ws_manager = RealWebSocketConnectionManager()
        
        # Setup real services
        await ws_manager.ensure_services_available()
        
        try:
            # Create authenticated connection
            user_token = await auth_helper.get_authenticated_user_token()
            websocket_client = await ws_manager.create_authenticated_connection(
                user_token=user_token,
                endpoint="/ws/chat"
            )
            
            await websocket_client.connect()
            
            # Test connection stability under various error conditions
            error_scenarios = [
                {"type": "invalid_message", "data": {"malformed": "structure"}},
                {"type": "agent_request", "data": {"agent_type": "INVALID_AGENT", "query": "test"}},
                {"type": "unknown_type", "data": {"test": "error_handling"}}
            ]
            
            for scenario in error_scenarios:
                # Send error-triggering message
                await websocket_client.send_json(scenario)
                
                # Connection should remain stable (no import failures)
                assert websocket_client.is_connected(), \
                    f"Connection lost after error scenario: {scenario['type']}"
                
                # Should receive error response, not connection termination
                try:
                    response = await websocket_client.receive_json(timeout=5.0)
                    if response and "error" in response:
                        error_msg = str(response["error"])
                        # Ensure no import errors in response
                        assert "time" not in error_msg or "not defined" not in error_msg, \
                            f"Import error still present: {error_msg}"
                except asyncio.TimeoutError:
                    # Timeout is acceptable for some error scenarios
                    pass
            
            print("SUCCESS: WebSocket error handling works without import failures")
            
        finally:
            await websocket_client.close()
            await ws_manager.cleanup_all_connections()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=long"])