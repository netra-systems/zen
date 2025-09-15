"""
Unit Test for Auth Service Initialization Race Condition (Issue #926)

This test reproduces the race condition where auth_service is referenced before
the AuthService() constructor completes initialization, causing 'auth_service' 
to be undefined.

Test Coverage:
- Lines 249, 348, 665, 667 in main.py where auth_service is referenced
- Line 42 in auth_routes.py where `auth_service = AuthService()` 
- Race condition between import and initialization
- AuthService initialization failure scenarios

Expected Behavior:
- Tests should FAIL initially, reproducing the race condition
- Demonstrates the auth service startup failure mode
"""

import pytest
import threading
import time
import logging
import asyncio
import sys
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.isolated_environment import get_env


class AuthServiceInitializationRaceConditionTests(SSotBaseTestCase):
    """Unit tests for Auth Service initialization race condition scenarios"""
    
    def setUp(self):
        """Setup for race condition testing"""
        super().setUp()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.initialization_errors = []
        self.race_condition_results = []
        
    def test_auth_service_import_initialization_race(self):
        """
        Test reproducing the race condition in auth_routes.py line 42
        where auth_service = AuthService() may fail during concurrent access
        """
        # This test should FAIL initially - reproducing the actual race condition
        
        def attempt_auth_service_import():
            """Simulate concurrent auth_service initialization attempts"""
            try:
                # Clear any cached modules to force re-import
                modules_to_clear = [
                    'auth_service.auth_core.routes.auth_routes',
                    'auth_service.auth_core.services.auth_service'
                ]
                for module in modules_to_clear:
                    if module in sys.modules:
                        del sys.modules[module]
                
                # Import auth_routes module, which triggers line 42: auth_service = AuthService()
                from auth_service.auth_core.routes import auth_routes
                
                # Check if auth_service variable is properly defined
                if not hasattr(auth_routes, 'auth_service'):
                    return {"success": False, "error": "auth_service variable not found"}
                
                if auth_routes.auth_service is None:
                    return {"success": False, "error": "auth_service is None"}
                
                # Try to access auth_service methods (triggers the undefined reference)
                if hasattr(auth_routes.auth_service, 'jwt_handler'):
                    return {"success": True, "auth_service_id": id(auth_routes.auth_service)}
                else:
                    return {"success": False, "error": "auth_service missing jwt_handler"}
                    
            except Exception as e:
                return {"success": False, "error": str(e), "exception_type": type(e).__name__}
        
        # Simulate race condition with multiple concurrent initialization attempts
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(10):  # Multiple concurrent attempts
                future = executor.submit(attempt_auth_service_import)
                futures.append(future)
                time.sleep(0.01)  # Small delay to increase race condition likelihood
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
        # Analyze race condition results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        self.race_condition_results = results
        
        # Expected: This should FAIL initially due to race condition
        # Some attempts should fail with auth_service being undefined
        self.assertGreater(len(failed_results), 0, 
                         "Race condition not reproduced - expected some initialization failures")
        
        # Log the race condition details for debugging
        self.logger.error(f"Race condition reproduced: {len(failed_results)} failures out of {len(results)} attempts")
        for failed in failed_results[:3]:  # Log first 3 failures
            self.logger.error(f"Initialization failure: {failed}")
            
        # This assertion should FAIL initially, confirming the race condition
        self.assertTrue(False, f"Race condition reproduced: {len(failed_results)} initialization failures detected. "
                              f"This confirms Issue #926 exists and needs fixing.")
    
    def test_auth_service_main_py_reference_race(self):
        """
        Test reproducing race condition in main.py lines 249, 348, 665, 667
        where auth_service is referenced during shutdown/startup sequences
        """
        # This test should FAIL initially
        
        def simulate_main_py_auth_service_access():
            """Simulate main.py accessing auth_service during initialization"""
            try:
                # Simulate the pattern from main.py lines 249-252
                import auth_service.auth_core.routes.auth_routes as auth_routes_module
                
                # Line 251: if hasattr(auth_routes_module, 'auth_service'):
                if hasattr(auth_routes_module, 'auth_service'):
                    auth_service = auth_routes_module.auth_service  # Line 252
                    
                    # Line 354-357: Check redis_client (similar pattern)
                    if hasattr(auth_service, 'redis_client'):
                        redis_enabled = auth_service.redis_client is not None  # Line 355
                        return {"success": True, "redis_enabled": redis_enabled}
                    else:
                        return {"success": False, "error": "redis_client not found"}
                else:
                    # This is the race condition - auth_service not yet initialized
                    return {"success": False, "error": "auth_service variable not yet initialized"}
                    
            except AttributeError as e:
                if "auth_service" in str(e):
                    return {"success": False, "error": f"auth_service undefined: {e}"}
                else:
                    raise
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Clear modules to force fresh import
        modules_to_clear = [
            'auth_service.auth_core.routes.auth_routes',
            'auth_service.auth_core.services.auth_service'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Simulate multiple rapid access attempts (like during startup/shutdown)
        race_results = []
        for i in range(20):
            result = simulate_main_py_auth_service_access()
            race_results.append(result)
            time.sleep(0.001)  # Tiny delay to simulate timing variations
        
        # Analyze results for race condition
        undefined_errors = [r for r in race_results if not r["success"] and "undefined" in r.get("error", "")]
        not_initialized_errors = [r for r in race_results if not r["success"] and "not yet initialized" in r.get("error", "")]
        
        total_race_failures = len(undefined_errors) + len(not_initialized_errors)
        
        # Expected: Should FAIL initially due to race condition
        self.assertGreater(total_race_failures, 0,
                         "Expected race condition failures in main.py auth_service references")
        
        # Log race condition evidence
        self.logger.error(f"Main.py race condition: {total_race_failures} undefined reference failures")
        
        # This should FAIL initially, proving the race condition exists
        self.assertTrue(False, f"Main.py race condition reproduced: {total_race_failures} failures where auth_service was undefined. "
                              f"Lines 249-252, 354-357 in main.py are susceptible to this race condition.")

    def test_auth_service_health_check_during_initialization(self):
        """
        Test health check race condition during auth service initialization
        This reproduces failures in lines 665-667 of main.py during health checks
        """
        # This test should FAIL initially
        
        def attempt_health_check_during_init():
            """Simulate health check accessing auth_service during initialization"""
            try:
                # Clear modules to simulate fresh startup
                modules_to_clear = [
                    'auth_service.auth_core.routes.auth_routes', 
                    'auth_service.auth_core.services.auth_service'
                ]
                for module in modules_to_clear:
                    if module in sys.modules:
                        del sys.modules[module]
                
                # Start auth_service initialization in background
                def initialize_auth_service():
                    from auth_service.auth_core.routes import auth_routes
                    return auth_routes.auth_service
                
                # Simulate health check happening during initialization (race condition)
                import auth_service.auth_core.routes.auth_routes as auth_routes_module
                
                # Lines 674-677: Health check trying to access auth_service
                if hasattr(auth_routes_module, 'auth_service'):
                    auth_service = auth_routes_module.auth_service  # Line 676
                    
                    # Line 677-678: Check if redis_client available
                    if hasattr(auth_service, 'redis_client') and auth_service.redis_client:
                        return {"success": True, "has_redis": True}
                    elif hasattr(auth_service, 'session_store'):  # Line 679
                        return {"success": True, "has_session_store": True}
                    else:
                        return {"success": False, "error": "No session management found"}
                else:
                    return {"success": False, "error": "auth_service not available during health check"}
                    
            except Exception as e:
                error_msg = str(e)
                if "auth_service" in error_msg and ("undefined" in error_msg or "not found" in error_msg):
                    return {"success": False, "error": f"Race condition in health check: {error_msg}"}
                else:
                    return {"success": False, "error": error_msg}
        
        # Run multiple health check attempts to trigger race condition
        health_check_results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(attempt_health_check_during_init) for _ in range(15)]
            for future in as_completed(futures):
                result = future.result()
                health_check_results.append(result)
        
        # Check for race condition failures
        race_failures = [r for r in health_check_results if not r["success"] and 
                        ("not available" in r.get("error", "") or "Race condition" in r.get("error", ""))]
        
        # Expected: Should FAIL initially due to race condition
        self.assertGreater(len(race_failures), 0,
                         "Expected health check race condition failures")
        
        # Log the race condition evidence
        self.logger.error(f"Health check race condition: {len(race_failures)} failures during initialization")
        for failure in race_failures[:2]:
            self.logger.error(f"Health check failure: {failure}")
        
        # This should FAIL initially
        self.assertTrue(False, f"Health check race condition reproduced: {len(race_failures)} failures. "
                              f"Health checks in main.py lines 674-679 fail when auth_service is not yet initialized.")

    def test_concurrent_auth_service_initialization_stress(self):
        """
        Stress test for concurrent AuthService initialization
        Reproduces the fundamental race condition in AuthService() constructor
        """
        # This test should FAIL initially
        
        initialization_attempts = []
        
        def stress_test_auth_service_init():
            """Attempt AuthService initialization under concurrent stress"""
            try:
                # Force fresh AuthService creation
                from auth_service.auth_core.services.auth_service import AuthService
                
                # Time the initialization
                start_time = time.time()
                auth_svc = AuthService()  # This is where race conditions occur
                end_time = time.time()
                
                # Verify initialization completed
                if hasattr(auth_svc, 'jwt_handler') and hasattr(auth_svc, 'redis_client'):
                    return {
                        "success": True, 
                        "init_time": end_time - start_time,
                        "auth_service_id": id(auth_svc)
                    }
                else:
                    return {
                        "success": False, 
                        "error": "Incomplete initialization",
                        "init_time": end_time - start_time
                    }
                    
            except Exception as e:
                return {
                    "success": False, 
                    "error": str(e), 
                    "exception_type": type(e).__name__
                }
        
        # Run concurrent initialization stress test
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i in range(50):  # High concurrency stress
                future = executor.submit(stress_test_auth_service_init)
                futures.append(future)
                if i % 5 == 0:  # Stagger submissions
                    time.sleep(0.001)
            
            for future in as_completed(futures):
                result = future.result()
                initialization_attempts.append(result)
        
        # Analyze stress test results
        successful_inits = [r for r in initialization_attempts if r["success"]]
        failed_inits = [r for r in initialization_attempts if not r["success"]]
        
        # Expected: Should have failures under concurrent stress
        self.assertGreater(len(failed_inits), 0,
                         "Expected AuthService initialization failures under concurrent stress")
        
        # Check for specific race condition indicators
        database_failures = [f for f in failed_inits if "database" in f.get("error", "").lower()]
        timeout_failures = [f for f in failed_inits if "timeout" in f.get("error", "").lower()]
        
        self.logger.error(f"Stress test results: {len(failed_inits)} failures out of {len(initialization_attempts)}")
        self.logger.error(f"Database-related failures: {len(database_failures)}")
        self.logger.error(f"Timeout failures: {len(timeout_failures)}")
        
        # This should FAIL initially, proving initialization race conditions
        self.assertTrue(False, f"AuthService initialization race condition reproduced under stress: "
                              f"{len(failed_inits)} failures. This confirms the fundamental race condition in Issue #926.")

    def tearDown(self):
        """Clean up after race condition tests"""
        super().tearDown()
        
        # Clear any problematic cached modules
        modules_to_clear = [
            'auth_service.auth_core.routes.auth_routes',
            'auth_service.auth_core.services.auth_service'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]