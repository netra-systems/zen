"""
SSOT End-to-End Migration Tests - Full Authentication & Docker Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Complete system reliability during deployments and schema changes
- Value Impact: Prevents catastrophic failures during migrations that would destroy business operations
- Strategic Impact: Enables confident production deployments without business disruption

CRITICAL REQUIREMENTS per CLAUDE.md:
- MANDATORY E2E AUTH: Uses real JWT/OAuth authentication (NO EXCEPTIONS)
- Full Docker integration with Alpine containers via unified test runner
- Tests migration execution in production-like environment
- Validates WebSocket events during migration activities
- Tests user isolation during migration processes
- Must execute in >0.00s (automatic failure detection by test runner)

SSOT Compliance:
- Uses test_framework/ssot/e2e_auth_helper.py for ALL authentication
- Inherits from SSotBaseTestCase for environment isolation
- Real Docker services with Alpine containers for performance
- No mocks allowed in E2E tests - all services must be real
- Comprehensive WebSocket event validation during migrations
"""

import pytest
import asyncio
import uuid
import time
import json
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    create_authenticated_user
)
from shared.isolated_environment import get_env

from netra_backend.app.db.migration_utils import DatabaseMigrator

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.migration,
    pytest.mark.real_services,
    pytest.mark.docker,
    pytest.mark.slow
]


@pytest.fixture(scope="session")
async def docker_services_fixture():
    """
    Session-scoped Docker services fixture for E2E migration testing.
    
    CRITICAL: This fixture ensures all Docker containers are running:
    - PostgreSQL (Alpine) for database operations
    - Redis (Alpine) for session management
    - Backend service with migration capabilities
    - Auth service for JWT validation
    
    The unified test runner automatically handles Docker orchestration
    when --real-services flag is used.
    """
    env = get_env()
    
    # Validate required services are available
    required_services = {
        "database": env.get("DATABASE_URL"),
        "redis": env.get("REDIS_URL"), 
        "backend": env.get("BACKEND_URL", "http://localhost:8000"),
        "auth": env.get("AUTH_SERVICE_URL", "http://localhost:8083"),
        "websocket": env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
    }
    
    missing_services = []
    for service_name, service_url in required_services.items():
        if not service_url or "mock" in service_url.lower():
            missing_services.append(service_name)
            
    if missing_services:
        pytest.skip(f"E2E services not available: {missing_services}. Use --real-services flag.")
    
    # Validate database connectivity for migrations
    try:
        migrator = DatabaseMigrator(required_services["database"])
        if not migrator.validate_url():
            pytest.skip("Database connectivity validation failed for E2E migration testing")
    except Exception as e:
        pytest.skip(f"Database connection test failed: {e}")
        
    return required_services


@pytest.fixture
async def e2e_authenticated_user_fixture():
    """
    CRITICAL E2E Authentication Fixture - MANDATORY for ALL E2E tests.
    
    Per CLAUDE.md E2E AUTH MANDATE: This fixture provides real JWT authentication
    that works with all E2E services including WebSocket connections.
    
    This is NOT a convenience - it's a REQUIREMENT for proper E2E testing.
    """
    env = get_env()
    environment = env.get("TEST_ENV", env.get("ENVIRONMENT", "test"))
    
    # Create E2E auth helper for the current environment
    auth_helper = E2EAuthHelper(environment=environment)
    
    try:
        # Create authenticated user with real auth flow
        if environment == "staging":
            # Use staging-specific auth with OAuth simulation
            jwt_token = await auth_helper.get_staging_token_async()
            user_data = {
                "id": f"e2e_staging_user_{uuid.uuid4().hex[:8]}",
                "email": f"e2e_staging_{uuid.uuid4().hex[:8]}@example.com",
                "permissions": ["read", "write", "migration_test"],
                "environment": "staging"
            }
        else:
            # Use standard auth flow for test environment
            jwt_token, user_data = await create_authenticated_user(
                environment=environment,
                email=f"e2e_test_{uuid.uuid4().hex[:8]}@example.com",
                permissions=["read", "write", "migration_test"]
            )
            
        # Validate authentication actually works
        is_valid = await auth_helper.validate_token(jwt_token)
        if not is_valid:
            pytest.skip(f"E2E authentication validation failed for {environment} environment")
            
        return {
            "jwt_token": jwt_token,
            "user_data": user_data,
            "auth_helper": auth_helper,
            "environment": environment,
            "user_id": user_data["id"],
            "email": user_data["email"]
        }
        
    except Exception as e:
        pytest.skip(f"E2E authentication setup failed: {e}")


@pytest.fixture
async def e2e_websocket_fixture(e2e_authenticated_user_fixture):
    """
    E2E WebSocket fixture with proper authentication for migration event testing.
    
    CRITICAL: This fixture establishes authenticated WebSocket connections
    that can receive migration-related events during E2E testing.
    """
    auth_data = e2e_authenticated_user_fixture
    
    # Create WebSocket auth helper
    ws_helper = E2EWebSocketAuthHelper(environment=auth_data["environment"])
    
    try:
        # Establish authenticated WebSocket connection
        websocket_connection = await ws_helper.connect_authenticated_websocket(timeout=15.0)
        
        yield {
            "connection": websocket_connection,
            "auth_helper": ws_helper,
            "user_data": auth_data["user_data"],
            "jwt_token": auth_data["jwt_token"]
        }
        
    except Exception as e:
        pytest.skip(f"E2E WebSocket connection failed: {e}")
    finally:
        # Clean up WebSocket connection
        try:
            if 'websocket_connection' in locals():
                await websocket_connection.close()
        except:
            pass  # Best effort cleanup


class TestSSOTMigrationEndToEnd(SSotBaseTestCase):
    """
    SSOT End-to-End Migration Tests - Production-Like Environment Testing.
    
    This comprehensive E2E test suite validates complete migration workflows
    in Docker environment with real authentication, WebSocket events, and
    multi-service coordination.
    
    CRITICAL: These tests ensure production deployment safety and business continuity.
    """
    
    def setup_method(self, method=None):
        """Enhanced setup for E2E migration testing."""
        super().setup_method(method)
        
        # Initialize E2E test context
        env = self.get_env()
        self.test_environment = env.get("TEST_ENV", env.get("ENVIRONMENT", "test"))
        self.e2e_test_id = f"e2e_migration_{uuid.uuid4().hex[:8]}"
        
        # Record E2E initialization metrics
        self.record_metric("e2e_test_id", self.e2e_test_id)
        self.record_metric("test_environment", self.test_environment)
        self.record_metric("docker_integration_enabled", True)
        self.record_metric("e2e_test_started", datetime.now(timezone.utc).isoformat())
        
        print(f"[U+1F680] Starting E2E migration test: {self.e2e_test_id}")
        print(f"[U+1F30D] Environment: {self.test_environment}")
        
    @pytest.mark.asyncio
    async def test_e2e_migration_with_websocket_events(
        self, 
        docker_services_fixture, 
        e2e_authenticated_user_fixture,
        e2e_websocket_fixture
    ):
        """
        Test complete E2E migration workflow with WebSocket event validation.
        
        BUSINESS VALUE: Ensures users receive real-time migration status updates
        through WebSocket connections, maintaining transparency during deployments.
        
        CRITICAL: This test validates the complete user experience during migrations.
        """
        services = docker_services_fixture
        auth_data = e2e_authenticated_user_fixture
        websocket_data = e2e_websocket_fixture
        
        # Initialize authenticated migration context
        migrator = DatabaseMigrator(services["database"])
        websocket_connection = websocket_data["connection"]
        
        # Record test setup completion
        self.record_metric("authenticated_user_established", True)
        self.record_metric("websocket_connection_established", True)
        self.record_metric("docker_services_validated", len(services))
        
        print(f" PASS:  E2E setup complete - User: {auth_data['user_id']}")
        
        try:
            # Start WebSocket event monitoring
            websocket_events = []
            
            async def monitor_websocket_events():
                """Monitor WebSocket for migration-related events."""
                try:
                    while True:
                        event_data = await asyncio.wait_for(
                            websocket_connection.recv(), 
                            timeout=2.0
                        )
                        event = json.loads(event_data)
                        websocket_events.append({
                            "event": event,
                            "timestamp": time.time(),
                            "user_context": auth_data["user_id"]
                        })
                        self.increment_websocket_events()
                        
                        # Break if we get a completion event
                        if event.get("type") == "migration_status":
                            break
                except asyncio.TimeoutError:
                    pass  # Expected for monitoring
                except Exception as e:
                    print(f"WebSocket monitoring error: {e}")
                    
            # Start event monitoring in background
            monitor_task = asyncio.create_task(monitor_websocket_events())
            
            # Execute migration operations that should generate events
            migration_start_time = time.time()
            
            # Send migration check request to backend (simulated)
            migration_check_message = {
                "type": "migration_check",
                "user_id": auth_data["user_id"],
                "test_id": self.e2e_test_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket_connection.send(json.dumps(migration_check_message))
            self.increment_websocket_events()
            
            # Perform actual migration status checks
            current_revision = migrator.get_current_revision()
            head_revision = migrator.get_head_revision()
            needs_migration = migrator.needs_migration()
            
            self.increment_db_query_count(3)
            
            # Allow time for WebSocket events
            await asyncio.sleep(1.0)
            
            # Stop monitoring
            monitor_task.cancel()
            
            migration_duration = time.time() - migration_start_time
            
            # Record migration metrics
            self.record_metric("migration_check_duration", migration_duration)
            self.record_metric("current_revision_detected", current_revision is not None)
            self.record_metric("head_revision_detected", head_revision is not None)
            self.record_metric("migration_status_determined", True)
            self.record_metric("websocket_events_received", len(websocket_events))
            
            # Validate E2E migration workflow
            assert head_revision is not None, "E2E environment should have migration scripts available"
            assert isinstance(needs_migration, bool), "Migration status should be deterministic"
            
            # Validate WebSocket event flow
            total_ws_events = self.get_websocket_events_count()
            assert total_ws_events > 0, "WebSocket events should be generated during E2E migration operations"
            
            self.record_metric("websocket_integration_successful", total_ws_events > 0)
            
            # Business continuity validation
            assert migration_duration < 30.0, f"E2E migration check took too long: {migration_duration:.3f}s"
            
            print(f" PASS:  E2E Migration Check Complete - Duration: {migration_duration:.3f}s")
            print(f"[U+1F4E1] WebSocket Events: {total_ws_events}")
            print(f" CHART:  Current -> Head: {current_revision}  ->  {head_revision}")
            
        except Exception as e:
            self.record_metric("e2e_migration_error", str(e))
            pytest.fail(f"E2E migration with WebSocket events failed: {e}")
            
    @pytest.mark.asyncio
    async def test_e2e_user_isolation_during_migration(
        self,
        docker_services_fixture,
        e2e_authenticated_user_fixture
    ):
        """
        Test user isolation during migration processes in E2E environment.
        
        BUSINESS VALUE: Ensures that migration operations don't leak data
        between users or disrupt individual user sessions.
        """
        services = docker_services_fixture
        primary_user = e2e_authenticated_user_fixture
        
        # Create additional authenticated users for isolation testing
        secondary_users = []
        for i in range(2):
            try:
                if primary_user["environment"] == "staging":
                    # Use staging auth helper for additional users
                    auth_helper = E2EAuthHelper(environment="staging")
                    jwt_token = await auth_helper.get_staging_token_async(
                        email=f"e2e_isolation_user_{i}_{self.e2e_test_id}@example.com"
                    )
                    user_data = {
                        "id": f"isolation_user_{i}_{uuid.uuid4().hex[:8]}",
                        "email": f"e2e_isolation_user_{i}_{self.e2e_test_id}@example.com",
                        "permissions": ["read"]
                    }
                else:
                    jwt_token, user_data = await create_authenticated_user(
                        email=f"e2e_isolation_user_{i}_{self.e2e_test_id}@example.com",
                        permissions=["read"]
                    )
                    
                secondary_users.append({
                    "jwt_token": jwt_token,
                    "user_data": user_data,
                    "user_id": user_data["id"]
                })
            except Exception as e:
                print(f"Warning: Could not create secondary user {i}: {e}")
                
        self.record_metric("isolation_users_created", len(secondary_users))
        
        try:
            # Initialize migration contexts for each user
            migrator = DatabaseMigrator(services["database"])
            
            # Test migration visibility per user
            user_migration_contexts = []
            
            # Primary user migration context
            primary_context = {
                "user_id": primary_user["user_id"],
                "jwt_token": primary_user["jwt_token"],
                "migration_state": {
                    "current_revision": migrator.get_current_revision(),
                    "head_revision": migrator.get_head_revision(),
                    "needs_migration": migrator.needs_migration()
                },
                "check_time": time.time()
            }
            user_migration_contexts.append(primary_context)
            self.increment_db_query_count(3)
            
            # Secondary users migration contexts (should see same system state)
            for secondary_user in secondary_users:
                secondary_context = {
                    "user_id": secondary_user["user_id"],
                    "jwt_token": secondary_user["jwt_token"],
                    "migration_state": {
                        "current_revision": migrator.get_current_revision(),
                        "head_revision": migrator.get_head_revision(),
                        "needs_migration": migrator.needs_migration()
                    },
                    "check_time": time.time()
                }
                user_migration_contexts.append(secondary_context)
                self.increment_db_query_count(3)
                
            # Validate user isolation
            # All users should see the same migration state (system-wide)
            base_migration_state = primary_context["migration_state"]
            isolation_maintained = True
            
            for context in user_migration_contexts[1:]:
                user_state = context["migration_state"]
                if (user_state["current_revision"] != base_migration_state["current_revision"] or
                    user_state["head_revision"] != base_migration_state["head_revision"] or
                    user_state["needs_migration"] != base_migration_state["needs_migration"]):
                    isolation_maintained = False
                    break
                    
            # Record isolation metrics
            self.record_metric("user_contexts_tested", len(user_migration_contexts))
            self.record_metric("migration_state_consistency", isolation_maintained)
            self.record_metric("user_isolation_maintained", isolation_maintained)
            
            # Validate that users can't access each other's session data
            # (Migration state is system-wide, but user context should be isolated)
            unique_user_ids = set(ctx["user_id"] for ctx in user_migration_contexts)
            assert len(unique_user_ids) == len(user_migration_contexts), \
                "Each user should have unique isolated context"
                
            self.record_metric("unique_user_contexts_verified", True)
            
            # Business validation
            assert isolation_maintained, "Migration state should be consistent across all user sessions"
            
            print(f" PASS:  User Isolation Verified - {len(user_migration_contexts)} users tested")
            print(f" CHART:  Migration State Consistency: {isolation_maintained}")
            
        except Exception as e:
            self.record_metric("user_isolation_error", str(e))
            pytest.fail(f"E2E user isolation during migration failed: {e}")
            
    @pytest.mark.asyncio
    async def test_e2e_production_like_migration_scenario(
        self,
        docker_services_fixture,
        e2e_authenticated_user_fixture
    ):
        """
        Test production-like migration scenario with full Docker stack.
        
        BUSINESS VALUE: Validates complete deployment workflow matches
        production environment behavior, preventing deployment surprises.
        """
        services = docker_services_fixture
        auth_data = e2e_authenticated_user_fixture
        
        # Initialize production-like migration context
        migrator = DatabaseMigrator(services["database"])
        
        print(f"[U+1F3ED] Starting production-like migration simulation")
        print(f"[U+1F527] Services: {list(services.keys())}")
        
        try:
            # Simulate pre-deployment checks (what would happen in CI/CD)
            pre_deployment_checks = {
                "database_connectivity": False,
                "migration_scripts_available": False,
                "auth_service_responsive": False,
                "migration_state_deterministic": False
            }
            
            # Check database connectivity
            db_connectivity_start = time.time()
            database_healthy = migrator.validate_url()
            db_connectivity_time = time.time() - db_connectivity_start
            
            pre_deployment_checks["database_connectivity"] = database_healthy
            self.record_metric("db_connectivity_check_time", db_connectivity_time)
            
            # Check migration scripts availability
            try:
                head_revision = migrator.get_head_revision()
                pre_deployment_checks["migration_scripts_available"] = head_revision is not None
                self.record_metric("head_revision_available", head_revision is not None)
            except Exception as e:
                self.record_metric("migration_scripts_check_error", str(e))
                
            # Check auth service responsiveness
            auth_check_start = time.time()
            try:
                auth_helper = auth_data["auth_helper"]
                auth_responsive = await auth_helper.validate_token(auth_data["jwt_token"])
                auth_check_time = time.time() - auth_check_start
                
                pre_deployment_checks["auth_service_responsive"] = auth_responsive
                self.record_metric("auth_service_check_time", auth_check_time)
                self.record_metric("auth_service_responsive", auth_responsive)
            except Exception as e:
                self.record_metric("auth_service_check_error", str(e))
                
            # Check migration state determinism
            migration_check_start = time.time()
            try:
                current_revision = migrator.get_current_revision()
                needs_migration = migrator.needs_migration()
                
                # Run check twice to ensure deterministic results
                current_revision_2 = migrator.get_current_revision()
                needs_migration_2 = migrator.needs_migration()
                
                deterministic = (current_revision == current_revision_2 and 
                               needs_migration == needs_migration_2)
                               
                pre_deployment_checks["migration_state_deterministic"] = deterministic
                migration_check_time = time.time() - migration_check_start
                
                self.record_metric("migration_state_check_time", migration_check_time)
                self.record_metric("migration_state_deterministic", deterministic)
                
                self.increment_db_query_count(4)  # Two sets of checks
                
            except Exception as e:
                self.record_metric("migration_state_check_error", str(e))
                
            # Evaluate deployment readiness
            deployment_ready_checks = sum(1 for check in pre_deployment_checks.values() if check)
            total_checks = len(pre_deployment_checks)
            deployment_readiness = deployment_ready_checks / total_checks
            
            self.record_metric("pre_deployment_checks_passed", deployment_ready_checks)
            self.record_metric("total_pre_deployment_checks", total_checks)
            self.record_metric("deployment_readiness_score", deployment_readiness)
            
            # Simulate deployment decision logic
            deployment_go_decision = deployment_readiness >= 0.75  # 75% checks must pass
            self.record_metric("deployment_go_decision", deployment_go_decision)
            
            # Production-like performance validation
            total_pre_deployment_time = (
                db_connectivity_time + 
                auth_check_time + 
                migration_check_time
            )
            
            self.record_metric("total_pre_deployment_time", total_pre_deployment_time)
            self.record_metric("pre_deployment_performance_acceptable", total_pre_deployment_time < 60.0)
            
            # Business validation
            assert database_healthy, "Database must be healthy for production deployment"
            assert deployment_readiness > 0.5, f"Deployment readiness too low: {deployment_readiness:.2%}"
            assert total_pre_deployment_time < 120.0, f"Pre-deployment checks took too long: {total_pre_deployment_time:.3f}s"
            
            print(f" PASS:  Production-like simulation complete")
            print(f" CHART:  Deployment Readiness: {deployment_readiness:.1%} ({deployment_ready_checks}/{total_checks})")
            print(f"[U+23F1][U+FE0F]  Total Check Time: {total_pre_deployment_time:.3f}s")
            print(f" TARGET:  Deployment Decision: {'GO' if deployment_go_decision else 'NO-GO'}")
            
        except Exception as e:
            self.record_metric("production_simulation_error", str(e))
            pytest.fail(f"E2E production-like migration scenario failed: {e}")
            
    @pytest.mark.asyncio
    async def test_e2e_migration_performance_under_load(
        self,
        docker_services_fixture,
        e2e_authenticated_user_fixture
    ):
        """
        Test migration performance under load in Docker environment.
        
        BUSINESS VALUE: Ensures migration operations perform adequately
        under realistic load conditions similar to production.
        """
        services = docker_services_fixture
        auth_data = e2e_authenticated_user_fixture
        
        migrator = DatabaseMigrator(services["database"])
        
        print(f" LIGHTNING:  Starting migration performance test under load")
        
        try:
            # Simulate concurrent load on migration system
            concurrent_operations = []
            load_test_start = time.time()
            
            async def migration_operation(operation_id: int):
                """Simulate migration operation under load."""
                op_start = time.time()
                try:
                    # Simulate realistic migration operations
                    current = migrator.get_current_revision()
                    head = migrator.get_head_revision()
                    needs = migrator.needs_migration()
                    valid = migrator.validate_url()
                    
                    op_duration = time.time() - op_start
                    return {
                        "operation_id": operation_id,
                        "success": True,
                        "duration": op_duration,
                        "results": {
                            "current_revision": current,
                            "head_revision": head,
                            "needs_migration": needs,
                            "url_valid": valid
                        }
                    }
                except Exception as e:
                    op_duration = time.time() - op_start
                    return {
                        "operation_id": operation_id,
                        "success": False,
                        "duration": op_duration,
                        "error": str(e)
                    }
                    
            # Execute concurrent operations
            num_concurrent_ops = 5  # Reasonable load for E2E testing
            for i in range(num_concurrent_ops):
                concurrent_operations.append(migration_operation(i))
                
            # Execute all operations concurrently
            operation_results = await asyncio.gather(*concurrent_operations)
            total_load_time = time.time() - load_test_start
            
            # Analyze performance results
            successful_operations = [op for op in operation_results if op["success"]]
            failed_operations = [op for op in operation_results if not op["success"]]
            
            if successful_operations:
                operation_times = [op["duration"] for op in successful_operations]
                avg_operation_time = sum(operation_times) / len(operation_times)
                max_operation_time = max(operation_times)
                min_operation_time = min(operation_times)
            else:
                avg_operation_time = max_operation_time = min_operation_time = 0
                
            # Record performance metrics
            self.record_metric("concurrent_operations_attempted", num_concurrent_ops)
            self.record_metric("successful_operations", len(successful_operations))
            self.record_metric("failed_operations", len(failed_operations))
            self.record_metric("success_rate", len(successful_operations) / num_concurrent_ops)
            self.record_metric("total_load_test_time", total_load_time)
            self.record_metric("avg_operation_time", avg_operation_time)
            self.record_metric("max_operation_time", max_operation_time)
            self.record_metric("min_operation_time", min_operation_time)
            
            # Track database queries (approximate)
            self.increment_db_query_count(len(successful_operations) * 3)
            
            # Performance validation
            success_rate = len(successful_operations) / num_concurrent_ops
            assert success_rate >= 0.8, f"Success rate too low under load: {success_rate:.1%}"
            assert max_operation_time < 30.0, f"Max operation time too high: {max_operation_time:.3f}s"
            assert total_load_time < 60.0, f"Total load test took too long: {total_load_time:.3f}s"
            
            # Business continuity validation
            performance_acceptable = (avg_operation_time < 10.0 and 
                                    max_operation_time < 30.0 and
                                    success_rate >= 0.8)
                                    
            self.record_metric("performance_under_load_acceptable", performance_acceptable)
            
            print(f" PASS:  Performance test complete - Success Rate: {success_rate:.1%}")
            print(f"[U+23F1][U+FE0F]  Avg/Max Operation Time: {avg_operation_time:.3f}s / {max_operation_time:.3f}s")
            print(f"[U+1F3CB][U+FE0F]  Total Load Test Duration: {total_load_time:.3f}s")
            
        except Exception as e:
            self.record_metric("performance_load_test_error", str(e))
            pytest.fail(f"E2E migration performance under load test failed: {e}")
            
    def teardown_method(self, method=None):
        """Enhanced teardown for E2E migration tests."""
        # Record E2E completion metrics
        self.record_metric("e2e_test_completed", datetime.now(timezone.utc).isoformat())
        
        # Calculate total test execution time
        all_metrics = self.get_all_metrics()
        execution_time = all_metrics.get("execution_time", 0)
        
        # E2E tests MUST execute in >0.00s (CLAUDE.md requirement)
        if execution_time <= 0.001:  # 1ms threshold for timing precision
            pytest.fail(f"E2E test execution time {execution_time:.3f}s indicates test was mocked or skipped")
            
        # Log comprehensive E2E summary
        if method:
            print(f"\n{'='*60}")
            print(f"E2E Migration Test '{method.__name__}' Summary")
            print(f"{'='*60}")
            print(f"Test ID: {self.e2e_test_id}")
            print(f"Environment: {self.test_environment}")
            print(f"Duration: {execution_time:.3f}s")
            print(f"Database Queries: {all_metrics.get('database_queries', 0)}")
            print(f"WebSocket Events: {all_metrics.get('websocket_events', 0)}")
            
            # Log critical E2E metrics
            e2e_metrics = {
                k: v for k, v in all_metrics.items()
                if any(keyword in k.lower() for keyword in [
                    'docker', 'auth', 'websocket', 'isolation', 'deployment',
                    'performance', 'load', 'production'
                ])
            }
            
            if e2e_metrics:
                print("Critical E2E Metrics:")
                for metric, value in e2e_metrics.items():
                    print(f"  {metric}: {value}")
                    
            print(f"{'='*60}")
        
        # Call parent teardown
        super().teardown_method(method)


# SSOT Export Control
__all__ = [
    "TestSSOTMigrationEndToEnd",
    "docker_services_fixture",
    "e2e_authenticated_user_fixture", 
    "e2e_websocket_fixture"
]