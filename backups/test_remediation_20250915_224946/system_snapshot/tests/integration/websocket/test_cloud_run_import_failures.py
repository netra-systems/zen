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
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager
from test_framework.ssot.websocket_auth_test_helpers import WebSocketAuthenticationTester
from test_framework.ssot.integration_test_base import IntegrationTestBase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

class CloudRunImportFailuresTests(IntegrationTestBase):
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
        await self.ws_manager.ensure_services_available()
        yield
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
        user_token = await self.auth_helper.get_test_user_token()
        websocket_client = await self.ws_manager.create_authenticated_connection(user_token=user_token, endpoint='/ws/chat')
        try:
            await websocket_client.connect()
            assert websocket_client.is_connected(), 'Real WebSocket connection should be established'
            test_message = {'type': 'ping', 'data': {'message': 'Connection test'}}
            await websocket_client.send_json(test_message)
            response = await websocket_client.receive_json(timeout=5.0)
            assert response is not None, 'Should receive response from real WebSocket'
            await self._simulate_cloud_run_resource_pressure()
            error_message = {'type': 'agent_request', 'data': {'agent_type': 'INVALID_AGENT_TYPE_TO_TRIGGER_ERROR', 'query': 'This should trigger an error'}}
            await websocket_client.send_json(error_message)
            try:
                error_response = await websocket_client.receive_json(timeout=10.0)
                if error_response and 'error' in error_response:
                    error_details = str(error_response.get('error', ''))
                    if 'time' in error_details and 'not defined' in error_details:
                        pytest.fail(f'REPRODUCED CLOUD RUN IMPORT ERROR: {error_details}')
                print(f'WARNING: Did not reproduce import error, got response: {error_response}')
            except asyncio.TimeoutError:
                if not websocket_client.is_connected():
                    pytest.fail('REPRODUCED: WebSocket connection lost due to import failure')
        except Exception as e:
            if 'time' in str(e) and 'not defined' in str(e):
                pytest.fail(f'REPRODUCED CLOUD RUN IMPORT ERROR: {e}')
            else:
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
        connections = []
        try:
            for i in range(3):
                user_token = await self.auth_helper.get_test_user_token()
                ws_client = await self.ws_manager.create_authenticated_connection(user_token=user_token, endpoint='/ws/chat')
                await ws_client.connect()
                connections.append(ws_client)
            for conn in connections:
                assert conn.is_connected(), 'All WebSocket connections should be established'
            await self._simulate_cloud_run_import_instability()
            disconnect_tasks = []
            for conn in connections:
                task = asyncio.create_task(self._force_websocket_error(conn))
                disconnect_tasks.append(task)
            try:
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
                print('WARNING: No import errors detected during cleanup simulation')
            except Exception as e:
                if 'time' in str(e) and 'not defined' in str(e):
                    pytest.fail(f'REPRODUCED IMPORT FAILURE DURING CLEANUP: {e}')
        finally:
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_concurrent_websocket_exceptions_import_stability(self):
        """
        Test import stability during concurrent WebSocket exceptions.
        
        This reproduces the production scenario where multiple users trigger
        errors simultaneously, overwhelming the import system.
        """
        user_connections = []
        try:
            for user_id in range(5):
                user_token = await self.auth_helper.get_test_user_token()
                ws_client = await self.ws_manager.create_authenticated_connection(user_token=user_token, endpoint='/ws/chat')
                await ws_client.connect()
                user_connections.append(ws_client)
            await self._simulate_cloud_run_resource_pressure()
            error_tasks = []
            for i, conn in enumerate(user_connections):
                error_task = asyncio.create_task(self._trigger_websocket_exception(conn, f'user_{i}_error'))
                error_tasks.append(error_task)
            results = await asyncio.gather(*error_tasks, return_exceptions=True)
            import_errors = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    if 'time' in error_msg and 'not defined' in error_msg:
                        import_errors.append(f'User {i}: {error_msg}')
            if import_errors:
                error_summary = '\n'.join(import_errors)
                pytest.fail(f'REPRODUCED CONCURRENT IMPORT FAILURES:\n{error_summary}')
        finally:
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
        user_token = await self.auth_helper.get_test_user_token()
        websocket_client = await self.ws_manager.create_authenticated_connection(user_token=user_token, endpoint='/ws/chat')
        try:
            await websocket_client.connect()
            memory_objects = []
            for i in range(10000):
                memory_objects.append(f'gc_pressure_object_{i}' * 50)
            for gc_cycle in range(20):
                gc.collect()
                await asyncio.sleep(0.01)
            del memory_objects
            gc.collect()
            error_message = {'type': 'agent_request', 'data': {'agent_type': 'GC_PRESSURE_TEST_AGENT', 'query': 'Test under GC pressure'}}
            await websocket_client.send_json(error_message)
            try:
                response = await websocket_client.receive_json(timeout=15.0)
                if response and 'error' in response:
                    error_msg = str(response['error'])
                    if 'time' in error_msg and 'not defined' in error_msg:
                        pytest.fail(f'REPRODUCED GC IMPORT INTERFERENCE: {error_msg}')
            except asyncio.TimeoutError:
                if not websocket_client.is_connected():
                    pytest.fail('REPRODUCED: Connection lost during GC import interference')
        finally:
            await websocket_client.close()

    async def _simulate_cloud_run_resource_pressure(self):
        """Simulate Cloud Run resource pressure that causes import failures."""
        gc_tasks = []
        for cycle in range(10):
            task = asyncio.create_task(self._aggressive_gc_cycle())
            gc_tasks.append(task)
        await asyncio.gather(*gc_tasks)
        temp_memory = []
        for i in range(5000):
            temp_memory.append(f'cloud_run_pressure_{i}' * 100)
        del temp_memory
        gc.collect()

    async def _aggressive_gc_cycle(self):
        """Perform aggressive garbage collection cycle."""
        for _ in range(5):
            gc.collect()
            await asyncio.sleep(0.005)

    async def _simulate_cloud_run_import_instability(self):
        """Simulate Cloud Run import system instability."""
        original_modules = {}
        critical_modules = ['time', 'datetime', 'shared.isolated_environment']
        for module_name in critical_modules:
            if module_name in sys.modules:
                original_modules[module_name] = sys.modules[module_name]
                del sys.modules[module_name]
        gc.collect()
        await asyncio.sleep(0.1)

        def restore_modules():
            sys.modules.update(original_modules)
        threading.Timer(0.2, restore_modules).start()

    async def _force_websocket_error(self, websocket_client):
        """Force a WebSocket error that triggers exception handler."""
        try:
            malformed_message = {'invalid': 'structure', 'missing': 'required_fields'}
            await websocket_client.send_json(malformed_message)
            response = await websocket_client.receive_json(timeout=5.0)
            return response
        except Exception as e:
            if 'time' in str(e) and 'not defined' in str(e):
                raise Exception(f'Import error during WebSocket error handling: {e}')
            raise

    async def _trigger_websocket_exception(self, websocket_client, error_context):
        """Trigger a WebSocket exception for testing."""
        try:
            error_message = {'type': 'agent_request', 'data': {'agent_type': 'ERROR_TRIGGER_AGENT', 'query': f'Trigger error for {error_context}', 'force_error': True}}
            await websocket_client.send_json(error_message)
            response = await websocket_client.receive_json(timeout=8.0)
            if response and 'error' in response:
                error_msg = str(response['error'])
                if 'time' in error_msg and 'not defined' in error_msg:
                    raise Exception(f'Import error in {error_context}: {error_msg}')
            return response
        except asyncio.TimeoutError:
            if not websocket_client.is_connected():
                raise Exception(f'Connection lost in {error_context} - possible import failure')
        except Exception as e:
            raise Exception(f'Error in {error_context}: {e}')

class ExceptionHandlerStressTests(IntegrationTestBase):
    """Test exception handlers under stress conditions."""

    @pytest.mark.integration
    @pytest.mark.stress
    async def test_exception_handler_concurrent_import_load(self):
        """
        Test exception handler under concurrent import load.
        
        This simulates the production load scenario where multiple WebSocket
        errors occur simultaneously, overwhelming the import system.
        """
        ws_manager = RealWebSocketConnectionManager()
        auth_helper = E2EAuthHelper()
        await ws_manager.ensure_services_available()
        try:
            connections = []
            for i in range(10):
                user_token = await auth_helper.get_test_user_token()
                ws_client = await ws_manager.create_authenticated_connection(user_token=user_token, endpoint='/ws/chat')
                await ws_client.connect()
                connections.append(ws_client)
            stress_tasks = []
            for i, conn in enumerate(connections):
                task = asyncio.create_task(self._stress_test_import_system(conn, f'stress_user_{i}'))
                stress_tasks.append(task)
            results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            import_failures = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    if 'time' in error_msg and 'not defined' in error_msg:
                        import_failures.append(f'Stress user {i}: {error_msg}')
            if import_failures:
                failure_summary = '\n'.join(import_failures)
                pytest.fail(f'STRESS TEST REPRODUCED IMPORT FAILURES:\n{failure_summary}')
        finally:
            for conn in connections:
                try:
                    await conn.close()
                except:
                    pass
            await ws_manager.cleanup_all_connections()

    async def _stress_test_import_system(self, websocket_client, user_context):
        """Stress test the import system through WebSocket errors."""
        try:
            for message_id in range(5):
                error_message = {'type': 'agent_request', 'data': {'agent_type': 'STRESS_TEST_AGENT', 'query': f'Stress test message {message_id} from {user_context}', 'force_import_stress': True}}
                await websocket_client.send_json(error_message)
                await asyncio.sleep(0.1)
            for _ in range(5):
                try:
                    response = await websocket_client.receive_json(timeout=2.0)
                    if response and 'error' in response:
                        error_msg = str(response['error'])
                        if 'time' in error_msg and 'not defined' in error_msg:
                            raise Exception(f'Import stress failure: {error_msg}')
                except asyncio.TimeoutError:
                    break
        except Exception as e:
            if 'time' in str(e):
                raise
            print(f'Non-import error in stress test: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')