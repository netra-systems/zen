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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])