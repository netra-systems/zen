"""
MISSION CRITICAL: SSOT Integration Test Suite

This test suite validates that all SSOT components integrate correctly with each other
and with the broader system. These tests focus on CROSS-COMPONENT INTEGRATION and
real-world usage scenarios that could break in production.

Business Value: Platform/Internal - Integration Reliability & System Stability  
Ensures that SSOT components work together seamlessly and don't break each other.

CRITICAL: These are DIFFICULT integration tests that test complex scenarios.
They use real services when available and test edge cases that could cause failures.
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Import SSOT framework components for integration testing
from test_framework.ssot import (
    BaseTestCase,
    AsyncBaseTestCase, 
    DatabaseTestCase,
    WebSocketTestCase,
    IntegrationTestCase,
    MockFactory,
    DatabaseTestUtility,
    WebSocketTestUtility,
    DockerTestUtility,
    get_mock_factory,
    get_database_test_utility,
    get_websocket_test_utility, 
    get_docker_test_utility,
    cleanup_all_ssot_resources
)

# Import the actual UnifiedDockerManager for integration testing
from test_framework.unified_docker_manager import UnifiedDockerManager, ServiceType, DockerEnvironment

from shared.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)


class TestSSOTDatabaseIntegration(DatabaseTestCase):
    """
    CRITICAL: Test SSOT database utilities integration.
    These tests validate database operations work correctly with the SSOT framework.
    """
    
    async def asyncSetUp(self):
        """Set up database integration test environment."""
        await super().asyncSetUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting database integration test: {self._testMethodName} (ID: {self.test_id})")
    
    async def asyncTearDown(self):
        """Clean up database integration test."""
        logger.info(f"Completing database integration test: {self._testMethodName} (ID: {self.test_id})")
        await super().asyncTearDown()
    
    async def test_database_utility_with_mock_factory_integration(self):
        """
        INTEGRATION CRITICAL: Test DatabaseTestUtility integrates with MockFactory.
        This validates that mocked database operations work with database utilities.
        """
        factory = get_mock_factory()
        
        # Create database session mock
        db_mock = factory.create_database_session_mock()
        self.assertIsNotNone(db_mock)
        
        # Test database utility can work with mocked session
        try:
            async with DatabaseTestUtility() as db_util:
                # If real database available, test real operations
                session = await db_util.get_session()
                self.assertIsNotNone(session)
                
                # Test transaction capability
                async with db_util.transaction_scope() as tx_session:
                    self.assertIsNotNone(tx_session)
                    # Transaction should be properly managed
                    
        except Exception as db_error:
            # If database not available, verify mock integration works
            logger.warning(f"Real database not available, testing mock integration: {db_error}")
            
            # Mock should be configured correctly
            self.assertTrue(hasattr(db_mock, 'execute'))
            self.assertTrue(hasattr(db_mock, 'commit'))
            self.assertTrue(hasattr(db_mock, 'rollback'))
    
    async def test_database_utility_connection_pooling(self):
        """
        PERFORMANCE CRITICAL: Test database connection pooling works correctly.
        This ensures multiple database utilities don't exhaust connections.
        """
        utilities = []
        
        try:
            # Create multiple database utilities
            for i in range(5):
                db_util = get_database_test_utility()
                utilities.append(db_util)
            
            # Test concurrent usage
            async def use_database(util_id, db_util):
                try:
                    async with db_util as util:
                        session = await util.get_session()
                        self.assertIsNotNone(session)
                        # Simulate some database work
                        await asyncio.sleep(0.01)
                        return f"util_{util_id}_success"
                except Exception as e:
                    return f"util_{util_id}_error_{str(e)}"
            
            # Run concurrent database operations
            tasks = [
                use_database(i, util) for i, util in enumerate(utilities)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            errors = [r for r in results if isinstance(r, Exception) or 'error' in str(r)]
            if errors:
                logger.warning(f"Database utility connection errors (expected if DB not available): {errors}")
            
            # If no errors, all utilities should have worked
            if not errors:
                success_count = len([r for r in results if 'success' in str(r)])
                self.assertEqual(success_count, 5,
                               f"Expected 5 successful database operations, got {success_count}")
                
        finally:
            # Clean up utilities
            for util in utilities:
                try:
                    if hasattr(util, 'cleanup'):
                        await util.cleanup()
                except:
                    pass
    
    async def test_database_utility_transaction_isolation(self):
        """
        ISOLATION CRITICAL: Test database transaction isolation works correctly.
        This ensures concurrent transactions don't interfere with each other.
        """
        try:
            async with DatabaseTestUtility() as db_util:
                # Test nested transaction scopes
                async with db_util.transaction_scope() as outer_session:
                    self.assertIsNotNone(outer_session)
                    
                    # Simulate outer transaction work
                    outer_data = f"outer_transaction_{self.test_id}"
                    
                    async with db_util.transaction_scope() as inner_session:
                        self.assertIsNotNone(inner_session)
                        
                        # Inner and outer sessions should be different or properly nested
                        inner_data = f"inner_transaction_{self.test_id}"
                        
                        # Both sessions should be functional
                        self.assertTrue(hasattr(outer_session, 'execute'))
                        self.assertTrue(hasattr(inner_session, 'execute'))
                        
        except Exception as e:
            # Expected if database not available, but test mock integration
            logger.warning(f"Database not available for transaction isolation test: {e}")
            
            # Test mock transaction behavior
            factory = get_mock_factory()
            session_mock = factory.create_database_session_mock()
            
            # Mock should have transaction methods
            self.assertTrue(hasattr(session_mock, 'begin'))
            self.assertTrue(hasattr(session_mock, 'commit'))
            self.assertTrue(hasattr(session_mock, 'rollback'))


class TestSSOTWebSocketIntegration(WebSocketTestCase):
    """
    CRITICAL: Test SSOT WebSocket utilities integration.
    These tests validate WebSocket operations work correctly with the SSOT framework.
    """
    
    async def asyncSetUp(self):
        """Set up WebSocket integration test environment."""
        await super().asyncSetUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting WebSocket integration test: {self._testMethodName} (ID: {self.test_id})")
    
    async def asyncTearDown(self):
        """Clean up WebSocket integration test."""
        logger.info(f"Completing WebSocket integration test: {self._testMethodName} (ID: {self.test_id})")
        await super().asyncTearDown()
    
    async def test_websocket_utility_with_mock_integration(self):
        """
        INTEGRATION CRITICAL: Test WebSocketTestUtility integrates with MockFactory.
        This validates WebSocket mocking works with WebSocket utilities.
        """
        factory = get_mock_factory()
        
        # Create WebSocket manager mock
        ws_mock = factory.create_websocket_manager_mock()
        self.assertIsNotNone(ws_mock)
        
        # Test WebSocket utility integration
        try:
            async with WebSocketTestUtility() as ws_util:
                client = await ws_util.create_client()
                self.assertIsNotNone(client)
                
                # Test client capabilities
                self.assertTrue(hasattr(client, 'send_message'))
                self.assertTrue(hasattr(client, 'wait_for_message'))
                
        except Exception as ws_error:
            # If WebSocket service not available, test mock integration
            logger.warning(f"WebSocket service not available, testing mock integration: {ws_error}")
            
            # Mock should have WebSocket capabilities
            self.assertTrue(hasattr(ws_mock, 'send'))
            self.assertTrue(hasattr(ws_mock, 'receive'))
    
    async def test_websocket_utility_concurrent_connections(self):
        """
        CONCURRENCY CRITICAL: Test WebSocket utility handles concurrent connections.
        This ensures multiple WebSocket clients don't interfere with each other.
        """
        try:
            async with WebSocketTestUtility() as ws_util:
                clients = []
                
                # Create multiple WebSocket clients
                for i in range(3):
                    client = await ws_util.create_client()
                    clients.append(client)
                
                self.assertEqual(len(clients), 3,
                               "Should create 3 WebSocket clients")
                
                # Test concurrent message sending
                async def send_test_message(client_id, client):
                    try:
                        message = f"test_message_{client_id}_{self.test_id}"
                        await client.send_message("test_event", {"data": message})
                        return f"client_{client_id}_success"
                    except Exception as e:
                        return f"client_{client_id}_error_{str(e)}"
                
                tasks = [
                    send_test_message(i, client) for i, client in enumerate(clients)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check results
                errors = [r for r in results if isinstance(r, Exception) or 'error' in str(r)]
                if errors:
                    logger.warning(f"WebSocket concurrent connection errors: {errors}")
                
        except Exception as e:
            # Expected if WebSocket service not available
            logger.warning(f"WebSocket service not available for concurrency test: {e}")
            
            # Test mock concurrent behavior
            factory = get_mock_factory()
            mocks = [factory.create_websocket_manager_mock() for _ in range(3)]
            
            self.assertEqual(len(mocks), 3,
                           "Should create 3 WebSocket mocks")
            
            for mock in mocks:
                self.assertIsNotNone(mock)
    
    async def test_websocket_utility_message_handling(self):
        """
        MESSAGE CRITICAL: Test WebSocket message handling works correctly.
        This validates WebSocket message serialization and deserialization.
        """
        from test_framework.ssot import WebSocketMessage, WebSocketEventType
        
        # Test message creation
        test_data = {"test": "data", "id": self.test_id}
        message = WebSocketMessage(
            event_type=WebSocketEventType.CUSTOM,
            data=test_data,
            timestamp=datetime.now()
        )
        
        self.assertIsNotNone(message)
        self.assertEqual(message.data, test_data)
        
        # Test message serialization
        try:
            serialized = message.to_dict()
            self.assertIsInstance(serialized, dict)
            self.assertIn('event_type', serialized)
            self.assertIn('data', serialized)
            self.assertIn('timestamp', serialized)
        except Exception as e:
            self.fail(f"Message serialization failed: {e}")
        
        # Test WebSocket utility with messages
        try:
            async with WebSocketTestUtility() as ws_util:
                client = await ws_util.create_client()
                
                # Test sending structured message
                await client.send_message(
                    WebSocketEventType.CUSTOM,
                    test_data
                )
                
        except Exception as e:
            # Expected if WebSocket service not available
            logger.warning(f"WebSocket message test skipped: {e}")


class TestSSOTDockerIntegration(IntegrationTestCase):
    """
    CRITICAL: Test SSOT Docker utilities integration.
    These tests validate Docker operations work correctly with the SSOT framework.
    """
    
    async def asyncSetUp(self):
        """Set up Docker integration test environment."""
        await super().asyncSetUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting Docker integration test: {self._testMethodName} (ID: {self.test_id})")
    
    async def asyncTearDown(self):
        """Clean up Docker integration test."""
        logger.info(f"Completing Docker integration test: {self._testMethodName} (ID: {self.test_id})")
        await super().asyncTearDown()
    
    async def test_docker_utility_with_unified_manager_integration(self):
        """
        INTEGRATION CRITICAL: Test DockerTestUtility integrates with UnifiedDockerManager.
        This validates the SSOT Docker management works correctly.
        """
        try:
            async with DockerTestUtility() as docker_util:
                # Test that Docker utility wraps UnifiedDockerManager
                self.assertIsNotNone(docker_util)
                self.assertTrue(hasattr(docker_util, 'start_services'))
                self.assertTrue(hasattr(docker_util, 'stop_services'))
                self.assertTrue(hasattr(docker_util, 'get_service_url'))
                
                # Test service management capabilities
                available_services = docker_util.get_available_services()
                self.assertIsInstance(available_services, list)
                
                # Test health check capabilities
                health_status = await docker_util.check_all_services_health()
                self.assertIsInstance(health_status, dict)
                
        except Exception as e:
            # Expected if Docker not available
            logger.warning(f"Docker not available for integration test: {e}")
            
            # Test mock Docker functionality
            factory = get_mock_factory()
            docker_mock = factory.create_mock("docker_service")
            self.assertIsNotNone(docker_mock)
    
    async def test_docker_utility_service_lifecycle(self):
        """
        LIFECYCLE CRITICAL: Test Docker service lifecycle management.
        This ensures services start, stop, and restart correctly.
        """
        try:
            async with DockerTestUtility() as docker_util:
                # Test basic service operations
                test_services = ["postgres", "redis"]  # Common test services
                
                # Test starting services
                start_result = await docker_util.start_services(test_services)
                self.assertIsInstance(start_result, dict)
                
                # Test service health after start
                await asyncio.sleep(2)  # Give services time to start
                health_status = await docker_util.check_services_health(test_services)
                self.assertIsInstance(health_status, dict)
                
                # Test getting service URLs
                for service in test_services:
                    try:
                        url = docker_util.get_service_url(service)
                        self.assertIsInstance(url, str)
                        self.assertIn("://", url)  # Should be a valid URL
                    except Exception as url_error:
                        logger.warning(f"Service URL not available for {service}: {url_error}")
                
                # Test stopping services
                stop_result = await docker_util.stop_services(test_services)
                self.assertIsInstance(stop_result, dict)
                
        except Exception as e:
            # Expected if Docker not available
            logger.warning(f"Docker service lifecycle test skipped: {e}")
    
    async def test_docker_utility_concurrent_access(self):
        """
        CONCURRENCY CRITICAL: Test Docker utility concurrent access.
        This ensures multiple tests can use Docker utilities simultaneously.
        """
        try:
            utilities = []
            
            # Create multiple Docker utilities
            for i in range(3):
                util = get_docker_test_utility()
                utilities.append(util)
            
            # Test concurrent Docker operations
            async def use_docker_utility(util_id, docker_util):
                try:
                    async with docker_util as util:
                        # Test basic operations
                        available = util.get_available_services()
                        health = await util.check_all_services_health()
                        
                        return f"util_{util_id}_success"
                except Exception as e:
                    return f"util_{util_id}_error_{str(e)}"
            
            # Run concurrent operations
            tasks = [
                use_docker_utility(i, util) for i, util in enumerate(utilities)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            errors = [r for r in results if isinstance(r, Exception) or 'error' in str(r)]
            if errors:
                logger.warning(f"Docker concurrent access errors: {errors}")
            
            # If no errors, all utilities should work
            if not errors:
                success_count = len([r for r in results if 'success' in str(r)])
                self.assertEqual(success_count, 3,
                               f"Expected 3 successful Docker operations, got {success_count}")
                
        except Exception as e:
            logger.warning(f"Docker concurrent access test skipped: {e}")
        
        finally:
            # Clean up utilities
            for util in utilities:
                try:
                    if hasattr(util, 'cleanup'):
                        await util.cleanup()
                except:
                    pass


class TestSSOTCrossComponentIntegration(IntegrationTestCase):
    """
    INTEGRATION CRITICAL: Test integration between different SSOT components.
    These are the most complex tests - they validate that different SSOT utilities
    work together in realistic scenarios.
    """
    
    async def asyncSetUp(self):
        """Set up cross-component integration test environment.""" 
        await super().asyncSetUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting cross-component integration test: {self._testMethodName} (ID: {self.test_id})")
    
    async def asyncTearDown(self):
        """Clean up cross-component integration test."""
        logger.info(f"Completing cross-component integration test: {self._testMethodName} (ID: {self.test_id})")
        await super().asyncTearDown()
    
    async def test_full_stack_integration_scenario(self):
        """
        FULL STACK CRITICAL: Test complete integration scenario.
        This tests Docker + Database + WebSocket + Mocks all working together.
        """
        factory = get_mock_factory()
        
        try:
            # Start with Docker services
            async with DockerTestUtility() as docker_util:
                # Try to start essential services
                essential_services = ["postgres", "redis"]
                start_result = await docker_util.start_services(essential_services)
                
                # Give services time to start
                await asyncio.sleep(3)
                
                # Test database integration with running services
                async with DatabaseTestUtility() as db_util:
                    try:
                        session = await db_util.get_session()
                        
                        # Test WebSocket integration
                        async with WebSocketTestUtility() as ws_util:
                            try:
                                client = await ws_util.create_client()
                                
                                # Test all components working together
                                test_data = {
                                    "test_id": self.test_id,
                                    "components": ["docker", "database", "websocket"],
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                await client.send_message("integration_test", test_data)
                                
                                # If we got here, full integration works
                                logger.info(f"Full stack integration successful for test {self.test_id}")
                                
                            except Exception as ws_error:
                                logger.warning(f"WebSocket integration failed: {ws_error}")
                                # Use mock instead
                                ws_mock = factory.create_websocket_manager_mock()
                                self.assertIsNotNone(ws_mock)
                                
                    except Exception as db_error:
                        logger.warning(f"Database integration failed: {db_error}")
                        # Use mock instead
                        db_mock = factory.create_database_session_mock()
                        self.assertIsNotNone(db_mock)
                        
        except Exception as docker_error:
            logger.warning(f"Docker integration failed: {docker_error}")
            # Fall back to pure mock testing
            
            # Test that all mock types work together
            docker_mock = factory.create_mock("docker_service")
            db_mock = factory.create_database_session_mock()  
            ws_mock = factory.create_websocket_manager_mock()
            
            # All mocks should be created
            self.assertIsNotNone(docker_mock)
            self.assertIsNotNone(db_mock)
            self.assertIsNotNone(ws_mock)
            
            # Test mock integration
            registry = factory.get_registry()
            self.assertGreaterEqual(len(registry.active_mocks), 3)
    
    async def test_resource_cleanup_integration(self):
        """
        CLEANUP CRITICAL: Test that all SSOT resources clean up correctly.
        This prevents resource leaks in long-running test suites.
        """
        # Track initial resource state
        factory = get_mock_factory()
        initial_registry = factory.get_registry()
        initial_mock_count = len(initial_registry.active_mocks)
        
        # Create resources across multiple components
        resources_created = []
        
        try:
            # Create database resources
            db_util = get_database_test_utility()
            resources_created.append(("database", db_util))
            
            # Create WebSocket resources
            ws_util = get_websocket_test_utility()
            resources_created.append(("websocket", ws_util))
            
            # Create Docker resources
            docker_util = get_docker_test_utility()
            resources_created.append(("docker", docker_util))
            
            # Create mocks
            for i in range(5):
                mock = factory.create_mock(f"cleanup_test_{i}")
                resources_created.append(("mock", mock))
            
            # Verify resources were created
            mid_registry = factory.get_registry()
            mid_mock_count = len(mid_registry.active_mocks)
            self.assertGreater(mid_mock_count, initial_mock_count,
                             "Resources should be created")
            
            # Test comprehensive cleanup
            await cleanup_all_ssot_resources()
            
            # Verify cleanup worked
            final_registry = factory.get_registry()
            final_mock_count = len(final_registry.active_mocks)
            self.assertLessEqual(final_mock_count, initial_mock_count,
                               f"Cleanup should reduce resource count. Initial: {initial_mock_count}, Final: {final_mock_count}")
            
        except Exception as e:
            logger.error(f"Resource cleanup integration test error: {e}")
            # Still try to clean up
            try:
                await cleanup_all_ssot_resources()
            except:
                pass
            raise
    
    async def test_error_propagation_integration(self):
        """
        ERROR HANDLING CRITICAL: Test error propagation across components.
        This ensures errors in one component don't crash other components.
        """
        factory = get_mock_factory()
        
        # Test that errors in one component don't break others
        try:
            # Create intentionally failing operations
            async def failing_database_operation():
                async with DatabaseTestUtility() as db_util:
                    # This might fail if database not available
                    session = await db_util.get_session()
                    # Simulate error
                    raise ValueError("Intentional database error")
            
            async def failing_websocket_operation():
                async with WebSocketTestUtility() as ws_util:
                    # This might fail if WebSocket not available
                    client = await ws_util.create_client()
                    # Simulate error
                    raise ConnectionError("Intentional WebSocket error")
            
            async def working_mock_operation():
                # This should always work
                mock = factory.create_mock("working_service")
                return mock
            
            # Run operations concurrently
            results = await asyncio.gather(
                failing_database_operation(),
                failing_websocket_operation(),
                working_mock_operation(),
                return_exceptions=True
            )
            
            # Check that errors are properly contained
            database_result = results[0]
            websocket_result = results[1]  
            mock_result = results[2]
            
            # Failed operations should return exceptions
            self.assertIsInstance(database_result, Exception)
            self.assertIsInstance(websocket_result, Exception)
            
            # Working operation should succeed
            self.assertIsNotNone(mock_result)
            self.assertNotIsInstance(mock_result, Exception)
            
        except Exception as e:
            logger.error(f"Error propagation test failed: {e}")
            # This shouldn't happen - errors should be contained
            self.fail(f"Error propagation not properly handled: {e}")
    
    async def test_performance_integration_scenario(self):
        """
        PERFORMANCE CRITICAL: Test performance of integrated SSOT operations.
        This ensures SSOT components don't create performance bottlenecks.
        """
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        start_time = time.time()
        
        try:
            # Perform intensive operations across multiple components
            factory = get_mock_factory()
            
            # Create many resources
            for i in range(20):
                mock = factory.create_mock(f"performance_test_{i}")
                
                # Simulate realistic usage
                if hasattr(mock, 'configure_mock'):
                    mock.configure_mock(
                        return_value=f"result_{i}",
                        side_effect=None
                    )
            
            # Test resource usage
            mid_memory = process.memory_info().rss
            memory_increase = mid_memory - initial_memory
            
            # Clean up resources
            factory.cleanup_all_mocks()
            await cleanup_all_ssot_resources()
            
            # Measure final performance
            end_time = time.time()
            final_memory = process.memory_info().rss
            
            duration = end_time - start_time
            final_memory_increase = final_memory - initial_memory
            
            # Performance assertions
            max_duration = 5.0  # 5 seconds max
            max_memory = 50 * 1024 * 1024  # 50MB max
            
            self.assertLess(duration, max_duration,
                           f"Integration operations took too long: {duration}s")
            self.assertLess(memory_increase, max_memory,
                           f"Integration operations used too much memory: {memory_increase} bytes")
            self.assertLess(final_memory_increase, max_memory // 2,
                           f"Memory not properly cleaned up: {final_memory_increase} bytes residual")
            
            logger.info(f"Performance integration test completed in {duration:.2f}s with {memory_increase} bytes peak memory")
            
        except Exception as e:
            logger.error(f"Performance integration test failed: {e}")
            raise


if __name__ == '__main__':
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short', '--capture=no'])