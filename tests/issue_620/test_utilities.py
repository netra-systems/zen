"""Test Utilities for Issue #620 SSOT ExecutionEngine Migration Testing.

This module provides utility functions and infrastructure for testing
the SSOT ExecutionEngine migration without Docker dependencies.

Business Impact: Enables comprehensive testing of $500K+ ARR protection measures.
"""

import os
import re
import ast
import glob
import importlib
import inspect
import time
from typing import Dict, List, Any, Optional, Tuple, Type, Callable
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import asyncio

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionEngineDetector:
    """Utility to detect and analyze ExecutionEngine implementations."""
    
    @staticmethod
    def find_execution_engine_imports() -> List[Tuple[str, str]]:
        """Find all ExecutionEngine import statements in the codebase.
        
        Returns:
            List of (file_path, import_statement) tuples
        """
        execution_engine_imports = []
        
        # Define search patterns
        import_patterns = [
            r'from\s+.*execution_engine\s+import\s+ExecutionEngine',
            r'from\s+.*user_execution_engine\s+import\s+UserExecutionEngine',
            r'import\s+.*execution_engine',
            r'import\s+.*user_execution_engine'
        ]
        
        # Search common directories
        search_dirs = [
            'netra_backend',
            'tests',
            'test_framework'
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for file_path in Path(search_dir).rglob('*.py'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern in import_patterns:
                            matches = re.findall(pattern, content, re.MULTILINE)
                            for match in matches:
                                execution_engine_imports.append((str(file_path), match))
                                
                    except Exception as e:
                        logger.debug(f"Could not scan {file_path}: {e}")
                        continue
        
        return execution_engine_imports
    
    @staticmethod
    def import_execution_engine_from_file(file_path: str) -> Optional[Type]:
        """Import ExecutionEngine from specific file context.
        
        Args:
            file_path: Path to file containing ExecutionEngine import
            
        Returns:
            ExecutionEngine class if found, None otherwise
        """
        try:
            # Parse file to find import statements
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if 'execution_engine' in str(node.module):
                        for alias in node.names:
                            if alias.name == 'ExecutionEngine':
                                # Try to import from the module
                                module = importlib.import_module(node.module)
                                return getattr(module, 'ExecutionEngine', None)
                                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if 'execution_engine' in alias.name:
                            module = importlib.import_module(alias.name)
                            return getattr(module, 'ExecutionEngine', None)
        
        except Exception as e:
            logger.debug(f"Could not import ExecutionEngine from {file_path}: {e}")
            return None
    
    @staticmethod
    def analyze_execution_engine_classes() -> Dict[str, Any]:
        """Analyze all ExecutionEngine classes in the system.
        
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            "classes_found": [],
            "unique_classes": 0,
            "modules": set(),
            "method_signatures": {},
            "constructor_signatures": {},
            "ssot_compliant": False
        }
        
        # Try to import known ExecutionEngine implementations
        execution_engine_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.supervisor.user_execution_engine'
        ]
        
        for module_path in execution_engine_modules:
            try:
                module = importlib.import_module(module_path)
                
                # Look for ExecutionEngine classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (inspect.isclass(attr) and 
                        'ExecutionEngine' in attr.__name__ and
                        attr.__module__ == module_path):
                        
                        class_info = {
                            "name": attr.__name__,
                            "module": attr.__module__,
                            "class": attr
                        }
                        analysis["classes_found"].append(class_info)
                        analysis["modules"].add(module_path)
                        
                        # Analyze method signatures
                        methods = {}
                        for method_name in dir(attr):
                            if not method_name.startswith('_') and callable(getattr(attr, method_name)):
                                try:
                                    method = getattr(attr, method_name)
                                    sig = inspect.signature(method)
                                    methods[method_name] = str(sig)
                                except Exception:
                                    methods[method_name] = "signature_unavailable"
                        
                        analysis["method_signatures"][attr.__name__] = methods
                        
                        # Analyze constructor
                        try:
                            constructor_sig = inspect.signature(attr.__init__)
                            analysis["constructor_signatures"][attr.__name__] = str(constructor_sig)
                        except Exception:
                            analysis["constructor_signatures"][attr.__name__] = "constructor_unavailable"
                        
            except ImportError:
                logger.debug(f"Could not import {module_path}")
                continue
        
        # Determine uniqueness and SSOT compliance
        unique_classes = set()
        for class_info in analysis["classes_found"]:
            unique_classes.add(class_info["class"])
        
        analysis["unique_classes"] = len(unique_classes)
        analysis["ssot_compliant"] = len(unique_classes) <= 1
        
        return analysis


class UserContextContaminationChecker:
    """Utility to check for user context contamination vulnerabilities."""
    
    @staticmethod
    def check_for_user_data_contamination(result: AgentExecutionResult, 
                                        user_context: UserExecutionContext) -> bool:
        """Check if user data from other contexts appears in result.
        
        Args:
            result: Agent execution result to check
            user_context: Expected user context
            
        Returns:
            True if contamination detected, False otherwise
        """
        if not result or not result.data:
            return False
            
        result_str = str(result.data)
        user_id = user_context.user_id
        
        # Check for other user IDs in the result
        other_user_patterns = [
            r'user_\d+',  # user_1, user_2, etc.
            r'concurrent_user_\d+',
            r'isolation_user_\d+',
            r'test_user_\d+'
        ]
        
        for pattern in other_user_patterns:
            matches = re.findall(pattern, result_str)
            for match in matches:
                if match != user_id and user_id not in match:
                    logger.warning(f"Potential contamination: Found {match} in result for {user_id}")
                    return True
        
        # Check for sensitive data patterns from other users
        sensitive_patterns = [
            r'CONFIDENTIAL_USER_\d+_DATA',
            r'SECRET_DATA_USER_\d+', 
            r'USER\d+_PRIVATE_RESPONSE',
            r'ACCOUNT_\d+_SENSITIVE_INFO'
        ]
        
        for pattern in sensitive_patterns:
            matches = re.findall(pattern, result_str)
            for match in matches:
                expected_match = match.replace('USER', f'USER_{user_context.metadata.get("user_index", "0")}')
                if match != expected_match:
                    logger.warning(f"Sensitive data contamination: Found {match} in result for {user_id}")
                    return True
        
        return False
    
    @staticmethod
    def check_websocket_event_contamination(user1_context: UserExecutionContext,
                                          user2_context: UserExecutionContext,
                                          captured_events: List[Dict]) -> bool:
        """Check if WebSocket events are sent to wrong users.
        
        Args:
            user1_context: First user context
            user2_context: Second user context  
            captured_events: List of captured WebSocket events
            
        Returns:
            True if contamination detected, False otherwise
        """
        user1_run_id = user1_context.run_id
        user2_run_id = user2_context.run_id
        
        for event in captured_events:
            args = event.get("args", [])
            kwargs = event.get("kwargs", {})
            
            # Check if event run_id matches expected user
            if args and len(args) > 0:
                event_run_id = str(args[0])
                
                # If event is for user1 but contains user2's run_id (or vice versa)
                if user1_run_id in event_run_id and user2_run_id in str(event):
                    logger.warning(f"WebSocket contamination: User1 event contains User2 data")
                    return True
                    
                if user2_run_id in event_run_id and user1_run_id in str(event):
                    logger.warning(f"WebSocket contamination: User2 event contains User1 data")
                    return True
        
        return False
    
    @staticmethod
    def generate_contamination_test_data(num_users: int) -> List[UserExecutionContext]:
        """Generate user contexts with unique data for contamination testing.
        
        Args:
            num_users: Number of user contexts to generate
            
        Returns:
            List of UserExecutionContext with unique sensitive data
        """
        user_contexts = []
        
        for i in range(num_users):
            context = UserExecutionContext(
                user_id=f"contamination_test_user_{i}",
                thread_id=f"contamination_thread_{i}",
                run_id=f"contamination_run_{i}",
                request_id=f"contamination_req_{i}",
                audit_metadata={
                    f"user_{i}_secret": f"CONFIDENTIAL_USER_{i}_DATA",
                    f"user_{i}_account": f"ACCOUNT_{i}_{int(time.time())}",
                    f"user_{i}_ssn": f"{i:03d}-{i:02d}-{i:04d}",
                    "user_index": i,
                    "contamination_test": True,
                    "created_timestamp": time.time()
                }
            )
            user_contexts.append(context)
        
        return user_contexts


class MockExecutionEngineFactory:
    """Factory for creating mock execution engines for testing."""
    
    @staticmethod
    def create_mock_agent_registry() -> Mock:
        """Create mock agent registry for testing."""
        mock_registry = Mock()
        mock_registry.get = Mock(return_value=Mock())
        mock_registry.list_keys = Mock(return_value=[
            "triage_agent", 
            "data_helper_agent", 
            "supervisor_agent",
            "apex_optimizer_agent"
        ])
        mock_registry.get_agents = Mock(return_value={
            "triage_agent": Mock(),
            "data_helper_agent": Mock(),
            "supervisor_agent": Mock()
        })
        return mock_registry
    
    @staticmethod
    def create_mock_websocket_bridge() -> Mock:
        """Create mock WebSocket bridge for testing."""
        mock_bridge = Mock()
        mock_bridge.notify_agent_started = AsyncMock()
        mock_bridge.notify_agent_thinking = AsyncMock()
        mock_bridge.notify_agent_completed = AsyncMock()
        mock_bridge.notify_tool_executing = AsyncMock()
        mock_bridge.notify_tool_completed = AsyncMock()
        mock_bridge.notify_agent_error = AsyncMock()
        mock_bridge.notify_agent_death = AsyncMock()
        mock_bridge.get_metrics = AsyncMock(return_value={"events_sent": 0})
        return mock_bridge
    
    @staticmethod
    def create_mock_agent_factory() -> Mock:
        """Create mock agent factory for UserExecutionEngine."""
        mock_factory = Mock()
        mock_factory.create_agent = Mock(return_value=Mock())
        mock_factory.get_agent = Mock(return_value=Mock())
        return mock_factory
    
    @staticmethod
    def create_mock_websocket_emitter(user_context: UserExecutionContext) -> Mock:
        """Create mock WebSocket emitter for UserExecutionEngine."""
        mock_emitter = Mock()
        mock_emitter.user_id = user_context.user_id
        mock_emitter.thread_id = user_context.thread_id
        mock_emitter.run_id = user_context.run_id
        mock_emitter.notify_agent_started = AsyncMock()
        mock_emitter.notify_agent_thinking = AsyncMock()
        mock_emitter.notify_agent_completed = AsyncMock()
        mock_emitter.notify_tool_executing = AsyncMock()
        mock_emitter.notify_tool_completed = AsyncMock()
        return mock_emitter
    
    @staticmethod
    async def create_execution_engine_for_testing(user_context: UserExecutionContext,
                                                 engine_type: str = "auto") -> Any:
        """Create execution engine for testing.
        
        Args:
            user_context: User execution context
            engine_type: "auto", "user_execution_engine", or "execution_engine"
            
        Returns:
            Execution engine instance
        """
        if engine_type == "auto":
            # Try UserExecutionEngine first
            try:
                return await MockExecutionEngineFactory._create_user_execution_engine(user_context)
            except ImportError:
                try:
                    return MockExecutionEngineFactory._create_execution_engine(user_context)
                except ImportError:
                    raise ImportError("No ExecutionEngine implementation available")
        
        elif engine_type == "user_execution_engine":
            return await MockExecutionEngineFactory._create_user_execution_engine(user_context)
            
        elif engine_type == "execution_engine":
            return MockExecutionEngineFactory._create_execution_engine(user_context)
            
        else:
            raise ValueError(f"Unknown engine type: {engine_type}")
    
    @staticmethod
    async def _create_user_execution_engine(user_context: UserExecutionContext):
        """Create UserExecutionEngine for testing."""
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        
        # Try legacy compatibility first
        try:
            mock_registry = MockExecutionEngineFactory.create_mock_agent_registry()
            mock_bridge = MockExecutionEngineFactory.create_mock_websocket_bridge()
            
            engine = await UserExecutionEngine.create_from_legacy(
                registry=mock_registry,
                websocket_bridge=mock_bridge,
                user_context=user_context
            )
            return engine
            
        except Exception:
            # Try direct constructor
            mock_factory = MockExecutionEngineFactory.create_mock_agent_factory()
            mock_emitter = MockExecutionEngineFactory.create_mock_websocket_emitter(user_context)
            
            engine = UserExecutionEngine(user_context, mock_factory, mock_emitter)
            return engine
    
    @staticmethod
    def _create_execution_engine(user_context: UserExecutionContext):
        """Create deprecated ExecutionEngine for testing."""
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        
        mock_registry = MockExecutionEngineFactory.create_mock_agent_registry()
        mock_bridge = MockExecutionEngineFactory.create_mock_websocket_bridge()
        
        engine = ExecutionEngine(mock_registry, mock_bridge, user_context)
        return engine


class TestDataGenerator:
    """Generator for test data and scenarios."""
    
    @staticmethod
    def create_authenticated_user_context(user_id: str, 
                                        metadata: Optional[Dict[str, Any]] = None) -> UserExecutionContext:
        """Create authenticated user context for testing."""
        default_metadata = {
            "authenticated": True,
            "test_user": True,
            "created_timestamp": time.time(),
            "test_session_id": f"test_session_{int(time.time())}"
        }
        
        if metadata:
            default_metadata.update(metadata)
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"{user_id}_thread",
            run_id=f"{user_id}_run_{int(time.time())}",
            request_id=f"{user_id}_req_{int(time.time())}",
            audit_metadata=default_metadata
        )
    
    @staticmethod
    def create_agent_execution_context(user_context: UserExecutionContext,
                                     agent_name: str,
                                     user_input: str,
                                     metadata: Optional[Dict[str, Any]] = None) -> AgentExecutionContext:
        """Create agent execution context for testing."""
        default_metadata = {
            "test_execution": True,
            "created_timestamp": time.time()
        }
        
        if metadata:
            default_metadata.update(metadata)
        
        return AgentExecutionContext(
            agent_name=agent_name,
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            user_input=user_input,
            audit_metadata=default_metadata
        )
    
    @staticmethod
    def create_mock_agent_result(agent_name: str,
                               success: bool = True,
                               execution_time: float = 1.0,
                               response_data: Optional[Dict[str, Any]] = None) -> AgentExecutionResult:
        """Create mock agent execution result."""
        default_data = {
            "response": f"Mock response from {agent_name}",
            "agent_type": agent_name,
            "test_result": True,
            "timestamp": time.time()
        }
        
        if response_data:
            default_data.update(response_data)
        
        return AgentExecutionResult(
            success=success,
            agent_name=agent_name,
            execution_time=execution_time,
            data=default_data if success else None,
            error=None if success else f"Mock error from {agent_name}"
        )


class NonDockerTestEnvironment:
    """Utility for setting up non-Docker test environment."""
    
    @staticmethod
    def setup_test_environment() -> Dict[str, Any]:
        """Setup non-Docker test environment.
        
        Returns:
            Environment configuration
        """
        env_config = {
            "test_mode": True,
            "docker_disabled": True,
            "mock_services": True,
            "real_services": False,
            "database_mocked": True,
            "websocket_mocked": True
        }
        
        # Set environment variables for testing
        os.environ["TEST_MODE"] = "true"
        os.environ["DOCKER_DISABLED"] = "true"
        os.environ["MOCK_SERVICES"] = "true"
        
        return env_config
    
    @staticmethod
    def cleanup_test_environment():
        """Cleanup test environment."""
        # Clean up environment variables
        test_vars = ["TEST_MODE", "DOCKER_DISABLED", "MOCK_SERVICES"]
        for var in test_vars:
            if var in os.environ:
                del os.environ[var]
    
    @staticmethod
    def get_real_agent_registry():
        """Get real agent registry for non-Docker testing."""
        # This would return a real agent registry configured for non-Docker testing
        # For now, return a mock
        return MockExecutionEngineFactory.create_mock_agent_registry()
    
    @staticmethod
    def get_real_websocket_bridge():
        """Get real WebSocket bridge for non-Docker testing."""
        # This would return a real WebSocket bridge configured for non-Docker testing
        # For now, return a mock
        return MockExecutionEngineFactory.create_mock_websocket_bridge()


class MigrationProgressTracker:
    """Track migration progress and validation status."""
    
    def __init__(self):
        self.metrics = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "ssot_violations_found": 0,
            "contamination_issues_found": 0,
            "websocket_failures": 0,
            "golden_path_successes": 0,
            "start_time": time.time()
        }
    
    def record_test_result(self, test_name: str, passed: bool, 
                          test_type: str = "general", details: Optional[Dict] = None):
        """Record test result."""
        self.metrics["tests_run"] += 1
        
        if passed:
            self.metrics["tests_passed"] += 1
            if test_type == "golden_path":
                self.metrics["golden_path_successes"] += 1
        else:
            self.metrics["tests_failed"] += 1
            if test_type == "ssot":
                self.metrics["ssot_violations_found"] += 1
            elif test_type == "contamination":
                self.metrics["contamination_issues_found"] += 1
            elif test_type == "websocket":
                self.metrics["websocket_failures"] += 1
        
        logger.info(f"Test result recorded: {test_name} - {'PASS' if passed else 'FAIL'}")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get migration status report."""
        elapsed_time = time.time() - self.metrics["start_time"]
        
        return {
            "metrics": self.metrics.copy(),
            "elapsed_time": elapsed_time,
            "success_rate": (self.metrics["tests_passed"] / max(self.metrics["tests_run"], 1)) * 100,
            "ssot_compliance": self.metrics["ssot_violations_found"] == 0,
            "user_isolation": self.metrics["contamination_issues_found"] == 0,
            "websocket_integrity": self.metrics["websocket_failures"] == 0,
            "golden_path_protected": self.metrics["golden_path_successes"] > 0,
            "migration_ready": all([
                self.metrics["ssot_violations_found"] == 0,
                self.metrics["contamination_issues_found"] == 0, 
                self.metrics["websocket_failures"] == 0,
                self.metrics["golden_path_successes"] > 0
            ])
        }


class E2ETestHelpers:
    """Helpers for E2E testing with staging GCP environment."""
    
    @staticmethod
    def get_staging_gcp_config() -> Dict[str, str]:
        """Get staging GCP configuration."""
        return {
            "project_id": "netra-staging",
            "environment": "staging",
            "region": "us-central1",
            "service_account": "staging-test@netra-staging.iam.gserviceaccount.com",
            "api_base_url": "https://staging-api.netra.systems",
            "websocket_url": "wss://staging-ws.netra.systems"
        }
    
    @staticmethod
    async def create_staging_user_context(user_id: str) -> UserExecutionContext:
        """Create user context for staging environment."""
        return UserExecutionContext(
            user_id=f"staging_{user_id}",
            thread_id=f"staging_thread_{int(time.time())}",
            run_id=f"staging_run_{int(time.time())}",
            request_id=f"staging_req_{int(time.time())}",
            metadata={
                "environment": "staging",
                "e2e_test": True,
                "gcp_staging": True,
                "created_timestamp": time.time()
            }
        )
    
    @staticmethod
    def get_staging_agent_registry(config: Dict[str, str]):
        """Get agent registry configured for staging."""
        # This would return a real agent registry for staging
        # For now, return enhanced mock
        mock_registry = MockExecutionEngineFactory.create_mock_agent_registry()
        mock_registry.staging_config = config
        return mock_registry
    
    @staticmethod
    def get_staging_websocket_bridge(config: Dict[str, str]):
        """Get WebSocket bridge configured for staging."""
        # This would return a real WebSocket bridge for staging
        # For now, return enhanced mock
        mock_bridge = MockExecutionEngineFactory.create_mock_websocket_bridge()
        mock_bridge.staging_config = config
        return mock_bridge
    
    @staticmethod
    async def establish_staging_websocket_connection(user_id: str, config: Dict[str, str]):
        """Establish WebSocket connection to staging."""
        # This would establish a real WebSocket connection to staging
        # For now, return mock connection
        mock_connection = Mock()
        mock_connection.user_id = user_id
        mock_connection.config = config
        mock_connection.on = Mock()
        mock_connection.disconnect = AsyncMock()
        return mock_connection
    
    @staticmethod
    async def cleanup_staging_user_context(user_context: UserExecutionContext):
        """Cleanup staging user context and resources."""
        logger.info(f"Cleaning up staging context for {user_context.user_id}")
        # This would clean up real staging resources
        pass


# Export all utilities for easy import
__all__ = [
    'ExecutionEngineDetector',
    'UserContextContaminationChecker', 
    'MockExecutionEngineFactory',
    'TestDataGenerator',
    'NonDockerTestEnvironment',
    'MigrationProgressTracker',
    'E2ETestHelpers'
]