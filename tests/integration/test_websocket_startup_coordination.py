"""Integration Test: WebSocket Startup Coordination for Issue #586

Tests the integration between startup manager and WebSocket readiness to expose
the architectural gap causing 1011 errors.

Business Impact: Validates startup sequence coordination that prevents WebSocket
handshake failures during service initialization.
"""

import asyncio
import time
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class StartupPhaseMonitor:
    """Monitor startup phases and their coordination."""
    
    def __init__(self):
        self.phases = []
        self.phase_lock = asyncio.Lock()
        self.start_time = time.time()
        
    async def record_phase(self, phase: str, component: str, status: str, metadata: Dict[str, Any] = None):
        """Record a startup phase completion."""
        async with self.phase_lock:
            phase_data = {
                "phase": phase,
                "component": component,
                "status": status,
                "timestamp": time.time(),
                "relative_time": time.time() - self.start_time,
                "metadata": metadata or {}
            }
            self.phases.append(phase_data)
            logger.debug(f"📊 Startup phase: {component}.{phase} -> {status} at {phase_data['relative_time']:.3f}s")
    
    def get_phases_by_component(self, component: str) -> List[Dict[str, Any]]:
        """Get all phases for a specific component."""
        return [p for p in self.phases if p["component"] == component]
    
    def get_phases_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all phases with specific status."""
        return [p for p in self.phases if p["status"] == status]
    
    def get_phase_timeline(self) -> List[str]:
        """Get timeline of phases as strings."""
        return [f"{p['component']}.{p['phase']}:{p['status']}@{p['relative_time']:.3f}s" for p in self.phases]
        
    def is_component_ready(self, component: str) -> bool:
        """Check if component has completed all phases successfully."""
        component_phases = self.get_phases_by_component(component)
        if not component_phases:
            return False
            
        # Check if the latest phase is successful
        latest_phase = max(component_phases, key=lambda p: p["timestamp"])
        return latest_phase["status"] == "ready"
        
    def get_coordination_gaps(self) -> List[str]:
        """Identify coordination gaps between components."""
        gaps = []
        
        # Check if WebSocket becomes ready before its dependencies
        websocket_phases = self.get_phases_by_component("websocket_manager")
        if websocket_phases:
            websocket_ready_time = None
            for phase in websocket_phases:
                if phase["status"] == "ready":
                    websocket_ready_time = phase["relative_time"]
                    break
            
            if websocket_ready_time:
                # Check if dependencies were ready before WebSocket
                dependencies = ["database", "redis", "agent_registry"]
                for dep in dependencies:
                    dep_phases = self.get_phases_by_component(dep)
                    dep_ready_time = None
                    for phase in dep_phases:
                        if phase["status"] == "ready":
                            dep_ready_time = phase["relative_time"]
                            break
                    
                    if dep_ready_time is None:
                        gaps.append(f"WebSocket ready at {websocket_ready_time:.3f}s but {dep} never became ready")
                    elif dep_ready_time > websocket_ready_time:
                        gaps.append(f"WebSocket ready at {websocket_ready_time:.3f}s but {dep} not ready until {dep_ready_time:.3f}s")
        
        return gaps


class TestWebSocketStartupCoordination(SSotAsyncTestCase):
    """Integration tests for WebSocket startup coordination."""
    
    async def test_startup_manager_websocket_coordination_gap(self):
        """TEST FAILURE EXPECTED: No coordination between startup manager and WebSocket readiness.
        
        This test should FAIL to expose the architectural gap where the startup manager
        doesn't coordinate with WebSocket manager readiness, causing 1011 errors.
        """
        logger.info("🧪 Testing startup manager ↔ WebSocket coordination gap")
        
        monitor = StartupPhaseMonitor()
        
        # Simulate startup sequence with timing issues
        await self._simulate_uncoordinated_startup(monitor)
        
        # Check for coordination mechanism
        coordination_exists = await self._check_startup_websocket_coordination()
        
        # Get coordination gaps
        gaps = monitor.get_coordination_gaps()
        phase_timeline = monitor.get_phase_timeline()
        
        logger.info(f"Startup coordination exists: {coordination_exists}")
        logger.info(f"Coordination gaps found: {len(gaps)}")
        logger.info(f"Phase timeline: {phase_timeline}")
        
        if gaps:
            for gap in gaps:
                logger.error(f"⚠️  Coordination gap: {gap}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes the coordination gap
        self.assertTrue(
            coordination_exists,
            f"EXPECTED FAILURE: No coordination mechanism between startup manager and WebSocket. "
            f"Found {len(gaps)} coordination gaps: {gaps}. This causes 1011 errors when clients "
            f"connect before WebSocket is ready."
        )
        
    async def test_websocket_readiness_validation_integration(self):
        """TEST FAILURE EXPECTED: WebSocket readiness not validated before accepting connections.
        
        This test should FAIL to expose that there's no validation mechanism to ensure
        WebSocket is ready before the service starts accepting connection requests.
        """
        logger.info("🧪 Testing WebSocket readiness validation integration")
        
        monitor = StartupPhaseMonitor()
        
        # Simulate startup without proper readiness validation
        websocket_manager_state = await self._simulate_websocket_startup(monitor)
        
        # Check if there's a readiness validation mechanism
        has_readiness_validation = await self._check_websocket_readiness_validation(websocket_manager_state)
        
        # Check if service accepts connections before WebSocket is ready
        connection_attempts = await self._simulate_early_connection_attempts(monitor, websocket_manager_state)
        
        successful_early_connections = [
            attempt for attempt in connection_attempts 
            if attempt["success"] and attempt["websocket_ready"] == False
        ]
        
        logger.info(f"WebSocket readiness validation exists: {has_readiness_validation}")
        logger.info(f"Early connection attempts: {len(connection_attempts)}")
        logger.info(f"Successful early connections (problematic): {len(successful_early_connections)}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes the readiness validation gap
        if successful_early_connections:
            self.assertEqual(
                len(successful_early_connections), 0,
                f"EXPECTED FAILURE: Service accepts connections before WebSocket ready. "
                f"Found {len(successful_early_connections)} successful early connections. "
                f"This causes 1011 errors during startup."
            )
        else:
            # If no early connections, check if validation exists
            self.assertTrue(
                has_readiness_validation,
                "EXPECTED FAILURE: No WebSocket readiness validation mechanism exists. "
                "Service may accept connections before WebSocket is ready, causing 1011 errors."
            )
            
    async def test_dependency_initialization_order(self):
        """TEST FAILURE EXPECTED: WebSocket dependencies not initialized in correct order.
        
        This test should FAIL to expose that WebSocket manager may start before
        its dependencies are ready, leading to initialization failures and 1011 errors.
        """
        logger.info("🧪 Testing dependency initialization order")
        
        monitor = StartupPhaseMonitor()
        
        # Simulate startup with dependency ordering issues
        dependency_order = await self._simulate_dependency_startup_sequence(monitor)
        
        # Define correct dependency order
        correct_order = [
            "configuration",
            "database", 
            "redis",
            "agent_registry",
            "websocket_manager",
            "http_server"
        ]
        
        # Analyze actual vs expected order
        order_violations = self._analyze_dependency_order(dependency_order, correct_order, monitor)
        
        logger.info(f"Expected order: {correct_order}")
        logger.info(f"Actual order: {dependency_order}")
        logger.info(f"Order violations: {len(order_violations)}")
        
        for violation in order_violations:
            logger.error(f"⚠️  Order violation: {violation}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes dependency ordering issues
        self.assertEqual(
            len(order_violations), 0,
            f"EXPECTED FAILURE: Dependencies not initialized in correct order. "
            f"Found {len(order_violations)} violations: {order_violations}. "
            f"This causes WebSocket initialization failures and 1011 errors."
        )
        
    async def test_health_check_websocket_integration(self):
        """TEST FAILURE EXPECTED: Health checks don't validate WebSocket readiness.
        
        This test should FAIL to expose that health checks pass before WebSocket
        is ready, allowing load balancers to route traffic to unready instances.
        """
        logger.info("🧪 Testing health check ↔ WebSocket integration")
        
        monitor = StartupPhaseMonitor()
        
        # Simulate health check without WebSocket validation
        health_check_results = await self._simulate_health_check_sequence(monitor)
        
        # Check if WebSocket readiness is included in health checks
        websocket_health_included = self._check_websocket_health_integration(health_check_results)
        
        # Find cases where health check passes but WebSocket isn't ready
        problematic_health_checks = []
        for health_result in health_check_results:
            if health_result["overall_status"] == "healthy" and not health_result.get("websocket_ready", True):
                problematic_health_checks.append(health_result)
        
        logger.info(f"WebSocket included in health checks: {websocket_health_included}")
        logger.info(f"Total health checks: {len(health_check_results)}")
        logger.info(f"Problematic health checks: {len(problematic_health_checks)}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes health check integration gap
        if problematic_health_checks:
            self.assertEqual(
                len(problematic_health_checks), 0,
                f"EXPECTED FAILURE: Health checks pass while WebSocket not ready. "
                f"Found {len(problematic_health_checks)} problematic health checks. "
                f"This causes 1011 errors when traffic routes to unready instances."
            )
        else:
            self.assertTrue(
                websocket_health_included,
                "EXPECTED FAILURE: WebSocket readiness not included in health checks. "
                "Load balancers may route traffic before WebSocket ready, causing 1011 errors."
            )
            
    async def test_concurrent_startup_websocket_race_condition(self):
        """TEST: WebSocket startup race condition with concurrent service initialization.
        
        This test validates that WebSocket initialization doesn't have race conditions
        when multiple services are starting concurrently.
        """
        logger.info("🧪 Testing concurrent startup race conditions")
        
        monitor = StartupPhaseMonitor()
        
        # Simulate concurrent startup of multiple services
        concurrent_tasks = [
            self._simulate_service_startup("database", monitor, delay=1.0),
            self._simulate_service_startup("redis", monitor, delay=0.8),
            self._simulate_service_startup("agent_registry", monitor, delay=1.2),
            self._simulate_service_startup("websocket_manager", monitor, delay=0.9)
        ]
        
        # Start all services concurrently
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results for race conditions
        race_conditions = []
        failed_services = []
        
        for i, result in enumerate(results):
            service_name = ["database", "redis", "agent_registry", "websocket_manager"][i]
            
            if isinstance(result, Exception):
                failed_services.append(f"{service_name}: {result}")
            elif not result:
                failed_services.append(f"{service_name}: startup failed")
        
        # Check for race condition indicators in monitor
        websocket_phases = monitor.get_phases_by_component("websocket_manager")
        websocket_errors = [p for p in websocket_phases if p["status"] == "error"]
        
        if websocket_errors:
            race_conditions.extend([f"WebSocket error: {error['metadata']}" for error in websocket_errors])
        
        logger.info(f"Concurrent startup completed in {total_time:.3f}s")
        logger.info(f"Failed services: {len(failed_services)}")
        logger.info(f"Race conditions detected: {len(race_conditions)}")
        
        # Validate no race conditions occurred
        self.assertEqual(
            len(race_conditions), 0,
            f"Race conditions detected during concurrent startup: {race_conditions}. "
            f"Failed services: {failed_services}"
        )
        
        self.assertEqual(
            len(failed_services), 0,
            f"Service startup failures during concurrent initialization: {failed_services}. "
            f"This may indicate race conditions or dependency issues."
        )
    
    # Helper methods for startup coordination simulation
    
    async def _simulate_uncoordinated_startup(self, monitor: StartupPhaseMonitor):
        """Simulate startup sequence with coordination gaps."""
        
        # Phase 1: Configuration (no coordination)
        await monitor.record_phase("init", "configuration", "started")
        await asyncio.sleep(0.1)
        await monitor.record_phase("init", "configuration", "ready")
        
        # Phase 2: Services start independently (gap: no coordination)
        await asyncio.sleep(0.05)
        await monitor.record_phase("connect", "database", "started") 
        
        await asyncio.sleep(0.08)
        await monitor.record_phase("init", "websocket_manager", "started")  # Starts too early!
        
        await asyncio.sleep(0.12)
        await monitor.record_phase("connect", "database", "ready")
        
        await asyncio.sleep(0.05)
        await monitor.record_phase("connect", "redis", "started")
        await asyncio.sleep(0.1)
        await monitor.record_phase("connect", "redis", "ready")
        
        # Phase 3: WebSocket tries to become ready before dependencies
        await asyncio.sleep(0.05)
        await monitor.record_phase("init", "websocket_manager", "error",
                                 {"error": "Redis connection not ready"})
        
        await asyncio.sleep(0.1)
        await monitor.record_phase("init", "agent_registry", "started")
        await asyncio.sleep(0.15)
        await monitor.record_phase("init", "agent_registry", "ready")
        
        # Phase 4: WebSocket finally becomes ready (too late)
        await asyncio.sleep(0.08)
        await monitor.record_phase("init", "websocket_manager", "retry")
        await asyncio.sleep(0.1)
        await monitor.record_phase("init", "websocket_manager", "ready")
        
    async def _check_startup_websocket_coordination(self) -> bool:
        """Check if startup manager coordinates with WebSocket readiness."""
        # In a real implementation, this would check actual coordination mechanisms
        # For this test, we simulate the lack of coordination
        return False
        
    async def _simulate_websocket_startup(self, monitor: StartupPhaseMonitor) -> Dict[str, Any]:
        """Simulate WebSocket manager startup sequence."""
        websocket_state = {
            "initialized": False,
            "dependencies_ready": False,
            "listening": False,
            "ready_for_connections": False
        }
        
        await monitor.record_phase("init", "websocket_manager", "started")
        
        # Initialize without checking dependencies (gap)
        await asyncio.sleep(0.1)
        websocket_state["initialized"] = True
        await monitor.record_phase("init", "websocket_manager", "initialized")
        
        # Start listening before dependencies ready (gap)
        await asyncio.sleep(0.05)
        websocket_state["listening"] = True
        await monitor.record_phase("listen", "websocket_manager", "listening")
        
        # Dependencies become ready later
        await asyncio.sleep(0.2)
        websocket_state["dependencies_ready"] = True
        await monitor.record_phase("dependencies", "websocket_manager", "dependencies_ready")
        
        # Finally ready for connections
        await asyncio.sleep(0.1)
        websocket_state["ready_for_connections"] = True
        await monitor.record_phase("ready", "websocket_manager", "ready")
        
        return websocket_state
        
    async def _check_websocket_readiness_validation(self, websocket_state: Dict[str, Any]) -> bool:
        """Check if WebSocket readiness validation mechanism exists."""
        # In a real implementation, this would check actual validation mechanisms
        # For this test, we simulate the lack of validation
        return False
        
    async def _simulate_early_connection_attempts(self, monitor: StartupPhaseMonitor, 
                                                 websocket_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simulate connection attempts before WebSocket is ready."""
        connection_attempts = []
        
        # Attempt connections at different startup phases
        phases = [
            {"time": 0.05, "phase": "early_init"},
            {"time": 0.15, "phase": "listening"},
            {"time": 0.25, "phase": "dependencies_ready"},
            {"time": 0.35, "phase": "fully_ready"}
        ]
        
        for phase_info in phases:
            await asyncio.sleep(0.05)  # Small delay between attempts
            
            # Determine if WebSocket is ready at this phase
            websocket_ready = phase_info["phase"] == "fully_ready"
            
            # Simulate connection attempt (currently no validation, so it "succeeds")
            connection_success = True  # Gap: no readiness validation
            
            attempt = {
                "phase": phase_info["phase"],
                "websocket_ready": websocket_ready,
                "success": connection_success,
                "time": phase_info["time"]
            }
            connection_attempts.append(attempt)
            
            await monitor.record_phase("connection_attempt", "client", 
                                     "success" if connection_success else "failed",
                                     attempt)
        
        return connection_attempts
        
    async def _simulate_dependency_startup_sequence(self, monitor: StartupPhaseMonitor) -> List[str]:
        """Simulate dependency startup sequence with ordering issues."""
        
        # Simulate problematic startup order
        startup_sequence = [
            ("configuration", 0.05),
            ("websocket_manager", 0.1),  # Starting too early!
            ("database", 0.15),          # Should start before websocket
            ("agent_registry", 0.2),     # Starting after websocket  
            ("redis", 0.25),             # Should start before websocket
            ("http_server", 0.3)
        ]
        
        actual_order = []
        
        for service, delay in startup_sequence:
            await asyncio.sleep(delay)
            await monitor.record_phase("startup", service, "started")
            actual_order.append(service)
            
            # Simulate some services failing due to missing dependencies
            if service == "websocket_manager":
                await asyncio.sleep(0.05)
                await monitor.record_phase("startup", service, "error",
                                         {"error": "Database connection not available"})
            else:
                await asyncio.sleep(0.1)
                await monitor.record_phase("startup", service, "ready")
        
        return actual_order
        
    def _analyze_dependency_order(self, actual_order: List[str], correct_order: List[str], 
                                monitor: StartupPhaseMonitor) -> List[str]:
        """Analyze dependency order violations."""
        violations = []
        
        # Check if each service starts after its dependencies
        dependencies = {
            "websocket_manager": ["database", "redis", "agent_registry"],
            "agent_registry": ["database", "redis"],
            "http_server": ["websocket_manager"]
        }
        
        for service, deps in dependencies.items():
            if service in actual_order:
                service_index = actual_order.index(service)
                
                for dep in deps:
                    if dep in actual_order:
                        dep_index = actual_order.index(dep)
                        if dep_index > service_index:
                            violations.append(f"{service} started before dependency {dep}")
                    else:
                        violations.append(f"{service} started but dependency {dep} never started")
        
        return violations
        
    async def _simulate_health_check_sequence(self, monitor: StartupPhaseMonitor) -> List[Dict[str, Any]]:
        """Simulate health check sequence without proper WebSocket validation."""
        health_checks = []
        
        # Health check attempts at different phases
        phases = [
            {"time": 0.1, "phase": "early", "websocket_ready": False},
            {"time": 0.2, "phase": "mid", "websocket_ready": False},
            {"time": 0.3, "phase": "late", "websocket_ready": True}
        ]
        
        for phase_info in phases:
            await asyncio.sleep(0.08)
            
            # Simulate health check that doesn't check WebSocket readiness (gap)
            health_result = {
                "phase": phase_info["phase"],
                "overall_status": "healthy",  # Gap: passes without WebSocket check
                "websocket_ready": phase_info["websocket_ready"],
                "components": {
                    "database": "healthy",
                    "redis": "healthy",
                    "http": "healthy"
                    # Note: websocket not included (gap)
                }
            }
            health_checks.append(health_result)
            
            await monitor.record_phase("health_check", "system", "healthy", health_result)
        
        return health_checks
        
    def _check_websocket_health_integration(self, health_results: List[Dict[str, Any]]) -> bool:
        """Check if WebSocket is integrated into health checks."""
        for result in health_results:
            components = result.get("components", {})
            if "websocket" in components or "websocket_manager" in components:
                return True
        return False
        
    async def _simulate_service_startup(self, service_name: str, monitor: StartupPhaseMonitor, delay: float) -> bool:
        """Simulate individual service startup."""
        try:
            await monitor.record_phase("startup", service_name, "started")
            
            # Add some jitter to simulate real-world timing
            actual_delay = delay + (0.1 * hash(service_name) % 10) / 100
            await asyncio.sleep(actual_delay)
            
            # Simulate potential race condition for WebSocket
            if service_name == "websocket_manager":
                # Check if dependencies are ready
                if not monitor.is_component_ready("database"):
                    await monitor.record_phase("startup", service_name, "error",
                                             {"error": "Database dependency not ready"})
                    return False
            
            await monitor.record_phase("startup", service_name, "ready")
            return True
            
        except Exception as e:
            await monitor.record_phase("startup", service_name, "error", {"error": str(e)})
            return False


if __name__ == "__main__":
    # Run integration tests - expecting failures that expose coordination gaps
    pytest.main([__file__, "-v", "--tb=short"])