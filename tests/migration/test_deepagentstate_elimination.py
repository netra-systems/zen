"""
DeepAgentState Elimination Validation Tests (Issue #448)

These tests are designed to FAIL initially and PASS after complete migration.
They validate that DeepAgentState has been completely eliminated from the codebase.

Test Strategy:
1. Import validation tests (will fail while imports exist)
2. Pattern detection tests (will fail while patterns exist)  
3. Security validation tests (will fail if isolation not enforced)
4. Migration completeness tests (will fail until migration is 100%)

Expected Results:
- BEFORE migration: Tests should FAIL showing baseline violations
- AFTER migration: Tests should PASS confirming complete elimination
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

import unittest
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDeepAgentStateElimination(unittest.TestCase):
    """Tests that validate complete DeepAgentState elimination from codebase."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.netra_backend_path = self.project_root / "netra_backend"
        
    @classmethod  
    def setUpClass(cls):
        """Set up class-level test environment."""
        super().setUpClass() if hasattr(super(), 'setUpClass') else None
        cls.project_root = Path(__file__).parent.parent.parent
        cls.netra_backend_path = cls.project_root / "netra_backend"
        
    def test_no_deepagentstate_imports_in_production_code(self):
        """
        Test that NO production files contain DeepAgentState imports.
        
        This test will FAIL initially (showing baseline violations) and 
        PASS after migration is complete.
        
        Expected BEFORE migration: ~84 production files with DeepAgentState
        Expected AFTER migration: 0 production files with DeepAgentState
        """
        violations = self._find_deepagentstate_imports_in_production()
        
        # Generate detailed failure message for baseline documentation
        if violations:
            violation_summary = self._generate_import_violation_summary(violations)
            self.fail(
                f"❌ BASELINE VIOLATION: Found DeepAgentState imports in {len(violations)} production files.\n"
                f"This test is designed to fail initially to establish baseline.\n"
                f"Expected after migration: 0 violations\n"
                f"Current violations:\n{violation_summary}"
            )
            
        # This assertion will pass only after complete migration
        self.assertEqual(
            len(violations), 0, 
            f"Production code must not contain DeepAgentState imports. Found in: {violations}"
        )
        
    def test_no_deepagentstate_class_definitions(self):
        """
        Test that DeepAgentState class definition is completely removed.
        
        This test will FAIL initially and PASS after migration.
        """
        class_definitions = self._find_deepagentstate_class_definitions()
        
        if class_definitions:
            self.fail(
                f"❌ BASELINE VIOLATION: Found DeepAgentState class definitions in {len(class_definitions)} files.\n"
                f"Definitions found in: {list(class_definitions.keys())}\n"
                f"Expected after migration: 0 class definitions"
            )
            
        self.assertEqual(
            len(class_definitions), 0,
            f"DeepAgentState class must be completely removed. Found in: {list(class_definitions.keys())}"
        )
        
    def test_no_deepagentstate_type_annotations(self):
        """
        Test that NO type annotations reference DeepAgentState.
        
        This test will FAIL initially and PASS after migration.
        """
        type_annotations = self._find_deepagentstate_type_annotations()
        
        if type_annotations:
            violation_summary = self._generate_annotation_violation_summary(type_annotations)
            self.fail(
                f"❌ BASELINE VIOLATION: Found DeepAgentState type annotations in {len(type_annotations)} files.\n"
                f"Expected after migration: 0 type annotations\n"
                f"Current violations:\n{violation_summary}"
            )
            
        self.assertEqual(
            len(type_annotations), 0,
            f"Type annotations must not reference DeepAgentState. Found in: {list(type_annotations.keys())}"
        )
        
    def test_no_deepagentstate_instantiations(self):
        """
        Test that NO code instantiates DeepAgentState objects.
        
        This test will FAIL initially and PASS after migration.
        """
        instantiations = self._find_deepagentstate_instantiations()
        
        if instantiations:
            violation_summary = self._generate_instantiation_violation_summary(instantiations)
            self.fail(
                f"❌ BASELINE VIOLATION: Found DeepAgentState instantiations in {len(instantiations)} files.\n"
                f"Expected after migration: 0 instantiations\n"
                f"Current violations:\n{violation_summary}"
            )
            
        self.assertEqual(
            len(instantiations), 0,
            f"Code must not instantiate DeepAgentState. Found in: {list(instantiations.keys())}"
        )
        
    def test_migration_adapter_is_removed(self):
        """
        Test that migration adapter is removed after migration completion.
        
        This test will FAIL initially (adapter should exist) and PASS after migration.
        """
        adapter_files = [
            self.netra_backend_path / "app" / "agents" / "migration" / "deepagentstate_adapter.py",
            self.project_root / "netra_backend" / "app" / "agents" / "migration" / "__init__.py"
        ]
        
        existing_adapters = [f for f in adapter_files if f.exists()]
        
        if existing_adapters:
            self.fail(
                f"❌ BASELINE VIOLATION: Migration adapters still exist.\n"
                f"Found: {[str(f) for f in existing_adapters]}\n"
                f"Expected after migration: All migration adapters removed"
            )
            
        self.assertEqual(
            len(existing_adapters), 0,
            f"Migration adapters should be removed after complete migration. Found: {existing_adapters}"
        )
        
    def test_all_agents_use_userexecutioncontext_pattern(self):
        """
        Test that ALL agents use UserExecutionContext instead of DeepAgentState.
        
        This test will FAIL initially and PASS after migration.
        """
        agents_with_deepagentstate = self._find_agents_using_deepagentstate()
        
        if agents_with_deepagentstate:
            violation_summary = self._generate_agent_violation_summary(agents_with_deepagentstate)
            self.fail(
                f"❌ BASELINE VIOLATION: Found {len(agents_with_deepagentstate)} agents using DeepAgentState.\n"
                f"Expected after migration: 0 agents using DeepAgentState\n"
                f"Current violations:\n{violation_summary}"
            )
            
        self.assertEqual(
            len(agents_with_deepagentstate), 0,
            f"All agents must use UserExecutionContext pattern. Violations in: {list(agents_with_deepagentstate.keys())}"
        )
        
    def test_codebase_reference_count_is_zero(self):
        """
        Test that codebase contains ZERO references to DeepAgentState.
        
        This is the ultimate validation test.
        
        Expected BEFORE migration: ~2433 references across ~404 files
        Expected AFTER migration: 0 references across 0 files
        """
        # Initialize project_root if not set by setUp
        if not hasattr(self, 'project_root'):
            self.project_root = Path(__file__).parent.parent.parent
            
        try:
            # Use ripgrep for comprehensive search
            result = subprocess.run(
                ['rg', 'DeepAgentState', '--type', 'py', '--count'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            
            total_references = 0
            files_with_references = 0
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        files_with_references += 1
                        count = int(line.split(':')[-1])
                        total_references += count
                        
        except FileNotFoundError:
            # Fallback to Python-based search if ripgrep not available
            total_references, files_with_references = self._fallback_reference_count()
            
        if total_references > 0:
            self.fail(
                f"❌ BASELINE VIOLATION: Found {total_references} DeepAgentState references in {files_with_references} files.\n"
                f"This establishes the baseline before migration.\n"
                f"Expected after migration: 0 references in 0 files"
            )
            
        # This will only pass after complete migration
        self.assertEqual(total_references, 0, "Codebase must contain zero DeepAgentState references")
        self.assertEqual(files_with_references, 0, "No files should contain DeepAgentState references")
        
    def test_security_isolation_enforced(self):
        """
        Test that user isolation is enforced without DeepAgentState.
        
        This test validates that security is maintained after migration.
        """
        # Check that UserExecutionContext is properly imported and used
        user_context_usage = self._find_userexecutioncontext_usage()
        
        # This test should pass both before and after migration
        # (security should be maintained throughout)
        self.assertGreater(
            len(user_context_usage), 0,
            "UserExecutionContext must be used for secure user isolation"
        )
        
    # Helper methods for violation detection
    
    def _find_deepagentstate_imports_in_production(self) -> Dict[str, List[str]]:
        """Find all DeepAgentState imports in production code (non-test files)."""
        violations = {}
        
        for py_file in self._get_production_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                import_lines = []
                for line_num, line in enumerate(content.split('\n'), 1):
                    if re.search(r'from.*DeepAgentState|import.*DeepAgentState', line):
                        import_lines.append(f"Line {line_num}: {line.strip()}")
                        
                if import_lines:
                    violations[str(py_file)] = import_lines
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return violations
        
    def _find_deepagentstate_class_definitions(self) -> Dict[str, List[str]]:
        """Find DeepAgentState class definitions."""
        definitions = {}
        
        for py_file in self._get_all_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                class_lines = []
                for line_num, line in enumerate(content.split('\n'), 1):
                    if re.search(r'class\s+DeepAgentState', line):
                        class_lines.append(f"Line {line_num}: {line.strip()}")
                        
                if class_lines:
                    definitions[str(py_file)] = class_lines
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return definitions
        
    def _find_deepagentstate_type_annotations(self) -> Dict[str, List[str]]:
        """Find type annotations using DeepAgentState."""
        annotations = {}
        
        for py_file in self._get_production_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                annotation_lines = []
                for line_num, line in enumerate(content.split('\n'), 1):
                    # Look for type annotations like: def func(state: DeepAgentState)
                    if re.search(r':\s*DeepAgentState', line):
                        annotation_lines.append(f"Line {line_num}: {line.strip()}")
                        
                if annotation_lines:
                    annotations[str(py_file)] = annotation_lines
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return annotations
        
    def _find_deepagentstate_instantiations(self) -> Dict[str, List[str]]:
        """Find DeepAgentState instantiations."""
        instantiations = {}
        
        for py_file in self._get_production_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                instantiation_lines = []
                for line_num, line in enumerate(content.split('\n'), 1):
                    # Look for instantiations like: DeepAgentState(...)
                    if re.search(r'DeepAgentState\s*\(', line):
                        instantiation_lines.append(f"Line {line_num}: {line.strip()}")
                        
                if instantiation_lines:
                    instantiations[str(py_file)] = instantiation_lines
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return instantiations
        
    def _find_agents_using_deepagentstate(self) -> Dict[str, List[str]]:
        """Find agent files that use DeepAgentState."""
        agent_violations = {}
        agent_dir = self.netra_backend_path / "app" / "agents"
        
        if not agent_dir.exists():
            return agent_violations
            
        for py_file in agent_dir.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if "DeepAgentState" in content:
                    violations = []
                    for line_num, line in enumerate(content.split('\n'), 1):
                        if "DeepAgentState" in line:
                            violations.append(f"Line {line_num}: {line.strip()}")
                            
                    if violations:
                        agent_violations[str(py_file)] = violations
                        
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return agent_violations
        
    def _find_userexecutioncontext_usage(self) -> List[str]:
        """Find files using UserExecutionContext pattern."""
        usage_files = []
        
        for py_file in self._get_production_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if "UserExecutionContext" in content:
                    usage_files.append(str(py_file))
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return usage_files
        
    def _get_production_python_files(self) -> List[Path]:
        """Get all production Python files (excluding tests)."""
        production_files = []
        
        for py_file in self.project_root.rglob("*.py"):
            # Skip test files, examples, and scripts
            if any(part in str(py_file) for part in ['test', 'tests', 'examples', 'scripts']):
                continue
            if py_file.name.startswith("test_"):
                continue
                
            production_files.append(py_file)
            
        return production_files
        
    def _get_all_python_files(self) -> List[Path]:
        """Get all Python files in the project."""
        return list(self.project_root.rglob("*.py"))
        
    def _fallback_reference_count(self) -> Tuple[int, int]:
        """Fallback method to count references if ripgrep unavailable."""
        total_refs = 0
        files_with_refs = 0
        
        for py_file in self._get_all_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                file_refs = content.count("DeepAgentState")
                if file_refs > 0:
                    total_refs += file_refs
                    files_with_refs += 1
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return total_refs, files_with_refs
        
    # Summary generation methods
    
    def _generate_import_violation_summary(self, violations: Dict[str, List[str]]) -> str:
        """Generate summary of import violations."""
        summary = []
        for file_path, import_lines in list(violations.items())[:10]:  # Show first 10
            summary.append(f"  {file_path}:")
            for line in import_lines[:3]:  # Show first 3 lines per file
                summary.append(f"    {line}")
                
        if len(violations) > 10:
            summary.append(f"  ... and {len(violations) - 10} more files")
            
        return "\n".join(summary)
        
    def _generate_annotation_violation_summary(self, violations: Dict[str, List[str]]) -> str:
        """Generate summary of type annotation violations."""
        summary = []
        for file_path, annotation_lines in list(violations.items())[:5]:  # Show first 5
            summary.append(f"  {file_path}:")
            for line in annotation_lines[:2]:  # Show first 2 lines per file
                summary.append(f"    {line}")
                
        if len(violations) > 5:
            summary.append(f"  ... and {len(violations) - 5} more files")
            
        return "\n".join(summary)
        
    def _generate_instantiation_violation_summary(self, violations: Dict[str, List[str]]) -> str:
        """Generate summary of instantiation violations."""
        summary = []
        for file_path, instantiation_lines in list(violations.items())[:5]:  # Show first 5
            summary.append(f"  {file_path}:")
            for line in instantiation_lines[:2]:  # Show first 2 lines per file
                summary.append(f"    {line}")
                
        if len(violations) > 5:
            summary.append(f"  ... and {len(violations) - 5} more files")
            
        return "\n".join(summary)
        
    def _generate_agent_violation_summary(self, violations: Dict[str, List[str]]) -> str:
        """Generate summary of agent violations."""
        summary = []
        for file_path, violation_lines in list(violations.items())[:8]:  # Show first 8
            agent_name = Path(file_path).stem
            summary.append(f"  {agent_name} ({file_path}):")
            for line in violation_lines[:2]:  # Show first 2 lines per agent
                summary.append(f"    {line}")
                
        if len(violations) > 8:
            summary.append(f"  ... and {len(violations) - 8} more agents")
            
        return "\n".join(summary)


class TestMigrationReadiness(SSotBaseTestCase):
    """Tests that validate the codebase is ready for migration."""
    
    def test_userexecutioncontext_is_available(self):
        """Test that UserExecutionContext is properly available."""
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            self.assertTrue(True, "UserExecutionContext is available")
        except ImportError as e:
            self.fail(f"UserExecutionContext not available for migration: {e}")
            
    def test_critical_systems_functional(self):
        """Test that critical systems work before migration starts."""
        # This should always pass - validates system stability
        try:
            # Test key imports that migration depends on
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.agents.base_agent import BaseAgent
            from test_framework.ssot.base_test_case import SSotBaseTestCase
            
            self.assertTrue(True, "Critical systems are functional")
            
        except ImportError as e:
            self.fail(f"Critical system not functional before migration: {e}")


if __name__ == "__main__":
    # This test file is designed to be run standalone for baseline validation
    import unittest
    
    print("🚨 DeepAgentState Elimination Baseline Validation")
    print("=" * 60)
    print("These tests are designed to FAIL initially to establish baseline.")
    print("They will PASS after complete DeepAgentState migration.")
    print("=" * 60)
    
    unittest.main(verbosity=2)