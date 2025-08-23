#!/usr/bin/env python3
"""
Relaxed Violation Counter
Groups violations by file to provide a more reasonable violation count.
Instead of counting every mock usage as a separate violation, counts one violation per file.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from scripts.compliance.core import Violation


class RelaxedViolationCounter:
    """Groups violations by file to provide more reasonable counts"""
    
    def __init__(self):
        self.file_violations: Dict[str, Dict[str, List[Violation]]] = defaultdict(lambda: defaultdict(list))
        self.test_file_violations: Dict[str, Dict[str, List[Violation]]] = defaultdict(lambda: defaultdict(list))
    
    def add_violations(self, violations: List[Violation]) -> None:
        """Add violations and group them by file"""
        for violation in violations:
            file_path = violation.file_path
            violation_type = violation.violation_type
            
            # Separate test violations from production code violations
            if self._is_test_file(file_path):
                self.test_file_violations[file_path][violation_type].append(violation)
            else:
                self.file_violations[file_path][violation_type].append(violation)
    
    def get_relaxed_counts(self) -> Dict[str, int]:
        """Get relaxed violation counts (one per file per type)"""
        counts = {
            'production_violations': 0,
            'test_violations': 0,
            'total_violations': 0,
            'production_files_with_violations': 0,
            'test_files_with_violations': 0,
            'total_files_with_violations': 0
        }
        
        # Count production violations (one per file per type)
        for file_path, type_violations in self.file_violations.items():
            file_has_violations = False
            for violation_type, violations_list in type_violations.items():
                if violations_list:
                    counts['production_violations'] += 1  # One violation per type per file
                    file_has_violations = True
            
            if file_has_violations:
                counts['production_files_with_violations'] += 1
        
        # Count test violations (one per file per type)
        for file_path, type_violations in self.test_file_violations.items():
            file_has_violations = False
            for violation_type, violations_list in type_violations.items():
                if violations_list:
                    counts['test_violations'] += 1  # One violation per type per file
                    file_has_violations = True
            
            if file_has_violations:
                counts['test_files_with_violations'] += 1
        
        # Calculate totals
        counts['total_violations'] = counts['production_violations'] + counts['test_violations']
        counts['total_files_with_violations'] = (counts['production_files_with_violations'] + 
                                                 counts['test_files_with_violations'])
        
        return counts
    
    def get_detailed_summary(self) -> Dict[str, Dict[str, int]]:
        """Get detailed summary of violations by type"""
        summary = {
            'production': defaultdict(int),
            'test': defaultdict(int),
            'total': defaultdict(int)
        }
        
        # Summarize production violations
        for file_path, type_violations in self.file_violations.items():
            for violation_type, violations_list in type_violations.items():
                if violations_list:
                    summary['production'][violation_type] += 1
                    summary['total'][violation_type] += 1
        
        # Summarize test violations
        for file_path, type_violations in self.test_file_violations.items():
            for violation_type, violations_list in type_violations.items():
                if violations_list:
                    summary['test'][violation_type] += 1
                    summary['total'][violation_type] += 1
        
        return {
            'production': dict(summary['production']),
            'test': dict(summary['test']),
            'total': dict(summary['total'])
        }
    
    def get_top_violating_files(self, limit: int = 10) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
        """Get top files with most violations (production and test separately)"""
        prod_files = []
        test_files = []
        
        # Count violations per production file
        for file_path, type_violations in self.file_violations.items():
            violation_count = sum(1 for violations in type_violations.values() if violations)
            prod_files.append((file_path, violation_count))
        
        # Count violations per test file
        for file_path, type_violations in self.test_file_violations.items():
            violation_count = sum(1 for violations in type_violations.values() if violations)
            test_files.append((file_path, violation_count))
        
        # Sort and limit
        prod_files.sort(key=lambda x: x[1], reverse=True)
        test_files.sort(key=lambda x: x[1], reverse=True)
        
        return prod_files[:limit], test_files[:limit]
    
    def _is_test_file(self, file_path: str) -> bool:
        """Determine if a file is a test file"""
        path_lower = file_path.lower()
        return any([
            'test_' in path_lower,
            '_test.py' in path_lower,
            '/tests/' in path_lower.replace('\\', '/'),
            '/test/' in path_lower.replace('\\', '/'),
            'test_framework' in path_lower,
            'conftest.py' in path_lower
        ])
    
    def get_relaxed_violations_list(self) -> Tuple[List[Violation], List[Violation]]:
        """Get relaxed list of violations (one representative per file per type)"""
        production_violations = []
        test_violations = []
        
        # Get one representative violation per file per type for production
        for file_path, type_violations in self.file_violations.items():
            for violation_type, violations_list in type_violations.items():
                if violations_list:
                    # Take the first violation as representative
                    representative = violations_list[0]
                    # Update description to indicate multiple
                    if len(violations_list) > 1:
                        representative.description = (
                            f"{representative.description} ({len(violations_list)} occurrences in file)"
                        )
                    production_violations.append(representative)
        
        # Get one representative violation per file per type for tests
        for file_path, type_violations in self.test_file_violations.items():
            for violation_type, violations_list in type_violations.items():
                if violations_list:
                    # Take the first violation as representative
                    representative = violations_list[0]
                    # Update description to indicate multiple
                    if len(violations_list) > 1:
                        representative.description = (
                            f"{representative.description} ({len(violations_list)} occurrences in file)"
                        )
                    test_violations.append(representative)
        
        return production_violations, test_violations