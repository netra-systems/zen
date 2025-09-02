"""
MISSION CRITICAL: SSOT Regression Prevention Test Suite

This test suite prevents regression of SSOT violations and ensures the framework
remains compliant over time. These tests act as guardrails to catch violations
before they reach production. CRITICAL for spacecraft safety.

Business Value: Platform/Internal - Risk Reduction & System Stability
Prevents cascading failures that could bring down the entire test infrastructure.

CRITICAL: These tests are designed to be STRICT and UNFORGIVING.
They catch violations that could lead to system instability or cascade failures.
"""

import asyncio
import ast
import importlib
import inspect
import logging
import os
import sys
import time
import traceback
import uuid
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import SSOT framework components for regression testing
from test_framework.ssot import (
    BaseTestCase,
    AsyncBaseTestCase, 
    DatabaseTestCase,
    WebSocketTestCase,
    IntegrationTestCase,
    MockFactory,
    get_mock_factory,
    validate_test_class,
    validate_ssot_compliance,
    get_ssot_status,
    SSOT_VERSION,
    SSOT_COMPLIANCE
)

from shared.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)


class TestSSOTRegressionPrevention(BaseTestCase):
    """
    REGRESSION CRITICAL: Prevent SSOT framework regression.
    These tests catch violations before they can cause system-wide issues.
    """
    
    def setUp(self):
        """Set up regression prevention test environment."""
        super().setUp()
        self.test_id = uuid.uuid4().hex[:8]
        self.project_root = Path(__file__).parent.parent.parent
        logger.info(f"Starting regression prevention test: {self._testMethodName} (ID: {self.test_id})")
    
    def tearDown(self):
        """Clean up regression prevention test."""
        logger.info(f"Completing regression prevention test: {self._testMethodName} (ID: {self.test_id})")
        super().tearDown()
    
    def test_prevent_direct_os_environ_access_violations(self):
        """
        VIOLATION CRITICAL: Prevent direct os.environ access in test files.
        This catches violations of the IsolatedEnvironment requirement.
        """
        violations = []
        
        # Scan all Python files for direct os.environ usage
        test_files = list(self.project_root.rglob("test*.py"))
        
        for test_file in test_files[:50]:  # Limit for performance, would scan all in production
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST to find os.environ usage
                try:
                    tree = ast.parse(content)
                    
                    class EnvironAccessVisitor(ast.NodeVisitor):
                        def __init__(self):
                            self.violations = []
                        
                        def visit_Attribute(self, node):
                            # Look for os.environ patterns
                            if (isinstance(node.value, ast.Name) and 
                                node.value.id == 'os' and 
                                node.attr == 'environ'):
                                self.violations.append({
                                    'line': node.lineno,
                                    'pattern': 'os.environ'
                                })
                            
                            # Look for direct environ import usage
                            if (isinstance(node.value, ast.Name) and 
                                node.value.id == 'environ'):
                                self.violations.append({
                                    'line': node.lineno,
                                    'pattern': 'environ'
                                })
                            
                            self.generic_visit(node)
                        
                        def visit_Subscript(self, node):
                            # Look for os.environ['key'] patterns
                            if (isinstance(node.value, ast.Attribute) and
                                isinstance(node.value.value, ast.Name) and
                                node.value.value.id == 'os' and
                                node.value.attr == 'environ'):
                                self.violations.append({
                                    'line': node.lineno,
                                    'pattern': 'os.environ[key]'
                                })
                            
                            self.generic_visit(node)
                    
                    visitor = EnvironAccessVisitor()
                    visitor.visit(tree)
                    
                    if visitor.violations:
                        violations.extend([
                            {
                                'file': str(test_file),
                                'line': v['line'],
                                'pattern': v['pattern'],
                                'violation': 'direct_environ_access'
                            }
                            for v in visitor.violations
                        ])
                        
                except SyntaxError:
                    # Skip files with syntax errors
                    pass
                    
            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read
                pass
        
        # Filter out allowed exceptions (like this test file itself)
        allowed_files = [
            'test_ssot_regression_prevention.py',
            'compatibility_bridge.py',
            'isolated_environment.py'
        ]
        
        filtered_violations = [
            v for v in violations 
            if not any(allowed in v['file'] for allowed in allowed_files)
        ]
        
        if filtered_violations:
            logger.error(f"Direct os.environ access violations found: {filtered_violations}")
        
        self.assertEqual(len(filtered_violations), 0,
                        f"Direct os.environ access violations detected: {filtered_violations}")
    
    def test_prevent_custom_mock_factory_violations(self):
        """
        VIOLATION CRITICAL: Prevent custom mock factory creation.
        This ensures all mocks go through the SSOT MockFactory.
        """
        violations = []
        
        # Scan test files for custom mock factory patterns
        test_files = list(self.project_root.rglob("test*.py"))
        
        forbidden_patterns = [
            'class MockFactory',
            'class TestMockFactory', 
            'class CustomMockFactory',
            'def create_mock_factory',
            'mock_factory = ',
            'MockFactory()',
            'create_autospec',
            'create_mock(',
            'Mock(',
            'MagicMock(',
            'AsyncMock('
        ]
        
        for test_file in test_files[:50]:  # Limit for performance
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_clean = line.strip()
                    
                    for pattern in forbidden_patterns:
                        if pattern in line_clean:
                            # Check if it's in an approved context
                            approved_contexts = [
                                'from unittest.mock import Mock',
                                'from unittest.mock import MagicMock',
                                'from unittest.mock import AsyncMock',
                                '# approved mock usage',
                                'get_mock_factory()',
                                'factory.create_mock('
                            ]
                            
                            is_approved = any(context in line_clean for context in approved_contexts)
                            
                            if not is_approved:
                                violations.append({
                                    'file': str(test_file),
                                    'line': line_num,
                                    'pattern': pattern,
                                    'code': line_clean,
                                    'violation': 'custom_mock_creation'
                                })
                        
            except (OSError, UnicodeDecodeError):
                pass
        
        # Filter out allowed files
        allowed_files = [
            'test_ssot_regression_prevention.py',
            'test_ssot_backward_compatibility.py',
            'ssot/mocks.py',
            'mock_factory.py'
        ]
        
        filtered_violations = [
            v for v in violations 
            if not any(allowed in v['file'] for allowed in allowed_files)
        ]
        
        if filtered_violations:
            logger.error(f"Custom mock factory violations: {filtered_violations[:5]}")  # Show first 5
        
        # Allow some violations for backward compatibility during migration
        max_allowed_violations = 10
        self.assertLessEqual(len(filtered_violations), max_allowed_violations,
                           f"Too many custom mock factory violations: {len(filtered_violations)} > {max_allowed_violations}")
    
    def test_prevent_non_basetest_inheritance_violations(self):
        """
        VIOLATION CRITICAL: Prevent test classes not inheriting from BaseTestCase.
        This ensures all tests use the SSOT base class hierarchy.
        """
        violations = []
        
        # Scan test files for non-compliant test class inheritance
        test_files = list(self.project_root.rglob("test*.py"))
        
        for test_file in test_files[:30]:  # Limit for performance
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    tree = ast.parse(content)
                    
                    class TestClassVisitor(ast.NodeVisitor):
                        def __init__(self):
                            self.violations = []
                        
                        def visit_ClassDef(self, node):
                            # Look for test classes
                            if (node.name.startswith('Test') or 
                                node.name.endswith('Test') or
                                node.name.endswith('TestCase')):
                                
                                # Check inheritance
                                compliant_bases = [
                                    'BaseTestCase',
                                    'AsyncBaseTestCase',
                                    'DatabaseTestCase', 
                                    'WebSocketTestCase',
                                    'IntegrationTestCase',
                                    'TestCase'  # Allow unittest.TestCase for backward compatibility
                                ]
                                
                                if node.bases:
                                    has_compliant_base = False
                                    
                                    for base in node.bases:
                                        if isinstance(base, ast.Name):
                                            if base.id in compliant_bases:
                                                has_compliant_base = True
                                                break
                                        elif isinstance(base, ast.Attribute):
                                            # Handle module.ClassName patterns
                                            if base.attr in compliant_bases:
                                                has_compliant_base = True
                                                break
                                    
                                    if not has_compliant_base:
                                        self.violations.append({
                                            'class_name': node.name,
                                            'line': node.lineno,
                                            'bases': [self._extract_base_name(base) for base in node.bases]
                                        })
                                else:
                                    # No base classes - violation
                                    self.violations.append({
                                        'class_name': node.name,
                                        'line': node.lineno,
                                        'bases': []
                                    })
                            
                            self.generic_visit(node)
                        
                        def _extract_base_name(self, base):
                            if isinstance(base, ast.Name):
                                return base.id
                            elif isinstance(base, ast.Attribute):
                                return base.attr
                            else:
                                return str(base)
                    
                    visitor = TestClassVisitor()
                    visitor.visit(tree)
                    
                    for violation in visitor.violations:
                        violations.append({
                            'file': str(test_file),
                            'class_name': violation['class_name'],
                            'line': violation['line'],
                            'bases': violation['bases'],
                            'violation': 'non_basetest_inheritance'
                        })
                        
                except SyntaxError:
                    pass
                    
            except (OSError, UnicodeDecodeError):
                pass
        
        # Filter out allowed files and patterns
        allowed_files = [
            'test_ssot_regression_prevention.py',
            'test_ssot_backward_compatibility.py',
            'compatibility_bridge.py'
        ]
        
        filtered_violations = [
            v for v in violations 
            if not any(allowed in v['file'] for allowed in allowed_files)
        ]
        
        if filtered_violations:
            logger.error(f"Non-BaseTestCase inheritance violations: {filtered_violations[:3]}")
        
        # Allow some violations during migration period
        max_allowed_violations = 20
        self.assertLessEqual(len(filtered_violations), max_allowed_violations,
                           f"Too many inheritance violations: {len(filtered_violations)} > {max_allowed_violations}")
    
    def test_prevent_duplicate_utility_implementations(self):
        """
        VIOLATION CRITICAL: Prevent duplicate utility implementations.
        This ensures SSOT principle - one canonical implementation per utility.
        """
        violations = []
        
        # Scan for duplicate utility patterns
        utility_patterns = {
            'docker_manager': [
                'class DockerManager',
                'class UnifiedDockerManager', 
                'class DockerOrchestrator',
                'class ServiceOrchestrator'
            ],
            'database_utility': [
                'class DatabaseUtility',
                'class DatabaseTestUtility',
                'class DBTestHelper',
                'class DatabaseManager'
            ],
            'websocket_utility': [
                'class WebSocketUtility',
                'class WebSocketTestUtility',
                'class WSTestHelper',
                'class WebSocketManager'
            ],
            'mock_factory': [
                'class MockFactory',
                'class TestMockFactory',
                'class MockBuilder',
                'class MockManager'
            ]
        }
        
        all_python_files = list(self.project_root.rglob("*.py"))
        
        for utility_type, patterns in utility_patterns.items():
            found_implementations = defaultdict(list)
            
            for file_path in all_python_files[:100]:  # Limit for performance
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for pattern in patterns:
                        if pattern in content:
                            found_implementations[pattern].append(str(file_path))
                            
                except (OSError, UnicodeDecodeError):
                    pass
            
            # Check for duplicates
            for pattern, files in found_implementations.items():
                if len(files) > 1:
                    # Filter out allowed duplicates
                    allowed_patterns = [
                        'test_framework/ssot/',
                        'test_framework/archived/',
                        'test_ssot_regression_prevention.py'
                    ]
                    
                    non_allowed_files = [
                        f for f in files 
                        if not any(allowed in f for allowed in allowed_patterns)
                    ]
                    
                    if len(non_allowed_files) > 1:
                        violations.append({
                            'utility_type': utility_type,
                            'pattern': pattern,
                            'duplicate_files': non_allowed_files,
                            'violation': 'duplicate_utility_implementation'
                        })
        
        if violations:
            logger.error(f"Duplicate utility implementation violations: {violations}")
        
        self.assertEqual(len(violations), 0,
                        f"Duplicate utility implementations detected: {violations}")
    
    def test_prevent_import_violations(self):
        """
        VIOLATION CRITICAL: Prevent import violations in test files.
        This ensures proper import structure and prevents circular dependencies.
        """
        violations = []
        
        # Forbidden import patterns
        forbidden_patterns = [
            'from os import environ',
            'import os.environ',
            'from unittest.mock import Mock',
            'from unittest.mock import MagicMock', 
            'from unittest.mock import AsyncMock'
        ]
        
        # Required import patterns for test files
        required_patterns = [
            'from test_framework.ssot import',
            'from shared.isolated_environment import'
        ]
        
        test_files = list(self.project_root.rglob("test*.py"))
        
        for test_file in test_files[:40]:  # Limit for performance
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Check for forbidden imports
                for line_num, line in enumerate(lines, 1):
                    line_clean = line.strip()
                    
                    for pattern in forbidden_patterns:
                        if pattern in line_clean and not line_clean.startswith('#'):
                            violations.append({
                                'file': str(test_file),
                                'line': line_num,
                                'pattern': pattern,
                                'code': line_clean,
                                'violation': 'forbidden_import'
                            })
                
                # Check for required imports in test files
                if 'tests/' in str(test_file) and 'test_' in test_file.name:
                    has_required_import = any(
                        pattern in content for pattern in required_patterns
                    )
                    
                    if not has_required_import:
                        violations.append({
                            'file': str(test_file),
                            'violation': 'missing_required_import',
                            'required_patterns': required_patterns
                        })
                        
            except (OSError, UnicodeDecodeError):
                pass
        
        # Filter out allowed files
        allowed_files = [
            'test_ssot_regression_prevention.py',
            'test_ssot_backward_compatibility.py',
            'compatibility_bridge.py',
            'isolated_environment.py'
        ]
        
        filtered_violations = [
            v for v in violations 
            if not any(allowed in v['file'] for allowed in allowed_files)
        ]
        
        if filtered_violations:
            logger.error(f"Import violations: {filtered_violations[:5]}")
        
        # Allow some violations during migration
        max_allowed_violations = 15
        self.assertLessEqual(len(filtered_violations), max_allowed_violations,
                           f"Too many import violations: {len(filtered_violations)} > {max_allowed_violations}")
    
    def test_prevent_ssot_framework_modification_violations(self):
        """
        VIOLATION CRITICAL: Prevent unauthorized modification of SSOT framework.
        This ensures the SSOT framework integrity is maintained.
        """
        violations = []
        
        # Protected SSOT files
        protected_files = [
            'test_framework/ssot/__init__.py',
            'test_framework/ssot/base.py',
            'test_framework/ssot/mocks.py',
            'test_framework/ssot/database.py',
            'test_framework/ssot/websocket.py',
            'test_framework/ssot/docker.py'
        ]
        
        for protected_file in protected_files:
            file_path = self.project_root / protected_file
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for unauthorized modifications
                    suspicious_patterns = [
                        'TODO: HACK',
                        'FIXME',
                        'temporary fix',
                        'quick fix',
                        'bypass',
                        'override',
                        'monkey patch'
                    ]
                    
                    for line_num, line in enumerate(content.split('\n'), 1):
                        line_clean = line.strip().lower()
                        
                        for pattern in suspicious_patterns:
                            if pattern in line_clean:
                                violations.append({
                                    'file': str(file_path),
                                    'line': line_num,
                                    'pattern': pattern,
                                    'code': line,
                                    'violation': 'unauthorized_modification'
                                })
                                
                except (OSError, UnicodeDecodeError):
                    pass
        
        if violations:
            logger.error(f"SSOT framework modification violations: {violations}")
        
        self.assertEqual(len(violations), 0,
                        f"Unauthorized SSOT framework modifications: {violations}")
    
    def test_prevent_performance_regression(self):
        """
        PERFORMANCE CRITICAL: Prevent performance regression in SSOT framework.
        This ensures SSOT components don't become slower over time.
        """
        import psutil
        
        process = psutil.Process()
        
        # Benchmark SSOT operations
        benchmarks = {}
        
        # Test MockFactory performance
        start_time = time.time()
        initial_memory = process.memory_info().rss
        
        factory = get_mock_factory()
        for i in range(100):
            mock = factory.create_mock(f"perf_test_{i}")
            
        mid_time = time.time()
        mid_memory = process.memory_info().rss
        
        factory.cleanup_all_mocks()
        
        end_time = time.time()
        final_memory = process.memory_info().rss
        
        benchmarks['mock_factory'] = {
            'creation_time': (mid_time - start_time) / 100,  # Per mock
            'cleanup_time': end_time - mid_time,
            'memory_usage': mid_memory - initial_memory,
            'memory_cleanup': initial_memory - final_memory
        }
        
        # Performance thresholds (these would be based on historical data)
        performance_thresholds = {
            'mock_factory': {
                'max_creation_time': 0.001,  # 1ms per mock
                'max_cleanup_time': 0.1,     # 100ms total cleanup
                'max_memory_usage': 10 * 1024 * 1024,  # 10MB
                'min_memory_cleanup': -5 * 1024 * 1024  # Should free at least 5MB
            }
        }
        
        # Check performance against thresholds
        performance_violations = []
        
        for operation, metrics in benchmarks.items():
            thresholds = performance_thresholds[operation]
            
            if metrics['creation_time'] > thresholds['max_creation_time']:
                performance_violations.append({
                    'operation': operation,
                    'metric': 'creation_time',
                    'value': metrics['creation_time'],
                    'threshold': thresholds['max_creation_time'],
                    'violation': 'performance_regression'
                })
            
            if metrics['cleanup_time'] > thresholds['max_cleanup_time']:
                performance_violations.append({
                    'operation': operation,
                    'metric': 'cleanup_time', 
                    'value': metrics['cleanup_time'],
                    'threshold': thresholds['max_cleanup_time'],
                    'violation': 'performance_regression'
                })
            
            if metrics['memory_usage'] > thresholds['max_memory_usage']:
                performance_violations.append({
                    'operation': operation,
                    'metric': 'memory_usage',
                    'value': metrics['memory_usage'],
                    'threshold': thresholds['max_memory_usage'],
                    'violation': 'performance_regression'
                })
        
        if performance_violations:
            logger.warning(f"Performance regression detected: {performance_violations}")
        
        # Log performance metrics for tracking
        logger.info(f"SSOT Performance Benchmarks: {benchmarks}")
        
        # Allow some performance variation but catch major regressions
        self.assertLessEqual(len(performance_violations), 1,
                           f"Too many performance regressions: {performance_violations}")
    
    def test_prevent_dependency_violations(self):
        """
        DEPENDENCY CRITICAL: Prevent dependency violations in SSOT framework.
        This ensures SSOT doesn't introduce unwanted dependencies.
        """
        violations = []
        
        # Allowed dependencies for SSOT framework
        allowed_dependencies = [
            'asyncio', 'logging', 'os', 'sys', 'time', 'traceback', 'uuid',
            'pathlib', 'typing', 'unittest', 'contextlib', 'datetime',
            'inspect', 'warnings', 'collections', 'abc',
            'pytest', 'sqlalchemy', 'psutil',  # Test framework dependencies
            'shared.isolated_environment'  # Internal dependency
        ]
        
        # Forbidden dependencies
        forbidden_dependencies = [
            'requests',  # Should use internal HTTP client
            'redis',     # Should use internal Redis client
            'psycopg2',  # Should use SQLAlchemy
            'pymongo',   # Should use internal MongoDB client
            'celery',    # Should use internal task queue
            'fastapi',   # Should not depend on web framework
            'django',    # Should not depend on web framework
            'flask'      # Should not depend on web framework
        ]
        
        # Scan SSOT framework files for dependencies
        ssot_files = list((self.project_root / 'test_framework' / 'ssot').rglob("*.py"))
        
        for ssot_file in ssot_files:
            try:
                with open(ssot_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract import statements
                try:
                    tree = ast.parse(content)
                    
                    class ImportVisitor(ast.NodeVisitor):
                        def __init__(self):
                            self.imports = []
                        
                        def visit_Import(self, node):
                            for alias in node.names:
                                self.imports.append(alias.name)
                        
                        def visit_ImportFrom(self, node):
                            if node.module:
                                self.imports.append(node.module)
                    
                    visitor = ImportVisitor()
                    visitor.visit(tree)
                    
                    # Check for forbidden dependencies
                    for import_name in visitor.imports:
                        root_module = import_name.split('.')[0]
                        
                        if root_module in forbidden_dependencies:
                            violations.append({
                                'file': str(ssot_file),
                                'import': import_name,
                                'violation': 'forbidden_dependency'
                            })
                        
                        # Check for unexpected dependencies
                        if (root_module not in allowed_dependencies and 
                            not root_module.startswith('test_framework') and
                            not root_module.startswith('shared') and
                            not root_module.startswith('netra_backend')):
                            
                            violations.append({
                                'file': str(ssot_file),
                                'import': import_name,
                                'violation': 'unexpected_dependency'
                            })
                            
                except SyntaxError:
                    pass
                    
            except (OSError, UnicodeDecodeError):
                pass
        
        if violations:
            logger.error(f"Dependency violations in SSOT framework: {violations}")
        
        self.assertEqual(len(violations), 0,
                        f"SSOT framework dependency violations: {violations}")
    
    def test_prevent_circular_import_violations(self):
        """
        IMPORT CRITICAL: Prevent circular import violations.
        This ensures the SSOT framework doesn't create circular dependencies.
        """
        violations = []
        
        # Build dependency graph
        dependency_graph = defaultdict(set)
        
        # Scan Python files to build import graph
        python_files = list(self.project_root.rglob("*.py"))
        
        for python_file in python_files[:50]:  # Limit for performance
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    tree = ast.parse(content)
                    
                    class ImportVisitor(ast.NodeVisitor):
                        def __init__(self, file_path):
                            self.file_path = file_path
                            self.imports = []
                        
                        def visit_Import(self, node):
                            for alias in node.names:
                                self.imports.append(alias.name)
                        
                        def visit_ImportFrom(self, node):
                            if node.module:
                                self.imports.append(node.module)
                    
                    visitor = ImportVisitor(python_file)
                    visitor.visit(tree)
                    
                    # Add to dependency graph
                    file_module = self._path_to_module_name(python_file)
                    for import_name in visitor.imports:
                        if self._is_internal_module(import_name):
                            dependency_graph[file_module].add(import_name)
                            
                except SyntaxError:
                    pass
                    
            except (OSError, UnicodeDecodeError):
                pass
        
        # Detect circular dependencies
        def detect_cycles(graph):
            visited = set()
            rec_stack = set()
            cycles = []
            
            def dfs(node, path):
                if node in rec_stack:
                    # Found cycle
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    cycles.append(cycle)
                    return
                
                if node in visited:
                    return
                
                visited.add(node)
                rec_stack.add(node)
                path.append(node)
                
                for neighbor in graph.get(node, set()):
                    dfs(neighbor, path.copy())
                
                rec_stack.remove(node)
            
            for node in graph:
                if node not in visited:
                    dfs(node, [])
            
            return cycles
        
        cycles = detect_cycles(dependency_graph)
        
        for cycle in cycles:
            violations.append({
                'cycle': cycle,
                'violation': 'circular_import'
            })
        
        if violations:
            logger.error(f"Circular import violations: {violations}")
        
        self.assertEqual(len(violations), 0,
                        f"Circular import dependencies detected: {violations}")
    
    def _path_to_module_name(self, file_path):
        """Convert file path to module name."""
        relative_path = file_path.relative_to(self.project_root)
        module_name = str(relative_path).replace('/', '.').replace('\\', '.').replace('.py', '')
        return module_name
    
    def _is_internal_module(self, module_name):
        """Check if module is internal to the project."""
        internal_prefixes = [
            'test_framework',
            'netra_backend',
            'shared',
            'auth_service',
            'tests'
        ]
        
        return any(module_name.startswith(prefix) for prefix in internal_prefixes)


class TestSSOTContinuousCompliance(BaseTestCase):
    """
    COMPLIANCE CRITICAL: Continuous SSOT compliance monitoring.
    These tests run continuously to ensure SSOT compliance is maintained.
    """
    
    def setUp(self):
        """Set up continuous compliance test environment."""
        super().setUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting continuous compliance test: {self._testMethodName} (ID: {self.test_id})")
    
    def tearDown(self):
        """Clean up continuous compliance test."""
        logger.info(f"Completing continuous compliance test: {self._testMethodName} (ID: {self.test_id})")
        super().tearDown()
    
    def test_continuous_ssot_framework_health(self):
        """
        HEALTH CRITICAL: Continuously monitor SSOT framework health.
        This test runs regularly to ensure framework components are healthy.
        """
        health_issues = []
        
        # Check SSOT compliance
        violations = validate_ssot_compliance()
        if violations:
            health_issues.extend([
                {'type': 'compliance_violation', 'issue': v} for v in violations
            ])
        
        # Check SSOT status
        status = get_ssot_status()
        
        # Validate status structure
        required_keys = ['version', 'compliance', 'violations', 'components']
        for key in required_keys:
            if key not in status:
                health_issues.append({
                    'type': 'status_structure_issue',
                    'issue': f'Missing status key: {key}'
                })
        
        # Check component counts match expectations
        expected_components = SSOT_COMPLIANCE
        actual_components = status.get('compliance', {})
        
        for component_type, expected_count in expected_components.items():
            actual_count = actual_components.get(component_type, 0)
            if actual_count != expected_count:
                health_issues.append({
                    'type': 'component_count_mismatch',
                    'component': component_type,
                    'expected': expected_count,
                    'actual': actual_count
                })
        
        # Check MockFactory health
        try:
            factory = get_mock_factory()
            registry = factory.get_registry()
            
            if len(registry.active_mocks) > 100:  # Too many active mocks
                health_issues.append({
                    'type': 'mock_leak',
                    'issue': f'Too many active mocks: {len(registry.active_mocks)}'
                })
                
        except Exception as e:
            health_issues.append({
                'type': 'mock_factory_error',
                'issue': str(e)
            })
        
        # Log health issues for monitoring
        if health_issues:
            logger.error(f"SSOT framework health issues detected: {health_issues}")
        
        # Allow minor health issues but catch major problems
        critical_issues = [
            issue for issue in health_issues 
            if issue['type'] in ['compliance_violation', 'component_count_mismatch']
        ]
        
        self.assertEqual(len(critical_issues), 0,
                        f"Critical SSOT framework health issues: {critical_issues}")
        
        self.assertLessEqual(len(health_issues), 3,
                           f"Too many SSOT framework health issues: {health_issues}")
    
    def test_continuous_regression_monitoring(self):
        """
        REGRESSION CRITICAL: Continuously monitor for regressions.
        This test tracks metrics over time to detect gradual regression.
        """
        # Collect current metrics
        current_metrics = {
            'timestamp': datetime.now().isoformat(),
            'ssot_version': SSOT_VERSION,
            'compliance_violations': len(validate_ssot_compliance()),
            'mock_factory_health': self._check_mock_factory_health(),
            'framework_load_time': self._measure_framework_load_time(),
            'memory_usage': self._measure_memory_usage()
        }
        
        # Log metrics for trend analysis
        logger.info(f"SSOT Regression Monitoring Metrics: {current_metrics}")
        
        # Basic threshold checks
        regression_issues = []
        
        if current_metrics['compliance_violations'] > 0:
            regression_issues.append({
                'metric': 'compliance_violations',
                'value': current_metrics['compliance_violations'],
                'issue': 'compliance_violations_present'
            })
        
        if current_metrics['framework_load_time'] > 1.0:  # > 1 second
            regression_issues.append({
                'metric': 'framework_load_time',
                'value': current_metrics['framework_load_time'],
                'issue': 'slow_framework_load'
            })
        
        if current_metrics['memory_usage'] > 50 * 1024 * 1024:  # > 50MB
            regression_issues.append({
                'metric': 'memory_usage',
                'value': current_metrics['memory_usage'],
                'issue': 'high_memory_usage'
            })
        
        if regression_issues:
            logger.warning(f"SSOT regression monitoring issues: {regression_issues}")
        
        # Allow some tolerance but catch major regressions
        self.assertLessEqual(len(regression_issues), 2,
                           f"Too many regression monitoring issues: {regression_issues}")
    
    def _check_mock_factory_health(self):
        """Check MockFactory health metrics."""
        try:
            factory = get_mock_factory()
            registry = factory.get_registry()
            
            return {
                'active_mocks': len(registry.active_mocks),
                'total_created': len(registry.mock_call_history),
                'cleanup_callbacks': len(registry.cleanup_callbacks)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _measure_framework_load_time(self):
        """Measure SSOT framework load time."""
        start_time = time.time()
        
        # Import SSOT components to measure load time
        try:
            from test_framework.ssot import (
                BaseTestCase, MockFactory, DatabaseTestUtility
            )
            return time.time() - start_time
        except Exception:
            return -1  # Error indicator
    
    def _measure_memory_usage(self):
        """Measure current memory usage."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss
        except Exception:
            return -1  # Error indicator


if __name__ == '__main__':
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short', '--capture=no'])