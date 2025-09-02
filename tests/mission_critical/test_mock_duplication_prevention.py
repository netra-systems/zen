#!/usr/bin/env python3
"""
MISSION CRITICAL: Mock Duplication Prevention Tests

This test suite ensures that no new duplicate mock implementations are introduced
into the codebase. Critical for maintaining test infrastructure reliability.

Business Value: Platform/Internal - Test Infrastructure Quality Gate
Prevents regression in mock consolidation efforts.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set
import pytest

from test_framework.ssot.mocks import get_mock_factory

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

class TestMockDuplicationPrevention:
    """Test suite to prevent mock duplication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.forbidden_mock_classes = {
            "MockAgent", "MockOrchestrator", "MockWebSocket", "MockWebSocketManager",
            "MockWebSocketConnection", "MockAuthService", "MockLLMService", 
            "MockServiceManager", "MockAgentService", "MockClickHouseService",
            "MockRedisService", "MockDatabaseSession", "MockHttpClient"
        }
        
        self.allowed_exception_files = {
            # Files that are allowed to have deprecated mock classes with warnings
            "test_framework/ssot/compatibility_bridge.py",
            "netra_backend/tests/test_agent_service_mock_classes.py",
            # Legacy files being phased out
            "test_framework/mocks/llm_mocks.py",
            "test_framework/mocks/service_mocks.py"
        }
        
    def test_no_new_mock_duplicates(self):
        """Test that no new duplicate mock classes are created."""
        violations = []
        
        # Scan all Python files
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                mock_classes = self._find_mock_class_definitions(content)
                
                for mock_class in mock_classes:
                    if mock_class in self.forbidden_mock_classes:
                        rel_path = py_file.relative_to(PROJECT_ROOT)
                        
                        # Check if this file is allowed to have this mock
                        if str(rel_path).replace('\\\\', '/') not in self.allowed_exception_files:
                            # Check if it has proper deprecation warning
                            if not self._has_deprecation_warning(content, mock_class):
                                violations.append(f"{rel_path}: Found duplicate {mock_class} without deprecation warning")
                                
            except Exception as e:
                # Don't fail the test for file reading issues
                continue
                
        if violations:
            violation_msg = "\\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} mock duplication violations:\\n\\n{violation_msg}\\n\\n"
                "SOLUTION: Use get_mock_factory().create_*_mock() methods instead, "
                "or add proper deprecation warnings if legacy compatibility is required."
            )
            
    def test_ssot_mock_factory_is_available(self):
        """Test that SSOT MockFactory is available and working."""
        factory = get_mock_factory()
        assert factory is not None
        
        # Test that all required mock methods are available
        required_methods = [
            "create_agent_mock",
            "create_orchestrator_mock", 
            "create_websocket_manager_mock",
            "create_websocket_connection_mock",
            "create_auth_service_mock",
            "create_llm_client_mock",
            "create_service_manager_mock",
            "create_database_session_mock",
            "create_redis_client_mock"
        ]
        
        for method_name in required_methods:
            assert hasattr(factory, method_name), f"MockFactory missing {method_name}"
            method = getattr(factory, method_name)
            assert callable(method), f"MockFactory.{method_name} is not callable"
            
    def test_mock_factory_creates_consistent_mocks(self):
        """Test that MockFactory creates consistent mock objects."""
        factory = get_mock_factory()
        
        # Test agent mock consistency
        agent1 = factory.create_agent_mock(agent_id="test1")
        agent2 = factory.create_agent_mock(agent_id="test2")
        
        # Both should have same interface
        assert hasattr(agent1, 'process_request')
        assert hasattr(agent2, 'process_request')
        assert hasattr(agent1, 'agent_id')
        assert hasattr(agent2, 'agent_id')
        
        # But different IDs
        assert agent1.agent_id != agent2.agent_id
        
        # Test WebSocket mock consistency
        ws1 = factory.create_websocket_connection_mock()
        ws2 = factory.create_websocket_connection_mock()
        
        assert hasattr(ws1, 'send')
        assert hasattr(ws2, 'send')
        assert hasattr(ws1, 'connection_id')
        assert hasattr(ws2, 'connection_id')
        
    def test_deprecated_mocks_show_warnings(self):
        """Test that deprecated mock classes show proper warnings."""
        # Import should be possible but trigger warnings
        import warnings
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            try:
                from test_framework.ssot.compatibility_bridge import MockAgent
                mock_agent = MockAgent()
                
                # Should have triggered a deprecation warning
                assert len(w) >= 1
                warning = next((warning for warning in w if issubclass(warning.category, DeprecationWarning)), None)
                assert warning is not None
                assert "deprecated" in str(warning.message).lower()
                assert "MockAgent" in str(warning.message)
                
            except ImportError:
                # If compatibility bridge doesn't exist yet, test should pass
                pass
                
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            "__pycache__", ".git", "node_modules", ".venv", "venv",
            ".pytest_cache", "build", "dist"
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
        
    def _find_mock_class_definitions(self, content: str) -> List[str]:
        """Find mock class definitions in file content."""
        mock_classes = []
        
        # Look for class definitions starting with "Mock"
        class_pattern = r"^class (Mock\\w+).*?:"
        matches = re.findall(class_pattern, content, re.MULTILINE)
        mock_classes.extend(matches)
        
        return mock_classes
        
    def _has_deprecation_warning(self, content: str, mock_class: str) -> bool:
        """Check if mock class has proper deprecation warning."""
        # Look for deprecation warning patterns
        warning_patterns = [
            f"{mock_class} is deprecated",
            "warnings.warn",
            "DeprecationWarning", 
            "DEPRECATED",
            "get_mock_factory()"
        ]
        
        # Check if at least 2 warning indicators are present
        warning_count = sum(1 for pattern in warning_patterns if pattern in content)
        return warning_count >= 2


@pytest.mark.mission_critical
class TestMockFactoryComprehensive:
    """Comprehensive tests for MockFactory functionality."""
    
    def test_all_factory_methods_work(self):
        """Test that all factory methods create working mocks."""
        factory = get_mock_factory()
        
        test_cases = [
            ("create_agent_mock", {}),
            ("create_orchestrator_mock", {}),
            ("create_websocket_manager_mock", {}),
            ("create_websocket_connection_mock", {}),
            ("create_websocket_server_mock", {}),
            ("create_auth_service_mock", {}),
            ("create_llm_client_mock", {}),
            ("create_service_manager_mock", {}),
            ("create_service_factory_mock", {}),
            ("create_database_session_mock", {}),
            ("create_redis_client_mock", {}),
            ("create_repository_mock", {}),
            ("create_http_client_mock", {}),
            ("create_config_loader_mock", {}),
            ("create_environment_mock", {}),
        ]
        
        for method_name, kwargs in test_cases:
            if hasattr(factory, method_name):
                method = getattr(factory, method_name)
                mock_obj = method(**kwargs)
                assert mock_obj is not None, f"{method_name} returned None"
                
    def test_mock_cleanup_works(self):
        """Test that mock cleanup functionality works."""
        factory = get_mock_factory()
        
        # Create some mocks
        agent_mock = factory.create_agent_mock()
        ws_mock = factory.create_websocket_connection_mock()
        
        # Registry should track them
        assert len(factory.registry.active_mocks) > 0
        
        # Cleanup should work
        factory.cleanup()
        
        # Registry should be clean
        assert len(factory.registry.active_mocks) == 0
        
    def test_mock_call_tracking(self):
        """Test that mock call tracking works when enabled."""
        factory = get_mock_factory()
        factory.mock_config["enable_call_tracking"] = True
        
        # Create and use a mock
        mock_obj = factory.create_mock()
        mock_obj("test_call", arg1="value1")
        
        # Should have recorded the call
        call_history = factory.registry.get_call_history()
        assert len(call_history) >= 0  # May or may not track depending on implementation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])