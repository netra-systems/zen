"SSOT Execution Engine Violation Detection - Issue #1146"

Business Value Justification:
    - Segment: Platform/Internal
- Business Goal: Stability & System Integrity 
- Value Impact: Prevents execution engine duplication cascade failures affecting $"500K" plus ARR
- Strategic Impact: Ensures 12 execution engines → 1 UserExecutionEngine consolidation remains stable

CRITICAL MISSION: NEW 20% SSOT VALIDATION TESTS
This test detects violations of SSOT execution engine consolidation and prevents
regression back to multiple execution engine patterns that destabilize Golden Path.

Test Scope: SSOT violation detection for 12→1 execution engine consolidation
Priority: P0 - Mission Critical  
Docker: NO DEPENDENCIES - Unit/Integration non-docker only
NEW TEST: Part of 20% new validation tests for Issue #1146
""

import ast
import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import unittest
import pytest

# Add project root to path for test framework imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from test_framework.ssot.base_test_case import SSotBaseTestCase


class SSotExecutionEngineViolationDetection1146Tests(SSotBaseTestCase):
    Detects SSOT violations in execution engine consolidation and prevents regression."
    Detects SSOT violations in execution engine consolidation and prevents regression.""


    def setup_method(self, method=None):
        "Set up SSOT violation detection test environment."
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        self.netra_backend_root = self.project_root / netra_backend""
        
        # CRITICAL: These 11 execution engines must be consolidated into UserExecutionEngine
        self.forbidden_execution_engines = {
            ExecutionEngine: Legacy base class - must be interface only,
            LegacyExecutionEngine: Legacy implementation - must be removed","
            "ToolExecutionEngine: Tool-specific engine - must be consolidated,"
            MCPExecutionEngine: MCP-specific engine - must be consolidated, 
            "EnhancedToolExecutionEngine: Enhanced tool engine - must be consolidated,"
            PipelineExecutor: Pipeline-specific engine - must be consolidated,
            WorkflowExecutor: Workflow-specific engine - must be consolidated","
            "AgentExecutionEngine: Agent-specific engine - must be consolidated,"
            SupervisorExecutionEngine: Supervisor-specific engine - must be consolidated,
            "RegistryExecutionEngine: Registry-specific engine - must be consolidated,"
            FactoryExecutionEngine: Factory-specific engine - must be consolidated,
            UnifiedExecutionEngine: Another unified attempt - must be consolidated"
            UnifiedExecutionEngine: Another unified attempt - must be consolidated""

        }
        
        # ONLY ALLOWED: Single SSOT implementation
        self.allowed_execution_engines = {
            "UserExecutionEngine: SSOT implementation for Issue #1146,"
            IExecutionEngine: Interface definition - allowed,
            "ExecutionEngineInterface: Interface definition - allowed"
        }

    def test_no_forbidden_execution_engine_classes_exist(self):
        CRITICAL: Detect if any forbidden execution engine classes still exist."
        CRITICAL: Detect if any forbidden execution engine classes still exist.""

        forbidden_classes_found = []
        
        # Scan all Python files in netra_backend
        for py_file in self.netra_backend_root.rglob(*.py"):"
            # Skip test files - they can have mock versions
            if test in str(py_file).lower() or __pycache__ in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name
                                if class_name in self.forbidden_execution_engines:
                                    forbidden_classes_found.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'class': class_name,
                                        'reason': self.forbidden_execution_engines[class_name],
                                        'line': node.lineno
                                    }
                    except SyntaxError:
                        continue  # Skip files with syntax errors
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if forbidden_classes_found:
            error_msg = ["SSOT VIOLATION: Forbidden execution engine classes found (must consolidate into UserExecutionEngine):]"
            for violation in forbidden_classes_found:
                error_msg.append(f  - {violation['file']}:{violation['line']} class {violation['class']} ({violation['reason']})
            error_msg.append(f\nIssue #1146: All execution engines must be consolidated into UserExecutionEngine)
            error_msg.append(fBusiness Impact: Multiple execution engines cause state contamination affecting $"500K" plus ARR")"
            
            pytest.fail(\n.join(error_msg))

    def test_no_forbidden_execution_engine_imports(self):
        "CRITICAL: Detect imports of forbidden execution engine classes in production code."
        forbidden_imports_found = []
        
        # Build list of forbidden import patterns
        forbidden_patterns = []
        for forbidden_class in self.forbidden_execution_engines.keys():
            forbidden_patterns.extend([
                ffrom .* import .*{forbidden_class},
                fimport .*{forbidden_class},"
                fimport .*{forbidden_class},"
                f"from .*{forbidden_class.lower()},"
                forbidden_class  # Direct class name usage
            ]
        
        # Scan all Python files in netra_backend (excluding tests)
        for py_file in self.netra_backend_root.rglob(*.py):
            if test in str(py_file).lower() or __pycache__" in str(py_file):"
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        
                        # Skip comments and empty lines
                        if line_stripped.startswith('#') or not line_stripped:
                            continue
                            
                        # Check for forbidden execution engine references
                        for forbidden_class in self.forbidden_execution_engines.keys():
                            if forbidden_class in line and "UserExecutionEngine not in line:"
                                # Additional validation - make sure it's not just a comment or string'
                                if any(keyword in line for keyword in ['import', 'from', 'class', '(', '='):
                                    forbidden_imports_found.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': line_num,
                                        'content': line_stripped,
                                        'forbidden_class': forbidden_class,
                                        'reason': self.forbidden_execution_engines[forbidden_class]
                                    }
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if forbidden_imports_found:
            error_msg = [SSOT VIOLATION: Forbidden execution engine imports found in production code:]
            for violation in forbidden_imports_found:
                error_msg.append(f"  - {violation['file']}:{violation['line']} → {violation['forbidden_class']} ({violation['reason']})"
                error_msg.append(f    Code: {violation['content'][:100]}...")"
            error_msg.append(f\nIssue #1146: All execution engine imports must use UserExecutionEngine)
            error_msg.append(fGolden Path Impact: Multiple engines cause user isolation failures)"
            error_msg.append(fGolden Path Impact: Multiple engines cause user isolation failures)""

            
            pytest.fail("\n.join(error_msg))"

    def test_only_user_execution_engine_allowed_in_ssot_registry(self):
        CRITICAL: Validate SSOT import registry only allows UserExecutionEngine.""
        ssot_registry_path = self.project_root / SSOT_IMPORT_REGISTRY.md
        
        if not ssot_registry_path.exists():
            self.skipTest(SSOT_IMPORT_REGISTRY.md not found - cannot validate execution engine entries)"
            self.skipTest(SSOT_IMPORT_REGISTRY.md not found - cannot validate execution engine entries)""

        
        try:
            with open(ssot_registry_path, 'r', encoding='utf-8') as f:
                registry_content = f.read()
            
            # Find execution engine related entries
            registry_violations = []
            lines = registry_content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()
                
                # Check for forbidden execution engine patterns in registry
                for forbidden_class in self.forbidden_execution_engines.keys():
                    if forbidden_class.lower() in line_lower and "user_execution_engine not in line_lower:"
                        # Skip lines that are marking things as deprecated/removed
                        if not any(marker in line_lower for marker in ['deprecated', 'removed', 'forbidden', 'violation'):
                            registry_violations.append({
                                'line': line_num,
                                'content': line.strip(),
                                'forbidden_class': forbidden_class
                            }
            
            if registry_violations:
                error_msg = [SSOT REGISTRY VIOLATION: Forbidden execution engines found in SSOT registry:]
                for violation in registry_violations:
                    error_msg.append(f"  - Line {violation['line']}: {violation['content']})"
                    error_msg.append(f    Contains forbidden: {violation['forbidden_class']}")"
                error_msg.append(f\nIssue #1146: SSOT registry must only contain UserExecutionEngine entries)
                
                pytest.fail(\n.join(error_msg))"
                pytest.fail(\n.join(error_msg))""

                
        except (UnicodeDecodeError, PermissionError) as e:
            pytest.fail(f"Cannot read SSOT registry: {e})"

    def test_execution_engine_file_consolidation_complete(self):
        CRITICAL: Verify files containing forbidden execution engines are removed/consolidated."
        CRITICAL: Verify files containing forbidden execution engines are removed/consolidated."
        # Files that should be removed or consolidated after Issue #1146
        problematic_files = [
            "netra_backend/app/agents/execution_engine_legacy_adapter.py,"
            netra_backend/app/agents/tool_dispatcher_execution.py, 
            "netra_backend/app/agents/supervisor/mcp_execution_engine.py,"
            netra_backend/app/agents/unified_tool_execution.py,
            netra_backend/app/core/tools/unified_tool_dispatcher.py,  # If it contains ExecutionEngine"
            netra_backend/app/core/tools/unified_tool_dispatcher.py,  # If it contains ExecutionEngine"
            netra_backend/app/services/unified_tool_registry/execution_engine.py"
            netra_backend/app/services/unified_tool_registry/execution_engine.py""

        ]
        
        files_still_exist = []
        files_with_forbidden_classes = []
        
        for file_path in problematic_files:
            full_path = self.project_root / file_path
            
            if full_path.exists():
                files_still_exist.append(file_path)
                
                # Check if file contains forbidden execution engine classes
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for forbidden_class in self.forbidden_execution_engines.keys():
                        if fclass {forbidden_class} in content:
                            files_with_forbidden_classes.append({
                                'file': file_path,
                                'class': forbidden_class,
                                'reason': self.forbidden_execution_engines[forbidden_class]
                            }
                            
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        # Report violations
        if files_with_forbidden_classes:
            error_msg = [CONSOLIDATION INCOMPLETE: Files still contain forbidden execution engine classes:]"
            error_msg = [CONSOLIDATION INCOMPLETE: Files still contain forbidden execution engine classes:]""

            for violation in files_with_forbidden_classes:
                error_msg.append(f"  - {violation['file']} contains class {violation['class']} ({violation['reason']})"
            error_msg.append(f\nIssue #1146: These files must be refactored to use UserExecutionEngine)
            error_msg.append(fBusiness Impact: File fragmentation prevents SSOT consolidation success)
            
            pytest.fail(\n".join(error_msg))"
        
        # Warn about files that still exist but don't have forbidden classes'
        if files_still_exist and not files_with_forbidden_classes:
            warning_msg = fFiles exist but appear cleaned of forbidden classes: {files_still_exist}
            warning_msg += f\nThese files may be safe but should be verified for Issue #1146 consolidation
            print(f"WARNING: {warning_msg}))"

    def test_user_execution_engine_is_only_execution_engine_implementation(self"):"
        CRITICAL: Validate UserExecutionEngine is the only execution engine implementation."
        CRITICAL: Validate UserExecutionEngine is the only execution engine implementation.""

        execution_engine_implementations = []
        
        # Scan for any class that implements execution engine interface
        for py_file in self.netra_backend_root.rglob("*.py):"
            if test in str(py_file).lower() or __pycache__ in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Look for class definitions that might be execution engines
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        
                        # Check for class definitions with execution engine patterns
                        if line_stripped.startswith('class ') and 'ExecutionEngine' in line:
                            class_name = line_stripped.split('(')[0].replace('class ', '').strip(':')
                            
                            # Skip interfaces and allowed classes
                            if class_name not in self.allowed_execution_engines:
                                execution_engine_implementations.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': line_num,
                                    'class': class_name,
                                    'full_line': line_stripped
                                }
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if execution_engine_implementations:
            error_msg = [SSOT VIOLATION: Multiple execution engine implementations found (only UserExecutionEngine allowed):"]"
            for impl in execution_engine_implementations:
                error_msg.append(f  - {impl['file']}:{impl['line']} class {impl['class']})
                error_msg.append(f    Code: {impl['full_line']})
            error_msg.append(f"\nIssue #1146: Only UserExecutionEngine should implement execution engine interface)"
            error_msg.append(fAllowed classes: {list(self.allowed_execution_engines.keys())}")"
            
            pytest.fail(\n.join(error_msg))

    def test_no_execution_engine_factory_creates_forbidden_engines(self):
        ""CRITICAL: Validate factories only create UserExecutionEngine instances.""

        factory_violations = []
        
        # Look for factory methods that might create forbidden execution engines
        factory_patterns = ['create_execution_engine', 'get_execution_engine', 'build_execution_engine']
        
        for py_file in self.netra_backend_root.rglob(*.py):"
        for py_file in self.netra_backend_root.rglob(*.py):"
            if test" in str(py_file).lower() or __pycache__ in str(py_file):"
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        line_stripped = line.strip()
                        
                        # Check for factory methods
                        for pattern in factory_patterns:
                            if pattern in line and 'def ' in line:
                                # Look ahead for what this factory creates
                                for check_line_num in range(line_num, min(line_num + 20, len(lines))):
                                    check_line = lines[check_line_num].strip()
                                    
                                    # Check for instantiation of forbidden engines
                                    for forbidden_class in self.forbidden_execution_engines.keys():
                                        if f'{forbidden_class)(' in check_line and 'return' in check_line:
                                            factory_violations.append({
                                                'file': str(py_file.relative_to(self.project_root)),
                                                'factory_line': line_num,
                                                'violation_line': check_line_num + 1,
                                                'factory_method': pattern,
                                                'forbidden_class': forbidden_class,
                                                'code': check_line
                                            }
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if factory_violations:
            error_msg = [FACTORY VIOLATION: Factories creating forbidden execution engines found:]
            for violation in factory_violations:
                error_msg.append(f"  - {violation['file']}:{violation['factory_line']} method {violation['factory_method']})"
                error_msg.append(f    Line {violation['violation_line']}: creates {violation['forbidden_class']}")"
                error_msg.append(f    Code: {violation['code']})
            error_msg.append(f\nIssue #1146: All factories must create only UserExecutionEngine instances)"
            error_msg.append(f\nIssue #1146: All factories must create only UserExecutionEngine instances)""

            
            pytest.fail("\n.join(error_msg))"


if __name__ == '__main__':
    unittest.main()
))))))))))))))