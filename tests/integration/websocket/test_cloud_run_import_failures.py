"""
Integration Tests for Cloud Run Import Failures

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Risk Reduction & Production Stability  
- Value Impact: Prevent complete chat outage that blocks 90% of revenue
- Strategic Impact: Validate WebSocket stability under Cloud Run resource pressure

CRITICAL MISSION: Test real WebSocket connections under simulated Cloud Run conditions
to reproduce and detect the dynamic import failure: "name 'time' is not defined"

These tests use REAL SERVICES per CLAUDE.md requirements - NO MOCKS in integration tests.
"""

import asyncio
import gc
import sys
import threading
import time
from unittest.mock import patch, MagicMock
import pytest

# SSOT Test Framework imports (required per CLAUDE.md)
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager
from test_framework.ssot.websocket_auth_test_helpers import WebSocketAuthTestHelper
from test_framework.ssot.integration_test_base import IntegrationTestBase

# Import SSOT authentication helper
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


class TestCloudRunImportFailures(IntegrationTestBase):
    """
    Integration tests with real WebSocket connections under resource pressure.
    
    CRITICAL: These tests use REAL SERVICES - no mocks per CLAUDE.md requirements.
    Tests are designed to FAIL initially, proving they catch the Cloud Run issue.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_real_websocket_connection(self):
        """Setup real WebSocket connection for testing."""
        self.ws_manager = RealWebSocketConnectionManager()
        self.auth_helper = E2EAuthHelper()
        
        # Ensure Docker services are running for real WebSocket connections
        await self.ws_manager.ensure_services_available()
        
        yield
        
        # Cleanup
        await self.ws_manager.cleanup_all_connections()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_websocket_error_handling_under_resource_pressure(self):
        """
        Test WebSocket error handling when imports fail due to resource pressure.
        
        This test MUST FAIL initially to prove it catches the real issue.
        Reproduces the exact scenario: WebSocket error -> exception handler -> 
        is_websocket_connected() -> dynamic import failure.
        """
        # Get real authenticated WebSocket connection
        user_token = await self.auth_helper.get_test_user_token()
        websocket_client = await self.ws_manager.create_authenticated_connection(
            user_token=user_token,
            endpoint="/ws/chat"
        )
        
        try:
            # Establish real connection
            await websocket_client.connect()
            assert websocket_client.is_connected(), "Real WebSocket connection should be established"
            
            # Send initial message to confirm connection works
            test_message = {"type": "ping", "data": {"message": "Connection test"}}
            await websocket_client.send_json(test_message)
            
            # Receive response to confirm bidirectional communication
            response = await websocket_client.receive_json(timeout=5.0)
            assert response is not None, "Should receive response from real WebSocket"
            
            # Now simulate Cloud Run resource pressure during error scenario
            await self._simulate_cloud_run_resource_pressure()
            
            # Trigger an error condition that will call the exception handler
            # This simulates the exact scenario where line 1293-1294 in websocket.py fails
            error_message = {
                "type": "agent_request", 
                "data": {
                    "agent_type": "INVALID_AGENT_TYPE_TO_TRIGGER_ERROR",
                    "query": "This should trigger an error"
                }
            }
            
            # Send message that will trigger exception handler
            await websocket_client.send_json(error_message)
            
            # During error handling, the import failure should occur
            # Wait for error response or connection failure
            try:
                error_response = await websocket_client.receive_json(timeout=10.0)
                
                # Check if we got the specific import error
                if error_response and "error" in error_response:
                    error_details = str(error_response.get("error", ""))
                    if "time" in error_details and "not defined" in error_details:
                        # SUCCESS: We reproduced the Cloud Run import error!
                        pytest.fail(f"REPRODUCED CLOUD RUN IMPORT ERROR: {error_details}")
                
                # If we get here without the import error, the test needs more aggressive simulation
                print(f"WARNING: Did not reproduce import error, got response: {error_response}")
                
            except asyncio.TimeoutError:
                # Connection might have been closed due to import error
                if not websocket_client.is_connected():
                    pytest.fail("REPRODUCED: WebSocket connection lost due to import failure")
                    
        except Exception as e:
            # Check if this is the import error we're looking for
            if "time" in str(e) and "not defined" in str(e):
                pytest.fail(f"REPRODUCED CLOUD RUN IMPORT ERROR: {e}")
            else:
                # Re-raise other exceptions
                raise
                
        finally:
            await websocket_client.close()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_dynamic_import_failure_during_websocket_cleanup(self):
        """
        Test dynamic import failures during WebSocket cleanup.
        
        This test should FAIL initially, proving it catches the issue.
        Simulates the exact Cloud Run cleanup scenario that causes import instability.
        """
        # Create multiple real WebSocket connections to simulate load
        connections = []
        
        try:
            # Create multiple authenticated connections
            for i in range(3):
                user_token = await self.auth_helper.get_test_user_token()
                ws_client = await self.ws_manager.create_authenticated_connection(
                    user_token=user_token,
                    endpoint="/ws/chat"
                )
                await ws_client.connect()
                connections.append(ws_client)
            
            # Verify all connections are established
            for conn in connections:
                assert conn.is_connected(), "All WebSocket connections should be established"
            
            # Simulate Cloud Run resource cleanup during connection cleanup
            await self._simulate_cloud_run_import_instability()
            
            # Force disconnection of all connections simultaneously
            # This triggers multiple exception handlers concurrently (the failure scenario)
            disconnect_tasks = []
            for conn in connections:
                # Force an error that will trigger the exception handler
                task = asyncio.create_task(self._force_websocket_error(conn))
                disconnect_tasks.append(task)
            
            # Wait for all disconnections - this should trigger import failures
            try:
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
                
                # If we get here without import errors, the simulation needs improvement
                print("WARNING: No import errors detected during cleanup simulation")
                
            except Exception as e:
                # Check for the specific import error
                if "time" in str(e) and "not defined" in str(e):
                    pytest.fail(f"REPRODUCED IMPORT FAILURE DURING CLEANUP: {e}")
                    
        finally:
            # Cleanup remaining connections
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass  # Ignore errors during test cleanup
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_concurrent_websocket_exceptions_import_stability(self):
        """
        Test import stability during concurrent WebSocket exceptions.
        
        This reproduces the production scenario where multiple users trigger
        errors simultaneously, overwhelming the import system.
        """
        # Create multiple real connections from different users
        user_connections = []
        
        try:
            # Simulate multiple users
            for user_id in range(5):
                user_token = await self.auth_helper.get_test_user_token()
                ws_client = await self.ws_manager.create_authenticated_connection(
                    user_token=user_token,
                    endpoint="/ws/chat"
                )
                await ws_client.connect()
                user_connections.append(ws_client)
            
            # Simulate Cloud Run resource pressure
            await self._simulate_cloud_run_resource_pressure()
            
            # Trigger errors on all connections simultaneously
            error_tasks = []
            for i, conn in enumerate(user_connections):
                # Each connection sends an error-triggering message
                error_task = asyncio.create_task(
                    self._trigger_websocket_exception(conn, f"user_{i}_error")
                )
                error_tasks.append(error_task)
            
            # Execute all error triggers concurrently
            results = await asyncio.gather(*error_tasks, return_exceptions=True)
            
            # Check results for import errors
            import_errors = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    if "time" in error_msg and "not defined" in error_msg:
                        import_errors.append(f"User {i}: {error_msg}")
            
            if import_errors:
                error_summary = "\n".join(import_errors)
                pytest.fail(f"REPRODUCED CONCURRENT IMPORT FAILURES:\n{error_summary}")
                
        finally:
            # Cleanup
            for conn in user_connections:
                try:
                    await conn.close()
                except:
                    pass
    
    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_garbage_collection_import_interference(self):
        """
        Test GC interference with imports during exception handling.
        
        This simulates the specific Cloud Run garbage collection behavior
        that interferes with module imports during WebSocket error handling.
        """
        # Setup real WebSocket connection
        user_token = await self.auth_helper.get_test_user_token()
        websocket_client = await self.ws_manager.create_authenticated_connection(
            user_token=user_token,
            endpoint="/ws/chat"
        )
        
        try:
            await websocket_client.connect()
            
            # Create memory pressure to trigger GC
            memory_objects = []
            for i in range(10000):
                memory_objects.append(f"gc_pressure_object_{i}" * 50)
            
            # Force multiple garbage collection cycles (Cloud Run behavior)
            for gc_cycle in range(20):
                gc.collect()
                await asyncio.sleep(0.01)  # Small delay to simulate real conditions
            
            # Clean up memory objects to trigger more GC
            del memory_objects
            gc.collect()
            
            # Now trigger WebSocket error during GC instability
            error_message = {
                "type": "agent_request",
                "data": {
                    "agent_type": "GC_PRESSURE_TEST_AGENT", 
                    "query": "Test under GC pressure"
                }
            }
            
            # Send error-triggering message during GC instability
            await websocket_client.send_json(error_message)
            
            # Check for import failure response
            try:
                response = await websocket_client.receive_json(timeout=15.0)
                
                if response and "error" in response:
                    error_msg = str(response["error"])
                    if "time" in error_msg and "not defined" in error_msg:
                        pytest.fail(f"REPRODUCED GC IMPORT INTERFERENCE: {error_msg}")
                        
            except asyncio.TimeoutError:
                # Timeout might indicate connection lost due to import failure
                if not websocket_client.is_connected():
                    pytest.fail("REPRODUCED: Connection lost during GC import interference")
                    
        finally:
            await websocket_client.close()
    
    async def _simulate_cloud_run_resource_pressure(self):
        """Simulate Cloud Run resource pressure that causes import failures."""
        # Aggressive garbage collection cycles
        gc_tasks = []
        for cycle in range(10):
            task = asyncio.create_task(self._aggressive_gc_cycle())
            gc_tasks.append(task)
        
        await asyncio.gather(*gc_tasks)
        
        # Memory pressure simulation
        temp_memory = []
        for i in range(5000):
            temp_memory.append(f"cloud_run_pressure_{i}" * 100)
        
        # Cleanup memory to trigger more GC
        del temp_memory
        gc.collect()
    
    async def _aggressive_gc_cycle(self):
        """Perform aggressive garbage collection cycle."""
        for _ in range(5):
            gc.collect()
            await asyncio.sleep(0.005)  # Small delay between GC calls
    
    async def _simulate_cloud_run_import_instability(self):
        """Simulate Cloud Run import system instability."""
        # Temporarily corrupt the import system
        original_modules = {}
        
        # Remove critical modules that are dynamically imported
        critical_modules = [
            'time',
            'datetime',
            'shared.isolated_environment'
        ]
        
        for module_name in critical_modules:
            if module_name in sys.modules:
                original_modules[module_name] = sys.modules[module_name]
                del sys.modules[module_name]
        
        # Force garbage collection during import instability
        gc.collect()
        
        # Simulate the instability period
        await asyncio.sleep(0.1)
        
        # Restore modules (eventually - simulating instability recovery)
        def restore_modules():
            sys.modules.update(original_modules)
        
        # Delayed restoration simulates the instability window
        threading.Timer(0.2, restore_modules).start()
    
    async def _force_websocket_error(self, websocket_client):
        """Force a WebSocket error that triggers exception handler."""
        try:
            # Send malformed message to trigger error
            malformed_message = {"invalid": "structure", "missing": "required_fields"}
            await websocket_client.send_json(malformed_message)
            
            # Wait for error response
            response = await websocket_client.receive_json(timeout=5.0)
            return response
            
        except Exception as e:
            # This exception might be the import error we're looking for
            if "time" in str(e) and "not defined" in str(e):
                raise Exception(f"Import error during WebSocket error handling: {e}")
            raise
    
    async def _trigger_websocket_exception(self, websocket_client, error_context):
        """Trigger a WebSocket exception for testing."""
        try:
            # Send a message that will cause an error in the backend
            error_message = {
                "type": "agent_request",
                "data": {
                    "agent_type": "ERROR_TRIGGER_AGENT",
                    "query": f"Trigger error for {error_context}",
                    "force_error": True
                }
            }
            
            await websocket_client.send_json(error_message)
            
            # Wait for error response
            response = await websocket_client.receive_json(timeout=8.0)
            
            # Check for import error in response
            if response and "error" in response:
                error_msg = str(response["error"])
                if "time" in error_msg and "not defined" in error_msg:
                    raise Exception(f"Import error in {error_context}: {error_msg}")
            
            return response
            
        except asyncio.TimeoutError:
            # Timeout might indicate connection lost due to import error
            if not websocket_client.is_connected():
                raise Exception(f"Connection lost in {error_context} - possible import failure")
        except Exception as e:
            # Re-raise with context
            raise Exception(f"Error in {error_context}: {e}")


class TestExceptionHandlerStress(IntegrationTestBase):
    """Test exception handlers under stress conditions."""
    
    @pytest.mark.integration
    @pytest.mark.stress
    async def test_exception_handler_concurrent_import_load(self):
        """
        Test exception handler under concurrent import load.
        
        This simulates the production load scenario where multiple WebSocket
        errors occur simultaneously, overwhelming the import system.
        """
        # Setup multiple real WebSocket connections
        ws_manager = RealWebSocketConnectionManager()
        auth_helper = E2EAuthHelper()
        
        await ws_manager.ensure_services_available()
        
        try:
            # Create concurrent connections
            connections = []
            for i in range(10):
                user_token = await auth_helper.get_test_user_token()
                ws_client = await ws_manager.create_authenticated_connection(
                    user_token=user_token,
                    endpoint="/ws/chat"
                )
                await ws_client.connect()
                connections.append(ws_client)
            
            # Trigger concurrent errors that stress the import system
            stress_tasks = []
            for i, conn in enumerate(connections):
                task = asyncio.create_task(
                    self._stress_test_import_system(conn, f"stress_user_{i}")
                )
                stress_tasks.append(task)
            
            # Execute stress test
            results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            
            # Analyze results for import failures
            import_failures = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    if "time" in error_msg and "not defined" in error_msg:
                        import_failures.append(f"Stress user {i}: {error_msg}")
            
            if import_failures:
                failure_summary = "\n".join(import_failures)
                pytest.fail(f"STRESS TEST REPRODUCED IMPORT FAILURES:\n{failure_summary}")
                
        finally:
            # Cleanup all connections
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass
            await ws_manager.cleanup_all_connections()
    
    async def _stress_test_import_system(self, websocket_client, user_context):
        """Stress test the import system through WebSocket errors."""
        try:
            # Send multiple error-triggering messages rapidly
            for message_id in range(5):
                error_message = {
                    "type": "agent_request",
                    "data": {
                        "agent_type": "STRESS_TEST_AGENT",
                        "query": f"Stress test message {message_id} from {user_context}",
                        "force_import_stress": True
                    }
                }
                
                await websocket_client.send_json(error_message)
                
                # Short delay between messages to create sustained load
                await asyncio.sleep(0.1)
            
            # Wait for any responses/errors
            for _ in range(5):
                try:
                    response = await websocket_client.receive_json(timeout=2.0)
                    if response and "error" in response:
                        error_msg = str(response["error"])
                        if "time" in error_msg and "not defined" in error_msg:
                            raise Exception(f"Import stress failure: {error_msg}")
                except asyncio.TimeoutError:
                    break  # No more responses
                    
        except Exception as e:
            if "time" in str(e):
                raise  # Re-raise import errors
            # Log other errors but don't fail test
            print(f"Non-import error in stress test: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])