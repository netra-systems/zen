"""
Test Child Context Inheritance Isolation Patterns

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Ensure child agent operations maintain user isolation while enabling hierarchical workflows
- Value Impact: Enables complex multi-step AI workflows without compromising user data security
- Strategic Impact: CRITICAL - Child contexts enable sub-agent patterns while maintaining security boundaries

This test suite validates that child context inheritance maintains complete user isolation:
- Child contexts inherit parent data correctly but remain isolated objects
- Hierarchical operation tracking works without shared state
- Concurrent child operations don't interfere with each other
- Deep nesting maintains isolation at all levels
- Parent-child relationships are traceable without leaking data

Architecture Tested:
- UserExecutionContext.create_child_context() patterns
- Child context inheritance with proper isolation
- Operation depth tracking and hierarchy management
- Child context cleanup doesn't affect parent or siblings
"""
import asyncio
import pytest
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from netra_backend.app.services.user_execution_context import UserExecutionContext, UserContextFactory, InvalidContextError, ContextIsolationError, validate_user_context
from test_framework.ssot.base_test_case import SSotBaseTestCase

class ChildContextInheritanceIsolationTests(SSotBaseTestCase):
    """Test child context inheritance maintains complete isolation."""

    def setup_method(self):
        """Set up test environment."""
        self.parent_contexts: List[UserExecutionContext] = []
        self.child_contexts: List[UserExecutionContext] = []

    def teardown_method(self):
        """Clean up test resources."""
        self.parent_contexts.clear()
        self.child_contexts.clear()

    def test_child_context_inherits_parent_data_with_isolation(self):
        """Test child context inherits parent data while maintaining object isolation."""
        parent_context = UserContextFactory.create_context(user_id='parent_inheritance_user', thread_id='parent_inheritance_thread', run_id='parent_inheritance_run')
        parent_context.agent_context.update({'parent_workflow': 'data_analysis', 'parent_permissions': ['read', 'write', 'execute'], 'parent_config': {'timeout': 30, 'retries': 3}, 'shared_state': {'session_data': 'important_data'}})
        parent_context.audit_metadata.update({'parent_initiated_at': datetime.now(timezone.utc).isoformat(), 'parent_source': 'api_request', 'parent_trace_id': 'parent_trace_12345'})
        self.parent_contexts.append(parent_context)
        child_context = parent_context.create_child_context(operation_name='data_validation', additional_agent_context={'child_workflow': 'validation_step_1', 'child_permissions': ['validate', 'report'], 'validation_config': {'strict_mode': True}}, additional_audit_metadata={'child_initiated_at': datetime.now(timezone.utc).isoformat(), 'child_operation': 'validation', 'child_trace_id': 'child_trace_67890'})
        self.child_contexts.append(child_context)
        assert child_context.user_id == parent_context.user_id
        assert child_context.thread_id == parent_context.thread_id
        assert child_context.run_id == parent_context.run_id
        assert child_context.parent_request_id == parent_context.request_id
        assert child_context.operation_depth == parent_context.operation_depth + 1
        assert child_context.agent_context['parent_workflow'] == 'data_analysis'
        assert child_context.agent_context['parent_permissions'] == ['read', 'write', 'execute']
        assert child_context.agent_context['parent_config'] == {'timeout': 30, 'retries': 3}
        assert child_context.agent_context['shared_state'] == {'session_data': 'important_data'}
        assert child_context.audit_metadata['parent_initiated_at'] == parent_context.audit_metadata['parent_initiated_at']
        assert child_context.audit_metadata['parent_source'] == 'api_request'
        assert child_context.audit_metadata['parent_trace_id'] == 'parent_trace_12345'
        assert child_context.agent_context['child_workflow'] == 'validation_step_1'
        assert child_context.agent_context['child_permissions'] == ['validate', 'report']
        assert child_context.agent_context['validation_config'] == {'strict_mode': True}
        assert 'child_initiated_at' in child_context.audit_metadata
        assert child_context.audit_metadata['child_operation'] == 'validation'
        assert child_context.audit_metadata['child_trace_id'] == 'child_trace_67890'
        assert id(child_context.agent_context) != id(parent_context.agent_context), 'Child agent_context shares object reference with parent - ISOLATION VIOLATION'
        assert id(child_context.audit_metadata) != id(parent_context.audit_metadata), 'Child audit_metadata shares object reference with parent - ISOLATION VIOLATION'
        assert child_context.request_id != parent_context.request_id, 'Child should have unique request_id'
        assert child_context.verify_isolation() is True
        assert parent_context.verify_isolation() is True

    def test_child_context_modification_isolation(self):
        """Test that modifications to child context don't affect parent or siblings."""
        parent_context = UserContextFactory.create_context(user_id='modification_user', thread_id='modification_thread', run_id='modification_run')
        parent_context.agent_context['shared_data'] = {'original': 'value'}
        parent_context.audit_metadata['parent_metadata'] = 'original_metadata'
        self.parent_contexts.append(parent_context)
        children = []
        for i in range(3):
            child = parent_context.create_child_context(operation_name=f'child_operation_{i}', additional_agent_context={f'child_{i}_data': f'child_value_{i}'}, additional_audit_metadata={f'child_{i}_audit': f'child_audit_{i}'})
            children.append(child)
            self.child_contexts.append(child)
        for i, child in enumerate(children):
            assert child.agent_context['shared_data'] == {'original': 'value'}
            assert child.audit_metadata['parent_metadata'] == 'original_metadata'
            assert child.agent_context[f'child_{i}_data'] == f'child_value_{i}'
        children[1].agent_context['shared_data']['modified_by'] = 'child_1'
        children[1].agent_context['new_child1_data'] = 'child1_specific'
        children[1].audit_metadata['modified_metadata'] = 'child1_modified'
        assert parent_context.agent_context['shared_data'] == {'original': 'value'}, 'Parent context contaminated by child modification - ISOLATION VIOLATION'
        assert 'new_child1_data' not in parent_context.agent_context, 'Parent context contaminated with child-specific data - ISOLATION VIOLATION'
        assert 'modified_metadata' not in parent_context.audit_metadata, 'Parent audit_metadata contaminated by child - ISOLATION VIOLATION'
        for i, child in enumerate(children):
            if i != 1:
                assert child.agent_context['shared_data'] == {'original': 'value'}, f'Child {i} contaminated by sibling modification - ISOLATION VIOLATION'
                assert 'new_child1_data' not in child.agent_context, f'Child {i} contaminated with child1-specific data - ISOLATION VIOLATION'
                assert 'modified_metadata' not in child.audit_metadata, f'Child {i} audit_metadata contaminated by sibling - ISOLATION VIOLATION'
        modified_child = children[1]
        assert modified_child.agent_context['shared_data']['modified_by'] == 'child_1'
        assert modified_child.agent_context['new_child1_data'] == 'child1_specific'
        assert modified_child.audit_metadata['modified_metadata'] == 'child1_modified'

    def test_deep_child_context_hierarchy_isolation(self):
        """Test deep hierarchical child contexts maintain isolation at all levels."""
        root_context = UserContextFactory.create_context(user_id='hierarchy_user', thread_id='hierarchy_thread', run_id='hierarchy_run')
        root_context.agent_context['level_0_data'] = 'root_level'
        root_context.audit_metadata['hierarchy_start'] = datetime.now(timezone.utc).isoformat()
        contexts = [root_context]
        max_depth = 4
        for depth in range(1, max_depth + 1):
            parent = contexts[-1]
            child = parent.create_child_context(operation_name=f'operation_level_{depth}', additional_agent_context={f'level_{depth}_data': f'data_at_level_{depth}', f'operation_specific': f'level_{depth}_operation'}, additional_audit_metadata={f'level_{depth}_timestamp': datetime.now(timezone.utc).isoformat(), f'level_{depth}_operation': f'operation_level_{depth}'})
            contexts.append(child)
            assert child.operation_depth == depth
            assert child.parent_request_id == parent.request_id
            for level in range(depth):
                assert child.agent_context[f'level_{level}_data'] == f'data_at_level_{level}' if level > 0 else 'root_level'
        self.parent_contexts.append(root_context)
        self.child_contexts.extend(contexts[1:])
        for i, ctx1 in enumerate(contexts):
            for j, ctx2 in enumerate(contexts):
                if i != j:
                    assert ctx1.request_id != ctx2.request_id
                    assert id(ctx1.agent_context) != id(ctx2.agent_context), f'Level {i} and {j} share agent_context object - ISOLATION VIOLATION'
                    assert id(ctx1.audit_metadata) != id(ctx2.audit_metadata), f'Level {i} and {j} share audit_metadata object - ISOLATION VIOLATION'
        deepest_context = contexts[-1]
        deepest_context.agent_context['deep_modification'] = 'modified_at_level_4'
        for i, ctx in enumerate(contexts[:-1]):
            assert 'deep_modification' not in ctx.agent_context, f'Level {i} contaminated by deep level modification - ISOLATION VIOLATION'
        for depth, ctx in enumerate(contexts):
            assert ctx.operation_depth == depth, f'Context at level {depth} has wrong operation_depth'
        deepest = contexts[-1]
        assert deepest.agent_context['level_0_data'] == 'root_level'
        for level in range(1, max_depth + 1):
            assert deepest.agent_context[f'level_{level}_data'] == f'data_at_level_{level}'

    def test_concurrent_child_context_creation_isolation(self):
        """Test concurrent child context creation maintains isolation."""
        parent_context = UserContextFactory.create_context(user_id='concurrent_parent_user', thread_id='concurrent_parent_thread', run_id='concurrent_parent_run')
        parent_context.agent_context['shared_config'] = {'concurrent': True, 'max_threads': 10}
        parent_context.audit_metadata['parent_id'] = 'concurrent_parent_12345'
        self.parent_contexts.append(parent_context)

        def create_child_context(child_index: int) -> UserExecutionContext:
            """Create a child context with specific data."""
            return parent_context.create_child_context(operation_name=f'concurrent_operation_{child_index}', additional_agent_context={f'child_{child_index}_data': f'concurrent_value_{child_index}', 'thread_id': threading.current_thread().ident, 'creation_order': child_index}, additional_audit_metadata={f'child_{child_index}_created': datetime.now(timezone.utc).isoformat(), 'concurrent_creation': True})
        num_children = 10
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {executor.submit(create_child_context, i): i for i in range(num_children)}
            child_contexts = {}
            for future in as_completed(future_to_index):
                child_index = future_to_index[future]
                try:
                    child_context = future.result(timeout=10)
                    child_contexts[child_index] = child_context
                    self.child_contexts.append(child_context)
                except Exception as e:
                    pytest.fail(f'Concurrent child context creation failed for index {child_index}: {e}')
        assert len(child_contexts) == num_children
        children_list = list(child_contexts.values())
        for i, child1 in enumerate(children_list):
            assert child1.user_id == parent_context.user_id
            assert child1.parent_request_id == parent_context.request_id
            assert child1.agent_context['shared_config'] == {'concurrent': True, 'max_threads': 10}
            assert child1.audit_metadata['parent_id'] == 'concurrent_parent_12345'
            assert child1.request_id != parent_context.request_id
            assert child1.verify_isolation() is True
            for j, child2 in enumerate(children_list):
                if i != j:
                    assert child1.request_id != child2.request_id, f'Children {i} and {j} have same request_id - ISOLATION VIOLATION'
                    assert id(child1.agent_context) != id(child2.agent_context), f'Concurrent children {i} and {j} share agent_context - ISOLATION VIOLATION'
                    assert id(child1.audit_metadata) != id(child2.audit_metadata), f'Concurrent children {i} and {j} share audit_metadata - ISOLATION VIOLATION'
                    creation_order_1 = child1.agent_context['creation_order']
                    creation_order_2 = child2.agent_context['creation_order']
                    child_data_key_1 = f'child_{creation_order_1}_data'
                    child_data_key_2 = f'child_{creation_order_2}_data'
                    assert child_data_key_2 not in child1.agent_context, f'Child {i} contains data from child {j} - ISOLATION VIOLATION'
                    assert child_data_key_1 not in child2.agent_context, f'Child {j} contains data from child {i} - ISOLATION VIOLATION'

    def test_child_context_supervisor_compatibility_isolation(self):
        """Test supervisor-compatible child context creation maintains isolation."""
        parent_context = UserContextFactory.create_context(user_id='supervisor_parent_user', thread_id='supervisor_parent_thread', run_id='supervisor_parent_run')
        parent_unified_metadata = {'workflow_state': 'in_progress', 'agent_permissions': ['read', 'write', 'execute'], 'audit_trail_id': 'supervisor_audit_12345', 'parent_operation': 'main_workflow', 'operation_depth': 0}
        parent_with_metadata = parent_context.from_request_supervisor(user_id=parent_context.user_id, thread_id=parent_context.thread_id, run_id=parent_context.run_id, request_id=parent_context.request_id, metadata=parent_unified_metadata)
        self.parent_contexts.append(parent_with_metadata)
        child_additional_metadata = {'child_workflow_state': 'processing', 'child_specific_permissions': ['validate'], 'child_audit_data': 'supervisor_child_audit_67890'}
        child_context = parent_with_metadata.create_child_context_supervisor(operation_name='supervisor_child_operation', additional_metadata=child_additional_metadata)
        self.child_contexts.append(child_context)
        assert child_context.user_id == parent_with_metadata.user_id
        assert child_context.parent_request_id == parent_with_metadata.request_id
        assert child_context.operation_depth == 1
        child_unified = child_context.metadata
        assert child_unified['workflow_state'] == 'in_progress'
        assert child_unified['agent_permissions'] == ['read', 'write', 'execute']
        assert child_unified['audit_trail_id'] == 'supervisor_audit_12345'
        assert child_unified['child_workflow_state'] == 'processing'
        assert child_unified['child_specific_permissions'] == ['validate']
        assert child_unified['child_audit_data'] == 'supervisor_child_audit_67890'
        assert child_unified['parent_request_id'] == parent_with_metadata.request_id
        assert child_unified['operation_name'] == 'supervisor_child_operation'
        assert child_unified['operation_depth'] == 1
        assert id(child_context.agent_context) != id(parent_with_metadata.agent_context), 'Supervisor child shares agent_context with parent - ISOLATION VIOLATION'
        assert id(child_context.audit_metadata) != id(parent_with_metadata.audit_metadata), 'Supervisor child shares audit_metadata with parent - ISOLATION VIOLATION'
        assert child_context.verify_isolation() is True
        assert parent_with_metadata.verify_isolation() is True
        child_context.metadata['child_modification'] = 'supervisor_child_modified'
        parent_unified = parent_with_metadata.metadata
        assert 'child_modification' not in parent_unified, 'Parent metadata contaminated by supervisor child modification - ISOLATION VIOLATION'

    def test_child_context_error_conditions_isolation(self):
        """Test child context error conditions maintain isolation."""
        parent_context = UserContextFactory.create_context(user_id='error_test_user', thread_id='error_test_thread', run_id='error_test_run')
        self.parent_contexts.append(parent_context)
        with pytest.raises(InvalidContextError, match='operation_name must be a non-empty string'):
            parent_context.create_child_context(operation_name='')
        with pytest.raises(InvalidContextError, match='operation_name must be a non-empty string'):
            parent_context.create_child_context(operation_name=None)
        with pytest.raises(InvalidContextError, match='operation_name must be a non-empty string'):
            parent_context.create_child_context(operation_name='   ')
        deep_context = parent_context
        max_allowed_depth = 10
        for depth in range(1, max_allowed_depth + 1):
            deep_context = deep_context.create_child_context(operation_name=f'depth_test_{depth}')
            self.child_contexts.append(deep_context)
        assert deep_context.operation_depth == max_allowed_depth
        with pytest.raises(InvalidContextError, match='Maximum operation depth .* exceeded'):
            deep_context.create_child_context(operation_name='beyond_max_depth')
        assert parent_context.verify_isolation() is True
        assert parent_context.operation_depth == 0
        assert deep_context.verify_isolation() is True
        assert deep_context.operation_depth == max_allowed_depth
        current = deep_context
        depth = max_allowed_depth
        while current.parent_request_id is not None:
            assert current.operation_depth == depth
            assert current.verify_isolation() is True
            depth -= 1
            break

    def test_child_context_metadata_merge_isolation(self):
        """Test child context metadata merging maintains isolation."""
        parent_context = UserContextFactory.create_context(user_id='merge_test_user', thread_id='merge_test_thread', run_id='merge_test_run')
        parent_context.agent_context.update({'nested_config': {'database': {'host': 'parent_db', 'port': 5432}, 'api_keys': {'service_a': 'parent_key_a', 'service_b': 'parent_key_b'}, 'permissions': {'read': True, 'write': True, 'admin': False}}, 'simple_values': ['parent_value_1', 'parent_value_2'], 'parent_only': 'parent_specific_data'})
        parent_context.audit_metadata.update({'security_context': {'user_roles': ['user', 'analyst'], 'access_level': 'standard', 'session_info': {'ip': '192.168.1.1', 'browser': 'chrome'}}, 'tracking': {'parent_initiated': True, 'source': 'api'}})
        self.parent_contexts.append(parent_context)
        child_context = parent_context.create_child_context(operation_name='metadata_merge_test', additional_agent_context={'nested_config': {'database': {'timeout': 30}, 'api_keys': {'service_c': 'child_key_c'}, 'child_specific': {'feature_x': True}}, 'simple_values': ['child_value_1'], 'child_only': 'child_specific_data'}, additional_audit_metadata={'security_context': {'child_permissions': {'validate': True}, 'operation_level': 'child'}, 'child_tracking': {'child_initiated': True, 'child_source': 'parent_delegation'}})
        self.child_contexts.append(child_context)
        child_agent = child_context.agent_context
        child_audit = child_context.audit_metadata
        assert 'parent_only' in child_agent
        assert child_agent['parent_only'] == 'parent_specific_data'
        assert 'nested_config' in child_agent
        child_nested = child_agent['nested_config']
        assert child_nested['database']['host'] == 'parent_db'
        assert child_nested['database']['port'] == 5432
        assert child_nested['api_keys']['service_a'] == 'parent_key_a'
        assert child_nested['api_keys']['service_b'] == 'parent_key_b'
        assert child_nested['permissions']['read'] is True
        assert child_nested['permissions']['write'] is True
        assert child_nested['permissions']['admin'] is False
        assert child_nested['database']['timeout'] == 30
        assert child_nested['api_keys']['service_c'] == 'child_key_c'
        assert child_nested['child_specific']['feature_x'] is True
        assert child_agent['simple_values'] == ['child_value_1']
        assert child_agent['child_only'] == 'child_specific_data'
        assert child_audit['tracking']['parent_initiated'] is True
        assert child_audit['tracking']['source'] == 'api'
        assert child_audit['child_tracking']['child_initiated'] is True
        assert child_audit['security_context']['user_roles'] == ['user', 'analyst']
        assert child_audit['security_context']['access_level'] == 'standard'
        assert child_audit['security_context']['child_permissions']['validate'] is True
        assert id(child_context.agent_context) != id(parent_context.agent_context), 'Child agent_context shares object with parent - ISOLATION VIOLATION'
        assert id(child_context.audit_metadata) != id(parent_context.audit_metadata), 'Child audit_metadata shares object with parent - ISOLATION VIOLATION'
        assert id(child_agent['nested_config']) != id(parent_context.agent_context['nested_config']), 'Child nested_config shares object with parent - ISOLATION VIOLATION'
        assert id(child_audit['security_context']) != id(parent_context.audit_metadata['security_context']), 'Child security_context shares object with parent - ISOLATION VIOLATION'
        child_agent['nested_config']['database']['child_modification'] = 'child_db_change'
        child_audit['security_context']['child_audit_modification'] = 'child_security_change'
        parent_nested = parent_context.agent_context['nested_config']
        parent_security = parent_context.audit_metadata['security_context']
        assert 'child_modification' not in parent_nested['database'], 'Parent nested database contaminated by child - ISOLATION VIOLATION'
        assert 'child_audit_modification' not in parent_security, 'Parent security_context contaminated by child - ISOLATION VIOLATION'
        assert parent_context.verify_isolation() is True
        assert child_context.verify_isolation() is True
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')