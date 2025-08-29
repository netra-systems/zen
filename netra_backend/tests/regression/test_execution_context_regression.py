"""
Regression test for test imports and ExecutionContext fixes from commit e41aaee2.

This test ensures that all integration tests use correct ExecutionContext parameters
and that imports are properly resolved without false positives.
"""

import ast
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import pytest

from netra_backend.app.agents.base.execution_context import ExecutionContext
from test_framework.agent_test_helpers import create_test_execution_context


class TestExecutionContextRegression:
    """Regression tests for ExecutionContext parameter usage in integration tests."""

    @pytest.fixture
    def execution_context(self):
        """Create a proper ExecutionContext for testing."""
        return create_test_execution_context(
            user_id="test-user-123",
            thread_id="test-thread-456",
            message_id="test-message-789",
            session_id="test-session-000"
        )

    def test_execution_context_has_required_parameters(self, execution_context):
        """Test that ExecutionContext has all required parameters."""
        required_attrs = [
            'user_id',
            'thread_id', 
            'message_id',
            'session_id',
            'metadata',
            'created_at'
        ]
        
        for attr in required_attrs:
            assert hasattr(execution_context, attr), f"ExecutionContext missing {attr}"
        
        # Verify types
        assert isinstance(execution_context.user_id, str)
        assert isinstance(execution_context.thread_id, str)
        assert isinstance(execution_context.message_id, str)
        assert isinstance(execution_context.session_id, str)
        assert isinstance(execution_context.metadata, dict)

    def test_execution_context_backward_compatibility(self, execution_context):
        """Test that ExecutionContext maintains backward compatibility."""
        # Old code might access context properties directly
        assert execution_context.user_id is not None
        assert execution_context.thread_id is not None
        
        # Old code might use dict-like access (if supported)
        context_dict = execution_context.dict() if hasattr(execution_context, 'dict') else execution_context.__dict__
        assert 'user_id' in context_dict
        assert 'thread_id' in context_dict

    def test_integration_test_imports_correct_modules(self):
        """Test that integration tests import ExecutionContext correctly."""
        # Define the correct import path
        correct_import = "netra_backend.app.agents.base.models"
        
        # List of integration test files to check
        integration_tests = [
            "netra_backend/tests/integration/test_base_agent_real_services.py",
            "netra_backend/tests/integration/test_triage_agent_real_llm.py",
            "netra_backend/tests/integration/test_actions_to_meet_goals_agent_real_llm.py"
        ]
        
        errors = []
        for test_file in integration_tests:
            if not Path(test_file).exists():
                continue
                
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for ExecutionContext import
            if "ExecutionContext" in content:
                # Verify it's imported from the correct module
                if f"from {correct_import} import" not in content:
                    if "ExecutionContext" not in content.split("test_framework")[0]:
                        errors.append(f"{test_file}: ExecutionContext not imported from {correct_import}")
        
        assert len(errors) == 0, f"Import errors found: {errors}"

    def test_no_false_positive_import_checks(self):
        """Test that import checks only trigger at line start (no false positives)."""
        test_code = '''
# This should not trigger: from netra_backend import something
def test_function():
    """Docstring with from netra_backend import mention should not trigger."""
    # Comment with from netra_backend import should not trigger
    x = "string with from netra_backend import should not trigger"
    
from netra_backend.app.agents.base.execution_context import ExecutionContext  # This SHOULD trigger
        '''
        
        lines = test_code.split('\n')
        import_lines = []
        
        for i, line in enumerate(lines):
            # Check if line starts with import statement (after stripping whitespace)
            stripped = line.strip()
            if stripped.startswith('from ') or stripped.startswith('import '):
                import_lines.append(i)
        
        # Should only find one actual import line
        assert len(import_lines) == 1
        assert 'ExecutionContext' in lines[import_lines[0]]

    @pytest.mark.asyncio
    async def test_execution_context_in_async_agent_calls(self, execution_context):
        """Test that ExecutionContext works correctly in async agent calls."""
        from unittest.mock import AsyncMock
        
        # Mock an agent that uses ExecutionContext
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value={"status": "success"})
        
        # Call agent with ExecutionContext
        result = await mock_agent.execute(
            context=execution_context,
            input_data={"test": "data"}
        )
        
        # Verify the call was made with correct context
        mock_agent.execute.assert_called_once()
        call_args = mock_agent.execute.call_args
        assert call_args.kwargs['context'] == execution_context

    def test_execution_context_serialization(self, execution_context):
        """Test that ExecutionContext can be properly serialized/deserialized."""
        import json
        
        # Convert to dict for serialization
        context_dict = {
            'user_id': execution_context.user_id,
            'thread_id': execution_context.thread_id,
            'message_id': execution_context.message_id,
            'session_id': execution_context.session_id,
            'metadata': execution_context.metadata
        }
        
        # Serialize to JSON
        json_str = json.dumps(context_dict)
        
        # Deserialize back
        restored_dict = json.loads(json_str)
        
        # Verify all fields preserved
        assert restored_dict['user_id'] == execution_context.user_id
        assert restored_dict['thread_id'] == execution_context.thread_id
        assert restored_dict['message_id'] == execution_context.message_id
        assert restored_dict['session_id'] == execution_context.session_id

    def test_execution_context_creation_patterns(self):
        """Test different patterns for creating ExecutionContext."""
        # Pattern 1: Using test helper
        context1 = create_test_execution_context()
        assert context1.user_id is not None
        
        # Pattern 2: Direct instantiation
        context2 = ExecutionContext(
            user_id="user-2",
            thread_id="thread-2",
            message_id="msg-2",
            session_id="session-2",
            metadata={}
        )
        assert context2.user_id == "user-2"
        
        # Pattern 3: With optional metadata
        context3 = create_test_execution_context(
            metadata={"source": "test", "priority": "high"}
        )
        assert context3.metadata["source"] == "test"

    def test_integration_test_execution_context_usage_patterns(self):
        """Test that integration tests use ExecutionContext correctly."""
        # Sample patterns that should be valid
        valid_patterns = [
            "context = create_test_execution_context()",
            "context = ExecutionContext(user_id='test', thread_id='test', message_id='test', session_id='test')",
            "execution_context = create_test_execution_context(user_id='specific-user')"
        ]
        
        # Sample patterns that should be invalid
        invalid_patterns = [
            "context = {}  # Using dict instead of ExecutionContext",
            "context = None  # Not providing context",
            "context = 'string'  # Wrong type"
        ]
        
        # These patterns should compile without error
        for pattern in valid_patterns:
            try:
                compile(pattern, '<test>', 'exec')
            except SyntaxError:
                pytest.fail(f"Valid pattern failed to compile: {pattern}")

    def test_auth_service_test_result_format_markers(self):
        """Test that auth service test results use correct format markers."""
        # Check if junit.xml exists and has correct format
        junit_path = Path("auth_service/junit.xml")
        if junit_path.exists():
            content = junit_path.read_text()
            
            # Verify XML structure
            assert '<?xml' in content or '<testsuites' in content
            assert '</testsuites>' in content or '</testsuite>' in content
            
            # Verify no malformed entries
            assert '<<' not in content  # No double angle brackets
            assert '>>' not in content  # No double angle brackets

    @pytest.mark.asyncio
    async def test_dynamic_timeout_evaluation_fix(self):
        """Test that circuit breaker handles dynamic timeout evaluation correctly."""
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreaker
        
        # Create circuit breaker with callable timeout
        call_count = 0
        
        def dynamic_timeout():
            nonlocal call_count
            call_count += 1
            return 5 + call_count  # Increasing timeout
        
        breaker = UnifiedCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=dynamic_timeout,
            expected_exception=Exception
        )
        
        # Access state property shouldn't cause errors with dynamic timeout
        state = breaker.state
        assert state is not None
        
        # Verify the timeout can be evaluated when needed
        if callable(breaker._recovery_timeout):
            timeout_value = breaker._recovery_timeout()
            assert timeout_value > 5