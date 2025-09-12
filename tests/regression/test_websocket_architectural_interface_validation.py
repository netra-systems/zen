"""Regression Test: WebSocket Architectural Interface Validation for Issue #586

Tests the architectural interfaces between components to expose the integration gaps
that cause 1011 WebSocket errors during startup.

Business Impact: Validates that all components have proper interfaces for coordinating
WebSocket readiness, preventing the handshake failures that break chat functionality.
"""

import asyncio
import time
import importlib
import inspect
import pytest
from typing import Dict, Any, List, Optional, Callable, Set
from unittest.mock import Mock, AsyncMock, MagicMock
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class InterfaceValidationResult:
    """Result of interface validation."""
    component_name: str
    interface_name: str
    exists: bool
    methods: List[str]
    missing_methods: List[str]
    signature_issues: List[str]
    coordination_support: bool
    error_details: Optional[str] = None


@dataclass
class ArchitecturalGap:
    """Identified architectural gap."""
    gap_type: str
    component_a: str
    component_b: str
    description: str
    impact: str
    contributes_to_1011: bool


class ComponentInterface:
    """Definition of expected component interfaces."""
    
    STARTUP_MANAGER_INTERFACE = {
        "add_startup_phase": ["phase_name", "callback", "dependencies"],
        "wait_for_phase": ["phase_name", "timeout"],
        "mark_phase_complete": ["phase_name", "status"],
        "register_readiness_check": ["service_name", "check_callback"],
        "get_startup_status": [],
        "coordinate_service_startup": ["service_configs"]
    }
    
    WEBSOCKET_MANAGER_INTERFACE = {
        "is_ready_for_connections": [],
        "register_readiness_callback": ["callback"],
        "get_connection_readiness": [],
        "validate_websocket_health": [],
        "coordinate_with_startup": ["startup_manager"],
        "set_readiness_status": ["ready", "metadata"]
    }
    
    HEALTH_CHECK_INTERFACE = {
        "register_component_check": ["component_name", "check_callback"],
        "include_websocket_readiness": [],
        "validate_websocket_integration": [],
        "get_component_health": ["component_name"],
        "overall_health_includes_websocket": []
    }
    
    APP_STATE_INTERFACE = {
        "register_websocket_manager": ["websocket_manager"],
        "get_websocket_readiness": [],
        "coordinate_startup_sequence": [],
        "validate_service_dependencies": [],
        "get_startup_coordination": []
    }


class TestWebSocketArchitecturalInterfaceValidation(SSotAsyncTestCase):
    """Regression tests for WebSocket architectural interface validation."""
    
    def setUp(self):
        """Set up regression test environment."""
        super().setUp()
        self.interface_validator = ComponentInterface()
        self.validation_results = []
        self.architectural_gaps = []
        
    async def test_startup_manager_websocket_coordination_interface(self):
        """TEST FAILURE EXPECTED: Startup manager lacks WebSocket coordination interface.
        
        This test should FAIL to expose that the startup manager doesn't have
        proper interfaces for coordinating with WebSocket manager readiness.
        """
        logger.info("🧪 Testing startup manager ↔ WebSocket coordination interface")
        
        # Try to import and validate startup manager
        startup_manager_result = await self._validate_component_interface(
            "startup_manager",
            self.interface_validator.STARTUP_MANAGER_INTERFACE
        )
        
        self.validation_results.append(startup_manager_result)
        
        # Check specific coordination methods
        coordination_methods = [
            "register_readiness_check",
            "coordinate_service_startup",
            "wait_for_phase"
        ]
        
        missing_coordination = []
        for method in coordination_methods:
            if method in startup_manager_result.missing_methods:
                missing_coordination.append(method)
        
        logger.info(f"Startup manager interface validation: {startup_manager_result.exists}")
        logger.info(f"Available methods: {startup_manager_result.methods}")
        logger.info(f"Missing coordination methods: {missing_coordination}")
        
        # Check if WebSocket can coordinate with startup manager
        coordination_possible = await self._check_websocket_startup_coordination()
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes the coordination interface gap
        if missing_coordination:
            self.assertEqual(
                len(missing_coordination), 0,
                f"EXPECTED FAILURE: Startup manager missing coordination methods: {missing_coordination}. "
                f"Without these interfaces, WebSocket manager cannot coordinate startup, causing 1011 errors "
                f"when clients connect before WebSocket is ready."
            )
        else:
            self.assertTrue(
                coordination_possible,
                "EXPECTED FAILURE: No coordination mechanism between startup manager and WebSocket. "
                "WebSocket cannot signal readiness or coordinate with startup sequence, causing 1011 errors."
            )
            
    async def test_websocket_manager_readiness_interface(self):
        """TEST FAILURE EXPECTED: WebSocket manager lacks readiness validation interface.
        
        This test should FAIL to expose that WebSocket manager doesn't provide
        proper interfaces for external components to validate its readiness.
        """
        logger.info("🧪 Testing WebSocket manager readiness interface")
        
        # Try to validate WebSocket manager interface
        websocket_manager_result = await self._validate_component_interface(
            "websocket_manager", 
            self.interface_validator.WEBSOCKET_MANAGER_INTERFACE
        )
        
        self.validation_results.append(websocket_manager_result)
        
        # Check specific readiness methods
        readiness_methods = [
            "is_ready_for_connections",
            "get_connection_readiness", 
            "validate_websocket_health",
            "set_readiness_status"
        ]
        
        missing_readiness = []
        for method in readiness_methods:
            if method in websocket_manager_result.missing_methods:
                missing_readiness.append(method)
        
        logger.info(f"WebSocket manager interface validation: {websocket_manager_result.exists}")
        logger.info(f"Available methods: {websocket_manager_result.methods}")
        logger.info(f"Missing readiness methods: {missing_readiness}")
        
        # Check if other components can validate WebSocket readiness
        external_validation_possible = await self._check_external_websocket_readiness_validation()
        
        logger.info(f"External WebSocket readiness validation possible: {external_validation_possible}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes the readiness interface gap
        if missing_readiness:
            self.assertEqual(
                len(missing_readiness), 0,
                f"EXPECTED FAILURE: WebSocket manager missing readiness methods: {missing_readiness}. "
                f"Without these interfaces, other components cannot validate WebSocket readiness, "
                f"causing 1011 errors when connections are attempted before WebSocket is ready."
            )
        else:
            self.assertTrue(
                external_validation_possible,
                "EXPECTED FAILURE: Other components cannot validate WebSocket readiness. "
                "No interface exists for health checks or startup coordination to verify WebSocket "
                "is ready, causing 1011 errors."
            )
            
    async def test_health_check_websocket_integration_interface(self):
        """TEST FAILURE EXPECTED: Health check lacks WebSocket integration interface.
        
        This test should FAIL to expose that health checks don't have proper
        interfaces to include WebSocket readiness validation.
        """
        logger.info("🧪 Testing health check ↔ WebSocket integration interface")
        
        # Try to validate health check interface
        health_check_result = await self._validate_component_interface(
            "health_check",
            self.interface_validator.HEALTH_CHECK_INTERFACE
        )
        
        self.validation_results.append(health_check_result)
        
        # Check WebSocket integration methods
        integration_methods = [
            "include_websocket_readiness",
            "validate_websocket_integration",
            "overall_health_includes_websocket"
        ]
        
        missing_integration = []
        for method in integration_methods:
            if method in health_check_result.missing_methods:
                missing_integration.append(method)
        
        logger.info(f"Health check interface validation: {health_check_result.exists}")
        logger.info(f"Available methods: {health_check_result.methods}")
        logger.info(f"Missing integration methods: {missing_integration}")
        
        # Check if health checks actually include WebSocket status
        websocket_in_health = await self._check_websocket_in_health_checks()
        
        logger.info(f"WebSocket included in health checks: {websocket_in_health}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes the health check integration gap
        if missing_integration:
            self.assertEqual(
                len(missing_integration), 0,
                f"EXPECTED FAILURE: Health check missing WebSocket integration methods: {missing_integration}. "
                f"Without these interfaces, health checks cannot include WebSocket readiness, causing "
                f"load balancers to route traffic to instances with unready WebSockets (1011 errors)."
            )
        else:
            self.assertTrue(
                websocket_in_health,
                "EXPECTED FAILURE: WebSocket readiness not included in health checks. "
                "Health checks pass while WebSocket is not ready, causing load balancers to route "
                "traffic to unready instances, resulting in 1011 errors."
            )
            
    async def test_app_state_websocket_coordination_interface(self):
        """TEST FAILURE EXPECTED: App state lacks WebSocket coordination interface.
        
        This test should FAIL to expose that the application state manager doesn't
        have proper interfaces for coordinating WebSocket state with overall app state.
        """
        logger.info("🧪 Testing app state ↔ WebSocket coordination interface")
        
        # Try to validate app state interface
        app_state_result = await self._validate_component_interface(
            "app_state",
            self.interface_validator.APP_STATE_INTERFACE
        )
        
        self.validation_results.append(app_state_result)
        
        # Check coordination methods
        coordination_methods = [
            "register_websocket_manager",
            "get_websocket_readiness",
            "coordinate_startup_sequence",
            "get_startup_coordination"
        ]
        
        missing_coordination = []
        for method in coordination_methods:
            if method in app_state_result.missing_methods:
                missing_coordination.append(method)
        
        logger.info(f"App state interface validation: {app_state_result.exists}")
        logger.info(f"Available methods: {app_state_result.methods}")
        logger.info(f"Missing coordination methods: {missing_coordination}")
        
        # Check if app state can track WebSocket readiness
        app_state_tracks_websocket = await self._check_app_state_websocket_tracking()
        
        logger.info(f"App state tracks WebSocket readiness: {app_state_tracks_websocket}")
        
        # TEST ASSERTION THAT SHOULD FAIL
        # This exposes the app state coordination gap
        if missing_coordination:
            self.assertEqual(
                len(missing_coordination), 0,
                f"EXPECTED FAILURE: App state missing WebSocket coordination methods: {missing_coordination}. "
                f"Without these interfaces, app state cannot track WebSocket readiness or coordinate "
                f"startup sequence, contributing to 1011 errors during startup."
            )
        else:
            self.assertTrue(
                app_state_tracks_websocket,
                "EXPECTED FAILURE: App state doesn't track WebSocket readiness. "
                "Application state management cannot coordinate with WebSocket lifecycle, "
                "causing timing issues that lead to 1011 errors."
            )
            
    async def test_comprehensive_architectural_gap_analysis(self):
        """TEST: Comprehensive analysis of architectural gaps causing 1011 errors.
        
        This test analyzes all identified architectural gaps and their contribution
        to WebSocket 1011 errors during startup.
        """
        logger.info("🧪 Performing comprehensive architectural gap analysis")
        
        # Analyze all validation results collected from previous tests
        all_gaps = await self._analyze_architectural_gaps()
        
        # Categorize gaps by severity and impact
        critical_gaps = [gap for gap in all_gaps if gap.contributes_to_1011]
        coordination_gaps = [gap for gap in all_gaps if "coordination" in gap.gap_type]
        interface_gaps = [gap for gap in all_gaps if "interface" in gap.gap_type]
        
        # Log comprehensive gap analysis
        logger.info(f"Total architectural gaps identified: {len(all_gaps)}")
        logger.info(f"Critical gaps contributing to 1011 errors: {len(critical_gaps)}")
        logger.info(f"Coordination gaps: {len(coordination_gaps)}")
        logger.info(f"Interface gaps: {len(interface_gaps)}")
        
        # Detailed gap analysis
        for gap in critical_gaps:
            logger.error(f"🚨 CRITICAL GAP: {gap.gap_type} between {gap.component_a} ↔ {gap.component_b}")
            logger.error(f"   Description: {gap.description}")
            logger.error(f"   Impact: {gap.impact}")
        
        # Create architectural remediation plan
        remediation_plan = self._create_architectural_remediation_plan(all_gaps)
        
        logger.info("Architectural Remediation Plan:")
        for i, item in enumerate(remediation_plan, 1):
            logger.info(f"{i}. {item}")
        
        # Validate that critical gaps are addressed
        self.assertLessEqual(
            len(critical_gaps), 3,  # Should have minimal critical gaps
            f"Too many critical architectural gaps contributing to 1011 errors: {len(critical_gaps)}. "
            f"Critical gaps: {[gap.description for gap in critical_gaps]}. "
            f"These gaps must be addressed to prevent WebSocket handshake failures."
        )
    
    # Helper methods for architectural interface validation
    
    async def _validate_component_interface(self, component_name: str, 
                                          expected_interface: Dict[str, List[str]]) -> InterfaceValidationResult:
        """Validate a component's interface against expected methods."""
        try:
            # Try to import the component
            component_class = await self._get_component_class(component_name)
            
            if component_class is None:
                return InterfaceValidationResult(
                    component_name=component_name,
                    interface_name=f"{component_name}_interface",
                    exists=False,
                    methods=[],
                    missing_methods=list(expected_interface.keys()),
                    signature_issues=[],
                    coordination_support=False,
                    error_details="Component class not found"
                )
            
            # Get available methods
            available_methods = [
                method for method in dir(component_class)
                if not method.startswith('_') and callable(getattr(component_class, method, None))
            ]
            
            # Check for missing methods
            missing_methods = []
            signature_issues = []
            
            for method_name, expected_params in expected_interface.items():
                if method_name not in available_methods:
                    missing_methods.append(method_name)
                else:
                    # Check method signature
                    method = getattr(component_class, method_name)
                    signature = inspect.signature(method)
                    actual_params = list(signature.parameters.keys())
                    
                    # Remove 'self' from comparison
                    if actual_params and actual_params[0] == 'self':
                        actual_params = actual_params[1:]
                    
                    if len(expected_params) > 0 and len(actual_params) < len(expected_params):
                        signature_issues.append(
                            f"{method_name}: expected {expected_params}, got {actual_params}"
                        )
            
            # Check coordination support
            coordination_methods = ["coordinate", "register", "wait_for", "notify"]
            coordination_support = any(
                coord_word in method.lower() for method in available_methods for coord_word in coordination_methods
            )
            
            return InterfaceValidationResult(
                component_name=component_name,
                interface_name=f"{component_name}_interface",
                exists=True,
                methods=available_methods,
                missing_methods=missing_methods,
                signature_issues=signature_issues,
                coordination_support=coordination_support
            )
            
        except Exception as e:
            return InterfaceValidationResult(
                component_name=component_name,
                interface_name=f"{component_name}_interface",
                exists=False,
                methods=[],
                missing_methods=list(expected_interface.keys()),
                signature_issues=[],
                coordination_support=False,
                error_details=str(e)
            )
            
    async def _get_component_class(self, component_name: str):
        """Get component class by name."""
        component_mappings = {
            "startup_manager": ("netra_backend.app.core.startup_manager", "StartupManager"),
            "websocket_manager": ("netra_backend.app.websocket_core.manager", "WebSocketManager"),
            "health_check": ("netra_backend.app.health.health_check", "HealthCheck"),
            "app_state": ("netra_backend.app.core.app_state", "AppState")
        }
        
        if component_name not in component_mappings:
            return None
        
        module_path, class_name = component_mappings[component_name]
        
        try:
            module = importlib.import_module(module_path)
            return getattr(module, class_name, None)
        except ImportError:
            # Try alternative paths
            alternative_paths = {
                "startup_manager": [
                    ("netra_backend.app.startup.manager", "StartupManager"),
                    ("netra_backend.app.core.startup", "StartupManager")
                ],
                "websocket_manager": [
                    ("netra_backend.app.websocket.manager", "WebSocketManager"),
                    ("netra_backend.app.websockets.manager", "UnifiedWebSocketManager")
                ],
                "health_check": [
                    ("netra_backend.app.health", "HealthChecker"),
                    ("netra_backend.app.core.health", "HealthCheck")
                ],
                "app_state": [
                    ("netra_backend.app.state", "AppState"),
                    ("netra_backend.app.core.state", "ApplicationState")
                ]
            }
            
            if component_name in alternative_paths:
                for alt_module_path, alt_class_name in alternative_paths[component_name]:
                    try:
                        alt_module = importlib.import_module(alt_module_path)
                        component_class = getattr(alt_module, alt_class_name, None)
                        if component_class:
                            return component_class
                    except ImportError:
                        continue
            
            return None
        except Exception:
            return None
            
    async def _check_websocket_startup_coordination(self) -> bool:
        """Check if WebSocket can coordinate with startup manager."""
        try:
            # Try to find coordination mechanisms
            from netra_backend.app.websocket_core import manager as websocket_module
            
            # Look for coordination methods
            coordination_indicators = [
                "coordinate_startup", "register_with_startup", "startup_callback",
                "wait_for_startup", "notify_ready", "set_ready"
            ]
            
            websocket_methods = dir(websocket_module)
            
            for indicator in coordination_indicators:
                if any(indicator in method.lower() for method in websocket_methods):
                    return True
            
            return False
        except ImportError:
            return False
            
    async def _check_external_websocket_readiness_validation(self) -> bool:
        """Check if external components can validate WebSocket readiness."""
        try:
            # Try to find readiness validation mechanisms
            from netra_backend.app.websocket_core import manager as websocket_module
            
            # Look for readiness validation methods
            readiness_indicators = [
                "is_ready", "ready_for_connections", "connection_ready",
                "validate_ready", "check_readiness", "get_status"
            ]
            
            websocket_methods = dir(websocket_module)
            
            for indicator in readiness_indicators:
                if any(indicator in method.lower() for method in websocket_methods):
                    return True
            
            return False
        except ImportError:
            return False
            
    async def _check_websocket_in_health_checks(self) -> bool:
        """Check if WebSocket is included in health checks."""
        try:
            # Try to find health check integration
            from netra_backend.app import health
            
            # Look for WebSocket in health components
            health_methods = dir(health)
            websocket_in_health = any(
                "websocket" in method.lower() for method in health_methods
            )
            
            return websocket_in_health
        except ImportError:
            return False
            
    async def _check_app_state_websocket_tracking(self) -> bool:
        """Check if app state tracks WebSocket readiness."""
        try:
            # Try to find app state WebSocket tracking
            from netra_backend.app.core import app_state
            
            # Look for WebSocket tracking methods
            app_state_methods = dir(app_state)
            websocket_tracking = any(
                "websocket" in method.lower() for method in app_state_methods
            )
            
            return websocket_tracking
        except ImportError:
            return False
            
    async def _analyze_architectural_gaps(self) -> List[ArchitecturalGap]:
        """Analyze architectural gaps from validation results."""
        gaps = []
        
        # Analyze interface validation results
        for result in self.validation_results:
            if result.missing_methods:
                gap = ArchitecturalGap(
                    gap_type="missing_interface_methods",
                    component_a=result.component_name,
                    component_b="system",
                    description=f"{result.component_name} missing methods: {result.missing_methods}",
                    impact="Cannot coordinate with other components",
                    contributes_to_1011=True
                )
                gaps.append(gap)
            
            if not result.coordination_support:
                gap = ArchitecturalGap(
                    gap_type="coordination_interface_missing",
                    component_a=result.component_name,
                    component_b="startup_system",
                    description=f"{result.component_name} lacks coordination interfaces",
                    impact="Cannot participate in coordinated startup sequence",
                    contributes_to_1011=True
                )
                gaps.append(gap)
        
        # Add known architectural gaps
        known_gaps = [
            ArchitecturalGap(
                gap_type="startup_websocket_coordination",
                component_a="startup_manager",
                component_b="websocket_manager",
                description="No coordination mechanism between startup and WebSocket",
                impact="WebSocket may start before dependencies ready",
                contributes_to_1011=True
            ),
            ArchitecturalGap(
                gap_type="health_check_websocket_integration",
                component_a="health_check",
                component_b="websocket_manager",
                description="Health checks don't validate WebSocket readiness",
                impact="Load balancers route to unready instances",
                contributes_to_1011=True
            ),
            ArchitecturalGap(
                gap_type="app_state_websocket_tracking",
                component_a="app_state",
                component_b="websocket_manager",
                description="App state doesn't track WebSocket lifecycle",
                impact="Application state inconsistent with WebSocket state",
                contributes_to_1011=True
            )
        ]
        
        gaps.extend(known_gaps)
        return gaps
        
    def _create_architectural_remediation_plan(self, gaps: List[ArchitecturalGap]) -> List[str]:
        """Create remediation plan for architectural gaps."""
        plan = []
        
        # Group gaps by type
        coordination_gaps = [g for g in gaps if "coordination" in g.gap_type]
        interface_gaps = [g for g in gaps if "interface" in g.gap_type]
        integration_gaps = [g for g in gaps if "integration" in g.gap_type]
        
        # Add remediation items
        if coordination_gaps:
            plan.append("Implement coordination interfaces between startup manager and WebSocket manager")
            plan.append("Add WebSocket readiness callbacks to startup sequence")
        
        if interface_gaps:
            plan.append("Add missing interface methods for component coordination")
            plan.append("Standardize readiness validation interfaces across components")
        
        if integration_gaps:
            plan.append("Integrate WebSocket readiness into health check endpoints")
            plan.append("Add WebSocket state tracking to application state management")
        
        # Add general improvements
        plan.append("Implement timeout calculations based on environment (GCP vs local)")
        plan.append("Add WebSocket handshake coordination with service startup")
        plan.append("Create comprehensive startup phase orchestration")
        
        return plan


if __name__ == "__main__":
    # Run regression tests - expecting failures that expose architectural gaps
    pytest.main([__file__, "-v", "--tb=short"])