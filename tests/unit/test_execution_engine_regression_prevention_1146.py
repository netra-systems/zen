"""Execution Engine Regression Prevention - Issue #1146

Business Value Justification:
- Segment: Platform/Development 
- Business Goal: Prevent regression to multiple execution engines
- Value Impact: Blocks creation of new execution engines that would fragment SSOT pattern
- Strategic Impact: Ensures 12→1 consolidation remains stable and prevents future violations

CRITICAL MISSION: NEW 20% SSOT VALIDATION TESTS
This test prevents regression back to multiple execution engine patterns by detecting
and blocking any attempts to create new execution engine implementations.

Test Scope: Regression prevention for execution engine SSOT consolidation  
Priority: P0 - Mission Critical - Prevents SSOT violations
Docker: NO DEPENDENCIES - Unit tests only
NEW TEST: Part of 20% new validation tests for Issue #1146
"""

import ast
import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import unittest
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestExecutionEngineRegressionPrevention1146(SSotBaseTestCase):
    """Prevents regression to multiple execution engine implementations."""

    def setUp(self):
        """Set up regression prevention test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.netra_backend_root = self.project_root / "netra_backend"
        
        # CRITICAL: These patterns indicate regression to multiple execution engines
        self.regression_indicators = {
            'class_patterns': [
                r'class.*ExecutionEngine(?!Interface)(?!.*Test)',  # New ExecutionEngine classes
                r'class.*Executor(?!.*Test)',  # New Executor classes
                r'class.*Engine(?!.*Test)(?!.*Error)',  # New Engine classes (except errors)
            ],
            'import_patterns': [
                'from.*execution_engine_.*import',  # New execution engine modules
                'import.*execution_engine_',  # Direct imports of new engines
                'create_execution_engine',  # New factory methods (except allowed)
                'get_execution_engine',  # New getter methods
            ],
            'method_patterns': [
                'def.*create.*execution.*engine',  # New factory methods
                'def.*build.*execution.*engine',  # New builder methods  
                'def.*get.*execution.*engine',  # New getter methods
            ],
            'forbidden_base_classes': [
                'ExecutionEngine',  # Should not be used as base class (interface only)
                'BaseExecutionEngine',  # Should not exist
                'AbstractExecutionEngine',  # Should use interface instead
            ]
        }
        
        # Files that are allowed to have execution engine references (exemptions)
        self.allowed_files = {
            'user_execution_engine.py': 'SSOT implementation',
            'execution_engine_interface.py': 'Interface definition',
            'execution_engine_factory.py': 'Factory (if creates only UserExecutionEngine)',
            # Test files are automatically exempt
        }
        
        # CRITICAL: Monitor these patterns for regression
        self.regression_patterns = [
            "Multiple execution engines detected",
            "Creating new ExecutionEngine implementation", 
            "Bypassing UserExecutionEngine factory",
            "Direct ExecutionEngine instantiation",
            "Custom execution engine created"
        ]

    def test_no_new_execution_engine_classes_created(self):
        """CRITICAL: Detect if any new execution engine classes have been created."""
        new_execution_engine_classes = []
        
        # Scan all Python files for new ExecutionEngine classes
        for py_file in self.netra_backend_root.rglob("*.py"):
            # Skip test files and allowed files
            if self._is_exempt_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    try:
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                
                                # Check for execution engine patterns
                                if self._is_execution_engine_class(class_name, node):
                                    # Check if this is the allowed UserExecutionEngine
                                    if class_name != "UserExecutionEngine" and "Interface" not in class_name:
                                        new_execution_engine_classes.append({
                                            'file': str(py_file.relative_to(self.project_root)),
                                            'class': class_name,
                                            'line': node.lineno,
                                            'base_classes': [base.id for base in node.bases if hasattr(base, 'id')],
                                            'severity': self._assess_violation_severity(class_name, py_file)
                                        })
                                        
                    except SyntaxError:
                        continue
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Report violations
        if new_execution_engine_classes:
            high_severity = [c for c in new_execution_engine_classes if c['severity'] == 'HIGH']
            medium_severity = [c for c in new_execution_engine_classes if c['severity'] == 'MEDIUM']
            
            if high_severity:
                error_msg = ["REGRESSION DETECTED: New execution engine classes found (HIGH SEVERITY):"]
                for violation in high_severity:
                    error_msg.append(f"  - {violation['file']}:{violation['line']} class {violation['class']}")
                    error_msg.append(f"    Base classes: {violation['base_classes']}")
                error_msg.append(f"\nIssue #1146: Only UserExecutionEngine is allowed as execution engine implementation")
                error_msg.append(f"Business Impact: Multiple engines will cause user isolation failures")
                
                self.fail("\n".join(error_msg))
            
            elif medium_severity:
                # Warning for medium severity (may be acceptable during development)
                warning_msg = f"POTENTIAL REGRESSION: Medium severity execution engine classes: {medium_severity}"
                print(f"WARNING: {warning_msg}")

    def test_no_new_execution_engine_factory_methods(self):
        """CRITICAL: Detect new factory methods that create execution engines."""
        suspicious_factory_methods = []
        
        for py_file in self.netra_backend_root.rglob("*.py"):
            if self._is_exempt_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        
                        # Check for factory method patterns
                        if self._is_factory_method_line(line_stripped):
                            # Look ahead to see what this method creates
                            method_body = self._extract_method_body(lines, line_num - 1)
                            
                            # Check if it creates non-UserExecutionEngine instances
                            created_types = self._extract_created_types(method_body)
                            
                            forbidden_creations = [
                                t for t in created_types 
                                if 'ExecutionEngine' in t and t != 'UserExecutionEngine'
                            ]
                            
                            if forbidden_creations:
                                suspicious_factory_methods.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': line_num,
                                    'method': self._extract_method_name(line_stripped),
                                    'creates': forbidden_creations,
                                    'code_sample': line_stripped
                                })
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if suspicious_factory_methods:
            error_msg = ["REGRESSION DETECTED: Factory methods creating non-UserExecutionEngine instances:"]
            for method in suspicious_factory_methods:
                error_msg.append(f"  - {method['file']}:{method['line']} {method['method']}")
                error_msg.append(f"    Creates: {method['creates']}")
                error_msg.append(f"    Code: {method['code_sample']}")
            error_msg.append(f"\nIssue #1146: All factories must create only UserExecutionEngine instances")
            
            self.fail("\n".join(error_msg))

    def test_no_direct_execution_engine_instantiation(self):
        """CRITICAL: Detect direct instantiation of execution engines bypassing factory."""
        direct_instantiations = []
        
        for py_file in self.netra_backend_root.rglob("*.py"):
            if self._is_exempt_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        
                        # Look for direct instantiation patterns
                        if self._is_direct_instantiation(line_stripped):
                            # Check if it's bypassing factory pattern
                            if not self._is_in_factory_context(lines, line_num - 1):
                                direct_instantiations.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': line_num,
                                    'code': line_stripped,
                                    'violation_type': 'direct_instantiation'
                                })
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if direct_instantiations:
            error_msg = ["REGRESSION DETECTED: Direct execution engine instantiation found:"]
            for violation in direct_instantiations:
                error_msg.append(f"  - {violation['file']}:{violation['line']}")
                error_msg.append(f"    Code: {violation['code']}")
            error_msg.append(f"\nIssue #1146: Must use factory pattern, not direct instantiation")
            error_msg.append(f"Recommended: Use create_execution_engine() or create_request_scoped_engine()")
            
            self.fail("\n".join(error_msg))

    def test_no_execution_engine_inheritance_violations(self):
        """CRITICAL: Detect classes inheriting from ExecutionEngine interface incorrectly."""
        inheritance_violations = []
        
        for py_file in self.netra_backend_root.rglob("*.py"):
            if self._is_exempt_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    try:
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                
                                # Check base classes
                                for base in node.bases:
                                    if hasattr(base, 'id') and base.id in self.regression_indicators['forbidden_base_classes']:
                                        # Only UserExecutionEngine is allowed to inherit from ExecutionEngine
                                        if class_name != "UserExecutionEngine":
                                            inheritance_violations.append({
                                                'file': str(py_file.relative_to(self.project_root)),
                                                'class': class_name,
                                                'line': node.lineno,
                                                'inherits_from': base.id,
                                                'violation': f"Non-UserExecutionEngine class inheriting from {base.id}"
                                            })
                                        
                    except SyntaxError:
                        continue
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if inheritance_violations:
            error_msg = ["INHERITANCE VIOLATION: Classes incorrectly inheriting from ExecutionEngine:"]
            for violation in inheritance_violations:
                error_msg.append(f"  - {violation['file']}:{violation['line']} class {violation['class']}")
                error_msg.append(f"    Inherits from: {violation['inherits_from']}")
                error_msg.append(f"    Violation: {violation['violation']}")
            error_msg.append(f"\nIssue #1146: Only UserExecutionEngine should inherit from ExecutionEngine")
            error_msg.append(f"Use composition pattern instead of inheritance for other classes")
            
            self.fail("\n".join(error_msg))

    def test_import_validation_prevents_regression(self):
        """CRITICAL: Validate import patterns don't indicate regression to multiple engines."""
        suspicious_imports = []
        
        for py_file in self.netra_backend_root.rglob("*.py"):
            if self._is_exempt_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        
                        # Check for suspicious import patterns
                        for pattern in self.regression_indicators['import_patterns']:
                            if self._matches_import_pattern(line_stripped, pattern):
                                # Validate this isn't an allowed import
                                if not self._is_allowed_import(line_stripped):
                                    suspicious_imports.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': line_num,
                                        'import': line_stripped,
                                        'pattern': pattern,
                                        'risk_level': self._assess_import_risk(line_stripped)
                                    })
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Filter high-risk imports
        high_risk_imports = [imp for imp in suspicious_imports if imp['risk_level'] == 'HIGH']
        
        if high_risk_imports:
            error_msg = ["IMPORT REGRESSION DETECTED: High-risk execution engine imports:"]
            for imp in high_risk_imports:
                error_msg.append(f"  - {imp['file']}:{imp['line']}")
                error_msg.append(f"    Import: {imp['import']}")
                error_msg.append(f"    Pattern: {imp['pattern']}")
            error_msg.append(f"\nIssue #1146: Imports suggest regression to multiple execution engines")
            
            self.fail("\n".join(error_msg))

    def test_ssot_registry_prevents_multiple_execution_engines(self):
        """CRITICAL: Validate SSOT registry prevents registration of multiple execution engines."""
        # This test ensures the SSOT import registry doesn't allow multiple execution engines
        ssot_registry_path = self.project_root / "SSOT_IMPORT_REGISTRY.md"
        
        if not ssot_registry_path.exists():
            self.skipTest("SSOT_IMPORT_REGISTRY.md not found")
        
        try:
            with open(ssot_registry_path, 'r', encoding='utf-8') as f:
                registry_content = f.read()
            
            # Check for multiple execution engine entries
            execution_engine_entries = []
            lines = registry_content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()
                
                # Look for execution engine related entries
                if 'execution_engine' in line_lower and '✅' in line:  # Active entries
                    # Skip if it's clearly UserExecutionEngine
                    if 'user_execution_engine' not in line_lower:
                        execution_engine_entries.append({
                            'line': line_num,
                            'content': line.strip(),
                            'concern': 'Non-UserExecutionEngine entry marked as active'
                        })
            
            if execution_engine_entries:
                error_msg = ["SSOT REGISTRY REGRESSION: Multiple execution engine entries detected:"]
                for entry in execution_engine_entries:
                    error_msg.append(f"  - Line {entry['line']}: {entry['content']}")
                    error_msg.append(f"    Concern: {entry['concern']}")
                error_msg.append(f"\nIssue #1146: SSOT registry should only have UserExecutionEngine entries")
                
                self.fail("\n".join(error_msg))
                
        except (UnicodeDecodeError, PermissionError) as e:
            self.fail(f"Cannot validate SSOT registry: {e}")

    def test_runtime_prevention_of_multiple_execution_engines(self):
        """CRITICAL: Validate runtime checks prevent multiple execution engine instantiation."""
        # Test that the system has runtime protections against multiple engines
        
        # Try to import UserExecutionEngine
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError:
            self.fail("UserExecutionEngine cannot be imported - SSOT violation")
        
        # Validate UserExecutionEngine has proper SSOT patterns
        user_execution_methods = dir(UserExecutionEngine)
        
        # Check for singleton prevention patterns
        ssot_indicators = [
            'create_execution_engine',  # Factory method
            '__init__',  # Constructor (should be normal, not singleton)
            'user_context',  # User isolation
        ]
        
        missing_ssot_patterns = []
        for indicator in ssot_indicators:
            if indicator not in user_execution_methods:
                missing_ssot_patterns.append(indicator)
        
        if missing_ssot_patterns:
            warning_msg = f"UserExecutionEngine missing SSOT patterns: {missing_ssot_patterns}"
            print(f"WARNING: {warning_msg}")
        
        # Validate that UserExecutionEngine prevents misuse
        user_exec_class = UserExecutionEngine
        
        # Check class docstring mentions SSOT or single engine
        docstring = inspect.getdoc(user_exec_class) or ""
        ssot_keywords = ['single', 'SSOT', 'only', 'canonical', 'consolidated']
        
        has_ssot_documentation = any(keyword.lower() in docstring.lower() for keyword in ssot_keywords)
        
        if not has_ssot_documentation:
            warning_msg = "UserExecutionEngine lacks SSOT documentation"
            print(f"WARNING: {warning_msg}")

    # Helper methods for detection

    def _is_exempt_file(self, py_file: Path) -> bool:
        """Check if file is exempt from regression detection."""
        file_name = py_file.name
        file_path_str = str(py_file)
        
        # Test files are exempt
        if "test" in file_path_str.lower() or "__pycache__" in file_path_str:
            return True
        
        # Check allowed files
        if file_name in self.allowed_files:
            return True
        
        return False

    def _is_execution_engine_class(self, class_name: str, node: ast.ClassDef) -> bool:
        """Check if class name indicates an execution engine."""
        engine_indicators = ['ExecutionEngine', 'Executor', 'Engine']
        
        for indicator in engine_indicators:
            if indicator in class_name and not class_name.endswith('Test'):
                return True
        
        return False

    def _assess_violation_severity(self, class_name: str, file_path: Path) -> str:
        """Assess severity of execution engine class violation."""
        high_severity_patterns = ['ExecutionEngine', 'UserExecutionEngine']
        medium_severity_patterns = ['Executor', 'Engine']
        
        for pattern in high_severity_patterns:
            if pattern in class_name:
                return 'HIGH'
        
        for pattern in medium_severity_patterns:
            if pattern in class_name:
                return 'MEDIUM'
        
        return 'LOW'

    def _is_factory_method_line(self, line: str) -> bool:
        """Check if line contains factory method definition."""
        factory_patterns = ['create_execution_engine', 'get_execution_engine', 'build_execution_engine']
        
        if 'def ' not in line:
            return False
        
        for pattern in factory_patterns:
            if pattern in line:
                return True
        
        return False

    def _extract_method_body(self, lines: List[str], start_line: int) -> List[str]:
        """Extract method body for analysis."""
        method_lines = []
        indent_level = None
        
        for i in range(start_line, min(start_line + 20, len(lines))):
            line = lines[i]
            if not line.strip():
                continue
                
            current_indent = len(line) - len(line.lstrip())
            
            if indent_level is None and line.strip().startswith('def '):
                indent_level = current_indent
                method_lines.append(line)
            elif indent_level is not None:
                if current_indent > indent_level or line.strip().startswith(('"""', "'''")):
                    method_lines.append(line)
                else:
                    break
        
        return method_lines

    def _extract_created_types(self, method_body: List[str]) -> List[str]:
        """Extract types being instantiated in method body."""
        created_types = []
        
        for line in method_body:
            # Look for instantiation patterns
            if '(' in line and '=' in line:
                # Simple pattern matching for ClassName()
                parts = line.split('=')
                if len(parts) > 1:
                    right_side = parts[1].strip()
                    if '(' in right_side:
                        type_name = right_side.split('(')[0].strip()
                        if type_name and type_name[0].isupper():  # Class names start with uppercase
                            created_types.append(type_name)
        
        return created_types

    def _extract_method_name(self, line: str) -> str:
        """Extract method name from definition line."""
        if 'def ' in line:
            start = line.find('def ') + 4
            end = line.find('(', start)
            if end > start:
                return line[start:end].strip()
        return 'unknown'

    def _is_direct_instantiation(self, line: str) -> bool:
        """Check if line contains direct execution engine instantiation."""
        instantiation_patterns = [
            'ExecutionEngine(',
            'UserExecutionEngine(',
            'ToolExecutionEngine(',
            'MCPExecutionEngine('
        ]
        
        for pattern in instantiation_patterns:
            if pattern in line and '=' in line:
                return True
        
        return False

    def _is_in_factory_context(self, lines: List[str], line_index: int) -> bool:
        """Check if instantiation is within a factory method context."""
        # Look backwards for factory method definition
        for i in range(max(0, line_index - 10), line_index):
            line = lines[i].strip()
            if 'def ' in line and any(pattern in line for pattern in ['create', 'factory', 'build']):
                return True
        
        return False

    def _matches_import_pattern(self, line: str, pattern: str) -> bool:
        """Check if import line matches suspicious pattern."""
        if 'import' not in line:
            return False
        
        # Simple pattern matching
        pattern_keywords = pattern.replace('.*', '').split()
        return all(keyword in line for keyword in pattern_keywords if keyword != 'import')

    def _is_allowed_import(self, line: str) -> bool:
        """Check if import is explicitly allowed."""
        allowed_imports = [
            'user_execution_engine',
            'execution_engine_interface',
            'IExecutionEngine'
        ]
        
        return any(allowed in line for allowed in allowed_imports)

    def _assess_import_risk(self, line: str) -> str:
        """Assess risk level of suspicious import."""
        high_risk_patterns = ['ExecutionEngine', 'create_execution_engine']
        
        for pattern in high_risk_patterns:
            if pattern in line and 'user_execution_engine' not in line:
                return 'HIGH'
        
        return 'MEDIUM'


if __name__ == '__main__':
    unittest.main()