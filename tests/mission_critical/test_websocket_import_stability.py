"""
Mission Critical: WebSocket Import Stability Tests

Business Value Justification:
- Segment: Platform/Internal (Mission Critical Infrastructure)
- Business Goal: Prevent $120K+ MRR loss from chat outages
- Value Impact: Ensure 90% of business value (chat) never fails due to import errors
- Strategic Impact: Continuous monitoring of Cloud Run import stability

CRITICAL MISSION: Continuous monitoring test suite that detects Cloud Run dynamic
import failures before they reach production. These tests run in CI/CD pipeline.

Purpose: Prevent regression of the "name 'time' is not defined" issue that completely
blocks chat functionality in Cloud Run environments.
"""

import asyncio
import gc
import sys
import time
from typing import Dict, List, Any
import pytest

# SSOT Test Framework for mission-critical testing
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager
from test_framework.ssot.agent_event_validators import AgentEventValidator


class TestWebSocketImportStability(BaseTestCase):
    """
    Mission-critical tests for WebSocket import stability.
    
    These tests run in CI/CD pipeline to prevent regression of import failures.
    FAILURE OF ANY TEST = IMMEDIATE DEPLOYMENT BLOCK
    """
    
    @pytest.mark.mission_critical
    @pytest.mark.smoke
    async def test_basic_websocket_import_sanity(self):
        """
        Mission Critical: Basic WebSocket import sanity check.
        
        This test MUST PASS in all environments. Failure indicates critical
        import system regression.
        """
        # Test basic imports that failed in Cloud Run
        try:
            from netra_backend.app.websocket_core.utils import is_websocket_connected
            from netra_backend.app.websocket_core.utils import get_current_timestamp
            
            # Test basic functionality
            timestamp = get_current_timestamp()
            assert timestamp > 0, "get_current_timestamp should work"
            
            # Test with mock WebSocket
            from unittest.mock import MagicMock
            mock_ws = MagicMock()
            mock_ws.client_state = "CONNECTED"
            
            # This call previously failed with "time not defined"
            result = is_websocket_connected(mock_ws)
            assert result is not None, "is_websocket_connected should not fail with import error"
            
        except NameError as e:
            if "time" in str(e):
                pytest.fail(f"CRITICAL REGRESSION: Import stability broken: {e}")
            raise
    
    @pytest.mark.mission_critical
    @pytest.mark.integration
    async def test_websocket_exception_handler_import_stability(self):
        """
        Mission Critical: Exception handler import stability.
        
        Validates that exception handlers (line 1293-1294 in websocket.py) 
        don't fail with import errors under any conditions.
        """
        auth_helper = E2EAuthHelper()
        ws_manager = RealWebSocketConnectionManager()
        
        await ws_manager.ensure_services_available()
        
        try:
            # Create real authenticated connection
            user_token = await auth_helper.get_authenticated_user_token()
            websocket_client = await ws_manager.create_authenticated_connection(
                user_token=user_token,
                endpoint="/ws/chat"
            )
            
            await websocket_client.connect()
            
            # Force exception to trigger exception handler
            error_message = {
                "type": "agent_request",
                "data": {
                    "agent_type": "FORCE_EXCEPTION_AGENT",
                    "query": "This should trigger an exception to test handler"
                }
            }
            
            await websocket_client.send_json(error_message)
            
            # Exception handler should work without import errors
            try:
                response = await websocket_client.receive_json(timeout=10.0)
                
                # Check response for import errors
                if response and "error" in response:
                    error_msg = str(response["error"])
                    if "time" in error_msg and "not defined" in error_msg:
                        pytest.fail(f"CRITICAL: Exception handler import failure: {error_msg}")
                        
            except asyncio.TimeoutError:
                # Connection should remain stable even if no response
                if websocket_client.is_connected():
                    print("WARNING: No response received but connection stable")
                else:
                    pytest.fail("CRITICAL: Connection lost due to exception handler failure")
                    
        finally:
            await websocket_client.close()
            await ws_manager.cleanup_all_connections()
    
    @pytest.mark.mission_critical
    @pytest.mark.e2e
    async def test_chat_flow_import_regression_prevention(self):
        """
        Mission Critical: Prevent chat flow import regression.
        
        This test ensures chat functionality never regresses due to import issues.
        Failure = immediate production deployment block.
        """
        auth_helper = E2EAuthHelper()
        ws_manager = RealWebSocketConnectionManager()
        agent_validator = AgentEventValidator()
        
        await ws_manager.ensure_services_available()
        
        try:
            # Real authenticated chat session
            user_token = await auth_helper.get_authenticated_user_token()
            chat_client = await ws_manager.create_authenticated_connection(
                user_token=user_token,
                endpoint="/ws/chat"
            )
            
            await chat_client.connect()
            
            # Test critical chat flow that previously failed
            chat_message = {
                "type": "agent_request",
                "data": {
                    "agent_type": "data_explorer",
                    "query": "Test chat flow for import stability"
                }
            }
            
            await chat_client.send_json(chat_message)
            
            # MUST receive all required WebSocket events without import errors
            required_events = [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ]
            
            events = await agent_validator.validate_agent_event_sequence(
                chat_client,
                expected_events=required_events,
                timeout=30.0
            )
            
            # Validate no import errors in any event
            for event in events:
                if "error" in event:
                    error_msg = str(event["error"])
                    if "time" in error_msg and "not defined" in error_msg:
                        pytest.fail(f"CRITICAL REGRESSION: Chat import failure: {error_msg}")
            
            # Ensure we got complete event sequence
            assert len(events) >= len(required_events), \
                "Chat flow incomplete - possible import regression"
                
        finally:
            await chat_client.close()
            await ws_manager.cleanup_all_connections()
    
    @pytest.mark.mission_critical
    @pytest.mark.performance
    async def test_import_system_performance_baseline(self):
        """
        Mission Critical: Import system performance baseline.
        
        Monitors import performance to detect degradation that could lead
        to Cloud Run timeout issues.
        """
        import_performance_tests = [
            {
                "module": "netra_backend.app.websocket_core.utils",
                "function": "is_websocket_connected",
                "max_time_ms": 100
            },
            {
                "module": "netra_backend.app.websocket_core.utils", 
                "function": "get_current_timestamp",
                "max_time_ms": 50
            },
            {
                "module": "shared.isolated_environment",
                "function": "get_env",
                "max_time_ms": 75
            }
        ]
        
        for test_case in import_performance_tests:
            start_time = time.time()
            
            try:
                # Import and execute function
                module = __import__(test_case["module"], fromlist=[test_case["function"]])
                func = getattr(module, test_case["function"])
                
                if test_case["function"] == "is_websocket_connected":
                    from unittest.mock import MagicMock
                    mock_ws = MagicMock()
                    result = func(mock_ws)
                elif test_case["function"] == "get_env":
                    result = func()
                else:
                    result = func()
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Performance regression check
                if execution_time_ms > test_case["max_time_ms"]:
                    pytest.fail(
                        f"PERFORMANCE REGRESSION: {test_case['module']}.{test_case['function']} "
                        f"took {execution_time_ms:.2f}ms (max: {test_case['max_time_ms']}ms)"
                    )
                
                print(f"PASS: {test_case['function']} executed in {execution_time_ms:.2f}ms")
                
            except Exception as e:
                if "time" in str(e) and "not defined" in str(e):
                    pytest.fail(f"CRITICAL: Import regression in {test_case['module']}: {e}")
                raise
    
    @pytest.mark.mission_critical
    @pytest.mark.concurrent
    async def test_concurrent_websocket_import_stability(self):
        """
        Mission Critical: Concurrent WebSocket import stability.
        
        Tests import stability under concurrent load (production scenario).
        Prevents cascading failures across multiple users.
        """
        auth_helper = E2EAuthHelper()
        ws_manager = RealWebSocketConnectionManager()
        
        await ws_manager.ensure_services_available()
        
        # Test with multiple concurrent connections
        connections = []
        
        try:
            # Create 5 concurrent authenticated connections
            for i in range(5):
                user_token = await auth_helper.get_authenticated_user_token()
                ws_client = await ws_manager.create_authenticated_connection(
                    user_token=user_token,
                    endpoint="/ws/chat"
                )
                await ws_client.connect()
                connections.append(ws_client)
            
            # Send concurrent messages that stress import system
            tasks = []
            for i, conn in enumerate(connections):
                task = asyncio.create_task(
                    self._stress_test_connection_imports(conn, f"user_{i}")
                )
                tasks.append(task)
            
            # Execute concurrent stress test
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for import failures
            import_failures = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    if "time" in error_msg and "not defined" in error_msg:
                        import_failures.append(f"Connection {i}: {error_msg}")
            
            if import_failures:
                failure_summary = "\n".join(import_failures)
                pytest.fail(f"CRITICAL: Concurrent import failures detected:\n{failure_summary}")
                
        finally:
            # Cleanup all connections
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass
            await ws_manager.cleanup_all_connections()
    
    async def _stress_test_connection_imports(self, websocket_client, connection_id):
        """Stress test imports for a single connection."""
        try:
            # Send message that exercises import system
            stress_message = {
                "type": "agent_request",
                "data": {
                    "agent_type": "data_explorer",
                    "query": f"Import stress test from {connection_id}"
                }
            }
            
            await websocket_client.send_json(stress_message)
            
            # Wait for response
            response = await websocket_client.receive_json(timeout=15.0)
            
            # Check for import errors in response
            if response and "error" in response:
                error_msg = str(response["error"])
                if "time" in error_msg and "not defined" in error_msg:
                    raise Exception(f"Import failure in {connection_id}: {error_msg}")
            
            return {"connection_id": connection_id, "success": True}
            
        except Exception as e:
            if "time" in str(e):
                raise  # Re-raise import errors
            # Other errors are acceptable for stress testing
            return {"connection_id": connection_id, "error": str(e)}


class TestCloudRunEnvironmentCompatibility(BaseTestCase):
    """Test Cloud Run environment compatibility for import stability."""
    
    @pytest.mark.mission_critical
    @pytest.mark.environment
    def test_environment_detection_import_stability(self):
        """
        Test environment detection import stability.
        
        The is_websocket_connected function uses environment detection
        that previously failed with import errors.
        """
        # Test environment detection under various scenarios
        test_environments = ["development", "staging", "production"]
        
        for env in test_environments:
            with pytest.MonkeyPatch().context() as m:
                # Mock environment
                m.setenv("ENVIRONMENT", env)
                
                try:
                    # Test the import chain that previously failed
                    from shared.isolated_environment import get_env
                    env_result = get_env()
                    
                    assert env_result is not None, f"get_env failed for {env}"
                    
                    # Test WebSocket utils with this environment
                    from netra_backend.app.websocket_core.utils import is_websocket_connected
                    from unittest.mock import MagicMock
                    
                    mock_ws = MagicMock()
                    mock_ws.client_state = "CONNECTED"
                    
                    # This previously failed with "time not defined" in staging/production
                    result = is_websocket_connected(mock_ws)
                    assert result is not None, f"is_websocket_connected failed for {env}"
                    
                except NameError as e:
                    if "time" in str(e):
                        pytest.fail(f"CRITICAL: Import failure in {env} environment: {e}")
                    raise
    
    @pytest.mark.mission_critical
    @pytest.mark.smoke
    def test_critical_module_availability(self):
        """
        Test availability of critical modules that caused failures.
        
        Validates that all modules in the import chain are properly available.
        """
        critical_modules = [
            "time",
            "datetime", 
            "asyncio",
            "shared.isolated_environment",
            "netra_backend.app.websocket_core.utils",
            "netra_backend.app.websocket_core.connection_state_machine"
        ]
        
        for module_name in critical_modules:
            try:
                module = __import__(module_name, fromlist=[""])
                assert module is not None, f"Module {module_name} not available"
                
                # Test basic functionality if possible
                if module_name == "time":
                    assert hasattr(module, "time"), "time.time() not available"
                elif module_name == "datetime":
                    assert hasattr(module, "datetime"), "datetime.datetime not available"
                
                print(f"PASS: Module {module_name} available and functional")
                
            except ImportError as e:
                pytest.fail(f"CRITICAL: Module {module_name} import failed: {e}")
            except Exception as e:
                if "time" in str(e) and "not defined" in str(e):
                    pytest.fail(f"CRITICAL: Module {module_name} import chain broken: {e}")
                raise


if __name__ == "__main__":
    # Run mission-critical tests with strict failure requirements
    pytest.main([
        __file__, 
        "-v", 
        "--tb=long",
        "--strict-markers",
        "--maxfail=1"  # Stop on first failure for mission-critical tests
    ])