#!/usr/bin/env python3
"""
Architecture Scanner Quality Module  
Quality and debt scanning functions
"""

import glob
import re
from pathlib import Path
from typing import Dict, List, Any

from architecture_scanner_helpers import ScannerHelpers


class QualityScanner:
    """Handles quality and debt scanning"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
    
    def scan_test_stubs(self) -> List[Dict[str, Any]]:
        """Enhanced test stub detection"""
        patterns = ScannerHelpers.get_stub_patterns()
        violations = []
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if '__pycache__' in filepath or 'app/tests' in filepath:
                continue
            violations.extend(self._scan_file_for_stubs(filepath, patterns))
                
        return violations
    
    def _scan_file_for_stubs(self, filepath: str, patterns: List[tuple]) -> List[Dict[str, Any]]:
        """Scan single file for test stubs"""
        violations = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for pattern, description in patterns:
                violation = self._find_stub_pattern(filepath, content, lines, pattern, description)
                if violation:
                    violations.append(violation)
                    break
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
        return violations
    
    def _find_stub_pattern(self, filepath: str, content: str, lines: List[str], 
                          pattern: str, description: str) -> Dict[str, Any] | None:
        """Find stub pattern in file content"""
        for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
            line_num = content[:match.start()].count('\n') + 1
            return {
                'file': filepath,
                'line': line_num,
                'pattern': description,
                'severity': ScannerHelpers.SEVERITY_HIGH,
                'type': 'test_stub',
                'code_snippet': lines[line_num-1].strip() if line_num <= len(lines) else '',
                'recommendation': 'Replace with production implementation'
            }
        return None
    
    def scan_architectural_debt(self) -> List[Dict[str, Any]]:
        """Scan for architectural debt indicators"""
        debt_patterns = ScannerHelpers.get_debt_patterns()
        violations = []
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if ScannerHelpers.should_skip_file(filepath):
                continue
            violations.extend(self._scan_file_for_debt(filepath, debt_patterns))
                
        return violations
    
    def _scan_file_for_debt(self, filepath: str, patterns: List[tuple]) -> List[Dict[str, Any]]:
        """Scan single file for architectural debt"""
        violations = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for pattern, description in patterns:
                violations.extend(self._find_debt_patterns(filepath, content, lines, pattern, description))
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
        return violations
    
    def _find_debt_patterns(self, filepath: str, content: str, lines: List[str], 
                           pattern: str, description: str) -> List[Dict[str, Any]]:
        """Find all debt patterns in file"""
        violations = []
        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count('\n') + 1
            violations.append({
                'file': filepath,
                'line': line_num,
                'pattern': description,
                'severity': ScannerHelpers.SEVERITY_MEDIUM,
                'type': 'architectural_debt',
                'code_snippet': lines[line_num-1].strip() if line_num <= len(lines) else '',
                'recommendation': f'Address {description.lower()}'
            })
        return violations
    
    def scan_code_quality(self) -> List[Dict[str, Any]]:
        """Scan for code quality issues"""
        quality_patterns = ScannerHelpers.get_quality_patterns()
        violations = []
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if ScannerHelpers.should_skip_file(filepath) or 'test' in filepath.lower():
                continue
            violations.extend(self._scan_file_for_quality(filepath, quality_patterns))
                
        return violations
    
    def _scan_file_for_quality(self, filepath: str, patterns: List[tuple]) -> List[Dict[str, Any]]:
        """Scan single file for quality issues"""
        violations = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for pattern, description in patterns:
                violations.extend(self._find_quality_patterns(filepath, content, lines, pattern, description))
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
        return violations
    
    def _find_quality_patterns(self, filepath: str, content: str, lines: List[str], 
                              pattern: str, description: str) -> List[Dict[str, Any]]:
        """Find all quality patterns in file"""
        violations = []
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            violations.append({
                'file': filepath,
                'line': line_num,
                'pattern': description,
                'severity': ScannerHelpers.SEVERITY_MEDIUM,
                'type': 'code_quality',
                'code_snippet': lines[line_num-1].strip() if line_num <= len(lines) else '',
                'recommendation': description
            })
        return violations