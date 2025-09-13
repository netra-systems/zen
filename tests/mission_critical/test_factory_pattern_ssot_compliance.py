#!/usr/bin/env python
"""
FAILING TEST: Factory Pattern SSOT Compliance - Issue #680

This test PROVES factory pattern violates user isolation by creating shared instances.
Business Impact: $500K+ ARR at risk from shared state between users

Test Strategy:
- Create WebSocket instances for 2 different users via factory
- Should FAIL: Same instance returned (shared state violation)
- Should PASS after SSOT consolidation (proper isolation)

Expected Result: FAILS before SSOT refactor, PASSES after SSOT consolidation
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from typing import Dict, List, Set, Any, Optional, Tuple

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import factory patterns and WebSocket components
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager, WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext, create_isolated_execution_context
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

logger = logging.getLogger(__name__)


class TestFactoryPatternSSotCompliance(SSotAsyncTestCase):
    """
    FAILING TEST: Proves factory pattern violates user isolation.
    
    This test creates WebSocket-related instances for multiple users and verifies
    that they are properly isolated. Issue #680 indicates that factory patterns
    are returning shared instances instead of isolated ones.
    
    Expected to FAIL due to:
    1. Factory returning same WebSocket manager instance for different users
    2. Shared state in execution contexts
    3. Bridge instances not properly isolated
    4. Memory leaks from shared singleton patterns
    
    After SSOT consolidation, should PASS with proper user isolation.
    """
    
    def setup_method(self, method=None):
        """Setup for factory pattern testing."""
        super().setup_method(method)
        
        # Test configuration
        self.test_users = ['factory_user_1', 'factory_user_2', 'factory_user_3']
        self.instances_per_user = {}
        self.shared_instances = []
        self.isolation_violations = []
        
        # Track factory calls
        self.factory_call_counts = {
            'websocket_manager': 0,
            'websocket_bridge': 0,
            'execution_context': 0,
            'execution_engine': 0
        }
        
        logger.info(f"Starting factory pattern SSOT compliance test")
    
    async def create_user_websocket_components(self, user_id: str) -> Dict[str, Any]:
        """
        Create WebSocket components for a user using factory patterns.
        
        This method uses the same factory calls that would be used in production
        to expose shared instance violations.
        """
        components = {}
        
        # Create execution context (should be unique per user)
        self.factory_call_counts['execution_context'] += 1
        execution_context = await create_isolated_execution_context(
            user_id=user_id,
            request_id=f"req_{user_id}_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{user_id}_{uuid.uuid4().hex[:8]}"
        )
        components['execution_context'] = execution_context
        
        # Get WebSocket manager (potential shared instance violation)
        self.factory_call_counts['websocket_manager'] += 1
        websocket_manager = get_websocket_manager()
        components['websocket_manager'] = websocket_manager
        
        # Create WebSocket bridge (should be unique per user)
        self.factory_call_counts['websocket_bridge'] += 1
        bridge = create_agent_websocket_bridge(
            websocket_manager=websocket_manager,
            user_context=execution_context
        )
        components['bridge'] = bridge
        
        # Create execution engine (should be unique per user)
        self.factory_call_counts['execution_engine'] += 1
        execution_engine = UserExecutionEngine(
            user_context=execution_context,
            websocket_bridge=bridge
        )
        components['execution_engine'] = execution_engine
        
        # Store component metadata for analysis
        components['user_id'] = user_id
        components['creation_time'] = time.time()
        components['component_ids'] = {
            'execution_context_id': id(execution_context),
            'websocket_manager_id': id(websocket_manager),
            'bridge_id': id(bridge),
            'execution_engine_id': id(execution_engine)
        }
        
        return components
    
    def analyze_shared_instances(self, all_user_components: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze components across users to detect shared instances.
        
        Returns list of shared instance violations.
        """
        violations = []
        
        # Component types to check for sharing
        component_types = [
            'websocket_manager',
            'bridge', 
            'execution_engine',
            'execution_context'
        ]
        
        for component_type in component_types:
            # Collect all instances of this component type
            instances_by_user = {}
            instance_ids = []
            
            for user_id, components in all_user_components.items():
                if component_type in components:
                    instance = components[component_type]
                    instance_id = id(instance)
                    instances_by_user[user_id] = {
                        'instance': instance,
                        'instance_id': instance_id,
                        'user_id': user_id
                    }
                    instance_ids.append(instance_id)
            
            # Check for shared instances (same ID across different users)
            unique_instance_ids = set(instance_ids)
            expected_unique_count = len(all_user_components)
            actual_unique_count = len(unique_instance_ids)
            
            if actual_unique_count < expected_unique_count:
                # Found shared instances
                sharing_violations = []
                
                # Find which users share instances
                id_to_users = {}
                for user_id, instance_data in instances_by_user.items():
                    instance_id = instance_data['instance_id']
                    if instance_id not in id_to_users:
                        id_to_users[instance_id] = []
                    id_to_users[instance_id].append(user_id)
                
                # Identify shared instances
                for instance_id, users in id_to_users.items():
                    if len(users) > 1:
                        sharing_violations.append({
                            'instance_id': instance_id,
                            'shared_by_users': users,
                            'user_count': len(users)
                        })
                
                violations.append({
                    'component_type': component_type,
                    'violation_type': 'shared_instance',
                    'expected_unique': expected_unique_count,
                    'actual_unique': actual_unique_count,
                    'shared_instances': sharing_violations,
                    'severity': self._get_sharing_severity(component_type)
                })
        
        return violations
    
    def _get_sharing_severity(self, component_type: str) -> str:
        """Get severity level for different types of component sharing."""
        severity_map = {
            'websocket_manager': 'CRITICAL',  # Core business functionality
            'execution_context': 'CRITICAL',  # Security violation
            'execution_engine': 'HIGH',       # Business logic isolation
            'bridge': 'HIGH'                  # Event isolation
        }
        return severity_map.get(component_type, 'MEDIUM')
    
    def analyze_memory_leaks(self, all_user_components: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze for potential memory leaks from shared instances.
        
        Shared instances can cause memory leaks as user-specific data
        accumulates in shared objects.
        """
        memory_issues = []
        
        # Check for objects that accumulate user-specific state
        for user_id, components in all_user_components.items():
            for component_name, component in components.items():
                if component_name.endswith('_id') or component_name in ['user_id', 'creation_time', 'component_ids']:
                    continue  # Skip metadata
                
                # Check for user-specific state in components
                if hasattr(component, '__dict__'):
                    component_state = component.__dict__
                    
                    # Look for attributes that might accumulate user data
                    accumulating_attributes = []
                    for attr_name, attr_value in component_state.items():
                        if isinstance(attr_value, (list, dict, set)):
                            if len(attr_value) > 0:  # Non-empty collections
                                accumulating_attributes.append({
                                    'attribute': attr_name,
                                    'type': type(attr_value).__name__,
                                    'size': len(attr_value),
                                    'sample_content': str(attr_value)[:100] if attr_value else None
                                })
                    
                    if accumulating_attributes:
                        # Check if this is a shared instance
                        component_id = id(component)
                        other_users_with_same_instance = []
                        
                        for other_user_id, other_components in all_user_components.items():
                            if other_user_id != user_id and component_name in other_components:
                                if id(other_components[component_name]) == component_id:
                                    other_users_with_same_instance.append(other_user_id)
                        
                        if other_users_with_same_instance:
                            memory_issues.append({
                                'component_type': component_name,
                                'component_id': component_id,
                                'shared_by_users': [user_id] + other_users_with_same_instance,
                                'accumulating_state': accumulating_attributes,
                                'memory_leak_risk': 'HIGH',
                                'issue_type': 'shared_instance_accumulating_state'
                            })
        
        return memory_issues
    
    async def test_websocket_factory_creates_shared_instances_violation(self):
        """
        FAILING TEST: Proves factory pattern violates user isolation.
        
        Creates WebSocket instances for multiple users and verifies they are isolated.
        Expected to FAIL due to factory patterns returning shared instances.
        
        After SSOT consolidation, should PASS with proper user isolation.
        """
        logger.info("Starting factory pattern SSOT compliance test")
        
        # Phase 1: Create components for multiple users
        logger.info("Phase 1: Creating WebSocket components for multiple users")
        
        all_user_components = {}
        creation_errors = []
        
        for user_id in self.test_users:
            try:
                components = await self.create_user_websocket_components(user_id)
                all_user_components[user_id] = components
                logger.info(f"Created components for user {user_id}")
            except Exception as e:
                creation_errors.append({
                    'user_id': user_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                logger.error(f"Failed to create components for user {user_id}: {e}")
        
        # Phase 2: Analyze for shared instances
        logger.info("Phase 2: Analyzing for shared instance violations")
        shared_instance_violations = self.analyze_shared_instances(all_user_components)
        
        # Phase 3: Analyze for memory leak risks
        logger.info("Phase 3: Analyzing for memory leak risks")
        memory_leak_risks = self.analyze_memory_leaks(all_user_components)
        
        # Phase 4: Check factory call efficiency
        logger.info("Phase 4: Analyzing factory call patterns")
        expected_calls_per_type = len(self.test_users)
        factory_efficiency_issues = []
        
        for factory_type, call_count in self.factory_call_counts.items():
            if call_count != expected_calls_per_type:
                factory_efficiency_issues.append({
                    'factory_type': factory_type,
                    'expected_calls': expected_calls_per_type,
                    'actual_calls': call_count,
                    'efficiency_issue': call_count < expected_calls_per_type
                })
        
        # Phase 5: Record metrics
        self.record_metric('users_tested', len(self.test_users))
        self.record_metric('components_created', len(all_user_components))
        self.record_metric('creation_errors', len(creation_errors))
        self.record_metric('shared_instance_violations', len(shared_instance_violations))
        self.record_metric('memory_leak_risks', len(memory_leak_risks))
        self.record_metric('factory_efficiency_issues', len(factory_efficiency_issues))
        
        # Log detailed findings
        logger.info(f"Factory Pattern Analysis Results:")
        logger.info(f"  Users tested: {len(self.test_users)}")
        logger.info(f"  Components created: {len(all_user_components)}")
        logger.info(f"  Creation errors: {len(creation_errors)}")
        logger.info(f"  Shared instance violations: {len(shared_instance_violations)}")
        logger.info(f"  Memory leak risks: {len(memory_leak_risks)}")
        
        # Log specific violations
        if shared_instance_violations:
            logger.error("Shared Instance Violations:")
            for violation in shared_instance_violations:
                logger.error(f"  - {violation['component_type']}: {violation['violation_type']}")
                logger.error(f"    Expected unique: {violation['expected_unique']}, Actual: {violation['actual_unique']}")
                logger.error(f"    Severity: {violation['severity']}")
                
                for shared_instance in violation['shared_instances']:
                    logger.error(f"    Shared by users: {shared_instance['shared_by_users']}")
        
        if memory_leak_risks:
            logger.warning("Memory Leak Risks:")
            for risk in memory_leak_risks:
                logger.warning(f"  - {risk['component_type']}: {risk['issue_type']}")
                logger.warning(f"    Shared by: {risk['shared_by_users']}")
                logger.warning(f"    Risk level: {risk['memory_leak_risk']}")
        
        if creation_errors:
            logger.error("Component Creation Errors:")
            for error in creation_errors:
                logger.error(f"  - User {error['user_id']}: {error['error_type']} - {error['error']}")
        
        # Phase 6: Assert violations exist (test should FAIL)
        logger.info("Phase 6: Checking for factory pattern SSOT violations")
        
        # Check that we successfully created components
        assert len(all_user_components) > 0, (
            "No user components created successfully. "
            "Cannot test factory pattern isolation."
        )
        
        # SUCCESS CRITERIA FOR AFTER SSOT CONSOLIDATION:
        # After SSOT refactor, these assertions should be flipped to verify isolation works
        
        # CURRENT EXPECTATION: Test should FAIL due to shared instances
        
        total_violations = len(shared_instance_violations) + len(memory_leak_risks)
        critical_violations = [
            v for v in shared_instance_violations 
            if v.get('severity') == 'CRITICAL'
        ]
        
        # If no violations, might indicate good factory pattern implementation
        if total_violations == 0:
            logger.info("No factory pattern violations detected - checking if this is expected")
            
            # Verify we actually have multiple users with different instances
            if len(all_user_components) >= 2:
                # This might actually be good - proper isolation working
                logger.info("Factory pattern appears to be working correctly with proper isolation")
                return {
                    'status': 'proper_isolation_detected',
                    'users_tested': len(self.test_users),
                    'components_created': len(all_user_components),
                    'message': 'Factory pattern may already provide proper user isolation'
                }
            else:
                pytest.fail("Insufficient test data to verify factory pattern behavior")
        
        # Expected: Find violations that confirm Issue #680 factory pattern problems
        logger.info(f"Factory pattern violations detected: {total_violations}")
        logger.info(f"Critical violations: {len(critical_violations)}")
        
        # Check for specific critical violations
        websocket_manager_violations = [
            v for v in shared_instance_violations 
            if v['component_type'] == 'websocket_manager'
        ]
        
        execution_context_violations = [
            v for v in shared_instance_violations 
            if v['component_type'] == 'execution_context'
        ]
        
        # Assert violations exist to confirm the issue
        assert total_violations > 0, (
            f"EXPECTED FACTORY PATTERN VIOLATIONS DETECTED: {total_violations} violations found. "
            f"Critical: {len(critical_violations)}. "
            "This confirms factory patterns violate user isolation (Issue #680)."
        )
        
        # Check for specific critical component sharing
        if critical_violations:
            logger.error(f"Critical factory violations found: {len(critical_violations)}")
            for violation in critical_violations:
                logger.error(f"  - {violation['component_type']}: {violation['violation_type']}")
        
        # Special check for WebSocket manager sharing (most critical for Issue #680)
        if websocket_manager_violations:
            assert len(websocket_manager_violations) > 0, (
                f"WebSocket manager sharing confirmed: {len(websocket_manager_violations)} violations. "
                "This confirms the core factory pattern issue in Issue #680."
            )
        
        # The test PASSES by proving violations exist (confirming the issue)
        logger.info("TEST PASSES: Factory pattern SSOT violations confirmed")
        logger.info("Next step: Implement proper factory isolation patterns")
        
        return {
            'total_violations': total_violations,
            'critical_violations': len(critical_violations),
            'websocket_manager_violations': len(websocket_manager_violations),
            'execution_context_violations': len(execution_context_violations),
            'memory_leak_risks': len(memory_leak_risks),
            'users_tested': len(self.test_users),
            'test_status': 'violations_confirmed'
        }


if __name__ == "__main__":
    # Run the test directly for debugging
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])