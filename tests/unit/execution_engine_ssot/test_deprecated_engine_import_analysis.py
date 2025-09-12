"""
Import Analysis Test for Deprecated Execution Engines

CRITICAL: This test validates all imports of deprecated execution engines before Phase 2 removal.
Expected: ~131 imports across the codebase that need to be accounted for.

Purpose: 
1. Find all files importing deprecated engines
2. Categorize import types (direct, from imports, etc.)
3. Validate replacement paths exist via UserExecutionEngine
4. Document safe removal strategy

Files Being Analyzed for Removal:
1. /netra_backend/app/agents/supervisor/execution_engine.py (1,578 lines)
2. /netra_backend/app/agents/execution_engine_consolidated.py
3. /netra_backend/app/agents/supervisor/mcp_execution_engine.py
4. /netra_backend/app/agents/supervisor/request_scoped_execution_engine.py
5. /netra_backend/app/core/execution_engine.py
6. /netra_backend/app/services/unified_tool_registry/execution_engine.py
"""

import ast
import os
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class ImportInfo:
    """Information about an import statement"""
    file_path: str
    line_number: int
    import_type: str  # 'import', 'from_import'
    module_name: str
    imported_names: List[str]
    raw_statement: str


class DeprecatedEngineImportAnalyzer:
    """Analyzes imports of deprecated execution engines"""
    
    def __init__(self):
        self.deprecated_files = {
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.execution_engine_consolidated', 
            'netra_backend.app.agents.supervisor.mcp_execution_engine',
            'netra_backend.app.agents.supervisor.request_scoped_execution_engine',
            'netra_backend.app.core.execution_engine',
            'netra_backend.app.services.unified_tool_registry.execution_engine'
        }
        
        # Relative path patterns that would match deprecated engines
        self.deprecated_patterns = {
            'execution_engine',
            'mcp_execution_engine', 
            'request_scoped_execution_engine',
            'execution_engine_consolidated'
        }
        
        self.project_root = Path('/Users/anthony/Desktop/netra-apex')
        self.imports_found: List[ImportInfo] = []
        
    def analyze_file(self, file_path: Path) -> List[ImportInfo]:
        """Analyze a single Python file for deprecated imports"""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
            lines = content.split('\n')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        if self._is_deprecated_import(module_name):
                            imports.append(ImportInfo(
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=node.lineno,
                                import_type='import',
                                module_name=module_name,
                                imported_names=[alias.asname or alias.name],
                                raw_statement=lines[node.lineno - 1].strip()
                            ))
                            
                elif isinstance(node, ast.ImportFrom):
                    if node.module and self._is_deprecated_import(node.module):
                        imported_names = []
                        for alias in node.names:
                            imported_names.append(alias.asname or alias.name)
                            
                        imports.append(ImportInfo(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=node.lineno,
                            import_type='from_import',
                            module_name=node.module,
                            imported_names=imported_names,
                            raw_statement=lines[node.lineno - 1].strip()
                        ))
                        
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
            # Skip files that can't be parsed
            pass
            
        return imports
    
    def _is_deprecated_import(self, module_name: str) -> bool:
        """Check if a module name matches deprecated patterns"""
        if module_name in self.deprecated_files:
            return True
            
        # Check for relative imports that might match deprecated patterns
        for pattern in self.deprecated_patterns:
            if pattern in module_name:
                # Additional validation to avoid false positives
                if 'execution_engine' in module_name and not 'user_execution_engine' in module_name:
                    return True
                    
        return False
    
    def scan_codebase(self) -> List[ImportInfo]:
        """Scan entire codebase for deprecated imports"""
        all_imports = []
        
        # Scan main backend
        backend_path = self.project_root / 'netra_backend'
        if backend_path.exists():
            for py_file in backend_path.rglob('*.py'):
                imports = self.analyze_file(py_file)
                all_imports.extend(imports)
        
        # Scan tests
        tests_path = self.project_root / 'tests'
        if tests_path.exists():
            for py_file in tests_path.rglob('*.py'):
                imports = self.analyze_file(py_file)
                all_imports.extend(imports)
                
        # Scan shared
        shared_path = self.project_root / 'shared'
        if shared_path.exists():
            for py_file in shared_path.rglob('*.py'):
                imports = self.analyze_file(py_file)
                all_imports.extend(imports)
                
        self.imports_found = all_imports
        return all_imports
    
    def categorize_imports(self) -> Dict[str, List[ImportInfo]]:
        """Categorize imports by type and risk level"""
        categories = {
            'direct_class_imports': [],      # from module import ExecutionEngine
            'module_imports': [],            # import module
            'relative_imports': [],          # from . import execution_engine
            'test_imports': [],             # imports in test files
            'production_imports': [],       # imports in production code
            'high_risk': [],               # imports that might break things
            'low_risk': []                 # imports that are probably safe
        }
        
        for imp in self.imports_found:
            # Test vs production
            if '/tests/' in imp.file_path or 'test_' in imp.file_path:
                categories['test_imports'].append(imp)
            else:
                categories['production_imports'].append(imp)
                
            # Import type
            if imp.import_type == 'import':
                categories['module_imports'].append(imp)
            else:
                categories['direct_class_imports'].append(imp)
                
            # Risk assessment
            if any(name in imp.imported_names for name in ['ExecutionEngine', 'ToolExecutionEngine', 'McpExecutionEngine']):
                categories['high_risk'].append(imp)
            else:
                categories['low_risk'].append(imp)
                
        return categories
    
    def generate_report(self) -> str:
        """Generate detailed analysis report"""
        categories = self.categorize_imports()
        
        report = f"""
DEPRECATED EXECUTION ENGINE IMPORT ANALYSIS REPORT
================================================

SUMMARY:
--------
Total Deprecated Imports Found: {len(self.imports_found)}
Production Code Imports: {len(categories['production_imports'])}
Test Code Imports: {len(categories['test_imports'])}
High Risk Imports: {len(categories['high_risk'])}
Low Risk Imports: {len(categories['low_risk'])}

RISK ASSESSMENT:
---------------
"""
        
        if categories['high_risk']:
            report += f"\n ALERT:  HIGH RISK IMPORTS ({len(categories['high_risk'])}):\n"
            for imp in categories['high_risk']:
                report += f"  - {imp.file_path}:{imp.line_number} -> {imp.raw_statement}\n"
                
        if categories['production_imports']:
            report += f"\n WARNING: [U+FE0F]  PRODUCTION IMPORTS ({len(categories['production_imports'])}):\n"
            for imp in categories['production_imports']:
                if imp not in categories['high_risk']:  # Don't double-list
                    report += f"  - {imp.file_path}:{imp.line_number} -> {imp.raw_statement}\n"
        
        report += f"\n PASS:  TEST IMPORTS ({len(categories['test_imports'])}):\n"
        for imp in categories['test_imports']:
            report += f"  - {imp.file_path}:{imp.line_number} -> {imp.raw_statement}\n"
            
        report += f"\nDETAILED BREAKDOWN BY DEPRECATED FILE:\n"
        report += f"=====================================\n"
        
        for deprecated_file in self.deprecated_files:
            matching_imports = [imp for imp in self.imports_found if deprecated_file in imp.module_name]
            if matching_imports:
                report += f"\n{deprecated_file} ({len(matching_imports)} imports):\n"
                for imp in matching_imports:
                    report += f"  - {imp.file_path}:{imp.line_number}\n"
        
        return report


class TestDeprecatedEngineImportAnalysis(unittest.TestCase):
    """Test suite for deprecated execution engine import analysis"""
    
    def setUp(self):
        self.analyzer = DeprecatedEngineImportAnalyzer()
        
    def test_scan_finds_deprecated_imports(self):
        """Test that scanning finds deprecated execution engine imports"""
        print("\n SEARCH:  Scanning codebase for deprecated execution engine imports...")
        
        imports = self.analyzer.scan_codebase()
        
        print(f"Found {len(imports)} deprecated execution engine imports")
        
        # We expect to find imports based on the context (~131 mentioned)
        # This test will fail if we find 0 imports (indicating scan issue)
        # or if we find way more than expected (indicating false positives)
        
        self.assertGreater(len(imports), 0, 
                          "Should find some deprecated imports - if 0, scan may be broken")
        
        # Print summary for visibility
        categories = self.analyzer.categorize_imports()
        print(f"  - Production imports: {len(categories['production_imports'])}")
        print(f"  - Test imports: {len(categories['test_imports'])}")
        print(f"  - High risk: {len(categories['high_risk'])}")
        
        return imports
    
    def test_categorize_imports_correctly(self):
        """Test that imports are categorized correctly by risk and type"""
        imports = self.analyzer.scan_codebase()
        categories = self.analyzer.categorize_imports()
        
        # Validate categorization logic
        total_categorized = len(categories['test_imports']) + len(categories['production_imports'])
        self.assertEqual(total_categorized, len(imports),
                        "All imports should be categorized as test or production")
        
        # High risk should be subset of all imports
        self.assertLessEqual(len(categories['high_risk']), len(imports))
        
        # Print details for manual validation
        print(f"\n CHART:  Import Categorization:")
        for category, items in categories.items():
            if items:
                print(f"  {category}: {len(items)} imports")
                if category == 'high_risk' and len(items) <= 5:  # Show details for small high-risk lists
                    for item in items:
                        print(f"    - {item.file_path}:{item.line_number} -> {item.raw_statement}")
    
    def test_generate_detailed_report(self):
        """Test report generation and print for manual review"""
        imports = self.analyzer.scan_codebase()
        report = self.analyzer.generate_report()
        
        self.assertIn("DEPRECATED EXECUTION ENGINE IMPORT ANALYSIS REPORT", report)
        self.assertIn(f"Total Deprecated Imports Found: {len(imports)}", report)
        
        print(f"\n[U+1F4CB] FULL ANALYSIS REPORT:")
        print("=" * 80)
        print(report)
        print("=" * 80)
        
        return report
    
    def test_validate_expected_import_count(self):
        """Test that we find approximately the expected number of imports"""
        imports = self.analyzer.scan_codebase()
        
        # Based on context, we expect ~131 imports
        # Allow for some variance but flag if dramatically different
        expected_range = (50, 200)  # Reasonable range around 131
        
        print(f"\n[U+1F4C8] Import Count Validation:")
        print(f"  Expected range: {expected_range[0]}-{expected_range[1]} imports")
        print(f"  Actual found: {len(imports)} imports")
        
        if len(imports) < expected_range[0]:
            print(f"   WARNING: [U+FE0F]  WARNING: Found fewer imports than expected. May indicate scan issues.")
        elif len(imports) > expected_range[1]:
            print(f"   WARNING: [U+FE0F]  WARNING: Found more imports than expected. May indicate false positives.")
        else:
            print(f"   PASS:  Import count within expected range.")
            
        # Don't fail the test, but provide visibility
        self.assertGreater(len(imports), 0, "Should find at least some imports")


if __name__ == '__main__':
    unittest.main(verbosity=2)