"""
Integration Test for Auth Service Startup Initialization Sequence (Issue #926)

This test reproduces the startup sequence race condition where the FastAPI
lifespan function tries to access auth_service before it's fully initialized.

Test Coverage:
- FastAPI lifespan startup sequence in main.py
- Auth service initialization timing during app startup
- Database connection initialization race conditions
- Health check endpoint availability during startup
- Redis connection setup timing issues

Expected Behavior:
- Tests should FAIL initially, reproducing the startup timing issues
- Demonstrates when auth_service is not available during startup phases
"""

import pytest
import asyncio
import logging
import time
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class StartupInitializationSequenceTests(SSotAsyncTestCase):
    """Integration tests for Auth Service startup initialization sequence"""
    
    def setUp(self):
        """Setup for startup sequence testing"""
        super().setUp()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.startup_results = []
        self.initialization_timings = []
        
    async def test_fastapi_lifespan_auth_service_race_condition(self):
        """
        Test reproducing the race condition in FastAPI lifespan startup
        where auth_service is accessed before initialization completes
        """
        # This test should FAIL initially - reproducing the actual race condition
        
        async def simulate_lifespan_startup():
            """Simulate the FastAPI lifespan startup sequence"""
            startup_events = []
            
            try:
                # Clear modules to simulate fresh startup
                modules_to_clear = [
                    'auth_service.auth_core.routes.auth_routes',
                    'auth_service.auth_core.services.auth_service',
                    'auth_service.main'
                ]
                for module in modules_to_clear:
                    if module in sys.modules:
                        del sys.modules[module]
                
                startup_events.append("modules_cleared")
                
                # Step 1: Import main module (triggers auth_routes import)
                from auth_service import main
                startup_events.append("main_imported")
                
                # Step 2: Simulate lifespan startup accessing auth_service
                # This reproduces lines 249-252 in main.py lifespan function
                import auth_service.auth_core.routes.auth_routes as auth_routes_module
                startup_events.append("auth_routes_imported")
                
                # Line 250-252: Check if auth_service global variable exists
                if hasattr(auth_routes_module, 'auth_service'):
                    auth_service = auth_routes_module.auth_service
                    startup_events.append("auth_service_found")
                    
                    # Line 254: Check if redis_client is available 
                    if hasattr(auth_service, 'redis_client'):
                        redis_enabled = auth_service.redis_client is not None
                        startup_events.append(f"redis_check_completed:{redis_enabled}")
                    else:
                        startup_events.append("redis_client_missing")
                        
                    return {"success": True, "events": startup_events}
                else:
                    # This is the race condition - auth_service not yet initialized
                    startup_events.append("auth_service_missing")
                    return {"success": False, "error": "auth service not yet initialized", "events": startup_events}
                    
            except Exception as e:
                startup_events.append(f"exception:{type(e).__name__}")
                return {"success": False, "error": str(e), "events": startup_events}
        
        # Run startup simulation multiple times to catch race condition
        results = []
        for i in range(15):
            result = await simulate_lifespan_startup()
            results.append(result)
            await asyncio.sleep(0.01)  # Small delay between attempts
        
        # Analyze race condition results
        failed_startups = [r for r in results if not r["success"]]
        auth_service_missing = [r for r in failed_startups if "not yet initialized" in r.get("error", "")]
        
        # Expected: Should FAIL initially due to race condition
        self.assertGreater(len(failed_startups), 0,
                         "Expected startup race condition failures")
        
        self.logger.error(f"Startup race condition: {len(failed_startups)} failures out of {len(results)}")
        for failure in failed_startups[:3]:
            self.logger.error(f"Startup failure: {failure}")
            
        # This should FAIL initially, confirming the race condition
        self.assertTrue(False, f"FastAPI lifespan race condition reproduced: {len(failed_startups)} startup failures. "
                              f"Auth service not available during lifespan startup sequence.")

    async def test_concurrent_startup_and_health_check_race(self):
        """
        Test race condition between app startup and health check requests
        Reproduces the scenario where health checks fail during initialization
        """
        # This test should FAIL initially
        
        async def simulate_app_startup():
            """Simulate FastAPI app startup process"""
            try:
                startup_start = time.time()
                
                # Clear modules
                modules_to_clear = [
                    'auth_service.auth_core.routes.auth_routes',
                    'auth_service.auth_core.services.auth_service'
                ]
                for module in modules_to_clear:
                    if module in sys.modules:
                        del sys.modules[module]
                
                # Import and initialize
                from auth_service.auth_core.routes import auth_routes
                
                startup_time = time.time() - startup_start
                return {"success": True, "startup_time": startup_time}
                
            except Exception as e:
                startup_time = time.time() - startup_start
                return {"success": False, "error": str(e), "startup_time": startup_time}
        
        async def simulate_health_check_during_startup():
            """Simulate health check request during startup"""
            try:
                # Small delay to simulate timing variations
                await asyncio.sleep(0.001)
                
                # Attempt to access health check functionality
                import auth_service.auth_core.routes.auth_routes as auth_routes_module
                
                # Health check pattern from main.py lines 674-679
                if hasattr(auth_routes_module, 'auth_service'):
                    auth_service = auth_routes_module.auth_service
                    
                    # Check session management capabilities
                    if hasattr(auth_service, 'redis_client') and auth_service.redis_client:
                        return {"success": True, "session_type": "redis"}
                    elif hasattr(auth_service, 'session_store'):
                        return {"success": True, "session_type": "memory"}
                    else:
                        return {"success": False, "error": "No session management available"}
                else:
                    return {"success": False, "error": "auth_service not available for health check"}
                    
            except Exception as e:
                return {"success": False, "error": f"Health check failed: {str(e)}"}
        
        # Run concurrent startup and health check operations
        concurrent_results = []
        
        for round_num in range(10):
            # Start startup and health check concurrently
            startup_task = asyncio.create_task(simulate_app_startup())
            health_task = asyncio.create_task(simulate_health_check_during_startup())
            
            startup_result = await startup_task
            health_result = await health_task
            
            concurrent_results.append({
                "round": round_num,
                "startup": startup_result,
                "health_check": health_result
            })
            
            # Small delay between rounds
            await asyncio.sleep(0.005)
        
        # Analyze concurrent operation results
        health_check_failures = [r for r in concurrent_results 
                               if not r["health_check"]["success"]]
        startup_failures = [r for r in concurrent_results 
                          if not r["startup"]["success"]]
        
        race_condition_failures = [r for r in health_check_failures
                                 if "not available" in r["health_check"].get("error", "")]
        
        # Expected: Should have race condition failures
        self.assertGreater(len(race_condition_failures), 0,
                         "Expected health check race condition failures during startup")
        
        self.logger.error(f"Concurrent startup race: {len(health_check_failures)} health check failures")
        self.logger.error(f"Race condition specific: {len(race_condition_failures)} auth_service unavailable")
        
        # This should FAIL initially
        self.assertTrue(False, f"Startup/health check race condition reproduced: "
                              f"{len(race_condition_failures)} race condition failures. "
                              f"Health checks fail when auth_service is not yet available.")

    async def test_database_initialization_timing_race(self):
        """
        Test race condition in database initialization during auth service startup
        Reproduces database connectivity issues during concurrent startup
        """
        # This test should FAIL initially
        
        async def simulate_database_dependent_startup():
            """Simulate startup operations that depend on database initialization"""
            timing_results = []
            
            try:
                start_time = time.time()
                
                # Clear auth service modules
                modules_to_clear = [
                    'auth_service.auth_core.routes.auth_routes',
                    'auth_service.auth_core.services.auth_service',
                    'auth_service.auth_core.database.connection'
                ]
                for module in modules_to_clear:
                    if module in sys.modules:
                        del sys.modules[module]
                
                timing_results.append(("modules_cleared", time.time() - start_time))
                
                # Initialize AuthService (triggers database initialization)
                from auth_service.auth_core.services.auth_service import AuthService
                auth_svc = AuthService()
                
                timing_results.append(("auth_service_created", time.time() - start_time))
                
                # Check if database connection is ready
                if hasattr(auth_svc, '_db_connection') and auth_svc._db_connection:
                    # Simulate database readiness check
                    db_connection = auth_svc._db_connection
                    if hasattr(db_connection, 'is_ready'):
                        # This is where race conditions occur - database not ready yet
                        timing_results.append(("db_connection_check", time.time() - start_time))
                        return {
                            "success": True, 
                            "timing": timing_results,
                            "has_db_connection": True
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Database connection missing is_ready method",
                            "timing": timing_results
                        }
                else:
                    return {
                        "success": False,
                        "error": "Database connection not initialized",
                        "timing": timing_results
                    }
                    
            except Exception as e:
                timing_results.append(("exception", time.time() - start_time))
                return {
                    "success": False,
                    "error": str(e),
                    "exception_type": type(e).__name__,
                    "timing": timing_results
                }
        
        # Run multiple database initialization attempts
        db_init_results = []
        tasks = []
        
        for i in range(12):
            task = asyncio.create_task(simulate_database_dependent_startup())
            tasks.append(task)
            
            # Stagger task start times to increase race condition likelihood
            if i % 3 == 0:
                await asyncio.sleep(0.002)
        
        # Wait for all tasks to complete
        for task in tasks:
            result = await task
            db_init_results.append(result)
        
        # Analyze database initialization race conditions
        db_failures = [r for r in db_init_results if not r["success"]]
        connection_failures = [r for r in db_failures if "connection not initialized" in r.get("error", "")]
        timing_failures = [r for r in db_failures if "timeout" in r.get("error", "").lower()]
        
        # Expected: Should have database timing failures
        self.assertGreater(len(db_failures), 0,
                         "Expected database initialization race condition failures")
        
        self.logger.error(f"Database initialization race: {len(db_failures)} failures out of {len(db_init_results)}")
        self.logger.error(f"Connection not initialized: {len(connection_failures)}")
        self.logger.error(f"Timing failures: {len(timing_failures)}")
        
        # Log timing details for first few failures
        for failure in db_failures[:2]:
            if "timing" in failure:
                self.logger.error(f"Failure timing: {failure['timing']}")
        
        # This should FAIL initially
        self.assertTrue(False, f"Database initialization race condition reproduced: "
                              f"{len(db_failures)} failures. Database not ready during auth service startup.")

    async def test_redis_connection_initialization_race(self):
        """
        Test race condition in Redis connection setup during startup
        Reproduces Redis connectivity issues during concurrent initialization
        """
        # This test should FAIL initially
        
        async def simulate_redis_dependent_operations():
            """Simulate operations that depend on Redis being available"""
            try:
                # Clear modules to force fresh initialization
                modules_to_clear = [
                    'auth_service.auth_core.routes.auth_routes',
                    'auth_service.auth_core.services.auth_service'
                ]
                for module in modules_to_clear:
                    if module in sys.modules:
                        del sys.modules[module]
                
                # Initialize auth service
                from auth_service.auth_core.services.auth_service import AuthService
                auth_service = AuthService()
                
                # Check Redis connection status (reproduces main.py line 355)
                if hasattr(auth_service, 'redis_client'):
                    if auth_service.redis_client is not None:
                        # Try to perform Redis operation
                        return {"success": True, "redis_available": True}
                    else:
                        return {"success": False, "error": "Redis client is None"}
                else:
                    return {"success": False, "error": "Redis client attribute missing"}
                    
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Run concurrent Redis-dependent operations
        redis_results = []
        concurrent_tasks = []
        
        for i in range(8):
            task = asyncio.create_task(simulate_redis_dependent_operations())
            concurrent_tasks.append(task)
        
        # Execute all tasks concurrently to maximize race condition probability
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                redis_results.append({"success": False, "error": str(result)})
            else:
                redis_results.append(result)
        
        # Analyze Redis race condition results
        redis_failures = [r for r in redis_results if not r["success"]]
        redis_none_failures = [r for r in redis_failures if "Redis client is None" in r.get("error", "")]
        missing_attr_failures = [r for r in redis_failures if "attribute missing" in r.get("error", "")]
        
        total_redis_race_failures = len(redis_none_failures) + len(missing_attr_failures)
        
        # Expected: Should have Redis initialization race failures
        self.assertGreater(total_redis_race_failures, 0,
                         "Expected Redis connection race condition failures")
        
        self.logger.error(f"Redis initialization race: {total_redis_race_failures} failures out of {len(redis_results)}")
        self.logger.error(f"Redis client None: {len(redis_none_failures)}")
        self.logger.error(f"Missing Redis attribute: {len(missing_attr_failures)}")
        
        # This should FAIL initially
        self.assertTrue(False, f"Redis connection race condition reproduced: "
                              f"{total_redis_race_failures} failures. Redis not available during startup sequence.")

    def tearDown(self):
        """Clean up after startup sequence tests"""
        super().tearDown()
        
        # Clear problematic modules
        modules_to_clear = [
            'auth_service.auth_core.routes.auth_routes',
            'auth_service.auth_core.services.auth_service',
            'auth_service.auth_core.database.connection',
            'auth_service.main'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]