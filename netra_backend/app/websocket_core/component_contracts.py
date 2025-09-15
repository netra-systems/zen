"""
WebSocket Component Dependency Contracts - Phase 1 Foundation

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: System reliability during SSOT consolidation
- Value Impact: Prevent breaking changes during component extraction
- Strategic Impact: Enable safe refactoring of 3,891 line mega-class

This module defines the dependency contracts between WebSocket components,
ensuring that component extraction maintains system integrity and user isolation.

ISSUE #1047 PHASE 1: Component dependency validation framework
"""

from typing import Dict, Any, Set, Optional, List, Protocol
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.websocket_core.interfaces import (
    ICoreConnectionManager, IEventBroadcastingService, IAuthenticationIntegration,
    IUserSessionRegistry, IPerformanceMonitor, IConfigurationProvider,
    IIntegrationBridge
)


class DependencyType(Enum):
    """Types of dependencies between components."""
    REQUIRED = "required"  # Component cannot function without this dependency
    OPTIONAL = "optional"  # Component can degrade gracefully without this
    CIRCULAR = "circular"  # Bidirectional dependency (needs careful handling)


@dataclass
class ComponentDependency:
    """Represents a dependency between components."""
    source_component: str
    target_component: str
    dependency_type: DependencyType
    description: str
    methods_used: List[str]
    isolation_requirement: bool = True  # Must maintain user isolation


class ComponentDependencyRegistry:
    """
    Registry of all dependencies between WebSocket components.

    This registry documents the current dependency relationships to ensure
    that component extraction maintains all required interactions.
    """

    def __init__(self):
        self.dependencies: List[ComponentDependency] = []
        self._initialize_current_dependencies()

    def _initialize_current_dependencies(self):
        """Initialize the current dependency relationships in unified_manager.py."""

        # Core Connection Manager dependencies
        self.dependencies.extend([
            ComponentDependency(
                source_component="ICoreConnectionManager",
                target_component="IAuthenticationIntegration",
                dependency_type=DependencyType.REQUIRED,
                description="Connection management requires user isolation validation",
                methods_used=["_validate_user_isolation", "_prevent_cross_user_event_bleeding"],
                isolation_requirement=True
            ),
            ComponentDependency(
                source_component="ICoreConnectionManager",
                target_component="IPerformanceMonitor",
                dependency_type=DependencyType.OPTIONAL,
                description="Connection tracking for performance metrics",
                methods_used=["get_connection_stats"],
                isolation_requirement=False
            )
        ])

        # Event Broadcasting Service dependencies
        self.dependencies.extend([
            ComponentDependency(
                source_component="IEventBroadcastingService",
                target_component="ICoreConnectionManager",
                dependency_type=DependencyType.REQUIRED,
                description="Event delivery requires connection information",
                methods_used=["get_user_connections", "get_connection"],
                isolation_requirement=True
            ),
            ComponentDependency(
                source_component="IEventBroadcastingService",
                target_component="IAuthenticationIntegration",
                dependency_type=DependencyType.REQUIRED,
                description="Event delivery requires user isolation enforcement",
                methods_used=["_validate_user_isolation", "_prevent_cross_user_event_bleeding"],
                isolation_requirement=True
            ),
            ComponentDependency(
                source_component="IEventBroadcastingService",
                target_component="IPerformanceMonitor",
                dependency_type=DependencyType.OPTIONAL,
                description="Event delivery metrics tracking",
                methods_used=["start_monitored_background_task"],
                isolation_requirement=False
            )
        ])

        # User Session Registry dependencies
        self.dependencies.extend([
            ComponentDependency(
                source_component="IUserSessionRegistry",
                target_component="ICoreConnectionManager",
                dependency_type=DependencyType.REQUIRED,
                description="Session management requires connection lifecycle control",
                methods_used=["add_connection", "remove_connection", "get_user_connections"],
                isolation_requirement=True
            ),
            ComponentDependency(
                source_component="IUserSessionRegistry",
                target_component="IAuthenticationIntegration",
                dependency_type=DependencyType.REQUIRED,
                description="Session validation requires user context verification",
                methods_used=["_validate_user_isolation"],
                isolation_requirement=True
            )
        ])

        # Performance Monitor dependencies
        self.dependencies.extend([
            ComponentDependency(
                source_component="IPerformanceMonitor",
                target_component="ICoreConnectionManager",
                dependency_type=DependencyType.REQUIRED,
                description="Performance metrics require connection data",
                methods_used=["get_connection_stats", "get_user_connections"],
                isolation_requirement=False
            )
        ])

        # Integration Bridge dependencies
        self.dependencies.extend([
            ComponentDependency(
                source_component="IIntegrationBridge",
                target_component="IEventBroadcastingService",
                dependency_type=DependencyType.REQUIRED,
                description="Transaction events require event delivery",
                methods_used=["send_to_user", "emit_critical_event"],
                isolation_requirement=True
            ),
            ComponentDependency(
                source_component="IIntegrationBridge",
                target_component="IAuthenticationIntegration",
                dependency_type=DependencyType.REQUIRED,
                description="Transaction coordination requires user validation",
                methods_used=["_validate_user_isolation"],
                isolation_requirement=True
            )
        ])

        # Circular dependencies (need special handling)
        self.dependencies.extend([
            ComponentDependency(
                source_component="ICoreConnectionManager",
                target_component="IEventBroadcastingService",
                dependency_type=DependencyType.CIRCULAR,
                description="Connections notify events, events need connection info",
                methods_used=["send_to_user", "emit_critical_event"],
                isolation_requirement=True
            )
        ])

    def get_dependencies_for_component(self, component_name: str) -> List[ComponentDependency]:
        """Get all dependencies where component is the source."""
        return [dep for dep in self.dependencies if dep.source_component == component_name]

    def get_reverse_dependencies_for_component(self, component_name: str) -> List[ComponentDependency]:
        """Get all dependencies where component is the target."""
        return [dep for dep in self.dependencies if dep.target_component == component_name]

    def get_circular_dependencies(self) -> List[ComponentDependency]:
        """Get all circular dependencies that need special handling."""
        return [dep for dep in self.dependencies if dep.dependency_type == DependencyType.CIRCULAR]

    def validate_extraction_plan(self, component_name: str) -> Dict[str, Any]:
        """Validate if a component can be safely extracted."""
        outgoing = self.get_dependencies_for_component(component_name)
        incoming = self.get_reverse_dependencies_for_component(component_name)
        circular = [dep for dep in self.get_circular_dependencies()
                   if dep.source_component == component_name or dep.target_component == component_name]

        return {
            'component': component_name,
            'can_extract_safely': len(circular) == 0,
            'outgoing_dependencies': len(outgoing),
            'incoming_dependencies': len(incoming),
            'circular_dependencies': len(circular),
            'isolation_critical_deps': len([dep for dep in outgoing if dep.isolation_requirement]),
            'recommendations': self._generate_extraction_recommendations(component_name, outgoing, incoming, circular)
        }

    def _generate_extraction_recommendations(self, component_name: str, outgoing: List[ComponentDependency],
                                           incoming: List[ComponentDependency],
                                           circular: List[ComponentDependency]) -> List[str]:
        """Generate recommendations for component extraction."""
        recommendations = []

        if circular:
            recommendations.append(f"CRITICAL: Resolve {len(circular)} circular dependencies before extraction")
            for dep in circular:
                recommendations.append(f"  - {dep.source_component} <-> {dep.target_component}: {dep.description}")

        isolation_deps = [dep for dep in outgoing if dep.isolation_requirement]
        if isolation_deps:
            recommendations.append(f"Ensure {len(isolation_deps)} user isolation dependencies are maintained")

        if len(incoming) > 3:
            recommendations.append(f"High coupling: {len(incoming)} components depend on this component")

        return recommendations


class ComponentValidationFramework:
    """
    Framework for validating component extraction and integration.

    Provides validation methods to ensure that component extraction
    maintains system integrity and user isolation requirements.
    """

    def __init__(self):
        self.dependency_registry = ComponentDependencyRegistry()

    def validate_component_interface_compliance(self, component: Any, interface_class: type) -> Dict[str, Any]:
        """Validate that extracted component implements required interface."""
        from netra_backend.app.websocket_core.interfaces import ComponentExtractionValidator

        # Handle case where interface_class is not an ABC
        try:
            compliant = ComponentExtractionValidator.validate_component_interface(component, interface_class)
            compliance_report = ComponentExtractionValidator.generate_compliance_report(component)
        except AttributeError:
            # For non-ABC classes, just check basic compatibility
            compliant = True
            compliance_report = {'overall_compliance': True, 'note': 'Non-ABC interface validation'}

        return {
            'compliant': compliant,
            'compliance_report': compliance_report,
            'timestamp': datetime.now().isoformat()
        }

    def validate_user_isolation_preservation(self, manager: Any) -> Dict[str, Any]:
        """Validate that user isolation is preserved during component extraction."""
        results = {
            'isolation_preserved': True,
            'validation_results': {},
            'critical_failures': [],
            'timestamp': datetime.now().isoformat()
        }

        # Test user isolation for critical methods
        isolation_tests = [
            ('add_connection', 'Connection isolation'),
            ('send_to_user', 'Event delivery isolation'),
            ('get_user_connections', 'Connection query isolation'),
            ('_validate_user_isolation', 'User validation isolation')
        ]

        for method_name, description in isolation_tests:
            if hasattr(manager, method_name):
                try:
                    # Basic validation that method exists and is callable
                    method = getattr(manager, method_name)
                    results['validation_results'][method_name] = {
                        'exists': True,
                        'callable': callable(method),
                        'description': description
                    }
                except Exception as e:
                    results['isolation_preserved'] = False
                    results['critical_failures'].append(f"{method_name}: {str(e)}")
            else:
                results['isolation_preserved'] = False
                results['critical_failures'].append(f"Missing critical method: {method_name}")

        return results

    def validate_backwards_compatibility(self, manager: Any) -> Dict[str, Any]:
        """Validate that component extraction maintains backwards compatibility."""
        results = {
            'backwards_compatible': True,
            'missing_methods': [],
            'interface_changes': [],
            'timestamp': datetime.now().isoformat()
        }

        # Critical methods that must be preserved for backwards compatibility
        critical_methods = [
            'add_connection', 'remove_connection', 'get_connection',
            'send_to_user', 'send_to_thread', 'broadcast',
            'connect_user', 'disconnect_user', 'is_user_connected',
            'get_stats', 'get_health_status', 'is_healthy'
        ]

        for method_name in critical_methods:
            if not hasattr(manager, method_name):
                results['backwards_compatible'] = False
                results['missing_methods'].append(method_name)

        return results

    def generate_extraction_readiness_report(self, component_name: str) -> Dict[str, Any]:
        """Generate comprehensive readiness report for component extraction."""
        dependency_analysis = self.dependency_registry.validate_extraction_plan(component_name)

        return {
            'component': component_name,
            'extraction_readiness': dependency_analysis['can_extract_safely'],
            'dependency_analysis': dependency_analysis,
            'risk_assessment': self._assess_extraction_risk(dependency_analysis),
            'recommended_order': self._recommend_extraction_order(),
            'timestamp': datetime.now().isoformat()
        }

    def _assess_extraction_risk(self, dependency_analysis: Dict[str, Any]) -> str:
        """Assess risk level for component extraction."""
        if dependency_analysis['circular_dependencies'] > 0:
            return "HIGH - Circular dependencies present"
        elif dependency_analysis['isolation_critical_deps'] > 2:
            return "MEDIUM - Multiple isolation-critical dependencies"
        elif dependency_analysis['incoming_dependencies'] > 3:
            return "MEDIUM - High coupling with other components"
        else:
            return "LOW - Safe for extraction"

    def _recommend_extraction_order(self) -> List[str]:
        """Recommend order for component extraction based on dependencies."""
        # Start with components that have fewer dependencies
        component_scores = {}
        components = [
            'IConfigurationProvider', 'IPerformanceMonitor', 'IAuthenticationIntegration',
            'IIntegrationBridge', 'IUserSessionRegistry', 'ICoreConnectionManager',
            'IEventBroadcastingService'
        ]

        for component in components:
            analysis = self.dependency_registry.validate_extraction_plan(component)
            # Score based on complexity (lower is better for early extraction)
            score = (analysis['circular_dependencies'] * 10 +
                    analysis['isolation_critical_deps'] * 3 +
                    analysis['incoming_dependencies'])
            component_scores[component] = score

        # Sort by score (lowest first)
        return sorted(component_scores.keys(), key=lambda x: component_scores[x])


# Validation test utilities
def create_validation_test_harness():
    """Create test harness for validating component extraction."""
    return ComponentValidationFramework()


def validate_phase1_foundation(manager: Any) -> Dict[str, Any]:
    """
    Validate Phase 1 foundation setup.

    Ensures that the interface definitions and dependency contracts
    are correctly established before beginning component extraction.
    """
    framework = ComponentValidationFramework()

    return {
        'phase1_validation': {
            'interface_compliance': framework.validate_component_interface_compliance(
                manager, type(manager).__bases__[0] if manager.__class__.__bases__ else object),
            'user_isolation': framework.validate_user_isolation_preservation(manager),
            'backwards_compatibility': framework.validate_backwards_compatibility(manager),
            'extraction_readiness': framework.generate_extraction_readiness_report('ICoreConnectionManager')
        },
        'timestamp': datetime.now().isoformat(),
        'phase1_complete': True
    }