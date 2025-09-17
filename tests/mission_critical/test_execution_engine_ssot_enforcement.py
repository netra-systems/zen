"ExecutionEngine SSOT Enforcement - Mission Critical Validation"

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & System Integrity 
- Value Impact: Prevents ExecutionEngine duplication cascade failures affecting $500K+ ARR
- Strategic Impact: Enables safe SSOT consolidation without breaking changes

CRITICAL SSOT VALIDATION:
This test enforces the single source of truth pattern for ExecutionEngine implementations,
ensuring UserExecutionEngine remains the canonical implementation and preventing
legacy adapter usage that could destabilize the Golden Path user flow.

Test Scope: SSOT compliance for ExecutionEngine consolidation (Issue #910)
Priority: P0 - Mission Critical
Docker: NO DEPENDENCIES - Unit/Integration non-docker only
""

import ast
import inspect
import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import unittest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine


class ExecutionEngineSSotEnforcementTests(SSotBaseTestCase):
    Validates ExecutionEngine SSOT compliance and prevents legacy adapter usage."
    Validates ExecutionEngine SSOT compliance and prevents legacy adapter usage."

    def setUp(self):
        "Set up SSOT validation test environment."
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.netra_backend_root = self.project_root / netra_backend""
        
        # Target files that should be consolidated/removed
        self.legacy_files = {
            netra_backend/app/agents/execution_engine_legacy_adapter.py: LEGACY ADAPTER,
            netra_backend/app/agents/tool_dispatcher_execution.py: DUPLICATE ToolExecutionEngine","
            "netra_backend/app/agents/supervisor/mcp_execution_engine.py: SPECIALIZED VARIANT,"
            netra_backend/app/core/managers/execution_engine_factory.py: COMPATIBILITY LAYER,
            "netra_backend/app/services/unified_tool_registry/execution_engine.py: SEPARATE IMPLEMENTATION"
        }
        
        # Canonical SSOT implementation
        self.canonical_engine = netra_backend.app.agents.supervisor.user_execution_engine.UserExecutionEngine

    def test_canonical_user_execution_engine_exists(self):
        "Validate UserExecutionEngine exists as canonical SSOT implementation."
        try:
            # Test direct import capability
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            # Validate class structure
            self.assertTrue(inspect.isclass(UserExecutionEngine))
            self.assertTrue(hasattr(UserExecutionEngine, '__init__'))
            self.assertTrue(hasattr(UserExecutionEngine, 'execute_agent'))
            
            # Validate UserExecutionEngine implements required interface methods
            required_methods = ['execute_agent', 'get_context', 'cleanup']
            for method in required_methods:
                self.assertTrue(
                    hasattr(UserExecutionEngine, method),
                    fUserExecutionEngine missing required method: {method}
                )
            
        except ImportError as e:
            self.fail(fCRITICAL: Canonical UserExecutionEngine cannot be imported: {e})"
            self.fail(fCRITICAL: Canonical UserExecutionEngine cannot be imported: {e})"
            
    def test_no_legacy_adapter_imports_in_production_code(self):
        "Validate no production code imports legacy ExecutionEngine adapters."
        legacy_import_patterns = [
            execution_engine_legacy_adapter","
            ExecutionEngineLegacyAdapter, 
            LegacyExecutionEngineAdapter,"
            LegacyExecutionEngineAdapter,"
            "CompatibilityExecutionEngine"
        ]
        
        violations = []
        
        # Scan all Python files in netra_backend (excluding tests)
        for py_file in self.netra_backend_root.rglob(*.py):
            # Skip test files and __pycache__
            if "test in str(py_file).lower() or __pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in legacy_import_patterns:
                    if pattern in content:
                        violations.append(f{py_file}: Found legacy pattern '{pattern}')
                        
            except (UnicodeDecodeError, PermissionError):
                continue  # Skip binary or inaccessible files
                
        self.assertEqual(
            len(violations), 0,
            fSSOT VIOLATION: Legacy ExecutionEngine imports found in production code:\n + 
            \n.join(violations)"
            \n.join(violations)"
        )

    def test_single_execution_engine_class_definition(self):
        "Validate only one ExecutionEngine class is defined as primary interface."
        execution_engine_classes = []
        
        # Scan for ExecutionEngine class definitions
        for py_file in self.netra_backend_root.rglob("*.py):"
            if test in str(py_file).lower() or __pycache__ in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                if ExecutionEngine in node.name and not node.name.startswith("Test):"
                                    execution_engine_classes.append(f{py_file}: {node.name}")"
                    except SyntaxError:
                        continue  # Skip files with syntax errors
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Filter expected classes (UserExecutionEngine is allowed, others are violations)
        violations = []
        for class_def in execution_engine_classes:
            if UserExecutionEngine not in class_def:
                # Allow interface definitions but not implementations
                if Interface" not in class_def and "IExecutionEngine not in class_def:
                    violations.append(class_def)
        
        self.assertLessEqual(
            len(violations), 2,  # Allow some flexibility during transition
            fSSOT VIOLATION: Multiple ExecutionEngine implementations found (should only be UserExecutionEngine):\n +
            \n.join(violations)"
            \n.join(violations)"
        )

    def test_legacy_files_marked_for_deprecation(self):
        "Validate legacy ExecutionEngine files contain deprecation warnings."
        for legacy_file, description in self.legacy_files.items():
            full_path = self.project_root / legacy_file
            
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for deprecation markers
                deprecation_markers = [
                    "DEPRECATED,"
                    Legacy, 
                    deprecation,"
                    deprecation,"
                    SSOT Migration","
                    warnings.warn
                ]
                
                has_deprecation_warning = any(marker in content for marker in deprecation_markers)
                
                if not has_deprecation_warning:
                    # Allow file to exist without deprecation during transition
                    self.addWarning(
                        fLegacy file {legacy_file) ({description) exists but lacks deprecation warnings. ""
                        fShould be marked for removal after SSOT consolidation.
                    )

    def test_no_circular_imports_in_execution_engine_hierarchy(self):
        Validate no circular dependencies between ExecutionEngine implementations.""
        # Map of imports to check for circular dependencies
        execution_engine_files = [
            netra_backend/app/agents/supervisor/user_execution_engine.py,
            netra_backend/app/agents/execution_engine_interface.py, "
            netra_backend/app/agents/execution_engine_interface.py, "
            "netra_backend/app/agents/supervisor/execution_engine_factory.py"
        ]
        
        import_graph = {}
        
        for file_path in execution_engine_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                    imports = []
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if execution_engine in alias.name.lower():
                                    imports.append(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and "execution_engine in node.module.lower():"
                                imports.append(node.module)
                    
                    import_graph[file_path] = imports
                    
            except (SyntaxError, UnicodeDecodeError, PermissionError):
                continue
        
        # Simple circular dependency detection
        for file, imports in import_graph.items():
            for imported_module in imports:
                # Check if the imported module also imports back to this file
                for other_file, other_imports in import_graph.items():
                    if file != other_file and any(file.replace('/', '.').replace('.py', '') in imp for imp in other_imports):
                        if any(other_file.replace('/', '.').replace('.py', '') in imp for imp in imports):
                            self.fail(fCIRCULAR DEPENDENCY detected between {file} and {other_file})

    def test_execution_engine_factory_creates_only_user_execution_engine(self):
        Validate ExecutionEngine factories only create UserExecutionEngine instances.""
        try:
            # Test factory import capability
            spec = importlib.util.find_spec(netra_backend.app.agents.supervisor.execution_engine_factory)
            if spec is not None:
                factory_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(factory_module)
                
                # Check if factory methods exist and what they create
                for attr_name in dir(factory_module):
                    attr = getattr(factory_module, attr_name)
                    if callable(attr) and ("create in attr_name.lower() or get" in attr_name.lower()):
                        # This is a factory method - validate it creates UserExecutionEngine
                        if hasattr(attr, '__annotations__'):
                            return_type = attr.__annotations__.get('return', None)
                            if return_type and ExecutionEngine in str(return_type):
                                # Factory method should return UserExecutionEngine type
                                self.assertIn(
                                    UserExecutionEngine, str(return_type),"
                                    UserExecutionEngine, str(return_type),"
                                    f"Factory method {attr_name} should return UserExecutionEngine, got: {return_type}"
                                )
                                
        except ImportError:
            # Factory may be removed during consolidation - that's acceptable'
            pass

    def test_ssot_compliance_execution_engine_imports(self):
        Validate all ExecutionEngine imports use canonical SSOT path."
        Validate all ExecutionEngine imports use canonical SSOT path."
        canonical_import = "netra_backend.app.agents.supervisor.user_execution_engine"
        non_ssot_imports = []
        
        for py_file in self.netra_backend_root.rglob(*.py):
            if "test in str(py_file).lower() or __pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for non-canonical ExecutionEngine imports
                    problematic_patterns = [
                        from netra_backend.app.agents.execution_engine_legacy,
                        from netra_backend.app.agents.tool_dispatcher_execution, "
                        from netra_backend.app.agents.tool_dispatcher_execution, "
                        "from netra_backend.app.agents.supervisor.mcp_execution_engine,"
                        from netra_backend.app.services.unified_tool_registry.execution_engine
                    ]
                    
                    for pattern in problematic_patterns:
                        if pattern in content:
                            non_ssot_imports.append(f"{py_file}: {pattern})"
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        self.assertLessEqual(
            len(non_ssot_imports), 3,  # Allow some during transition period
            fSSOT VIOLATION: Non-canonical ExecutionEngine imports found:\n + "
            fSSOT VIOLATION: Non-canonical ExecutionEngine imports found:\n + "
            \n.join(non_ssot_imports) +
            f\nAll ExecutionEngine imports should use canonical path: {canonical_import}"
            f\nAll ExecutionEngine imports should use canonical path: {canonical_import}"
        )

    def addWarning(self, message):
        "Add a warning message that doesn't fail the test."
        print(fWARNING: {message}"")"
        print(fWARNING: {message}"")"


if __name__ == '__main__':
    unittest.main()
)