"
Issue #889 WebSocket Manager Duplication Integration Tests - REPRODUCTION SUITE

This integration test suite reproduces WebSocket manager duplication violations
in realistic service integration scenarios. Tests are designed to FAIL initially,
exposing the factory pattern bypasses and user isolation failures.

CRITICAL BUSINESS CONTEXT:
- Integration with real WebSocket core services reveals duplication patterns
- Multi-service interactions trigger the registry key inconsistencies
- Service-to-service WebSocket manager sharing causes user contamination
- Production staging environment patterns reproduced with real dependencies

TEST OBJECTIVES (Must FAIL initially):
1. Factory pattern bypass in service integration contexts
2. Manager sharing across different service instances
3. Registry corruption during concurrent service operations
4. Agent-WebSocket manager binding inconsistencies

INTEGRATION SCOPE:
- WebSocket core service integration
- Agent registry service interactions
- User context factory integration
- Service startup/shutdown lifecycle patterns

EXPECTED FAILURES:
- test_service_integration_manager_duplication: Same user gets multiple managers
- test_agent_websocket_binding_violations: Agents share WebSocket managers
- test_concurrent_service_startup_violations: Race conditions create duplicates
- test_user_context_factory_integration_failures: Factory bypasses in services

Business Value Justification (BVJ):
- Segment: Platform Integration (affects all user tiers)
- Business Goal: Stability - ensure service integration doesn't break WebSocket isolation
- Value Impact: Critical infrastructure reliability for $500K+ ARR chat functionality
- Revenue Impact: Prevent service integration failures affecting customer experience
"

import asyncio
import unittest
import sys
import os
import logging
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any, Set, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Add test_framework to path for SSOT imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'test_framework'))

# Import SSOT BaseTestCase - MANDATORY for all tests
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

# Import integration test utilities
try:
    from netra_backend.app.websocket_core.websocket_manager import (
        WebSocketManager,
        UnifiedWebSocketManager,
        WebSocketManagerFactory,
        get_websocket_manager,
        create_test_user_context,
        create_test_fallback_manager
    )
    from netra_backend.app.websocket_core.types import (
        WebSocketManagerMode,
        WebSocketConnection,
        create_isolated_mode
    )
    from netra_backend.app.websocket_core.websocket_manager import (
        _UnifiedWebSocketManagerImplementation
    )
    from netra_backend.app.agents.registry import (
        AgentRegistry, AgentType, AgentStatus, get_agent_registry
    )
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
    from netra_backend.app.core.user_context.factory import UserExecutionContextFactory
    from shared.types.core_types import ensure_user_id, ensure_thread_id
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logging.warning(fIntegration imports not available: {e}")
    IMPORTS_AVAILABLE = False


@dataclass
class IntegrationTestContext:
    Integration test context for service-level testing.""
    user_id: str
    session_id: str
    service_name: str
    startup_time: datetime = field(default_factory=datetime.now)
    websocket_managers: List[Any] = field(default_factory=list)
    agent_registry: Optional[Any] = None
    thread_id: Optional[str] = None
    request_id: Optional[str] = None

    def __post_init__(self):
        if not self.thread_id:
            self.thread_id = fthread-{self.service_name}-{self.session_id}
        if not self.request_id:
            self.request_id = freq-{self.service_name}-{self.session_id}


class Issue889WebSocketManagerDuplicationIntegrationTests(SSotAsyncTestCase):
    ""
    Integration tests to reproduce WebSocket manager duplication in service contexts.

    These tests MUST FAIL initially to demonstrate the current integration violations.
    Success would indicate the issue is already fixed at the integration level.


    def setup_method(self, method):
        "Setup for each test method."
        super().setup_method(method)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Create integration test contexts for multiple services
        self.service_contexts = {
            'chat_service': IntegrationTestContext(
                user_id=demo-user-001,"
                session_id="session-chat-integration,
                service_name=chat_service
            ),
            'agent_service': IntegrationTestContext(
                user_id="demo-user-001,"
                session_id=session-agent-integration,
                service_name=agent_service"
            ),
            'websocket_service': IntegrationTestContext(
                user_id=demo-user-001",
                session_id=session-websocket-integration,
                service_name=websocket_service""
            )
        }

        # Track all managers created across services
        self.all_managers_created = []
        self.service_manager_registry = {}
        self.duplication_events = []

        self.logger.info(fSetup integration test: {method.__name__} with {len(self.service_contexts)} services)

    def teardown_method(self, method):
        Cleanup after each test method.""
        # Clear all tracking data
        self.all_managers_created.clear()
        self.service_manager_registry.clear()
        self.duplication_events.clear()

        for context in self.service_contexts.values():
            context.websocket_managers.clear()

        super().teardown_method(method)
        self.logger.info(fTeardown integration test: {method.__name__})

    async def _simulate_service_startup_with_websocket_manager(self, context: IntegrationTestContext) -> Dict[str, Any]:
        
        Simulate service startup that creates WebSocket managers.

        This reproduces the patterns where services independently create
        WebSocket managers during startup, leading to duplication.
""
        service_result = {
            'service_name': context.service_name,
            'user_id': context.user_id,
            'managers_created': [],
            'startup_success': False,
            'duplication_detected': False
        }

        try:
            self.logger.info(fSimulating startup for {context.service_name})

            # Pattern 1: Service creates manager during initialization
            init_manager = get_websocket_manager(user_context=context)
            if init_manager:
                context.websocket_managers.append(init_manager)
                service_result['managers_created'].append({
                    'stage': 'initialization',
                    'manager_id': id(init_manager),
                    'type': type(init_manager).__name__
                }

            # Pattern 2: Service creates additional manager for agent integration
            if context.service_name == 'agent_service':
                agent_manager = get_websocket_manager(user_context=context)
                if agent_manager:
                    context.websocket_managers.append(agent_manager)
                    service_result['managers_created'].append({
                        'stage': 'agent_integration',
                        'manager_id': id(agent_manager),
                        'type': type(agent_manager).__name__
                    }

                    # Check if same as init manager (should be, but might not be)
                    if id(agent_manager) != id(init_manager):
                        service_result['duplication_detected'] = True
                        self.duplication_events.append({
                            'service': context.service_name,
                            'type': 'agent_integration_duplicate',
                            'init_manager_id': id(init_manager),
                            'agent_manager_id': id(agent_manager)
                        }

            # Pattern 3: Service creates manager for WebSocket event handling
            if context.service_name in ['chat_service', 'websocket_service']:
                event_manager = get_websocket_manager(user_context=context)
                if event_manager:
                    context.websocket_managers.append(event_manager)
                    service_result['managers_created'].append({
                        'stage': 'event_handling',
                        'manager_id': id(event_manager),
                        'type': type(event_manager).__name__
                    }

                    # Check for duplication with previous managers
                    previous_ids = {id(m) for m in context.websocket_managers[:-1]}
                    if id(event_manager) not in previous_ids and len(previous_ids) > 0:
                        service_result['duplication_detected'] = True
                        self.duplication_events.append({
                            'service': context.service_name,
                            'type': 'event_handling_duplicate',
                            'existing_ids': list(previous_ids),
                            'new_manager_id': id(event_manager)
                        }

            service_result['startup_success'] = True
            self.all_managers_created.extend(context.websocket_managers)
            self.service_manager_registry[context.service_name] = context.websocket_managers

        except Exception as e:
            self.logger.error(fService startup failed for {context.service_name}: {e})"
            service_result['error'] = str(e)

        return service_result

    @unittest.skipUnless(IMPORTS_AVAILABLE, "Integration imports not available)
    async def test_service_integration_manager_duplication(self):
        
        TEST MUST FAIL: Reproduce manager duplication across service integration.

        EXPECTED FAILURE: Multiple services for the same user create separate
        WebSocket manager instances instead of sharing the singleton.

        This reproduces the core integration violation where service boundaries
        break the SSOT factory pattern enforcement.
""
        self.logger.info(REPRODUCING: Service integration manager duplication for demo-user-001)

        # Start all services concurrently (as happens in real deployments)
        service_results = {}
        tasks = []

        for service_name, context in self.service_contexts.items():
            task = asyncio.create_task(
                self._simulate_service_startup_with_websocket_manager(context)
            )
            tasks.append((service_name, task))

        # Wait for all services to start
        for service_name, task in tasks:
            try:
                result = await task
                service_results[service_name] = result
                self.logger.info(fService {service_name} startup result: {result}")"
            except Exception as e:
                self.logger.error(fService {service_name} startup failed: {e})
                service_results[service_name] = {'error': str(e)}

        # Analyze manager duplication across services
        all_manager_ids = set()
        service_manager_counts = {}
        cross_service_duplicates = []

        for service_name, managers in self.service_manager_registry.items():
            manager_ids = {id(m) for m in managers if m is not None}
            service_manager_counts[service_name] = len(manager_ids)

            # Check for cross-service duplication
            for manager_id in manager_ids:
                if manager_id in all_manager_ids:
                    cross_service_duplicates.append({
                        'manager_id': manager_id,
                        'service': service_name,
                        'duplicate_of': [s for s, ms in self.service_manager_registry.items()
                                       if s != service_name and any(id(m) == manager_id for m in ms)]
                    }
                else:
                    all_manager_ids.add(manager_id)

        total_managers = len(all_manager_ids)
        services_with_managers = len([s for s, count in service_manager_counts.items() if count > 0]

        self.logger.critical(
            fINTEGRATION DUPLICATION ANALYSIS: 
            f"{total_managers} unique managers across {services_with_managers} services. 
            fService counts: {service_manager_counts}. "
            fCross-service duplicates: {len(cross_service_duplicates)}
        )

        # EXPECTED FAILURE: All services should share the same manager for demo-user-001
        # If this passes, the SSOT pattern is working correctly across services
        self.assertEqual(
            total_managers, 1,
            fSERVICE INTEGRATION DUPLICATION: Expected 1 shared manager for demo-user-001 across all services, "
            f"got {total_managers} managers. Service breakdown: {service_manager_counts}. 
            fThis reproduces Issue #889 at the service integration level.
        )

        # EXPECTED FAILURE: No cross-service manager duplication should occur
        self.assertEqual(
            len(cross_service_duplicates), services_with_managers - 1 if services_with_managers > 0 else 0,
            fCROSS-SERVICE SHARING FAILURE: Expected {services_with_managers - 1} cross-service shares, 
            fgot {len(cross_service_duplicates)} duplicates: {cross_service_duplicates}. ""
            fThis indicates SSOT factory is not working across service boundaries.
        )

    @unittest.skipUnless(IMPORTS_AVAILABLE, Integration imports not available)
    async def test_agent_websocket_binding_violations(self):
    ""
        TEST MUST FAIL: Reproduce agent-WebSocket manager binding violations.

        EXPECTED FAILURE: Agent instances bind to different WebSocket managers
        than expected, or multiple agents for same user bind to different managers.

        This reproduces the binding inconsistency that causes WebSocket events
        to be sent to wrong connections or lost entirely.
        
        self.logger.info(REPRODUCING: Agent-WebSocket binding violations for demo-user-001")"

        binding_violations = []
        agent_manager_bindings = {}

        try:
            # Create multiple agents that should share WebSocket manager
            agent_configs = [
                {'name': 'supervisor_agent', 'type': 'supervisor'},
                {'name': 'triage_agent', 'type': 'triage'},
                {'name': 'data_helper_agent', 'type': 'data_helper'}
            ]

            for agent_config in agent_configs:
                agent_name = agent_config['name']

                # Simulate agent creation with WebSocket manager binding
                try:
                    # Get manager for agent (should be same for all agents of same user)
                    agent_context = self.service_contexts['agent_service']
                    agent_manager = get_websocket_manager(user_context=agent_context)

                    if agent_manager:
                        agent_manager_bindings[agent_name] = {
                            'manager_id': id(agent_manager),
                            'manager_obj': agent_manager,
                            'user_id': agent_context.user_id,
                            'binding_time': datetime.now()
                        }

                        self.logger.info(fAgent {agent_name} bound to manager {id(agent_manager)})

                        # Simulate agent requesting additional WebSocket access
                        secondary_manager = get_websocket_manager(user_context=agent_context)
                        if secondary_manager and id(secondary_manager) != id(agent_manager):
                            binding_violations.append({
                                'agent': agent_name,
                                'violation_type': 'secondary_manager_different',
                                'primary_manager_id': id(agent_manager),
                                'secondary_manager_id': id(secondary_manager)
                            }
                            self.logger.error(
                                fBINDING VIOLATION: {agent_name} got different secondary manager 
                                f"{id(secondary_manager)} vs primary {id(agent_manager)}
                            )

                except Exception as e:
                    self.logger.error(fFailed to bind WebSocket manager for {agent_name}: {e}")
                    binding_violations.append({
                        'agent': agent_name,
                        'violation_type': 'binding_failed',
                        'error': str(e)
                    }

            # Analyze manager consistency across agent bindings
            manager_ids_used = {binding['manager_id'] for binding in agent_manager_bindings.values()}
            agents_bound = len(agent_manager_bindings)
            unique_managers = len(manager_ids_used)

            # Check for binding inconsistencies
            if unique_managers > 1:
                for agent_name, binding in agent_manager_bindings.items():
                    other_agents = [(n, b) for n, b in agent_manager_bindings.items() if n != agent_name]
                    for other_agent_name, other_binding in other_agents:
                        if binding['manager_id'] != other_binding['manager_id']:
                            binding_violations.append({
                                'agent': agent_name,
                                'violation_type': 'cross_agent_manager_mismatch',
                                'agent_manager_id': binding['manager_id'],
                                'other_agent': other_agent_name,
                                'other_manager_id': other_binding['manager_id']
                            }

            self.logger.critical(
                fAGENT BINDING ANALYSIS: {agents_bound} agents bound, 
                f{unique_managers} unique managers, {len(binding_violations)} violations"
            )

            # EXPECTED FAILURE: All agents for same user should bind to same manager
            self.assertEqual(
                unique_managers, 1,
                f"AGENT BINDING VIOLATION: Expected 1 shared manager for all demo-user-001 agents, 
                fgot {unique_managers} different managers. Agent bindings: {agent_manager_bindings}. 
                fThis reproduces Issue #889 agent binding inconsistency.
            )

            # EXPECTED FAILURE: No binding violations should occur
            self.assertEqual(
                len(binding_violations), 0,
                fAGENT WEBSOCKET BINDING FAILURES: {len(binding_violations)} violations detected: {binding_violations}. ""
                fThis reproduces Issue #889 agent-WebSocket coordination failures.
            )

        except Exception as e:
            self.logger.error(fFailed to test agent WebSocket binding: {e})
            self.fail(f"Could not reproduce agent binding violations: {e})

    @unittest.skipUnless(IMPORTS_AVAILABLE, Integration imports not available")
    async def test_concurrent_service_startup_violations(self):
    "
        TEST MUST FAIL: Reproduce race conditions in concurrent service startup.

        EXPECTED FAILURE: When multiple services start concurrently for the same user,
        race conditions in the factory pattern create multiple manager instances.

        This reproduces the timing-based duplication that occurs in production
        deployments where services initialize in parallel.
        "
        self.logger.info(REPRODUCING: Concurrent service startup race conditions for demo-user-001)

        race_condition_results = []
        concurrent_managers = {}
        timing_analysis = {}

        # Create multiple concurrent contexts with slight timing variations
        concurrent_contexts = []
        for i in range(5):
            context = IntegrationTestContext(
                user_id="demo-user-001,"
                session_id=fsession-concurrent-{i},
                service_name=fconcurrent_service_{i}
            )
            concurrent_contexts.append(context)

        async def concurrent_manager_creation(context, delay_ms=0):
            ""Create manager with optional delay to trigger race conditions.
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)

            start_time = time.time()
            try:
                manager = get_websocket_manager(user_context=context)
                end_time = time.time()

                return {
                    'context': context,
                    'manager_id': id(manager) if manager else None,
                    'manager_obj': manager,
                    'creation_time': start_time,
                    'duration': end_time - start_time,
                    'success': manager is not None
                }
            except Exception as e:
                end_time = time.time()
                return {
                    'context': context,
                    'manager_id': None,
                    'manager_obj': None,
                    'creation_time': start_time,
                    'duration': end_time - start_time,
                    'success': False,
                    'error': str(e)
                }

        # Test 1: Simultaneous creation (no delays)
        simultaneous_tasks = [
            asyncio.create_task(concurrent_manager_creation(ctx))
            for ctx in concurrent_contexts
        ]

        simultaneous_results = await asyncio.gather(*simultaneous_tasks, return_exceptions=True)

        successful_simultaneous = [r for r in simultaneous_results if isinstance(r, dict) and r['success']]
        manager_ids_simultaneous = {r['manager_id'] for r in successful_simultaneous}

        race_condition_results.append({
            'test_type': 'simultaneous',
            'contexts_tested': len(concurrent_contexts),
            'successful_creations': len(successful_simultaneous),
            'unique_managers': len(manager_ids_simultaneous),
            'manager_ids': list(manager_ids_simultaneous)
        }

        # Test 2: Staggered creation (small delays to trigger race conditions)
        staggered_delays = [0, 10, 20, 30, 40]  # milliseconds
        staggered_tasks = [
            asyncio.create_task(concurrent_manager_creation(ctx, delay))
            for ctx, delay in zip(concurrent_contexts, staggered_delays)
        ]

        staggered_results = await asyncio.gather(*staggered_tasks, return_exceptions=True)

        successful_staggered = [r for r in staggered_results if isinstance(r, dict) and r['success']]
        manager_ids_staggered = {r['manager_id'] for r in successful_staggered}

        race_condition_results.append({
            'test_type': 'staggered',
            'contexts_tested': len(concurrent_contexts),
            'successful_creations': len(successful_staggered),
            'unique_managers': len(manager_ids_staggered),
            'manager_ids': list(manager_ids_staggered),
            'delays_used': staggered_delays
        }

        # Analyze timing patterns for race conditions
        all_successful_results = successful_simultaneous + successful_staggered
        if all_successful_results:
            creation_times = [r['creation_time'] for r in all_successful_results]
            time_window = max(creation_times) - min(creation_times)

            timing_analysis = {
                'total_time_window': time_window,
                'min_creation_time': min(creation_times),
                'max_creation_time': max(creation_times),
                'average_duration': sum(r['duration'] for r in all_successful_results) / len(all_successful_results)
            }

        self.logger.critical(
            fCONCURRENT STARTUP ANALYSIS: 
            fSimultaneous: {len(manager_ids_simultaneous)} unique managers. ""
            fStaggered: {len(manager_ids_staggered)} unique managers. 
            fTiming window: {timing_analysis.get('total_time_window', 0):.3f}s
        )

        # EXPECTED FAILURE: All concurrent creations should return same manager
        total_unique_managers = len(manager_ids_simultaneous | manager_ids_staggered)
        self.assertEqual(
            total_unique_managers, 1,
            f"CONCURRENT STARTUP RACE CONDITION: Expected 1 shared manager across all concurrent creation attempts, 
            fgot {total_unique_managers} unique managers. "
            fSimultaneous: {manager_ids_simultaneous}, Staggered: {manager_ids_staggered}. 
            fThis reproduces Issue #889 race condition violations."
        )

        # EXPECTED FAILURE: Simultaneous creation should be consistent
        self.assertEqual(
            len(manager_ids_simultaneous), 1,
            f"SIMULTANEOUS CREATION RACE: Expected 1 manager from simultaneous creation, 
            fgot {len(manager_ids_simultaneous)} managers: {manager_ids_simultaneous}. 
            fThis reproduces timing-based duplication in Issue #889.
        )

        # EXPECTED FAILURE: Staggered creation should maintain consistency
        self.assertEqual(
            len(manager_ids_staggered), 1,
            fSTAGGERED CREATION RACE: Expected 1 manager from staggered creation, ""
            fgot {len(manager_ids_staggered)} managers: {manager_ids_staggered}. 
            fThis reproduces delay-based duplication in Issue #889.
        )

    @unittest.skipUnless(IMPORTS_AVAILABLE, "Integration imports not available)"
    async def test_user_context_factory_integration_failures(self):
        
        TEST MUST FAIL: Reproduce user context factory integration bypass patterns.

        EXPECTED FAILURE: Services bypass the UserExecutionContextFactory and create
        contexts directly, leading to inconsistent WebSocket manager bindings.

        This reproduces the integration-level bypass where services use ad-hoc
        context creation instead of the SSOT factory pattern.
""
        self.logger.info(REPRODUCING: User context factory integration bypass patterns)

        factory_bypass_results = []
        context_consistency_violations = []

        try:
            # Test different context creation patterns that might be used by services
            creation_patterns = [
                {
                    'name': 'factory_proper',
                    'method': lambda: UserExecutionContextFactory.create_test_context(user_id=demo-user-001)"
                },
                {
                    'name': 'fallback_creation',
                    'method': lambda: create_test_user_context()
                },
                {
                    'name': 'direct_mock_creation',
                    'method': lambda: type('MockContext', (), {
                        'user_id': 'demo-user-001',
                        'session_id': 'direct-session-001',
                        'request_id': 'direct-req-001',
                        'is_test': True
                    }()
                }
            ]

            contexts_created = {}
            managers_per_context = {}

            for pattern in creation_patterns:
                try:
                    # Create context using this pattern
                    context = pattern['method']()
                    contexts_created[pattern['name']] = context

                    # Get WebSocket manager for this context
                    manager = get_websocket_manager(user_context=context)
                    managers_per_context[pattern['name']] = {
                        'manager_id': id(manager) if manager else None,
                        'manager_obj': manager,
                        'context_user_id': getattr(context, 'user_id', 'unknown'),
                        'context_type': type(context).__name__
                    }

                    self.logger.info(
                        f"Pattern {pattern['name']}: context={type(context).__name__}, 
                        fmanager={id(manager) if manager else None}
                    )

                except Exception as e:
                    self.logger.error(fContext creation failed for {pattern['name']}: {e})
                    factory_bypass_results.append({
                        'pattern': pattern['name'],
                        'bypass_type': 'creation_failed',
                        'error': str(e)
                    }

            # Analyze consistency across context creation patterns
            manager_ids_by_pattern = {
                pattern: info['manager_id']
                for pattern, info in managers_per_context.items()
                if info['manager_id'] is not None
            }

            unique_managers_across_patterns = set(manager_ids_by_pattern.values())

            # Check for context-specific violations
            for pattern_name, info in managers_per_context.items():
                user_id = info['context_user_id']
                if user_id != 'demo-user-001':
                    context_consistency_violations.append({
                        'pattern': pattern_name,
                        'violation_type': 'user_id_mismatch',
                        'expected_user': 'demo-user-001',
                        'actual_user': user_id
                    }

                # Check for manager inconsistency across patterns
                if len(unique_managers_across_patterns) > 1:
                    other_managers = [
                        (p, mid) for p, mid in manager_ids_by_pattern.items()
                        if p != pattern_name and mid != info['manager_id']
                    ]
                    if other_managers:
                        factory_bypass_results.append({
                            'pattern': pattern_name,
                            'bypass_type': 'manager_inconsistency',
                            'manager_id': info['manager_id'],
                            'conflicting_patterns': other_managers
                        }

            self.logger.critical(
                fFACTORY INTEGRATION ANALYSIS: ""
                f{len(contexts_created)} contexts created, 
                f{len(unique_managers_across_patterns)} unique managers, 
                f"{len(factory_bypass_results)} bypass violations, 
                f{len(context_consistency_violations)} context violations"
            )

            # EXPECTED FAILURE: All patterns should produce same manager for demo-user-001
            self.assertEqual(
                len(unique_managers_across_patterns), 1,
                fFACTORY INTEGRATION BYPASS: Expected 1 shared manager across all context creation patterns, 
                fgot {len(unique_managers_across_patterns)} managers: {unique_managers_across_patterns}. "
                f"Pattern breakdown: {manager_ids_by_pattern}. 
                fThis reproduces Issue #889 factory bypass violations.
            )

            # EXPECTED FAILURE: No factory bypass violations should occur
            self.assertEqual(
                len(factory_bypass_results), 0,
                fFACTORY BYPASS VIOLATIONS: {len(factory_bypass_results)} bypass patterns detected: {factory_bypass_results}. 
                fThis reproduces Issue #889 SSOT factory integration failures.""
            )

            # EXPECTED FAILURE: No context consistency violations should occur
            self.assertEqual(
                len(context_consistency_violations), 0,
                fCONTEXT CONSISTENCY VIOLATIONS: {len(context_consistency_violations)} violations detected: {context_consistency_violations}. 
                fThis reproduces Issue #889 context creation inconsistencies.
            )

        except Exception as e:
            self.logger.error(f"Failed to test user context factory integration: {e})
            self.fail(fCould not reproduce factory integration failures: {e}")"


if __name__ == '__main__':
    # Configure logging for integration test visibility
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run integration tests with detailed output
    unittest.main(verbosity=2)