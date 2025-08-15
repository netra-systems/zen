#!/usr/bin/env python3
"""
Architecture Metrics Calculator
Focused module for calculating health metrics and compliance scores
"""

import ast
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class ArchitectureMetrics:
    """Calculates comprehensive architecture health metrics"""
    
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.scan_timestamp = datetime.now()
    
    def calculate_health_metrics(self, violations: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive health metrics"""
        total_files_scanned = self._count_total_files()
        total_functions_scanned = self._count_total_functions()
        violation_counts = self._calculate_violation_counts(violations)
        compliance_scores = self._calculate_compliance_scores(violations, total_files_scanned, total_functions_scanned)
        
        return {
            'scan_timestamp': self.scan_timestamp.isoformat(),
            'total_files_scanned': total_files_scanned,
            'total_functions_scanned': total_functions_scanned,
            'violation_counts': violation_counts,
            'compliance_scores': compliance_scores,
            'severity_breakdown': self._calculate_severity_breakdown(violations),
            'worst_offenders': self._get_worst_offenders(violations),
            'improvement_suggestions': self._generate_improvement_suggestions(violations)
        }
    
    def _calculate_violation_counts(self, violations: Dict[str, Any]) -> Dict[str, int]:
        """Calculate violation counts by type"""
        file_violations = len(violations.get('file_size_violations', []))
        function_violations = len(violations.get('function_complexity_violations', []))
        duplicate_types = len(violations.get('duplicate_types', {}))
        test_stubs = len(violations.get('test_stubs', []))
        missing_types = len(violations.get('missing_type_annotations', []))
        arch_debt = len(violations.get('architectural_debt', []))
        quality_issues = len(violations.get('code_quality_issues', []))
        
        return {
            'file_size_violations': file_violations,
            'function_complexity_violations': function_violations,
            'duplicate_types': duplicate_types,
            'test_stubs': test_stubs,
            'missing_type_annotations': missing_types,
            'architectural_debt': arch_debt,
            'code_quality_issues': quality_issues,
            'total_violations': file_violations + function_violations + duplicate_types + 
                              test_stubs + missing_types + arch_debt + quality_issues
        }
    
    def _calculate_compliance_scores(self, violations: Dict[str, Any], 
                                   total_files: int, total_functions: int) -> Dict[str, float]:
        """Calculate compliance scores"""
        file_violations = len(violations.get('file_size_violations', []))
        function_violations = len(violations.get('function_complexity_violations', []))
        total_violations = self._get_total_violations(violations)
        
        file_compliance = self._calculate_file_compliance(file_violations, total_files)
        function_compliance = self._calculate_function_compliance(function_violations, total_functions)
        overall_compliance = self._calculate_overall_compliance(total_violations, total_files)
        
        return {
            'file_compliance': round(file_compliance, 2),
            'function_compliance': round(function_compliance, 2),
            'overall_compliance': round(overall_compliance, 2)
        }
    
    def _calculate_file_compliance(self, file_violations: int, total_files: int) -> float:
        """Calculate file compliance score"""
        return max(0, 100 - (file_violations / max(total_files, 1)) * 100)
    
    def _calculate_function_compliance(self, function_violations: int, total_functions: int) -> float:
        """Calculate function compliance score"""
        return max(0, 100 - (function_violations / max(total_functions, 1)) * 100)
    
    def _calculate_overall_compliance(self, total_violations: int, total_files: int) -> float:
        """Calculate overall compliance score"""
        return max(0, 100 - (total_violations / max(total_files, 1)) * 10)
    
    def _get_total_violations(self, violations: Dict[str, Any]) -> int:
        """Get total violation count"""
        return (len(violations.get('file_size_violations', [])) +
                len(violations.get('function_complexity_violations', [])) +
                len(violations.get('duplicate_types', {})) +
                len(violations.get('test_stubs', [])) +
                len(violations.get('missing_type_annotations', [])) +
                len(violations.get('architectural_debt', [])) +
                len(violations.get('code_quality_issues', [])))
    
    def _calculate_severity_breakdown(self, violations: Dict[str, Any]) -> Dict[str, int]:
        """Calculate breakdown by severity"""
        breakdown = {self.SEVERITY_CRITICAL: 0, self.SEVERITY_HIGH: 0, self.SEVERITY_MEDIUM: 0}
        
        for violation_type, violations_list in violations.items():
            breakdown = self._process_violations_for_severity(violations_list, breakdown)
        
        return breakdown
    
    def _process_violations_for_severity(self, violations_list: Any, breakdown: Dict[str, int]) -> Dict[str, int]:
        """Process violations list for severity breakdown"""
        if isinstance(violations_list, list):
            breakdown = self._process_list_violations(violations_list, breakdown)
        elif isinstance(violations_list, dict):
            breakdown = self._process_dict_violations(violations_list, breakdown)
        return breakdown
    
    def _process_list_violations(self, violations_list: List, breakdown: Dict[str, int]) -> Dict[str, int]:
        """Process list-type violations for severity"""
        for violation in violations_list:
            severity = violation.get('severity', self.SEVERITY_MEDIUM)
            breakdown[severity] += 1
        return breakdown
    
    def _process_dict_violations(self, violations_dict: Dict, breakdown: Dict[str, int]) -> Dict[str, int]:
        """Process dict-type violations for severity"""
        for item in violations_dict.values():
            if isinstance(item, dict) and 'severity' in item:
                breakdown[item['severity']] += 1
        return breakdown
    
    def _get_worst_offenders(self, violations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get worst offending files"""
        offenders = []
        
        offenders.extend(self._get_file_offenders(violations))
        offenders.extend(self._get_function_offenders(violations))
        
        return sorted(offenders, key=lambda x: x['severity'], reverse=True)[:10]
    
    def _get_file_offenders(self, violations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get file size offenders"""
        offenders = []
        for violation in violations.get('file_size_violations', [])[:5]:
            offenders.append({
                'file': violation['file'],
                'type': 'File Size',
                'value': f"{violation['lines']} lines",
                'severity': violation['severity']
            })
        return offenders
    
    def _get_function_offenders(self, violations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get function complexity offenders"""
        offenders = []
        for violation in violations.get('function_complexity_violations', [])[:5]:
            offenders.append({
                'file': violation['file'],
                'type': 'Function Complexity',
                'value': f"{violation['function']}() - {violation['lines']} lines",
                'severity': violation['severity']
            })
        return offenders
    
    def _generate_improvement_suggestions(self, violations: Dict[str, Any]) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        suggestions.extend(self._get_file_suggestions(violations))
        suggestions.extend(self._get_function_suggestions(violations))
        suggestions.extend(self._get_type_suggestions(violations))
        suggestions.extend(self._get_general_suggestions(violations))
        
        return suggestions
    
    def _get_file_suggestions(self, violations: Dict[str, Any]) -> List[str]:
        """Get file-related suggestions"""
        suggestions = []
        file_violations = len(violations.get('file_size_violations', []))
        if file_violations > 0:
            suggestions.append(f"Split {file_violations} oversized files into focused modules")
        return suggestions
    
    def _get_function_suggestions(self, violations: Dict[str, Any]) -> List[str]:
        """Get function-related suggestions"""
        suggestions = []
        func_violations = len(violations.get('function_complexity_violations', []))
        if func_violations > 0:
            suggestions.append(f"Refactor {func_violations} complex functions into smaller units")
        return suggestions
    
    def _get_type_suggestions(self, violations: Dict[str, Any]) -> List[str]:
        """Get type-related suggestions"""
        suggestions = []
        
        if violations.get('duplicate_types'):
            suggestions.append("Consolidate duplicate type definitions into single sources")
        
        if violations.get('missing_type_annotations'):
            suggestions.append("Add missing type annotations for better type safety")
        
        return suggestions
    
    def _get_general_suggestions(self, violations: Dict[str, Any]) -> List[str]:
        """Get general improvement suggestions"""
        suggestions = []
        
        if violations.get('test_stubs'):
            suggestions.append("Replace test stubs with production implementations")
        
        if violations.get('architectural_debt'):
            suggestions.append("Address TODOs and architectural debt items")
        
        suggestions.append("Run compliance checks in CI/CD pipeline")
        suggestions.append("Set up automated monitoring alerts")
        
        return suggestions
    
    def _count_total_files(self) -> int:
        """Count total files scanned"""
        count = 0
        patterns = ['app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts', 'scripts/**/*.py']
        
        for pattern in patterns:
            count += self._count_pattern_files(pattern)
        
        return count
    
    def _count_pattern_files(self, pattern: str) -> int:
        """Count files matching pattern"""
        count = 0
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if not self._should_skip_file(filepath):
                count += 1
        return count
    
    def _count_total_functions(self) -> int:
        """Count total functions scanned"""
        count = 0
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip_file(filepath):
                continue
            count += self._count_file_functions(filepath)
        return count
    
    def _count_file_functions(self, filepath: str) -> int:
        """Count functions in single file"""
        count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        count += 1
        except Exception:
            pass
        return count
    
    def _should_skip_file(self, filepath: str) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '__pycache__', 'node_modules', '.git', 'migrations',
            'test_reports', 'docs', '.pytest_cache', 'htmlcov',
            'coverage', 'venv', '.venv', 'dist', 'build'
        ]
        return any(pattern in filepath for pattern in skip_patterns)