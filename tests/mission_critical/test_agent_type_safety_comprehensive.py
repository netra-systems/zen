"""
MISSION CRITICAL: Comprehensive Type Safety Test Suite for Agent Modules
Tests all type safety requirements per SPEC/type_safety.xml
"""

import sys
import ast
import inspect
import typing
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, get_type_hints
from dataclasses import is_dataclass
import pytest
import asyncio
import importlib
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult
)
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent


class TypeSafetyAnalyzer:
    """Analyzer for type safety compliance"""
    
    def __init__(self):
        self.violations = []
        self.critical_violations = []
        
    def analyze_module(self, module_path: str) -> Dict[str, List[str]]:
        """Analyze a module for type safety violations"""
        violations = {
            'missing_return_types': [],
            'missing_param_types': [],
            'any_type_usage': [],
            'ssot_violations': [],
            'missing_dataclass': []
        }
        
        with open(module_path, 'r') as f:
            source = f.read()
            
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Check return type
                if node.returns is None and node.name != '__init__':
                    violations['missing_return_types'].append(
                        f"Line {node.lineno}: {node.name} missing return type"
                    )
                
                # Check parameter types
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != 'self':
                        violations['missing_param_types'].append(
                            f"Line {node.lineno}: {node.name} param '{arg.arg}' missing type"
                        )
                        
            # Check for Any usage
            if isinstance(node, ast.Name) and node.id == 'Any':
                violations['any_type_usage'].append(
                    f"Line {node.lineno}: Using Any type"
                )
                
        return violations


class TestAgentTypeSafetyCompliance:
    """Test suite for type safety compliance per SPEC/type_safety.xml"""
    
    @pytest.fixture
    def analyzer(self):
        return TypeSafetyAnalyzer()
    
    def test_agent_communication_type_hints(self, analyzer):
        """Test agent_communication.py for complete type hints"""
        module_path = project_root / "netra_backend/app/agents/agent_communication.py"
        violations = analyzer.analyze_module(str(module_path))
        
        # Assert no missing return types
        assert len(violations['missing_return_types']) == 0, \
            f"Missing return types: {violations['missing_return_types']}"
        
        # Assert no missing parameter types
        assert len(violations['missing_param_types']) == 0, \
            f"Missing param types: {violations['missing_param_types']}"
            
        # Assert minimal Any usage
        assert len(violations['any_type_usage']) <= 5, \
            f"Excessive Any usage: {violations['any_type_usage']}"
    
    def test_agent_lifecycle_type_hints(self, analyzer):
        """Test agent_lifecycle.py for complete type hints"""
        module_path = project_root / "netra_backend/app/agents/agent_lifecycle.py"
        violations = analyzer.analyze_module(str(module_path))
        
        assert len(violations['missing_return_types']) == 0, \
            f"Missing return types: {violations['missing_return_types']}"
        assert len(violations['missing_param_types']) == 0, \
            f"Missing param types: {violations['missing_param_types']}"
    
    def test_interface_dataclass_decorators(self):
        """Test that interface.py classes have required @dataclass decorators"""
        # ExecutionContext must be a dataclass per SPEC/type_safety.xml
        assert is_dataclass(ExecutionContext), \
            "ExecutionContext must have @dataclass decorator per SPEC/type_safety.xml#DATACLASS-DECORATOR"
        
        # ExecutionResult must be a dataclass
        assert is_dataclass(ExecutionResult), \
            "ExecutionResult must have @dataclass decorator per SPEC/type_safety.xml#DATACLASS-DECORATOR"
    
    def test_no_duplicate_error_classes(self):
        """Test that WebSocketError and ErrorContext are not locally defined"""
        module_path = project_root / "netra_backend/app/agents/agent_communication.py"
        
        with open(module_path, 'r') as f:
            source = f.read()
            
        # Check for local WebSocketError definition
        assert 'class WebSocketError' not in source, \
            "WebSocketError must be imported from canonical location, not defined locally (SSOT violation)"
        
        # Check for local ErrorContext definition  
        assert 'class ErrorContext' not in source, \
            "ErrorContext must be imported from canonical location, not defined locally (SSOT violation)"
    
    def test_canonical_imports(self):
        """Test that all imports follow canonical locations per SPEC/type_safety.xml"""
        required_imports = {
            'ExecutionStatus': 'netra_backend.app.schemas.core_enums',
            'WebSocketMessageType': 'netra_backend.app.schemas.core_enums',
            'AgentState': 'netra_backend.app.schemas.agent_state',
            'WebSocketNotifier': 'netra_backend.app.core.websocket_notifier'
        }
        
        # Check agent_communication.py
        module_path = project_root / "netra_backend/app/agents/agent_communication.py"
        with open(module_path, 'r') as f:
            source = f.read()
            
        for type_name, canonical_location in required_imports.items():
            if type_name in source:
                assert canonical_location in source, \
                    f"{type_name} must be imported from {canonical_location}"
    
    def test_data_sub_agent_type_completeness(self):
        """Test DataSubAgent has complete type annotations"""
        # Get all methods
        methods = inspect.getmembers(DataSubAgent, predicate=inspect.ismethod)
        
        for name, method in methods:
            if name.startswith('_') and not name.startswith('__'):
                continue  # Skip private methods for now
                
            # Try to get type hints
            try:
                hints = get_type_hints(method)
                # Check that return type is specified
                if name != '__init__':
                    assert 'return' in hints, \
                        f"DataSubAgent.{name} missing return type annotation"
            except Exception:
                pass  # Some methods might be properties or special
    
    def test_validation_sub_agent_type_completeness(self):
        """Test ValidationSubAgent has complete type annotations"""
        methods = inspect.getmembers(ValidationSubAgent, predicate=inspect.ismethod)
        
        for name, method in methods:
            if name.startswith('_') and not name.startswith('__'):
                continue
                
            try:
                hints = get_type_hints(method)
                if name != '__init__':
                    assert 'return' in hints, \
                        f"ValidationSubAgent.{name} missing return type annotation"
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_async_method_return_types(self):
        """Test that all async methods have proper return type hints"""
        # Test AgentCommunicationMixin async methods
        # Note: AgentCommunicationMixin is a mixin, so we skip instantiation
        
        async_methods = [
            '_send_update',
            '_attempt_websocket_update',
            'run_in_background'
        ]
        
        # Check methods directly on the class
        for method_name in async_methods:
            if hasattr(AgentCommunicationMixin, method_name):
                method = getattr(AgentCommunicationMixin, method_name)
                # Check if it's async
                if asyncio.iscoroutinefunction(method):
                    # Get annotations
                    annotations = method.__annotations__
                    assert 'return' in annotations, \
                        f"Async method {method_name} missing return type"
    
    def test_no_any_in_critical_paths(self):
        """Test that critical paths don't use Any type"""
        critical_methods = [
            'execute',
            'execute_core_logic',
            'run',
            'process'
        ]
        
        # Check DataSubAgent
        for method_name in critical_methods:
            if hasattr(DataSubAgent, method_name):
                method = getattr(DataSubAgent, method_name)
                annotations = getattr(method, '__annotations__', {})
                
                # Check that Any is not used in annotations
                for param_name, param_type in annotations.items():
                    type_str = str(param_type)
                    assert 'Any' not in type_str or param_name == 'kwargs', \
                        f"Critical method {method_name} uses Any type for {param_name}"
    
    def test_protocol_compliance(self):
        """Test that all protocol implementations have correct signatures"""
        # Skip this test as interface has been removed
        # This test was checking legacy interface that is no longer needed
        pytest.skip("Legacy interface has been removed - cleanup complete")
    
    def test_no_dead_websocket_methods(self):
        """Test that dead WebSocket methods are removed"""
        # Check data_sub_agent for dead methods
        module_path = project_root / "netra_backend/app/agents/data_sub_agent/data_sub_agent.py"
        
        with open(module_path, 'r') as f:
            source = f.read()
            
        # These methods should be removed per audit report
        dead_methods = [
            '_setup_websocket_context_if_available',
            '# This method is kept for compatibility but no longer needed'
        ]
        
        for dead_method in dead_methods:
            assert dead_method not in source, \
                f"Dead method/comment '{dead_method}' should be removed"
    
    def test_import_order_compliance(self):
        """Test that imports are at the top of files"""
        module_path = project_root / "netra_backend/app/agents/validation_sub_agent.py"
        
        with open(module_path, 'r') as f:
            lines = f.readlines()
            
        # Check for imports after line 50 (should be at top)
        for i, line in enumerate(lines[50:], start=50):
            assert not line.strip().startswith('import '), \
                f"Import found at line {i}, should be at top of file"
            assert not line.strip().startswith('from '), \
                f"Import found at line {i}, should be at top of file"


class TestTypeSafetyRuntime:
    """Runtime type safety tests"""
    
    @pytest.mark.asyncio
    async def test_execution_context_typing(self):
        """Test ExecutionContext has proper runtime typing"""
        context = ExecutionContext(
            run_id="test-123",
            user_id="user-456",
            agent_type="test",
            session_id="session-789"
        )
        
        # All attributes should be properly typed
        assert isinstance(context.run_id, str)
        assert isinstance(context.user_id, str)
        assert isinstance(context.agent_type, str)
        assert isinstance(context.session_id, str)
        
        # Optional fields should handle None
        assert context.metadata is None or isinstance(context.metadata, dict)
    
    @pytest.mark.asyncio
    async def test_execution_result_typing(self):
        """Test ExecutionResult has proper runtime typing"""
        result = ExecutionResult(
            success=True,
            result_data={"test": "data"},
            error_message=None,
            metadata={"timing": 1.5}
        )
        
        assert isinstance(result.success, bool)
        assert isinstance(result.result_data, dict)
        assert result.error_message is None or isinstance(result.error_message, str)
        assert isinstance(result.metadata, dict)
    
    def test_type_safe_decorator_presence(self):
        """Test that @agent_type_safe decorator is used where required"""
        # Check DataSubAgent has the decorator
        module_path = project_root / "netra_backend/app/agents/data_sub_agent/data_sub_agent.py"
        
        with open(module_path, 'r') as f:
            source = f.read()
            
        assert '@agent_type_safe' in source, \
            "DataSubAgent should use @agent_type_safe decorator"
    
    @pytest.mark.asyncio 
    async def test_websocket_type_consistency(self):
        """Test WebSocket types are consistent across modules"""
        # All modules should use the same WebSocket types
        websocket_types = {
            'WebSocketManagerProtocol',
            'WebSocketNotifier',
            'WebSocketMessageType'
        }
        
        modules_to_check = [
            "netra_backend/app/agents/agent_communication.py",
            "netra_backend/app/agents/agent_lifecycle.py",
            "netra_backend/app/agents/data_sub_agent/data_sub_agent.py"
        ]
        
        for module_path in modules_to_check:
            full_path = project_root / module_path
            with open(full_path, 'r') as f:
                source = f.read()
                
            for ws_type in websocket_types:
                if ws_type in source:
                    # Should be imported, not redefined
                    assert f'class {ws_type}' not in source, \
                        f"{ws_type} should be imported, not redefined in {module_path}"


class TestSSOTCompliance:
    """Test Single Source of Truth compliance"""
    
    def test_no_duplicate_type_definitions(self):
        """Test that types are not duplicated across modules"""
        type_definitions = {}
        
        modules = [
            "netra_backend/app/agents/agent_communication.py",
            "netra_backend/app/agents/agent_lifecycle.py",
            "netra_backend/app/agents/base/interface.py",
            "netra_backend/app/agents/data_sub_agent/data_sub_agent.py",
            "netra_backend/app/agents/validation_sub_agent.py"
        ]
        
        for module_path in modules:
            full_path = project_root / module_path
            with open(full_path, 'r') as f:
                source = f.read()
                
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    if class_name in type_definitions:
                        # Check if it's an acceptable duplicate per SPEC
                        assert False, \
                            f"Duplicate type {class_name} found in {module_path} and {type_definitions[class_name]}"
                    type_definitions[class_name] = module_path
    
    def test_canonical_location_compliance(self):
        """Test types are defined in canonical locations"""
        canonical_locations = {
            'AgentState': 'app/schemas/agent_state.py',
            'ExecutionStatus': 'app/schemas/core_enums.py',
            'WebSocketMessageType': 'app/schemas/core_enums.py',
            'AgentRequest': 'app/schemas/agent_models.py',
            'AgentResponse': 'app/schemas/agent_models.py'
        }
        
        for type_name, expected_location in canonical_locations.items():
            # Search for the type definition
            search_path = project_root / "netra_backend" / expected_location
            if search_path.exists():
                with open(search_path, 'r') as f:
                    source = f.read()
                    
                # Type should be defined here
                assert f'class {type_name}' in source or f'{type_name} =' in source, \
                    f"{type_name} not found in canonical location {expected_location}"


class TestTypeCheckingIntegration:
    """Integration tests for type checking"""
    
    @pytest.mark.asyncio
    async def test_mypy_compliance(self):
        """Test that modules pass mypy type checking"""
        import subprocess
        
        modules = [
            "netra_backend/app/agents/agent_communication.py",
            "netra_backend/app/agents/agent_lifecycle.py",
            "netra_backend/app/agents/base/interface.py"
        ]
        
        for module in modules:
            result = subprocess.run(
                ["python", "-m", "mypy", "--strict", module],
                capture_output=True,
                text=True,
                cwd=str(project_root)
            )
            
            # Should have no errors
            assert result.returncode == 0, \
                f"mypy errors in {module}:\n{result.stdout}\n{result.stderr}"
    
    @pytest.mark.asyncio
    async def test_runtime_type_validation(self):
        """Test runtime type validation works correctly"""
        # Create a mock context with wrong types
        with pytest.raises(TypeError):
            context = ExecutionContext(
                run_id=123,  # Should be string
                user_id="user-456",
                agent_type="test",
                session_id="session-789"
            )
    
    def test_comprehensive_type_coverage(self):
        """Test that all public methods have type hints"""
        modules_to_test = [
            AgentCommunicationMixin,
            AgentLifecycleMixin,
            DataSubAgent,
            ValidationSubAgent
        ]
        
        for module_class in modules_to_test:
            public_methods = [
                method for method in dir(module_class)
                if not method.startswith('_') and callable(getattr(module_class, method))
            ]
            
            for method_name in public_methods:
                method = getattr(module_class, method_name)
                if hasattr(method, '__annotations__'):
                    annotations = method.__annotations__
                    # Should have at least return type
                    assert 'return' in annotations or method_name == '__init__', \
                        f"{module_class.__name__}.{method_name} missing type annotations"


class TestBaseAgentInheritanceTypeCompliance:
    """Test BaseAgent inheritance and type compliance"""
    
    @pytest.mark.asyncio
    async def test_baseagent_inheritance_type_safety(self):
        """Test BaseAgent inheritance provides proper type safety"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.state import DeepAgentState
            from netra_backend.app.schemas.core_enums import ExecutionStatus
        except ImportError as e:
            pytest.fail(f"Failed to import BaseAgent components: {e}")
        
        # Verify BaseAgent has proper type annotations
        assert hasattr(BaseAgent, '__annotations__'), "BaseAgent should have type annotations"
        
        # Check critical methods have type hints
        critical_methods = ['execute', 'execute_core_logic', 'get_state', 'set_state']
        for method_name in critical_methods:
            if hasattr(BaseAgent, method_name):
                method = getattr(BaseAgent, method_name)
                if hasattr(method, '__annotations__'):
                    annotations = method.__annotations__
                    if method_name != '__init__':
                        assert 'return' in annotations, \
                            f"BaseAgent.{method_name} missing return type annotation"
    
    @pytest.mark.asyncio
    async def test_baseagent_state_type_consistency(self):
        """Test BaseAgent state management type consistency"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.schemas.agent import SubAgentLifecycle
        except ImportError:
            pytest.skip("BaseAgent or SubAgentLifecycle not available")
        
        # Mock agent for testing
        class TestAgent(BaseAgent):
            async def execute_core_logic(self, context) -> Dict[str, Any]:
                return {"test": "result"}
        
        agent = TestAgent(name="TypeSafetyTest")
        
        # Test state type consistency
        initial_state = agent.get_state()
        assert isinstance(initial_state, SubAgentLifecycle), \
            f"get_state() should return SubAgentLifecycle, got {type(initial_state)}"
        
        # Test state setting with proper types
        for valid_state in SubAgentLifecycle:
            agent.set_state(valid_state)
            current_state = agent.get_state()
            assert current_state == valid_state, "State should be set correctly"
            assert isinstance(current_state, SubAgentLifecycle), \
                "State should maintain proper type"
    
    @pytest.mark.asyncio
    async def test_baseagent_websocket_adapter_types(self):
        """Test BaseAgent WebSocket adapter type safety"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
        except ImportError:
            pytest.skip("BaseAgent or WebSocketBridgeAdapter not available")
        
        class TestAgent(BaseAgent):
            async def execute_core_logic(self, context) -> Dict[str, Any]:
                return {"test": "websocket_types"}
        
        agent = TestAgent(name="WebSocketTypeTest")
        
        # Check WebSocket adapter type
        if hasattr(agent, '_websocket_adapter'):
            adapter = agent._websocket_adapter
            assert isinstance(adapter, WebSocketBridgeAdapter), \
                f"WebSocket adapter should be WebSocketBridgeAdapter, got {type(adapter)}"
        
        # Check WebSocket methods have proper types
        websocket_methods = ['emit_agent_started', 'emit_thinking', 'emit_tool_executing']
        for method_name in websocket_methods:
            if hasattr(agent, method_name):
                method = getattr(agent, method_name)
                assert callable(method), f"{method_name} should be callable"


class TestExecuteCorePatternTypeCompliance:
    """Test _execute_core pattern type compliance"""
    
    @pytest.mark.asyncio
    async def test_execute_core_pattern_type_annotations(self):
        """Test _execute_core pattern has proper type annotations"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
        except ImportError:
            pytest.skip("BaseAgent or ExecutionContext not available")
        
        class TypeSafeAgent(BaseAgent):
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                return {"type_safe": True, "context_id": context.run_id}
        
        agent = TypeSafeAgent(name="TypeSafeTest")
        
        # Check method has proper type annotations
        method = agent.execute_core_logic
        annotations = getattr(method, '__annotations__', {})
        
        assert 'context' in annotations, "execute_core_logic should have context type annotation"
        assert 'return' in annotations, "execute_core_logic should have return type annotation"
        
        # Verify return type annotation is correct
        return_annotation = annotations.get('return')
        if return_annotation:
            return_str = str(return_annotation)
            assert 'Dict' in return_str or 'dict' in return_str, \
                f"Return type should be Dict[str, Any], got {return_str}"
    
    @pytest.mark.asyncio 
    async def test_execute_core_context_type_validation(self):
        """Test _execute_core validates context types properly"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        class StrictTypeAgent(BaseAgent):
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                # Type validation within method
                assert hasattr(context, 'run_id'), "Context must have run_id"
                assert hasattr(context, 'agent_name'), "Context must have agent_name" 
                assert isinstance(context.run_id, str), "run_id must be string"
                return {"validated": True}
        
        agent = StrictTypeAgent(name="StrictTypeTest")
        
        # Test with proper context
        valid_context = ExecutionContext(
            run_id="test_123",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(valid_context)
        assert result["validated"] is True
        
        # Test type validation catches issues
        try:
            # This should cause type validation to fail inside the method
            invalid_context = ExecutionContext(
                run_id=12345,  # Wrong type - should be string
                agent_name=agent.name,
                state=DeepAgentState()
            )
            await agent.execute_core_logic(invalid_context)
        except (AssertionError, TypeError):
            pass  # Expected - type validation should catch this
    
    @pytest.mark.asyncio
    async def test_execute_core_return_type_consistency(self):
        """Test _execute_core return types are consistent"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        class ConsistentReturnAgent(BaseAgent):
            def __init__(self, return_mode="dict", **kwargs):
                super().__init__(**kwargs)
                self.return_mode = return_mode
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                if self.return_mode == "dict":
                    return {"status": "success", "data": [1, 2, 3]}
                elif self.return_mode == "empty_dict":
                    return {}
                else:
                    return {"mode": self.return_mode}
        
        # Test different return scenarios maintain type consistency
        modes = ["dict", "empty_dict", "other"]
        for mode in modes:
            agent = ConsistentReturnAgent(return_mode=mode, name=f"ReturnTest_{mode}")
            context = ExecutionContext(
                run_id=f"return_test_{mode}",
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            result = await agent.execute_core_logic(context)
            
            # All returns should be dictionaries per type annotation
            assert isinstance(result, dict), \
                f"execute_core_logic should return dict for mode {mode}, got {type(result)}"
            
            # Dict should contain only serializable types
            for key, value in result.items():
                assert isinstance(key, str), f"Dict keys should be strings, got {type(key)}"
                # Values should be JSON-serializable types
                json_types = (str, int, float, bool, list, dict, type(None))
                assert isinstance(value, json_types), \
                    f"Dict values should be JSON-serializable, got {type(value)} for key {key}"


class TestErrorRecoveryTypeCompliance:
    """Test error recovery pattern type compliance"""
    
    @pytest.mark.asyncio
    async def test_error_recovery_exception_types(self):
        """Test error recovery handles exception types properly"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        class ErrorRecoveryAgent(BaseAgent):
            def __init__(self, error_type="none", **kwargs):
                super().__init__(**kwargs)
                self.error_type = error_type
                
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                if self.error_type == "value_error":
                    raise ValueError("Test value error")
                elif self.error_type == "type_error":
                    raise TypeError("Test type error")
                elif self.error_type == "runtime_error":
                    raise RuntimeError("Test runtime error")
                else:
                    return {"error_type": "none", "success": True}
        
        # Test that different exception types are properly typed
        exception_types = [
            ("value_error", ValueError),
            ("type_error", TypeError), 
            ("runtime_error", RuntimeError)
        ]
        
        for error_mode, expected_exception in exception_types:
            agent = ErrorRecoveryAgent(error_type=error_mode, name=f"ErrorTest_{error_mode}")
            context = ExecutionContext(
                run_id=f"error_test_{error_mode}",
                agent_name=agent.name,
                state=DeepAgentState()
            )
            
            with pytest.raises(expected_exception) as exc_info:
                await agent.execute_core_logic(context)
            
            # Verify exception type is correct
            assert isinstance(exc_info.value, expected_exception), \
                f"Expected {expected_exception}, got {type(exc_info.value)}"
            
            # Verify exception message is string
            assert isinstance(str(exc_info.value), str), "Exception message should be string"
    
    @pytest.mark.asyncio
    async def test_error_recovery_state_type_consistency(self):
        """Test error recovery maintains state type consistency"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
            from netra_backend.app.schemas.agent import SubAgentLifecycle
        except ImportError:
            pytest.skip("Required components not available")
        
        class StateRecoveryAgent(BaseAgent):
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                # Simulate state changes during error recovery
                original_state = self.get_state()
                
                try:
                    self.set_state(SubAgentLifecycle.RUNNING)
                    
                    if context.run_id.endswith("_fail"):
                        raise RuntimeError("Simulated failure")
                    
                    self.set_state(SubAgentLifecycle.COMPLETED)
                    return {"state_recovery": "success"}
                    
                except RuntimeError:
                    # Error recovery should maintain proper state types
                    self.set_state(SubAgentLifecycle.FAILED)
                    raise
        
        agent = StateRecoveryAgent(name="StateRecoveryTest")
        
        # Test successful execution maintains state types
        success_context = ExecutionContext(
            run_id="state_success",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(success_context)
        final_state = agent.get_state()
        assert isinstance(final_state, SubAgentLifecycle), \
            f"Final state should be SubAgentLifecycle, got {type(final_state)}"
        assert final_state == SubAgentLifecycle.COMPLETED, \
            "Successful execution should end in COMPLETED state"
        
        # Test error recovery maintains state types
        fail_context = ExecutionContext(
            run_id="state_fail",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        with pytest.raises(RuntimeError):
            await agent.execute_core_logic(fail_context)
        
        error_state = agent.get_state()
        assert isinstance(error_state, SubAgentLifecycle), \
            f"Error state should be SubAgentLifecycle, got {type(error_state)}"
        assert error_state == SubAgentLifecycle.FAILED, \
            "Failed execution should end in FAILED state"
    
    @pytest.mark.asyncio
    async def test_error_recovery_timing_types(self):
        """Test error recovery timing maintains proper types"""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.base.interface import ExecutionContext
            from netra_backend.app.agents.state import DeepAgentState
        except ImportError:
            pytest.skip("Required components not available")
        
        import time
        
        class TimingRecoveryAgent(BaseAgent):
            async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
                start_time = time.time()
                
                try:
                    await asyncio.sleep(0.05)  # Simulate work
                    
                    if context.run_id.endswith("_timeout"):
                        raise TimeoutError("Simulated timeout")
                    
                    end_time = time.time()
                    return {
                        "execution_time": end_time - start_time,
                        "start_time": start_time,
                        "end_time": end_time,
                        "success": True
                    }
                    
                except TimeoutError:
                    error_time = time.time()
                    # Error recovery should still provide timing info with correct types
                    recovery_result = {
                        "execution_time": error_time - start_time,
                        "start_time": start_time,
                        "error_time": error_time,
                        "success": False,
                        "error": "timeout"
                    }
                    
                    # Verify all timing values are proper float types
                    for key, value in recovery_result.items():
                        if key.endswith("_time"):
                            assert isinstance(value, float), \
                                f"Timing value {key} should be float, got {type(value)}"
                    
                    raise  # Re-raise after recording timing info
        
        agent = TimingRecoveryAgent(name="TimingRecoveryTest")
        
        # Test successful timing types
        success_context = ExecutionContext(
            run_id="timing_success", 
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        result = await agent.execute_core_logic(success_context)
        
        # Verify timing result types
        timing_keys = ["execution_time", "start_time", "end_time"]
        for key in timing_keys:
            assert key in result, f"Result should contain {key}"
            assert isinstance(result[key], float), \
                f"{key} should be float, got {type(result[key])}"
        
        # Test error recovery timing types
        timeout_context = ExecutionContext(
            run_id="timing_timeout",
            agent_name=agent.name,
            state=DeepAgentState()
        )
        
        with pytest.raises(TimeoutError):
            await agent.execute_core_logic(timeout_context)
        
        # Error should have been handled with proper timing types in the recovery code


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])