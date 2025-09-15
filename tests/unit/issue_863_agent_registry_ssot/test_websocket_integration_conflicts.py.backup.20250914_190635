"""
Test WebSocket Integration Conflicts (Issue #863)

Tests the critical WebSocket integration failures caused by AgentRegistry
duplication that blocks the Golden Path user flow and prevents $500K+ ARR
from chat functionality.

Business Value: Validates that WebSocket events are delivered consistently
regardless of which AgentRegistry implementation is used, ensuring reliable
real-time chat communication.

Test Categories:
- Unit tests for WebSocket integration consistency
- No Docker required - pure interface and integration testing
- Focus on reproducing WebSocket bridge/manager conflicts
"""

import sys
import importlib
import inspect
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketIntegrationConflicts(SSotAsyncTestCase):
    """
    Test suite to validate WebSocket integration consistency across registry implementations.

    These tests identify how registry duplication breaks WebSocket event delivery,
    preventing users from receiving real-time agent updates in chat.
    """

    def setUp(self):
        """Set up test environment for WebSocket integration testing."""
        super().setUp()

        # Registry implementations that need consistent WebSocket integration
        self.registry_implementations = [
            "netra_backend.app.agents.registry",
            "netra_backend.app.agents.supervisor.agent_registry",
        ]

        # Critical WebSocket events that must be delivered for Golden Path
        self.critical_websocket_events = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        # WebSocket integration methods that must be consistent
        self.websocket_methods = [
            "set_websocket_manager",
            "set_websocket_bridge",
            "_notify_agent_event",
        ]

    def test_websocket_manager_integration_consistency(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate WebSocket manager integration inconsistencies.

        This test shows how different registry implementations handle WebSocket
        manager integration differently, causing event delivery failures.
        """
        registry_websocket_integration = {}

        for registry_path in self.registry_implementations:
            try:
                module = importlib.import_module(registry_path)
                if not hasattr(module, 'AgentRegistry'):
                    continue

                registry_class = getattr(module, 'AgentRegistry')

                # Analyze WebSocket manager integration
                integration_analysis = {
                    'has_set_websocket_manager': hasattr(registry_class, 'set_websocket_manager'),
                    'has_set_websocket_bridge': hasattr(registry_class, 'set_websocket_bridge'),
                    'has_notify_agent_event': hasattr(registry_class, '_notify_agent_event'),
                    'websocket_manager_signature': None,
                    'websocket_bridge_signature': None,
                    'supports_async_manager': False,
                }

                # Analyze set_websocket_manager method
                if integration_analysis['has_set_websocket_manager']:
                    manager_method = getattr(registry_class, 'set_websocket_manager')
                    integration_analysis['websocket_manager_signature'] = str(inspect.signature(manager_method))
                    integration_analysis['supports_async_manager'] = asyncio.iscoroutinefunction(manager_method)

                # Analyze set_websocket_bridge method
                if integration_analysis['has_set_websocket_bridge']:
                    bridge_method = getattr(registry_class, 'set_websocket_bridge')
                    integration_analysis['websocket_bridge_signature'] = str(inspect.signature(bridge_method))

                registry_websocket_integration[registry_path] = integration_analysis
                logger.info(f"WebSocket integration analysis for {registry_path}: {integration_analysis}")

            except ImportError as e:
                logger.warning(f"Could not import {registry_path}: {e}")
                continue

        # FAILURE CONDITION: Inconsistent WebSocket integration methods
        if len(registry_websocket_integration) > 1:
            # Check for method presence inconsistencies
            method_presence_conflicts = []
            for method_name in ['has_set_websocket_manager', 'has_set_websocket_bridge', 'has_notify_agent_event']:
                values = {path: analysis[method_name] for path, analysis in registry_websocket_integration.items()}
                if len(set(values.values())) > 1:  # Not all the same
                    method_presence_conflicts.append(f"{method_name}: {values}")

            # Check for signature inconsistencies
            signature_conflicts = []
            for method_name in ['websocket_manager_signature', 'websocket_bridge_signature']:
                signatures = {path: analysis[method_name] for path, analysis in registry_websocket_integration.items()
                            if analysis[method_name] is not None}
                if len(set(signatures.values())) > 1:  # Different signatures
                    signature_conflicts.append(f"{method_name}: {signatures}")

            # Log detailed conflicts
            logger.error("WebSocket integration conflicts detected:")
            for path, analysis in registry_websocket_integration.items():
                logger.error(f"  {path}:")
                for key, value in analysis.items():
                    logger.error(f"    {key}: {value}")

            all_conflicts = method_presence_conflicts + signature_conflicts
            if all_conflicts:
                self.fail(
                    f"CRITICAL WEBSOCKET INTEGRATION CONFLICTS: Registry implementations have inconsistent WebSocket integration. "
                    f"This prevents reliable event delivery in Golden Path, blocking chat functionality. "
                    f"Conflicts: {'; '.join(all_conflicts)}"
                )

        # If only one registry or all consistent, that's the goal state
        logger.info("WebSocket integration is consistent across registry implementations")

    def test_websocket_event_delivery_consistency(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate inconsistent WebSocket event delivery.

        This test shows how different registries handle event delivery differently,
        causing some events to be lost or delivered incorrectly.
        """
        event_delivery_analysis = {}

        for registry_path in self.registry_implementations:
            try:
                module = importlib.import_module(registry_path)
                if not hasattr(module, 'AgentRegistry'):
                    continue

                registry_class = getattr(module, 'AgentRegistry')

                # Create a mock WebSocket manager to test integration
                mock_websocket_manager = AsyncMock()
                mock_websocket_manager.send_event = AsyncMock()
                mock_websocket_manager.broadcast = AsyncMock()

                # Try to create registry instance and set WebSocket manager
                try:
                    # Try different construction patterns based on registry implementation
                    registry_instance = None

                    # First try with no parameters (basic registry)
                    try:
                        registry_instance = registry_class()
                    except TypeError:
                        # Try with common parameters (advanced registry)
                        try:
                            registry_instance = registry_class(llm_manager=Mock())
                        except TypeError:
                            # Skip this registry if we can't instantiate it
                            logger.warning(f"Could not instantiate {registry_path} - skipping event delivery test")
                            continue

                    if registry_instance is None:
                        continue

                    # Test WebSocket manager/bridge setting
                    event_delivery_analysis[registry_path] = {
                        'registry_created': True,
                        'websocket_manager_set': False,
                        'websocket_bridge_set': False,
                        'event_delivery_method': None,
                        'supports_user_isolation': False,
                        'errors': []
                    }

                    # Try setting WebSocket manager
                    if hasattr(registry_instance, 'set_websocket_manager'):
                        try:
                            if asyncio.iscoroutinefunction(registry_instance.set_websocket_manager):
                                # Async method - need to run in event loop
                                try:
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        # Can't run async in already running loop for this test
                                        event_delivery_analysis[registry_path]['errors'].append("Cannot test async method in running loop")
                                    else:
                                        loop.run_until_complete(registry_instance.set_websocket_manager(mock_websocket_manager))
                                        event_delivery_analysis[registry_path]['websocket_manager_set'] = True
                                except RuntimeError:
                                    # No event loop
                                    event_delivery_analysis[registry_path]['errors'].append("No event loop for async WebSocket manager")
                            else:
                                # Sync method
                                registry_instance.set_websocket_manager(mock_websocket_manager)
                                event_delivery_analysis[registry_path]['websocket_manager_set'] = True
                        except Exception as e:
                            event_delivery_analysis[registry_path]['errors'].append(f"Failed to set WebSocket manager: {e}")

                    # Try setting WebSocket bridge (alternative method)
                    if hasattr(registry_instance, 'set_websocket_bridge'):
                        try:
                            registry_instance.set_websocket_bridge(mock_websocket_manager)
                            event_delivery_analysis[registry_path]['websocket_bridge_set'] = True
                        except Exception as e:
                            event_delivery_analysis[registry_path]['errors'].append(f"Failed to set WebSocket bridge: {e}")

                    # Check event delivery method
                    if hasattr(registry_instance, '_notify_agent_event'):
                        event_delivery_analysis[registry_path]['event_delivery_method'] = '_notify_agent_event'
                    elif hasattr(registry_instance, 'emit_event'):
                        event_delivery_analysis[registry_path]['event_delivery_method'] = 'emit_event'
                    elif hasattr(registry_instance, 'send_websocket_event'):
                        event_delivery_analysis[registry_path]['event_delivery_method'] = 'send_websocket_event'

                    # Check for user isolation support
                    if hasattr(registry_instance, 'get_user_session') or hasattr(registry_instance, '_user_sessions'):
                        event_delivery_analysis[registry_path]['supports_user_isolation'] = True

                except Exception as e:
                    event_delivery_analysis[registry_path] = {
                        'registry_created': False,
                        'error': str(e)
                    }
                    logger.error(f"Failed to test event delivery for {registry_path}: {e}")

            except ImportError as e:
                logger.warning(f"Could not import {registry_path}: {e}")
                continue

        # Log detailed analysis
        logger.info("WebSocket event delivery analysis:")
        for path, analysis in event_delivery_analysis.items():
            logger.info(f"  {path}:")
            for key, value in analysis.items():
                if key == 'errors' and value:
                    logger.error(f"    {key}: {value}")
                else:
                    logger.info(f"    {key}: {value}")

        # FAILURE CONDITION: Inconsistent event delivery mechanisms
        if len(event_delivery_analysis) > 1:
            # Check for event delivery method inconsistencies
            event_methods = {}
            websocket_setup_methods = {}
            user_isolation_support = {}

            for path, analysis in event_delivery_analysis.items():
                if analysis.get('registry_created', False):
                    event_methods[path] = analysis.get('event_delivery_method')
                    websocket_setup_methods[path] = {
                        'manager': analysis.get('websocket_manager_set', False),
                        'bridge': analysis.get('websocket_bridge_set', False)
                    }
                    user_isolation_support[path] = analysis.get('supports_user_isolation', False)

            # Check for inconsistencies
            inconsistencies = []

            if len(set(event_methods.values())) > 1:
                inconsistencies.append(f"Event delivery methods differ: {event_methods}")

            if len(set(user_isolation_support.values())) > 1:
                inconsistencies.append(f"User isolation support differs: {user_isolation_support}")

            setup_methods_vary = False
            manager_support = {path: methods['manager'] for path, methods in websocket_setup_methods.items()}
            bridge_support = {path: methods['bridge'] for path, methods in websocket_setup_methods.items()}

            if len(set(manager_support.values())) > 1:
                setup_methods_vary = True
                inconsistencies.append(f"WebSocket manager support differs: {manager_support}")

            if len(set(bridge_support.values())) > 1:
                setup_methods_vary = True
                inconsistencies.append(f"WebSocket bridge support differs: {bridge_support}")

            if inconsistencies:
                self.fail(
                    f"CRITICAL WEBSOCKET EVENT DELIVERY INCONSISTENCIES: Registry implementations handle WebSocket events differently. "
                    f"This causes unpredictable event delivery in Golden Path, preventing reliable chat functionality. "
                    f"Inconsistencies: {'; '.join(inconsistencies)}"
                )

        logger.info("WebSocket event delivery is consistent across registry implementations")

    def test_websocket_bridge_compatibility(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate WebSocket bridge compatibility issues.

        This test shows how different registries expect different WebSocket bridge
        interfaces, preventing unified bridge usage across the system.
        """
        bridge_compatibility_analysis = {}

        # Create different mock bridge types to test compatibility
        mock_bridges = {
            'websocket_manager_type': Mock(),
            'agent_websocket_bridge_type': Mock(),
            'unified_emitter_type': Mock(),
        }

        # Add common WebSocket methods to all mock bridges
        for bridge_name, bridge_mock in mock_bridges.items():
            bridge_mock.send_event = AsyncMock()
            bridge_mock.emit = AsyncMock()
            bridge_mock.broadcast = AsyncMock()
            bridge_mock.register_connection = Mock()
            bridge_mock.disconnect_user = Mock()

        for registry_path in self.registry_implementations:
            try:
                module = importlib.import_module(registry_path)
                if not hasattr(module, 'AgentRegistry'):
                    continue

                registry_class = getattr(module, 'AgentRegistry')

                # Test compatibility with different bridge types
                compatibility_results = {}

                for bridge_type, bridge_mock in mock_bridges.items():
                    try:
                        # Try to create registry and set bridge
                        try:
                            registry_instance = registry_class()
                        except TypeError:
                            try:
                                registry_instance = registry_class(llm_manager=Mock())
                            except TypeError:
                                compatibility_results[bridge_type] = {'error': 'Cannot instantiate registry'}
                                continue

                        compatibility_test = {
                            'accepts_as_manager': False,
                            'accepts_as_bridge': False,
                            'errors': []
                        }

                        # Test as WebSocket manager
                        if hasattr(registry_instance, 'set_websocket_manager'):
                            try:
                                if asyncio.iscoroutinefunction(registry_instance.set_websocket_manager):
                                    # Skip async test in this context
                                    compatibility_test['errors'].append("Async manager method - cannot test")
                                else:
                                    registry_instance.set_websocket_manager(bridge_mock)
                                    compatibility_test['accepts_as_manager'] = True
                            except Exception as e:
                                compatibility_test['errors'].append(f"Manager error: {e}")

                        # Test as WebSocket bridge
                        if hasattr(registry_instance, 'set_websocket_bridge'):
                            try:
                                registry_instance.set_websocket_bridge(bridge_mock)
                                compatibility_test['accepts_as_bridge'] = True
                            except Exception as e:
                                compatibility_test['errors'].append(f"Bridge error: {e}")

                        compatibility_results[bridge_type] = compatibility_test

                    except Exception as e:
                        compatibility_results[bridge_type] = {'error': f"Test failed: {e}"}

                bridge_compatibility_analysis[registry_path] = compatibility_results

            except ImportError as e:
                logger.warning(f"Could not import {registry_path}: {e}")
                continue

        # Log detailed compatibility analysis
        logger.info("WebSocket bridge compatibility analysis:")
        for registry_path, compatibility in bridge_compatibility_analysis.items():
            logger.info(f"  {registry_path}:")
            for bridge_type, results in compatibility.items():
                logger.info(f"    {bridge_type}: {results}")

        # FAILURE CONDITION: Incompatible bridge interfaces
        if len(bridge_compatibility_analysis) > 1:
            # Check for bridge compatibility inconsistencies
            compatibility_inconsistencies = []

            for bridge_type in mock_bridges.keys():
                manager_compatibility = {}
                bridge_compatibility = {}

                for registry_path, compatibility in bridge_compatibility_analysis.items():
                    if bridge_type in compatibility and 'error' not in compatibility[bridge_type]:
                        results = compatibility[bridge_type]
                        manager_compatibility[registry_path] = results.get('accepts_as_manager', False)
                        bridge_compatibility[registry_path] = results.get('accepts_as_bridge', False)

                # Check if registries differ in bridge type acceptance
                if len(set(manager_compatibility.values())) > 1:
                    compatibility_inconsistencies.append(
                        f"{bridge_type} as manager: {manager_compatibility}"
                    )

                if len(set(bridge_compatibility.values())) > 1:
                    compatibility_inconsistencies.append(
                        f"{bridge_type} as bridge: {bridge_compatibility}"
                    )

            if compatibility_inconsistencies:
                self.fail(
                    f"CRITICAL WEBSOCKET BRIDGE COMPATIBILITY CONFLICTS: Registry implementations accept different bridge types. "
                    f"This prevents unified WebSocket bridge usage, causing event delivery failures in Golden Path. "
                    f"Compatibility conflicts: {'; '.join(compatibility_inconsistencies)}"
                )

        logger.info("WebSocket bridge compatibility is consistent across registry implementations")

    def test_websocket_event_schema_consistency(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate inconsistent WebSocket event schemas.

        This test validates that all registries emit WebSocket events with consistent
        schemas, ensuring reliable event processing by the frontend.
        """
        event_schema_analysis = {}

        for registry_path in self.registry_implementations:
            try:
                module = importlib.import_module(registry_path)
                if not hasattr(module, 'AgentRegistry'):
                    continue

                registry_class = getattr(module, 'AgentRegistry')

                # Analyze event emission patterns
                schema_analysis = {
                    'has_event_notification': False,
                    'event_method_signature': None,
                    'event_data_structure': None,
                    'supports_event_types': [],
                    'analysis_errors': []
                }

                # Look for event notification method
                if hasattr(registry_class, '_notify_agent_event'):
                    schema_analysis['has_event_notification'] = True
                    method = getattr(registry_class, '_notify_agent_event')
                    schema_analysis['event_method_signature'] = str(inspect.signature(method))

                    # Try to analyze the method implementation for event structure
                    try:
                        source = inspect.getsource(method)
                        # Look for event data structure patterns
                        if '"type":' in source or "'type':" in source:
                            schema_analysis['event_data_structure'] = 'dict_with_type'
                        if 'event_data' in source:
                            schema_analysis['event_data_structure'] = 'event_data_dict'

                        # Look for specific event types
                        for event_type in self.critical_websocket_events:
                            if event_type in source:
                                schema_analysis['supports_event_types'].append(event_type)

                    except Exception as e:
                        schema_analysis['analysis_errors'].append(f"Source analysis error: {e}")

                event_schema_analysis[registry_path] = schema_analysis

            except ImportError as e:
                logger.warning(f"Could not import {registry_path}: {e}")
                continue
            except Exception as e:
                event_schema_analysis[registry_path] = {
                    'analysis_error': str(e)
                }

        # Log schema analysis results
        logger.info("WebSocket event schema analysis:")
        for registry_path, analysis in event_schema_analysis.items():
            logger.info(f"  {registry_path}:")
            for key, value in analysis.items():
                if key == 'analysis_errors' and value:
                    logger.error(f"    {key}: {value}")
                else:
                    logger.info(f"    {key}: {value}")

        # FAILURE CONDITION: Inconsistent event schemas
        if len(event_schema_analysis) > 1:
            schema_inconsistencies = []

            # Check event method signature consistency
            signatures = {}
            for path, analysis in event_schema_analysis.items():
                if 'event_method_signature' in analysis and analysis['event_method_signature']:
                    signatures[path] = analysis['event_method_signature']

            if len(set(signatures.values())) > 1:
                schema_inconsistencies.append(f"Event method signatures differ: {signatures}")

            # Check event data structure consistency
            structures = {}
            for path, analysis in event_schema_analysis.items():
                if 'event_data_structure' in analysis and analysis['event_data_structure']:
                    structures[path] = analysis['event_data_structure']

            if len(set(structures.values())) > 1:
                schema_inconsistencies.append(f"Event data structures differ: {structures}")

            # Check critical event type support
            for event_type in self.critical_websocket_events:
                support_status = {}
                for path, analysis in event_schema_analysis.items():
                    supports_event = event_type in analysis.get('supports_event_types', [])
                    support_status[path] = supports_event

                if len(set(support_status.values())) > 1:  # Not all registries support the same events
                    schema_inconsistencies.append(f"Event type '{event_type}' support differs: {support_status}")

            if schema_inconsistencies:
                self.fail(
                    f"CRITICAL WEBSOCKET EVENT SCHEMA INCONSISTENCIES: Registry implementations emit different event schemas. "
                    f"This causes frontend parsing errors and breaks real-time chat updates in Golden Path. "
                    f"Schema inconsistencies: {'; '.join(schema_inconsistencies)}"
                )

        logger.info("WebSocket event schemas are consistent across registry implementations")

    def test_user_isolation_websocket_conflicts(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate user isolation conflicts in WebSocket handling.

        This test shows how different registries handle multi-user WebSocket scenarios
        differently, causing cross-user event contamination.
        """
        user_isolation_analysis = {}

        for registry_path in self.registry_implementations:
            try:
                module = importlib.import_module(registry_path)
                if not hasattr(module, 'AgentRegistry'):
                    continue

                registry_class = getattr(module, 'AgentRegistry')

                # Analyze user isolation capabilities
                isolation_analysis = {
                    'supports_user_sessions': False,
                    'has_per_user_websocket': False,
                    'has_user_context_parameter': False,
                    'isolation_methods': [],
                    'potential_contamination_risks': []
                }

                # Check for user session support
                class_methods = [method for method in dir(registry_class) if not method.startswith('__')]

                # Look for user isolation patterns
                user_session_indicators = ['user_session', 'get_user_session', '_user_sessions']
                for indicator in user_session_indicators:
                    if any(indicator in method for method in class_methods):
                        isolation_analysis['supports_user_sessions'] = True
                        break

                # Check for per-user WebSocket handling
                websocket_user_methods = [method for method in class_methods
                                        if 'websocket' in method.lower() and 'user' in method.lower()]
                if websocket_user_methods:
                    isolation_analysis['has_per_user_websocket'] = True
                    isolation_analysis['isolation_methods'].extend(websocket_user_methods)

                # Check method signatures for user context parameters
                websocket_methods = [method for method in class_methods if 'websocket' in method.lower()]
                for method_name in websocket_methods:
                    try:
                        method = getattr(registry_class, method_name)
                        if callable(method):
                            signature = inspect.signature(method)
                            params = list(signature.parameters.keys())
                            if any('user' in param.lower() or 'context' in param.lower() for param in params):
                                isolation_analysis['has_user_context_parameter'] = True
                                break
                    except Exception:
                        continue

                # Identify potential contamination risks
                if not isolation_analysis['supports_user_sessions']:
                    isolation_analysis['potential_contamination_risks'].append("No user session isolation")

                if not isolation_analysis['has_per_user_websocket']:
                    isolation_analysis['potential_contamination_risks'].append("Shared WebSocket handling")

                # Look for global state that could cause contamination
                try:
                    if hasattr(registry_class, '_websocket_manager') or hasattr(registry_class, 'websocket_manager'):
                        # Check if it's a class variable (shared) vs instance variable
                        source = inspect.getsource(registry_class)
                        if 'self._websocket_manager' not in source and 'self.websocket_manager' not in source:
                            isolation_analysis['potential_contamination_risks'].append("Global WebSocket manager state")
                except Exception:
                    pass

                user_isolation_analysis[registry_path] = isolation_analysis

            except ImportError as e:
                logger.warning(f"Could not import {registry_path}: {e}")
                continue

        # Log user isolation analysis
        logger.info("User isolation WebSocket analysis:")
        for registry_path, analysis in user_isolation_analysis.items():
            logger.info(f"  {registry_path}:")
            for key, value in analysis.items():
                if key == 'potential_contamination_risks' and value:
                    logger.error(f"    {key}: {value}")
                else:
                    logger.info(f"    {key}: {value}")

        # FAILURE CONDITION: Inconsistent user isolation approaches
        if len(user_isolation_analysis) > 1:
            isolation_inconsistencies = []

            # Check user session support consistency
            session_support = {path: analysis['supports_user_sessions'] for path, analysis in user_isolation_analysis.items()}
            if len(set(session_support.values())) > 1:
                isolation_inconsistencies.append(f"User session support differs: {session_support}")

            # Check per-user WebSocket handling consistency
            websocket_isolation = {path: analysis['has_per_user_websocket'] for path, analysis in user_isolation_analysis.items()}
            if len(set(websocket_isolation.values())) > 1:
                isolation_inconsistencies.append(f"Per-user WebSocket handling differs: {websocket_isolation}")

            # Check contamination risk levels
            contamination_risks = {}
            for path, analysis in user_isolation_analysis.items():
                risk_count = len(analysis['potential_contamination_risks'])
                contamination_risks[path] = risk_count

            if len(set(contamination_risks.values())) > 1:
                isolation_inconsistencies.append(f"Contamination risk levels differ: {contamination_risks}")

            # Any registry with contamination risks is a problem
            high_risk_registries = {path: risks for path, risks in contamination_risks.items() if risks > 0}
            if high_risk_registries:
                risk_details = []
                for path, risk_count in high_risk_registries.items():
                    risks = user_isolation_analysis[path]['potential_contamination_risks']
                    risk_details.append(f"{path}: {risks}")
                isolation_inconsistencies.append(f"High contamination risk registries: {risk_details}")

            if isolation_inconsistencies:
                self.fail(
                    f"CRITICAL USER ISOLATION WEBSOCKET CONFLICTS: Registry implementations have inconsistent user isolation. "
                    f"This causes cross-user event contamination, breaking multi-user chat functionality in Golden Path. "
                    f"Isolation conflicts: {'; '.join(isolation_inconsistencies)}"
                )

        logger.info("User isolation for WebSocket handling is consistent across registry implementations")


if __name__ == "__main__":
    # Allow running this test file directly for quick debugging
    pytest.main([__file__, "-v", "-s"])