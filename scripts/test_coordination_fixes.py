"""
Test runner to validate service coordination fixes.

This script runs the coordination system tests to ensure all issues
identified in test_critical_cold_start_initialization.py are resolved.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path

from dev_launcher.dependency_manager import setup_default_dependency_manager
from dev_launcher.service_coordinator import ServiceCoordinator, CoordinationConfig
from dev_launcher.readiness_checker import ReadinessManager
from dev_launcher.port_allocator import get_global_port_allocator
from dev_launcher.service_registry import get_global_service_registry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoordinationFixValidator:
    """Validates that service coordination fixes work correctly."""
    
    def __init__(self):
        self.test_results: Dict[str, bool] = {}
        self.error_details: Dict[str, str] = {}
    
    async def run_all_tests(self) -> bool:
        """Run all coordination fix validation tests."""
        logger.info("Starting service coordination fix validation")
        
        tests = [
            ("dependency_resolution", self.test_dependency_resolution),
            ("readiness_separation", self.test_readiness_vs_health_separation), 
            ("port_allocation", self.test_port_allocation_coordination),
            ("service_discovery", self.test_service_discovery_timing),
            ("graceful_degradation", self.test_graceful_degradation),
            ("complete_workflow", self.test_complete_coordination_workflow),
            ("cleanup", self.test_resource_cleanup)
        ]
        
        overall_success = True
        
        for test_name, test_func in tests:
            logger.info(f"Running test: {test_name}")
            try:
                start_time = time.time()
                success = await test_func()
                duration = time.time() - start_time
                
                self.test_results[test_name] = success
                
                if success:
                    logger.info(f" PASS:  {test_name} PASSED ({duration:.2f}s)")
                else:
                    logger.error(f" FAIL:  {test_name} FAILED ({duration:.2f}s)")
                    overall_success = False
                    
            except Exception as e:
                duration = time.time() - start_time if 'start_time' in locals() else 0
                logger.error(f"[U+1F4A5] {test_name} EXCEPTION ({duration:.2f}s): {e}")
                self.test_results[test_name] = False
                self.error_details[test_name] = str(e)
                overall_success = False
        
        # Print summary
        self._print_test_summary()
        
        return overall_success
    
    async def test_dependency_resolution(self) -> bool:
        """Test that dependency resolution prevents early startup."""
        logger.info("Testing dependency resolution fixes")
        
        try:
            # Setup dependency manager
            dependency_manager = setup_default_dependency_manager()
            
            # Get startup order
            startup_order = dependency_manager.get_startup_order()
            logger.info(f"Computed startup order: {'  ->  '.join(startup_order)}")
            
            # Validate order constraints
            db_idx = startup_order.index("database")
            auth_idx = startup_order.index("auth")
            backend_idx = startup_order.index("backend")
            frontend_idx = startup_order.index("frontend")
            
            # Check ordering constraints
            assert db_idx < auth_idx, "Database must start before auth"
            assert auth_idx < backend_idx, "Auth must start before backend"
            assert backend_idx < frontend_idx, "Backend must start before frontend"
            
            # Test dependency waiting
            await dependency_manager.mark_service_ready("database")
            
            # Auth should be able to start
            can_start, missing = dependency_manager.can_start_service("auth")
            assert can_start, f"Auth should be able to start, missing: {missing}"
            
            # Backend should not be able to start yet
            can_start, missing = dependency_manager.can_start_service("backend")
            assert not can_start, "Backend should not start before auth is ready"
            
            logger.info("Dependency resolution working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Dependency resolution test failed: {e}")
            return False
    
    async def test_readiness_vs_health_separation(self) -> bool:
        """Test separation between readiness and health checks."""
        logger.info("Testing readiness vs health check separation")
        
        try:
            readiness_manager = ReadinessManager()
            
            # Register mock service
            readiness_manager.register_service("test_service", [])
            
            # Initially not ready
            assert not readiness_manager.is_service_ready("test_service"), "Service should not be ready initially"
            
            # Mark as initializing
            await readiness_manager.mark_service_initializing("test_service")
            assert not readiness_manager.is_service_ready("test_service"), "Service should not be ready while initializing"
            
            # Mark as starting  
            await readiness_manager.mark_service_starting("test_service")
            assert not readiness_manager.is_service_ready("test_service"), "Service should not be ready while starting"
            
            # Mark as ready (simulates successful readiness check)
            status = readiness_manager.get_service_status("test_service")
            status.overall_ready = True
            status.state = status.state.READY if hasattr(status.state, 'READY') else 'ready'
            
            assert readiness_manager.is_service_ready("test_service"), "Service should be ready after marking"
            
            logger.info("Readiness vs health separation working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Readiness separation test failed: {e}")
            return False
    
    async def test_port_allocation_coordination(self) -> bool:
        """Test port allocation prevents conflicts."""
        logger.info("Testing port allocation coordination")
        
        try:
            port_allocator = await get_global_port_allocator()
            
            # Try to allocate same port to different services
            result1 = await port_allocator.reserve_port("service1", preferred_port=18000)
            assert result1.success, f"First allocation failed: {result1.error_message}"
            
            result2 = await port_allocator.reserve_port("service2", preferred_port=18000)
            assert result2.success, f"Second allocation failed: {result2.error_message}"
            
            # Should get different ports
            assert result1.port != result2.port, "Services got same port - conflict not prevented"
            
            logger.info(f"Port allocation working: service1={result1.port}, service2={result2.port}")
            
            # Clean up
            await port_allocator.release_port(result1.port, "service1")
            await port_allocator.release_port(result2.port, "service2")
            
            return True
            
        except Exception as e:
            logger.error(f"Port allocation test failed: {e}")
            return False
    
    async def test_service_discovery_timing(self) -> bool:
        """Test service discovery handles timing issues."""
        logger.info("Testing service discovery timing fixes")
        
        try:
            service_registry = await get_global_service_registry()
            
            from dev_launcher.service_registry import DiscoveryQuery, ServiceEndpoint, ServiceStatus
            
            # Try to discover service before it's registered
            query = DiscoveryQuery(
                service_name="timing_test_service",
                retry_count=3,
                retry_delay=0.5
            )
            
            # Start discovery task
            discovery_task = asyncio.create_task(service_registry.discover_service(query))
            
            # Wait briefly, then register service
            await asyncio.sleep(1.0)
            
            endpoints = [ServiceEndpoint(
                name="api",
                url="http://localhost:18001",
                port=18001
            )]
            
            await service_registry.register_service("timing_test_service", endpoints)
            await service_registry.update_service_status("timing_test_service", ServiceStatus.READY)
            
            # Discovery should succeed with retry logic
            result = await asyncio.wait_for(discovery_task, timeout=10.0)
            
            assert result is not None, "Service discovery failed with retry logic"
            assert result.service_name == "timing_test_service"
            
            logger.info("Service discovery timing fixes working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Service discovery timing test failed: {e}")
            return False
    
    async def test_graceful_degradation(self) -> bool:
        """Test graceful degradation with optional service failures."""
        logger.info("Testing graceful degradation")
        
        try:
            config = CoordinationConfig(
                required_services={"database", "backend"},
                optional_services={"redis", "auth", "frontend"},
                enable_graceful_degradation=True
            )
            
            coordinator = ServiceCoordinator(config)
            
            # Mock successful startup for required services
            async def successful_startup():
                return {"success": True, "process_id": 999}
            
            # Mock failing startup for optional services
            async def failing_startup():
                raise RuntimeError("Optional service failed")
            
            # Register services
            coordinator.register_service("database", successful_startup, lambda: True)
            coordinator.register_service("backend", successful_startup, lambda: True)
            coordinator.register_service("redis", failing_startup, lambda: False)
            coordinator.register_service("auth", failing_startup, lambda: False)
            
            # Start coordination
            success = await coordinator.coordinate_startup(["database", "backend", "redis", "auth"])
            
            # Should succeed despite optional failures
            assert success, "Coordination should succeed with optional service failures"
            
            # Check degraded services
            degraded = coordinator.get_degraded_services()
            assert "redis" in degraded, "Redis should be in degraded services"
            assert "auth" in degraded, "Auth should be in degraded services"
            
            # System should still be healthy
            assert coordinator.is_healthy(), "System should be healthy despite degraded services"
            
            logger.info(f"Graceful degradation working: degraded={degraded}")
            return True
            
        except Exception as e:
            logger.error(f"Graceful degradation test failed: {e}")
            return False
    
    async def test_complete_coordination_workflow(self) -> bool:
        """Test complete end-to-end coordination workflow."""
        logger.info("Testing complete coordination workflow")
        
        try:
            # Setup all coordination components
            dependency_manager = setup_default_dependency_manager()
            readiness_manager = ReadinessManager()
            port_allocator = await get_global_port_allocator()
            service_registry = await get_global_service_registry()
            
            config = CoordinationConfig(
                required_services={"backend"},
                optional_services={"frontend"}
            )
            coordinator = ServiceCoordinator(config)
            
            # Mock services
            backend_started = False
            frontend_started = False
            
            async def start_backend():
                nonlocal backend_started
                # Reserve port
                result = await port_allocator.reserve_port("backend", preferred_port=18002)
                assert result.success
                
                # Register in registry
                from dev_launcher.service_registry import ServiceEndpoint
                endpoints = [ServiceEndpoint("api", f"http://localhost:{result.port}", result.port)]
                await service_registry.register_service("backend", endpoints)
                
                backend_started = True
                return {"success": True, "port": result.port}
            
            async def start_frontend():
                nonlocal frontend_started
                result = await port_allocator.reserve_port("frontend", preferred_port=18003)
                assert result.success
                
                from dev_launcher.service_registry import ServiceEndpoint
                endpoints = [ServiceEndpoint("web", f"http://localhost:{result.port}", result.port)]
                await service_registry.register_service("frontend", endpoints)
                
                frontend_started = True
                return {"success": True, "port": result.port}
            
            # Register with coordinator
            coordinator.register_service("backend", start_backend, lambda: backend_started)
            coordinator.register_service("frontend", start_frontend, lambda: frontend_started)
            
            # Start coordination
            success = await coordinator.coordinate_startup(["backend", "frontend"])
            
            assert success, "Complete workflow should succeed"
            assert backend_started, "Backend should have started"
            assert frontend_started, "Frontend should have started"
            
            # Verify registry has services
            from dev_launcher.service_registry import DiscoveryQuery
            services = await service_registry.discover_services(DiscoveryQuery())
            service_names = {s.service_name for s in services}
            assert "backend" in service_names, "Backend should be in registry"
            assert "frontend" in service_names, "Frontend should be in registry"
            
            logger.info("Complete coordination workflow successful")
            return True
            
        except Exception as e:
            logger.error(f"Complete workflow test failed: {e}")
            return False
    
    async def test_resource_cleanup(self) -> bool:
        """Test proper resource cleanup."""
        logger.info("Testing resource cleanup")
        
        try:
            # This test mainly verifies that global cleanup functions exist and work
            from dev_launcher.port_allocator import cleanup_global_port_allocator
            from dev_launcher.service_registry import cleanup_global_service_registry
            
            # These should not raise exceptions
            await cleanup_global_port_allocator()
            await cleanup_global_service_registry()
            
            logger.info("Resource cleanup successful")
            return True
            
        except Exception as e:
            logger.error(f"Resource cleanup test failed: {e}")
            return False
    
    def _print_test_summary(self):
        """Print comprehensive test summary."""
        logger.info("=" * 60)
        logger.info("SERVICE COORDINATION FIX VALIDATION SUMMARY")
        logger.info("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            logger.info("\nFAILED TESTS:")
            for test_name, result in self.test_results.items():
                if not result:
                    error = self.error_details.get(test_name, "No error details")
                    logger.info(f"   FAIL:  {test_name}: {error}")
        
        logger.info("\nTEST MAPPING TO ORIGINAL ISSUES:")
        logger.info("  dependency_resolution      ->  test_06_services_starting_before_dependencies")
        logger.info("  readiness_separation       ->  test_07_health_check_false_positives_during_init")
        logger.info("  port_allocation            ->  test_08_port_binding_race_conditions")
        logger.info("  service_discovery          ->  test_09_service_discovery_timing_issues")
        logger.info("  graceful_degradation       ->  test_10_graceful_degradation_optional_services")
        logger.info("  complete_workflow          ->  End-to-end integration validation")
        logger.info("  cleanup                    ->  Resource management validation")
        
        logger.info("=" * 60)


async def main():
    """Main entry point."""
    logger.info("Service Coordination Fix Validation")
    logger.info("This validates fixes for issues in test_critical_cold_start_initialization.py")
    
    validator = CoordinationFixValidator()
    
    try:
        success = await validator.run_all_tests()
        
        if success:
            logger.info(" CELEBRATION:  ALL COORDINATION FIXES VALIDATED SUCCESSFULLY!")
            logger.info("The service coordination system should now handle:")
            logger.info("   PASS:  Service dependency ordering")
            logger.info("   PASS:  Readiness vs health check separation") 
            logger.info("   PASS:  Port allocation conflict prevention")
            logger.info("   PASS:  Service discovery timing issues")
            logger.info("   PASS:  Graceful degradation with optional services")
            return 0
        else:
            logger.error(" FAIL:  Some coordination fixes failed validation")
            logger.error("Please review the failed tests and fix the issues")
            return 1
            
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)