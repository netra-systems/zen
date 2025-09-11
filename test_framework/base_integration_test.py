"""
Base Integration Test Framework - SSOT for Real Services Integration Testing

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable REAL service integration testing without mocks
- Value Impact: Validates actual business workflows and service interactions
- Strategic Impact: Ensures system delivers real business value through proper testing
"""

import asyncio
import logging
import pytest
from typing import Any, Dict, Optional, AsyncIterator
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

from shared.isolated_environment import get_env
from test_framework.real_services import RealServicesManager, get_real_services
from shared.types.user_types import TestUserData

# Import service abstraction for --no-docker scenarios
try:
    from test_framework.service_abstraction import IntegrationServiceManager
except ImportError:
    logger.warning("Service abstraction not available - some integration tests may fail without Docker")
    IntegrationServiceManager = None


class BaseIntegrationTest(ABC):
    """
    Base class for integration tests - ENFORCES real services usage.
    
    CRITICAL: Integration tests MUST use real services (PostgreSQL, Redis) 
    to validate actual service interactions and business workflows.
    
    NO MOCKS ALLOWED - Use real_services fixtures for all database/cache operations.
    """
    
    def setup_method(self):
        """Set up method called before each test method."""
        self.setup_logging()
        self.setup_environment()
    
    def teardown_method(self):
        """Tear down method called after each test method."""
        self.cleanup_resources()
    
    def setup_logging(self):
        """Set up logging for tests."""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def setup_environment(self):
        """Set up isolated test environment."""
        self.env = get_env()
        self.env.set("TESTING", "1", source="integration_test")
        
        # Check if --no-docker flag was used (USE_REAL_SERVICES would be false)
        use_real_services = self.env.get("USE_REAL_SERVICES", "false").lower() == "true"
        if use_real_services:
            self.env.set("USE_REAL_SERVICES", "true", source="integration_test")
            self.env.set("SKIP_MOCKS", "true", source="integration_test") 
            logger.info("Integration test using real services (Docker)")
        else:
            # Use service abstractions for --no-docker scenarios
            self.env.set("USE_SERVICE_ABSTRACTION", "true", source="integration_test")
            logger.info("Integration test using service abstractions (--no-docker)")
        
        # Store which mode we're in for test methods to check
        self.using_real_services = use_real_services
        self.using_service_abstraction = not use_real_services
    
    def cleanup_resources(self):
        """Clean up resources after test."""
        # Override in subclasses if needed
        pass
    
    async def async_setup(self):
        """Async setup for tests that need it."""
        # Override in subclasses if needed
        pass
    
    async def async_teardown(self):
        """Async teardown for tests that need it."""
        # Override in subclasses if needed  
        pass

    # Helper methods for common integration test patterns
    async def create_test_user_context(self, real_services: RealServicesManager, user_data: Optional[Dict] = None) -> TestUserData:
        """
        Create isolated test user context with real database.
        
        Returns SSOT TestUserData object supporting both attribute and dict access.
        Resolves interface mismatch preventing Golden Path agent conversation sessions.
        """
        if not user_data:
            user_data = {
                'email': f'test-{asyncio.current_task().get_name()}@example.com',
                'name': 'Integration Test User',
                'is_active': True
            }
        
        # Insert real user into database
        user_id = await real_services.postgres.fetchval("""
            INSERT INTO auth.users (email, name, is_active)
            VALUES ($1, $2, $3)
            ON CONFLICT (email) DO UPDATE SET 
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active
            RETURNING id
        """, user_data['email'], user_data['name'], user_data['is_active'])
        
        user_data['id'] = str(user_id)
        
        # Convert dict to SSOT TestUserData object supporting both access patterns
        return TestUserData.from_dict(user_data)

    async def create_test_organization(self, real_services: RealServicesManager, user_id: str, org_data: Optional[Dict] = None) -> Dict:
        """Create real test organization with user membership."""
        if not org_data:
            org_data = {
                'name': f'Test Org {asyncio.current_task().get_name()}',
                'slug': f'test-org-{user_id[:8]}',
                'plan': 'free'
            }
        
        # Insert real organization
        org_id = await real_services.postgres.fetchval("""
            INSERT INTO backend.organizations (name, slug, plan)
            VALUES ($1, $2, $3)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                plan = EXCLUDED.plan
            RETURNING id
        """, org_data['name'], org_data['slug'], org_data['plan'])
        
        # Create membership
        await real_services.postgres.execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role)
            VALUES ($1, $2, 'admin')
            ON CONFLICT (user_id, organization_id) DO NOTHING
        """, user_id, org_id)
        
        org_data['id'] = str(org_id)
        return org_data

    async def create_test_session(self, real_services: RealServicesManager, user_id: str, session_data: Optional[Dict] = None) -> Dict:
        """Create real user session in Redis cache."""
        if not session_data:
            session_data = {
                'user_id': user_id,
                'created_at': asyncio.get_event_loop().time(),
                'expires_at': asyncio.get_event_loop().time() + 3600,  # 1 hour
                'active': True
            }
        
        # Store session in real Redis
        session_key = f"session:{user_id}"
        await real_services.redis.set_json(session_key, session_data, ex=3600)
        
        session_data['session_key'] = session_key
        return session_data

    def assert_business_value_delivered(self, result: Dict, expected_value_type: str):
        """
        Assert that test result delivers actual business value.
        
        Args:
            result: Test execution result
            expected_value_type: Type of business value expected (e.g. 'cost_savings', 'insights', 'automation')
        """
        assert result is not None, "Integration test must produce real results"
        
        # Check both nested 'results' and top-level for backward compatibility
        nested_results = result.get('results', {}) if isinstance(result.get('results'), dict) else {}
        
        if expected_value_type == 'cost_savings':
            has_savings = ('potential_savings' in result or 'cost_reduction' in result or
                          'potential_savings' in nested_results or 'cost_reduction' in nested_results)
            assert has_savings, "Cost optimization must identify potential savings"
        elif expected_value_type == 'insights':
            has_insights = ('recommendations' in result or 'analysis' in result or
                           'recommendations' in nested_results or 'analysis' in nested_results)
            assert has_insights, "Analysis must provide actionable insights"  
        elif expected_value_type == 'automation':
            has_automation = ('actions_taken' in result or 'automated_tasks' in result or
                             'actions_taken' in nested_results or 'automated_tasks' in nested_results)
            assert has_automation, "Automation must execute real actions"
        else:
            assert len(result) > 0, f"Business value type '{expected_value_type}' must produce measurable results"


class DatabaseIntegrationTest(BaseIntegrationTest):
    """Integration test base class for database-focused testing."""
    
    async def verify_database_transaction_isolation(self, real_services: RealServicesManager):
        """Verify database transactions properly isolate between concurrent operations."""
        # Test concurrent transaction isolation
        async def concurrent_insert(table: str, data: Dict, index: int):
            async with real_services.postgres.transaction() as tx:
                await tx.execute(f"INSERT INTO {table} (name, value) VALUES ($1, $2)", 
                               f"test_record_{index}", f"value_{index}")
                # Simulate processing delay
                await asyncio.sleep(0.1)
                return f"inserted_{index}"
        
        # Run concurrent operations
        results = await asyncio.gather(*[
            concurrent_insert("test_table", {}, i) for i in range(3)
        ])
        
        assert len(results) == 3, "All concurrent transactions must complete"
        return results


class CacheIntegrationTest(BaseIntegrationTest):
    """Integration test base class for Redis cache testing."""
    
    async def verify_cache_performance(self, real_services: RealServicesManager, operation_count: int = 100):
        """Verify Redis cache operations meet performance requirements."""
        import time
        
        start_time = time.time()
        
        # Batch cache operations
        for i in range(operation_count):
            await real_services.redis.set(f"perf_test:{i}", f"value_{i}")
            cached_value = await real_services.redis.get(f"perf_test:{i}")
            assert cached_value == f"value_{i}"
        
        duration = time.time() - start_time
        ops_per_second = operation_count / duration
        
        # Redis should handle at least 1000 ops/sec for simple operations
        assert ops_per_second > 100, f"Cache performance too slow: {ops_per_second:.2f} ops/sec"
        
        self.logger.info(f"Cache performance: {ops_per_second:.2f} operations/second")
        return ops_per_second


class WebSocketIntegrationTest(BaseIntegrationTest):
    """Integration test base class for WebSocket service testing."""
    
    async def verify_websocket_event_delivery(self, websocket_client, expected_events: list):
        """Verify all expected WebSocket events are delivered in correct order."""
        received_events = []
        
        # Collect events with timeout
        async def collect_events():
            async for event in websocket_client.receive_events(timeout=30):
                received_events.append(event)
                if len(received_events) >= len(expected_events):
                    break
        
        await collect_events()
        
        # Verify all expected events received
        received_types = [event.get('type') for event in received_events]
        for expected_event in expected_events:
            assert expected_event in received_types, f"Missing WebSocket event: {expected_event}"
        
        return received_events


class ServiceOrchestrationIntegrationTest(BaseIntegrationTest):
    """Integration test base class for multi-service coordination testing."""
    
    async def verify_service_health_cascade(self, real_services: RealServicesManager):
        """Verify all services are healthy and properly connected."""
        health_checks = {}
        
        # PostgreSQL health
        try:
            await real_services.postgres.fetchval("SELECT 1")
            health_checks['postgres'] = True
        except Exception as e:
            health_checks['postgres'] = False
            self.logger.error(f"PostgreSQL health check failed: {e}")
        
        # Redis health  
        try:
            await real_services.redis.ping()
            health_checks['redis'] = True
        except Exception as e:
            health_checks['redis'] = False
            self.logger.error(f"Redis health check failed: {e}")
        
        # All services must be healthy
        for service, is_healthy in health_checks.items():
            assert is_healthy, f"Service {service} is not healthy - integration tests cannot proceed"
        
        return health_checks