"""
Test 1: SSOT Import Compliance Test for agent_lifecycle.py (Issue #877)

PURPOSE: Validates agent_lifecycle.py uses correct SSOT imports for DeepAgentState
REGRESSION: agent_lifecycle.py still imports deprecated DeepAgentState from agents.state

This test MUST FAIL initially to prove the regression exists.
After fix, it will PASS when agent_lifecycle.py uses SSOT UserExecutionContext.

Design:
- Parse agent_lifecycle.py imports programmatically
- Detect deprecated DeepAgentState imports
- Verify SSOT UserExecutionContext usage
- Provide clear failure/pass criteria
"""
import ast
import inspect
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class AgentLifecycleImportComplianceTests(SSotBaseTestCase):
    """Test suite validating agent_lifecycle.py SSOT import compliance"""

    @classmethod
    def setUpClass(cls):
        """Set up test class with file paths and expected imports"""
        cls.agent_lifecycle_path = Path('netra_backend/app/agents/agent_lifecycle.py')
        cls.full_agent_lifecycle_path = Path(__file__).parent.parent.parent.parent / cls.agent_lifecycle_path
        cls.ssot_expected_imports = {'UserExecutionContext': 'netra_backend.app.services.user_execution_context', 'ExecutionState': 'netra_backend.app.schemas.agent_models'}
        cls.deprecated_imports = {'DeepAgentState': 'netra_backend.app.agents.state'}

    def test_agent_lifecycle_file_exists(self):
        """Validate agent_lifecycle.py exists and is readable"""
        self.assertTrue(self.full_agent_lifecycle_path.exists(), f'agent_lifecycle.py not found at {self.full_agent_lifecycle_path}')
        self.assertTrue(self.full_agent_lifecycle_path.is_file(), f'agent_lifecycle.py is not a file at {self.full_agent_lifecycle_path}')

    def test_agent_lifecycle_deprecated_import_detection(self):
        """
        FAILING TEST: Detects deprecated DeepAgentState import in agent_lifecycle.py

        Expected: FAIL initially (deprecated import exists)
        After Fix: PASS (no deprecated imports)
        """
        imports_analysis = self._parse_agent_lifecycle_imports()
        deprecated_found = []
        for import_info in imports_analysis['from_imports']:
            module = import_info['module']
            names = import_info['names']
            if module == 'netra_backend.app.agents.state' and 'DeepAgentState' in names:
                deprecated_found.append({'module': module, 'name': 'DeepAgentState', 'line': import_info.get('line', 'unknown')})
        self.assertEqual(len(deprecated_found), 0, f'SSOT REGRESSION DETECTED: agent_lifecycle.py imports deprecated DeepAgentState!\n  - Deprecated imports found: {deprecated_found}\n  - File: {self.full_agent_lifecycle_path}\n  - REMEDIATION REQUIRED: Replace with UserExecutionContext from SSOT source\n  - Issue #877: SSOT compliance violation in agent_lifecycle.py')

    def test_agent_lifecycle_method_signatures_compliance(self):
        """
        FAILING TEST: Validates method signatures use correct types

        Expected: FAIL initially (DeepAgentState in signatures)
        After Fix: PASS (UserExecutionContext in signatures)
        """
        method_analysis = self._analyze_method_signatures()
        violations = []
        for method_name, signature_info in method_analysis.items():
            if 'DeepAgentState' in str(signature_info.get('annotations', {})):
                violations.append({'method': method_name, 'signature': signature_info, 'violation': 'Uses deprecated DeepAgentState type annotation'})
        self.assertEqual(len(violations), 0, f'SSOT TYPE ANNOTATION VIOLATIONS in agent_lifecycle.py:\n  - Violations: {violations}\n  - REMEDIATION: Replace DeepAgentState with UserExecutionContext\n  - Issue #877: Method signatures must use SSOT types')

    def test_agent_lifecycle_ssot_import_presence(self):
        """
        FAILING TEST: Validates presence of SSOT imports

        Expected: FAIL initially (SSOT imports missing)
        After Fix: PASS (SSOT imports present)
        """
        imports_analysis = self._parse_agent_lifecycle_imports()
        ssot_imports_found = {}
        for import_info in imports_analysis['from_imports']:
            module = import_info['module']
            names = import_info['names']
            if module == 'netra_backend.app.services.user_execution_context':
                if 'UserExecutionContext' in names:
                    ssot_imports_found['UserExecutionContext'] = module
        self.assertIn('UserExecutionContext', ssot_imports_found, f'SSOT IMPORT MISSING: agent_lifecycle.py should import UserExecutionContext!\n  - Current imports: {list(ssot_imports_found.keys())}\n  - Expected: UserExecutionContext from netra_backend.app.services.user_execution_context\n  - Issue #877: SSOT migration incomplete')

    def test_agent_lifecycle_usage_pattern_compliance(self):
        """
        FAILING TEST: Validates DeepAgentState usage patterns are replaced

        Expected: FAIL initially (DeepAgentState usage found)
        After Fix: PASS (UserExecutionContext usage only)
        """
        source_analysis = self._analyze_source_usage_patterns()
        deepagentstate_usage = []
        for usage in source_analysis['variable_usage']:
            if 'DeepAgentState' in usage['context']:
                deepagentstate_usage.append(usage)
        self.assertEqual(len(deepagentstate_usage), 0, f'SSOT USAGE VIOLATIONS: DeepAgentState used in agent_lifecycle.py!\n  - Usage instances: {deepagentstate_usage}\n  - REMEDIATION: Replace with UserExecutionContext patterns\n  - Issue #877: Usage patterns must follow SSOT compliance')

    def _parse_agent_lifecycle_imports(self) -> Dict[str, Any]:
        """Parse imports from agent_lifecycle.py file"""
        try:
            with open(self.full_agent_lifecycle_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            self.fail(f'Could not read agent_lifecycle.py: {e}')
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            self.fail(f'Syntax error in agent_lifecycle.py: {e}')
        from_imports = []
        import_statements = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = []
                if node.names:
                    for alias in node.names:
                        names.append(alias.name)
                from_imports.append({'module': node.module or '', 'names': names, 'line': node.lineno})
            elif isinstance(node, ast.Import):
                names = []
                if node.names:
                    for alias in node.names:
                        names.append(alias.name)
                import_statements.append({'names': names, 'line': node.lineno})
        return {'from_imports': from_imports, 'import_statements': import_statements}

    def _analyze_method_signatures(self) -> Dict[str, Dict[str, Any]]:
        """Analyze method signatures in agent_lifecycle.py"""
        try:
            with open(self.full_agent_lifecycle_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
        except Exception as e:
            self.fail(f'Could not analyze method signatures: {e}')
        method_analysis = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                annotations = {}
                if node.returns:
                    annotations['return'] = ast.unparse(node.returns)
                for arg in node.args.args:
                    if arg.annotation:
                        annotations[arg.arg] = ast.unparse(arg.annotation)
                method_analysis[node.name] = {'annotations': annotations, 'line': node.lineno}
        return method_analysis

    def _analyze_source_usage_patterns(self) -> Dict[str, Any]:
        """Analyze usage patterns in agent_lifecycle.py source"""
        try:
            with open(self.full_agent_lifecycle_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            self.fail(f'Could not analyze usage patterns: {e}')
        variable_usage = []
        for line_num, line in enumerate(lines, 1):
            if 'DeepAgentState' in line:
                variable_usage.append({'line': line_num, 'context': line.strip(), 'type': 'DeepAgentState reference'})
        return {'variable_usage': variable_usage}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')