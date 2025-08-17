#!/usr/bin/env python3
"""
Statistics module for compliance reporting.
Handles violation statistics calculation and display.
"""

from typing import List, Dict
from .core import Violation, ComplianceResults


class StatisticsCalculator:
    """Calculates and displays violation statistics"""
    
    def print_detailed_statistics(self, results: ComplianceResults) -> None:
        """Print detailed violation statistics"""
        print("\nViolation Statistics:")
        print("-" * 40)
        stats = self.calculate_statistics(results)
        self.display_statistics(stats)
    
    def calculate_statistics(self, results: ComplianceResults) -> Dict:
        """Calculate detailed statistics"""
        stats = {'total': len(results.violations)}
        for vtype in ['file_size', 'function_complexity', 'duplicate_types', 'test_stub']:
            violations = self._get_violations_by_type(results, vtype)
            stats[vtype] = self._get_type_statistics(violations, vtype)
        return stats
    
    def _get_violations_by_type(self, results: ComplianceResults, 
                                violation_type: str) -> List[Violation]:
        """Get violations filtered by type"""
        return [v for v in results.violations if v.violation_type == violation_type]
    
    def _get_type_statistics(self, violations: List[Violation], vtype: str) -> Dict:
        """Get statistics for a violation type"""
        if vtype == 'function_complexity':
            return self._get_function_statistics(violations)
        return {'count': len(violations), 'files': len(set(v.file_path for v in violations))}
    
    def _get_function_statistics(self, violations: List[Violation]) -> Dict:
        """Get function-specific statistics"""
        errors = [v for v in violations if v.severity == 'medium']
        warnings = [v for v in violations if v.severity == 'low']
        return {
            'count': len(violations),
            'errors': len(errors),
            'warnings': len(warnings),
            'files': len(set(v.file_path for v in violations))
        }
    
    def display_statistics(self, stats: Dict) -> None:
        """Display formatted statistics"""
        if stats.get('file_size', {}).get('count', 0) > 0:
            print(f"  File Size: {stats['file_size']['count']} files")
        if stats.get('function_complexity', {}).get('count', 0) > 0:
            fc = stats['function_complexity']
            print(f"  Functions: {fc['errors']} errors, {fc['warnings']} warnings")
        if stats.get('duplicate_types', {}).get('count', 0) > 0:
            print(f"  Duplicates: {stats['duplicate_types']['count']} types")
        if stats.get('test_stub', {}).get('count', 0) > 0:
            print(f"  Test Stubs: {stats['test_stub']['count']} instances")
        print(f"\n  Total Violations: {stats['total']}")