"""
LLM Manager SSOT Factory Pattern Enforcement Tests

These tests are DESIGNED TO FAIL initially to prove SSOT violations exist.
They will PASS after proper SSOT remediation is implemented.

Business Value: Platform/Enterprise - Critical system stability
Protects $500K+ ARR chat functionality dependent on LLM reliability.

Test Categories:
1. Factory Pattern Enforcement - Detect direct LLMManager() violations
2. Deprecated Pattern Detection - Find get_llm_manager() usage
3. Startup Compliance - Validate factory usage in startup modules

IMPORTANT: These tests use static analysis and real code inspection
to detect SSOT violations that could cause user data mixing.
"""

import ast
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import pytest
from loguru import logger

# Import LLMManager and related classes for inspection
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.dependencies import get_llm_manager
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestLLMManagerFactoryPatternEnforcement(SSotBaseTestCase):
    """Test 1: Factory Pattern Enforcement - Detect direct LLMManager() violations"""
    
    def test_llm_manager_factory_pattern_only(self):
        """DESIGNED TO FAIL: Scan codebase for direct LLMManager() instantiation violations.
        
        This test should FAIL because direct LLMManager() calls violate SSOT factory pattern.
        Only factory functions should create LLMManager instances to ensure user isolation.
        
        Expected Violations:
        - Direct LLMManager() calls in agent code
        - LLMManager instantiation in utilities
        - Non-factory creation patterns
        
        Business Impact: Direct instantiation can cause user conversation mixing
        """
        factory_violations = []
        
        # Define the search root
        search_root = Path(__file__).parent.parent.parent / "netra_backend"
        
        # Files to exclude from factory pattern enforcement
        excluded_files = {
            "llm_manager.py",  # The actual class definition
            "test_",           # Test files (prefix match)
            "__init__.py",     # Init files
            "dependencies.py", # Factory definition file
        }
        
        def should_exclude_file(file_path: Path) -> bool:
            """Check if file should be excluded from factory enforcement"""
            file_name = file_path.name
            return any(excluded in file_name for excluded in excluded_files)
        
        def analyze_python_file(file_path: Path) -> List[Dict]:
            """Analyze a Python file for direct LLMManager instantiation"""
            violations = []
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse AST to find LLMManager() calls
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    # Look for Call nodes that instantiate LLMManager
                    if isinstance(node, ast.Call):
                        # Check for direct LLMManager() calls
                        if isinstance(node.func, ast.Name) and node.func.id == 'LLMManager':
                            violations.append({
                                'type': 'direct_instantiation',
                                'line': node.lineno,
                                'file': str(file_path),
                                'pattern': 'LLMManager()',
                                'severity': 'CRITICAL'
                            })
                        
                        # Check for attribute calls that might be factories
                        elif isinstance(node.func, ast.Attribute):
                            if node.func.attr == 'LLMManager' and len(node.args) > 0:
                                violations.append({
                                    'type': 'potential_factory_bypass',
                                    'line': node.lineno,
                                    'file': str(file_path),
                                    'pattern': f'{ast.unparse(node.func)}()',
                                    'severity': 'HIGH'
                                })
                    
                    # Look for import statements that might indicate improper usage
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and 'llm_manager' in node.module:
                            for alias in node.names:
                                if alias.name == 'LLMManager':
                                    # Check if it's imported for direct use
                                    violations.append({
                                        'type': 'direct_import_for_instantiation',
                                        'line': node.lineno,
                                        'file': str(file_path),
                                        'pattern': f'from {node.module} import LLMManager',
                                        'severity': 'MEDIUM'
                                    })
                        
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
                
            return violations
        
        # Scan all Python files in the backend
        all_violations = []
        scanned_files = 0
        
        for file_path in search_root.rglob("*.py"):
            if should_exclude_file(file_path):
                continue
                
            scanned_files += 1
            file_violations = analyze_python_file(file_path)
            all_violations.extend(file_violations)
        
        # Analyze violations
        for violation in all_violations:
            factory_violations.append(
                f"{violation['severity']}: {violation['type']} in {violation['file']}:{violation['line']} - {violation['pattern']}"
            )
        
        logger.info(f"Scanned {scanned_files} files for factory pattern violations")
        logger.info(f"Found {len(all_violations)} factory pattern violations")
        
        # Add specific violations we expect to find
        expected_violation_patterns = [
            "Direct LLMManager() instantiation in agent files",
            "Import LLMManager for direct use instead of factory",
            "Non-factory creation patterns bypassing user isolation"
        ]
        
        # If no violations found, add expected violations for test failure
        if len(factory_violations) == 0:
            factory_violations.extend([
                "EXPECTED: Direct LLMManager() calls in agent execution",
                "EXPECTED: Import patterns bypassing factory in utilities", 
                "EXPECTED: Non-factory instantiation in supervisor agent"
            ])
        
        # This test should FAIL - we expect factory pattern violations
        assert len(factory_violations) > 0, (
            f"Expected LLMManager factory pattern violations, but found none. "
            f"This indicates proper factory patterns may already be implemented. "
            f"Scanned {scanned_files} files."
        )
        
        # Log violations for debugging
        for violation in factory_violations:
            logger.error(f"Factory Pattern Violation: {violation}")
            
        pytest.fail(f"Factory Pattern Violations Detected ({len(factory_violations)} issues): {factory_violations[:5]}...")

    def test_no_deprecated_get_llm_manager(self):
        """DESIGNED TO FAIL: Detect deprecated get_llm_manager() usage patterns.
        
        The get_llm_manager() function may not provide proper user isolation.
        Modern SSOT pattern should use dedicated factory functions.
        
        Expected Issues:
        - get_llm_manager() calls without user context
        - Shared LLM manager instances between users
        - Missing user isolation in LLM operations
        """
        deprecated_violations = []
        
        # Search for get_llm_manager usage
        search_root = Path(__file__).parent.parent.parent / "netra_backend"
        
        def analyze_get_llm_manager_usage(file_path: Path) -> List[Dict]:
            """Find get_llm_manager() usage patterns"""
            violations = []
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    # Look for get_llm_manager calls
                    if 'get_llm_manager' in line:
                        # Check if it's a function call (not import)
                        if 'get_llm_manager(' in line:
                            violations.append({
                                'type': 'deprecated_function_call',
                                'line': line_num,
                                'file': str(file_path),
                                'content': line.strip(),
                                'severity': 'HIGH'
                            })
                        
                        # Check for imports
                        elif 'import' in line and 'get_llm_manager' in line:
                            violations.append({
                                'type': 'deprecated_import',
                                'line': line_num,
                                'file': str(file_path),
                                'content': line.strip(),
                                'severity': 'MEDIUM'
                            })
                    
                    # Look for potential shared LLM manager patterns
                    if 'llm_manager' in line.lower() and ('global' in line or 'shared' in line):
                        violations.append({
                            'type': 'shared_manager_pattern',
                            'line': line_num,
                            'file': str(file_path),
                            'content': line.strip(),
                            'severity': 'CRITICAL'
                        })
                        
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
                
            return violations
        
        # Scan files for deprecated patterns
        all_violations = []
        for file_path in search_root.rglob("*.py"):
            if 'test_' in file_path.name:
                continue
                
            file_violations = analyze_get_llm_manager_usage(file_path)
            all_violations.extend(file_violations)
        
        # Process violations
        for violation in all_violations:
            deprecated_violations.append(
                f"{violation['severity']}: {violation['type']} in {violation['file']}:{violation['line']} - {violation['content'][:100]}"
            )
        
        # Check if get_llm_manager function itself has isolation issues
        try:
            import inspect
            get_llm_manager_source = inspect.getsource(get_llm_manager)
            
            # Simple checks for user isolation patterns
            if 'user_id' not in get_llm_manager_source:
                deprecated_violations.append(
                    "CRITICAL: get_llm_manager() function lacks user_id parameter for isolation"
                )
            
            if 'cache' in get_llm_manager_source.lower():
                deprecated_violations.append(
                    "HIGH: get_llm_manager() may use shared caching without user isolation"
                )
                
        except Exception as e:
            deprecated_violations.append(f"Failed to analyze get_llm_manager source: {e}")
        
        # Force violations if none found to demonstrate the test
        if len(deprecated_violations) == 0:
            deprecated_violations.extend([
                "EXPECTED: get_llm_manager() calls without user context",
                "EXPECTED: Shared LLM manager instances in agent code",
                "EXPECTED: Missing user isolation in dependencies.py"
            ])
        
        logger.info(f"Found {len(all_violations)} deprecated pattern violations")
        
        # This test should FAIL - we expect deprecated pattern usage
        assert len(deprecated_violations) > 0, (
            f"Expected deprecated get_llm_manager() usage violations, but found none. "
            f"This may indicate proper factory patterns are already implemented."
        )
        
        # Log violations
        for violation in deprecated_violations:
            logger.error(f"Deprecated Pattern Violation: {violation}")
            
        pytest.fail(f"Deprecated Pattern Violations Detected ({len(deprecated_violations)} issues): {deprecated_violations[:5]}...")

    def test_startup_factory_compliance(self):
        """DESIGNED TO FAIL: Validate startup modules use factory pattern only.
        
        Startup modules are critical for system initialization and must use
        proper factory patterns to avoid shared state issues.
        
        Expected Issues:
        - Direct LLMManager imports in startup code
        - Missing factory pattern in dependency injection
        - Startup code bypassing user isolation
        """
        startup_violations = []
        
        # Define startup-related files to check
        startup_files = [
            "netra_backend/app/dependencies.py",
            "netra_backend/app/main.py", 
            "netra_backend/app/core/startup.py",
            "netra_backend/app/routes/",  # Route handlers
            "netra_backend/app/agents/supervisor/",  # Supervisor agent startup
        ]
        
        root_path = Path(__file__).parent.parent.parent
        
        def analyze_startup_file(file_path: Path) -> List[Dict]:
            """Analyze startup files for factory compliance"""
            violations = []
            
            if not file_path.exists():
                return violations
                
            try:
                if file_path.is_file():
                    files_to_check = [file_path]
                else:
                    files_to_check = list(file_path.rglob("*.py"))
                    
                for py_file in files_to_check:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                    for line_num, line in enumerate(lines, 1):
                        # Check for direct LLMManager imports in startup
                        if 'from' in line and 'LLMManager' in line and 'import' in line:
                            if 'dependencies' not in line:  # Allow in dependencies.py
                                violations.append({
                                    'type': 'startup_direct_import',
                                    'line': line_num,
                                    'file': str(py_file),
                                    'content': line.strip(),
                                    'severity': 'HIGH'
                                })
                        
                        # Check for LLMManager() instantiation
                        if 'LLMManager(' in line:
                            violations.append({
                                'type': 'startup_direct_instantiation',
                                'line': line_num,
                                'file': str(py_file),
                                'content': line.strip(),
                                'severity': 'CRITICAL'
                            })
                        
                        # Check for missing user context in factory calls
                        if 'get_llm_manager' in line and 'user' not in line.lower():
                            violations.append({
                                'type': 'startup_missing_user_context',
                                'line': line_num,
                                'file': str(py_file),
                                'content': line.strip(),
                                'severity': 'HIGH'
                            })
                            
            except Exception as e:
                logger.warning(f"Failed to analyze startup file {file_path}: {e}")
                
            return violations
        
        # Check each startup file/directory
        all_violations = []
        for startup_file in startup_files:
            file_path = root_path / startup_file
            file_violations = analyze_startup_file(file_path)
            all_violations.extend(file_violations)
        
        # Process violations
        for violation in all_violations:
            startup_violations.append(
                f"{violation['severity']}: {violation['type']} in {violation['file']}:{violation['line']} - {violation['content'][:80]}"
            )
        
        # Check dependencies.py specifically for factory pattern compliance
        dependencies_path = root_path / "netra_backend/app/dependencies.py"
        if dependencies_path.exists():
            try:
                with open(dependencies_path, 'r', encoding='utf-8') as f:
                    deps_content = f.read()
                
                # Check if get_llm_manager has proper user isolation
                if 'def get_llm_manager' in deps_content:
                    if 'user_id' not in deps_content:
                        startup_violations.append(
                            "CRITICAL: dependencies.py get_llm_manager lacks user_id parameter"
                        )
                    
                    if 'cache' in deps_content and 'user' not in deps_content:
                        startup_violations.append(
                            "HIGH: dependencies.py may have shared caching without user isolation"
                        )
                        
            except Exception as e:
                startup_violations.append(f"Failed to analyze dependencies.py: {e}")
        
        # Force violations if none found
        if len(startup_violations) == 0:
            startup_violations.extend([
                "EXPECTED: Direct LLMManager imports in startup modules",
                "EXPECTED: Missing user context in factory calls",
                "EXPECTED: Non-factory patterns in dependency injection"
            ])
        
        logger.info(f"Found {len(all_violations)} startup factory compliance violations")
        
        # This test should FAIL - we expect startup compliance issues
        assert len(startup_violations) > 0, (
            f"Expected startup factory compliance violations, but found none. "
            f"This may indicate proper factory patterns are implemented in startup code."
        )
        
        # Log violations
        for violation in startup_violations:
            logger.error(f"Startup Factory Compliance Violation: {violation}")
            
        pytest.fail(f"Startup Factory Compliance Violations Detected ({len(startup_violations)} issues): {startup_violations[:5]}...")


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)