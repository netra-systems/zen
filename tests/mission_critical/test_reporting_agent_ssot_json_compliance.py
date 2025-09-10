"""
MISSION CRITICAL: ReportingSubAgent SSOT JSON Compliance Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: SSOT compliance for Golden Path reliability
- Value Impact: Consistent JSON handling across all agent operations
- Strategic Impact: Eliminates JSON parsing inconsistencies affecting user experience

These tests MUST FAIL before remediation and PASS after remediation.
They detect SSOT violations in ReportingSubAgent JSON handling.

EXPECTED BEHAVIOR:
- Tests FAIL NOW (proving violation exists)  
- Tests PASS after migrating to unified_json_handler SSOT
"""

import ast
import inspect
import unittest
from pathlib import Path
from typing import List, Dict, Any


class TestReportingAgentSSOTJSONCompliance(unittest.TestCase):
    """Mission critical tests detecting SSOT violations in ReportingSubAgent JSON handling."""
    
    def setUp(self):
        # Use absolute paths from the test framework directory structure
        self.reporting_agent_path = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "agents" / "reporting_sub_agent.py"
        self.unified_json_handler_path = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "core" / "serialization" / "unified_json_handler.py"
        
        # Ensure files exist for testing
        self.assertTrue(self.reporting_agent_path.exists(), f"ReportingSubAgent not found at {self.reporting_agent_path}")
        self.assertTrue(self.unified_json_handler_path.exists(), f"Unified JSON handler not found at {self.unified_json_handler_path}")
        
    def test_reporting_agent_no_direct_json_imports(self):
        """CRITICAL: ReportingSubAgent MUST NOT import json module directly.
        
        EXPECTED: FAIL NOW - Direct json import found at line 708
        EXPECTED: PASS AFTER - Only SSOT imports used
        """
        with open(self.reporting_agent_path, 'r') as f:
            content = f.read()
        
        # Parse the AST to find import statements
        tree = ast.parse(content)
        direct_json_imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'json':
                        direct_json_imports.append(f"Line {node.lineno}: import json")
            elif isinstance(node, ast.ImportFrom) and node.module == 'json':
                direct_json_imports.append(f"Line {node.lineno}: from json import ...")
        
        # THIS TEST MUST FAIL NOW - Direct json import exists
        self.assertEqual([], direct_json_imports, 
                        f"SSOT VIOLATION: ReportingSubAgent has direct JSON imports: {direct_json_imports}. "
                        f"MUST use unified_json_handler.UnifiedJSONSerializer instead.")
    
    def test_reporting_agent_no_direct_json_calls(self):
        """CRITICAL: ReportingSubAgent MUST NOT call json.loads() or json.dumps() directly.
        
        EXPECTED: FAIL NOW - Direct json calls found at lines 709, 738
        EXPECTED: PASS AFTER - Only SSOT serializer calls used
        """
        with open(self.reporting_agent_path, 'r') as f:
            content = f.read()
        
        # Parse AST to find json.loads() and json.dumps() calls
        tree = ast.parse(content)
        direct_json_calls = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for json.loads() calls
                if (isinstance(node.func, ast.Attribute) and 
                    isinstance(node.func.value, ast.Name) and 
                    node.func.value.id == 'json' and 
                    node.func.attr in ['loads', 'dumps']):
                    direct_json_calls.append(f"Line {node.lineno}: json.{node.func.attr}()")
        
        # THIS TEST MUST FAIL NOW - Direct json calls exist
        self.assertEqual([], direct_json_calls,
                        f"SSOT VIOLATION: ReportingSubAgent has direct JSON calls: {direct_json_calls}. "
                        f"MUST use UnifiedJSONSerializer.safe_loads()/safe_dumps() instead.")
    
    def test_reporting_agent_imports_ssot_json_handler(self):
        """CRITICAL: ReportingSubAgent MUST import from unified_json_handler for all JSON operations.
        
        EXPECTED: PASS NOW - Already imports LLMResponseParser and JSONErrorFixer  
        EXPECTED: PASS AFTER - Should also import UnifiedJSONSerializer
        """
        with open(self.reporting_agent_path, 'r') as f:
            content = f.read()
        
        # Check for SSOT imports
        required_ssot_imports = [
            'LLMResponseParser',
            'JSONErrorFixer'
        ]
        
        missing_imports = []
        for import_name in required_ssot_imports:
            if import_name not in content:
                missing_imports.append(import_name)
        
        self.assertEqual([], missing_imports,
                        f"ReportingSubAgent missing SSOT imports: {missing_imports}")
        
        # Verify the import is from the correct SSOT module
        self.assertIn('from netra_backend.app.core.serialization.unified_json_handler import', content,
                     "ReportingSubAgent must import from SSOT unified_json_handler module")
    
    def test_reporting_agent_cache_methods_use_ssot_json(self):
        """CRITICAL: Cache methods MUST use SSOT JSON serialization.
        
        EXPECTED: FAIL NOW - Cache methods use direct json.loads/dumps
        EXPECTED: PASS AFTER - Cache methods use UnifiedJSONSerializer
        """
        # Import the class to inspect its methods
        import sys
        sys.path.append(str(self.reporting_agent_path.parent.parent.parent))
        
        try:
            from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
            
            # Get source code of cache methods
            get_cached_source = inspect.getsource(ReportingSubAgent._get_cached_report)
            cache_result_source = inspect.getsource(ReportingSubAgent._cache_report_result)
            
            # Check for SSOT violations in caching methods
            ssot_violations = []
            
            if 'json.loads(' in get_cached_source:
                ssot_violations.append("_get_cached_result uses json.loads() instead of SSOT UnifiedJSONSerializer.safe_loads()")
            
            if 'json.dumps(' in cache_result_source:
                ssot_violations.append("_cache_result uses json.dumps() instead of SSOT UnifiedJSONSerializer.safe_dumps()")
            
            # THIS TEST MUST FAIL NOW - Direct json usage in cache methods
            self.assertEqual([], ssot_violations,
                            f"SSOT VIOLATIONS in cache methods: {ssot_violations}")
                            
        except ImportError as e:
            self.fail(f"Could not import ReportingSubAgent for inspection: {e}")
    
    def test_unified_json_handler_has_required_serializer_methods(self):
        """Verify SSOT unified_json_handler provides the required serialization methods."""
        with open(self.unified_json_handler_path, 'r') as f:
            content = f.read()
        
        # Check for required SSOT serializer methods
        required_methods = [
            'safe_loads',
            'safe_dumps',
            'class UnifiedJSONSerializer'
        ]
        
        missing_methods = []
        for method in required_methods:
            if method not in content:
                missing_methods.append(method)
        
        self.assertEqual([], missing_methods,
                        f"SSOT unified_json_handler missing required methods: {missing_methods}")
    
    def test_reporting_agent_no_duplicate_json_error_handling(self):
        """CRITICAL: ReportingSubAgent MUST NOT duplicate JSON error handling logic.
        
        EXPECTED: PASS NOW - Uses SSOT JSONErrorFixer for LLM responses
        EXPECTED: PASS AFTER - All JSON error handling through SSOT
        """
        with open(self.reporting_agent_path, 'r') as f:
            content = f.read()
        
        # Look for custom JSON error handling patterns that duplicate SSOT
        duplicate_patterns = [
            'except json.JSONDecodeError',
            'JSONDecodeError',
            'json.decoder.JSONDecodeError',
            'try.*json.loads.*except',
            'try.*json.dumps.*except'
        ]
        
        violations = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in duplicate_patterns:
                if pattern in line and 'JSONErrorFixer' not in line:
                    violations.append(f"Line {i}: {line.strip()}")
        
        # Should have no custom JSON error handling outside SSOT
        self.assertEqual([], violations,
                        f"Duplicate JSON error handling found (should use SSOT JSONErrorFixer): {violations}")


if __name__ == '__main__':
    unittest.main()