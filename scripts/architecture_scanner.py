#!/usr/bin/env python3
"""
Architecture Violation Scanner
Focused module for detecting all types of architecture violations
"""

import ast
import glob
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

from architecture_scanner_helpers import ScannerHelpers
from architecture_scanner_quality import QualityScanner


class ArchitectureScanner:
    """Scans codebase for architecture violations"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.quality_scanner = QualityScanner(root_path)
    
    def scan_all_violations(self) -> Dict[str, Any]:
        """Comprehensive scan of all architecture violations"""
        return {
            'file_size_violations': self.scan_file_sizes(),
            'function_complexity_violations': self.scan_function_complexity(),
            'duplicate_types': self.scan_duplicate_types(),
            'test_stubs': self.quality_scanner.scan_test_stubs(),
            'missing_type_annotations': self.scan_missing_types(),
            'architectural_debt': self.quality_scanner.scan_architectural_debt(),
            'code_quality_issues': self.quality_scanner.scan_code_quality()
        }
    
    def scan_file_sizes(self) -> List[Dict[str, Any]]:
        """Enhanced file size scanning with severity levels"""
        violations = []
        patterns = ScannerHelpers.get_scan_patterns()
        
        for pattern in patterns:
            violations.extend(self._scan_pattern_for_size(pattern))
                    
        return sorted(violations, key=lambda x: x['lines'], reverse=True)
    
    def _scan_pattern_for_size(self, pattern: str) -> List[Dict[str, Any]]:
        """Scan single pattern for file size violations"""
        violations = []
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if ScannerHelpers.should_skip_file(filepath):
                continue
            violation = self._check_file_size(filepath)
            if violation:
                violations.append(violation)
        return violations
    
    def _check_file_size(self, filepath: str) -> Dict[str, Any] | None:
        """Check if single file exceeds size limit"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                line_count = len(f.readlines())
            
            if line_count > ScannerHelpers.MAX_FILE_LINES:
                return ScannerHelpers.create_file_violation(filepath, line_count)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
        return None
    
    def scan_function_complexity(self) -> List[Dict[str, Any]]:
        """Enhanced function complexity scanning"""
        violations = []
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if ScannerHelpers.should_skip_file(filepath):
                continue
            violations.extend(self._scan_file_functions(filepath))
                
        return sorted(violations, key=lambda x: x['lines'], reverse=True)
    
    def _scan_file_functions(self, filepath: str) -> List[Dict[str, Any]]:
        """Scan functions in a single file"""
        violations = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                violation = self._check_function_complexity(filepath, node)
                if violation:
                    violations.append(violation)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
        return violations
    
    def _check_function_complexity(self, filepath: str, node: ast.AST) -> Dict[str, Any] | None:
        """Check if function exceeds complexity limit"""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None
        
        lines = ScannerHelpers.count_function_lines(node)
        if lines > ScannerHelpers.MAX_FUNCTION_LINES:
            return ScannerHelpers.create_function_violation(filepath, node, lines)
        return None
    
    def scan_duplicate_types(self) -> Dict[str, Any]:
        """Enhanced duplicate type scanning with impact analysis"""
        type_definitions = defaultdict(list)
        
        self._scan_python_types(type_definitions)
        self._scan_typescript_types(type_definitions)
        
        return self._filter_duplicates(type_definitions)
    
    def _scan_python_types(self, type_definitions: defaultdict) -> None:
        """Scan Python files for type definitions"""
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if ScannerHelpers.should_skip_file(filepath):
                continue
            self._extract_python_types(filepath, type_definitions)
    
    def _extract_python_types(self, filepath: str, type_definitions: defaultdict) -> None:
        """Extract type definitions from Python file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    type_definitions[node.name].append({
                        'file': filepath,
                        'line': node.lineno,
                        'type': 'class'
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    def _scan_typescript_types(self, type_definitions: defaultdict) -> None:
        """Scan TypeScript files for type definitions"""
        patterns = ['frontend/**/*.ts', 'frontend/**/*.tsx']
        for pattern in patterns:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if 'node_modules' in filepath:
                    continue
                self._extract_typescript_types(filepath, type_definitions)
    
    def _extract_typescript_types(self, filepath: str, type_definitions: defaultdict) -> None:
        """Extract type definitions from TypeScript file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
                line_num = content[:match.start()].count('\n') + 1
                type_definitions[match.group(1)].append({
                    'file': filepath,
                    'line': line_num,
                    'type': 'interface/type'
                })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    def _filter_duplicates(self, type_definitions: defaultdict) -> Dict[str, Any]:
        """Filter and process duplicate types"""
        duplicates = {}
        for type_name, definitions in type_definitions.items():
            if len(definitions) > 1:
                duplicates[type_name] = {
                    'count': len(definitions),
                    'definitions': definitions,
                    'severity': ScannerHelpers.get_duplicate_severity(len(definitions)),
                    'recommendation': f"Consolidate {len(definitions)} definitions into single source"
                }
        return duplicates
    
    
    def scan_missing_types(self) -> List[Dict[str, Any]]:
        """Scan for missing type annotations"""
        violations = []
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if ScannerHelpers.should_skip_file(filepath):
                continue
            violations.extend(self._scan_file_for_missing_types(filepath))
                
        return violations
    
    def _scan_file_for_missing_types(self, filepath: str) -> List[Dict[str, Any]]:
        """Scan single file for missing type annotations"""
        violations = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    violations.extend(self._check_function_types(filepath, node))
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
        return violations
    
    def _check_function_types(self, filepath: str, node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Check function for missing type annotations"""
        violations = []
        
        # Check return type
        if node.returns is None and node.name != '__init__':
            violations.append(ScannerHelpers.create_missing_return_type(filepath, node))
        
        # Check parameter types
        for arg in node.args.args:
            if arg.annotation is None and arg.arg != 'self':
                violations.append(ScannerHelpers.create_missing_param_type(filepath, node, arg))
        
        return violations
    
