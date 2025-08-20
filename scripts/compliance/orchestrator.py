#!/usr/bin/env python3
"""
Architecture compliance orchestrator.
Coordinates all compliance checking modules and aggregates results.
"""

from collections import defaultdict
from typing import List, Dict

from .core import (
    Violation, ComplianceConfig, ComplianceResults, 
    create_compliance_results
)
from .file_checker import FileChecker, count_total_files
from .function_checker import FunctionChecker
from .type_checker import TypeChecker
from .stub_checker import StubChecker
from .ssot_checker import SSOTChecker
from .test_limits_checker import TestLimitsChecker
from .reporter import ComplianceReporter


class ArchitectureEnforcer:
    """Orchestrates architectural rule enforcement"""
    
    def __init__(self, root_path: str = ".", max_file_lines: int = 500, 
                 max_function_lines: int = 25, violation_limit: int = 10,
                 smart_limits: bool = True, use_emoji: bool = True,
                 target_folders: List[str] = None, ignore_folders: List[str] = None,
                 check_test_limits: bool = True):
        self.config = ComplianceConfig(root_path, max_file_lines, max_function_lines,
                                      target_folders, ignore_folders)
        self.check_test_limits = check_test_limits
        self.file_checker = FileChecker(self.config)
        self.function_checker = FunctionChecker(self.config)
        self.type_checker = TypeChecker(self.config)
        self.stub_checker = StubChecker(self.config)
        self.ssot_checker = SSOTChecker(self.config)
        self.test_limits_checker = TestLimitsChecker(self.config) if check_test_limits else None
        self.reporter = ComplianceReporter(max_file_lines, max_function_lines,
                                          violation_limit, smart_limits, use_emoji)
    
    def run_all_checks(self) -> ComplianceResults:
        """Run all compliance checks and return structured results"""
        all_violations = self._collect_all_violations()
        violations_by_type = self._group_violations_by_type(all_violations)
        total_files = count_total_files(self.config)
        compliance_score = self._calculate_compliance_score(all_violations, total_files)
        category_scores = self._calculate_category_scores(all_violations)
        return create_compliance_results(
            all_violations, total_files, compliance_score, violations_by_type,
            self.config.max_file_lines, self.config.max_function_lines, category_scores
        )
    
    def _collect_all_violations(self) -> List[Violation]:
        """Collect violations from all checkers"""
        violations = []
        violations.extend(self.file_checker.check_file_sizes())
        violations.extend(self.function_checker.check_function_complexity())
        violations.extend(self.type_checker.check_duplicate_types())
        violations.extend(self.stub_checker.check_test_stubs())
        violations.extend(self.ssot_checker.check_ssot_violations())
        if self.test_limits_checker:
            violations.extend(self.test_limits_checker.check_test_limits())
        return violations
    
    def _group_violations_by_type(self, violations: List[Violation]) -> Dict[str, int]:
        """Group violations by type for summary"""
        violations_by_type = defaultdict(int)
        for violation in violations:
            violations_by_type[violation.violation_type] += 1
        return dict(violations_by_type)
    
    def _calculate_compliance_score(self, violations: List[Violation], total_files: int) -> float:
        """Calculate compliance score percentage"""
        if total_files == 0:
            return 100.0
        files_with_violations = len(set(v.file_path for v in violations))
        clean_files = total_files - files_with_violations
        return max(0.0, (clean_files / total_files) * 100)
    
    def _calculate_category_scores(self, violations: List[Violation]) -> Dict[str, Dict]:
        """Calculate compliance scores by category"""
        categories = {
            'real_system': {'violations': [], 'files': set(), 'total_files': 0},
            'test_files': {'violations': [], 'files': set(), 'total_files': 0},
            'other': {'violations': [], 'files': set(), 'total_files': 0}
        }
        
        # Count total files in each category
        file_counts = self._count_files_by_category()
        for cat, count in file_counts.items():
            categories[cat]['total_files'] = count
        
        # Categorize violations
        for v in violations:
            path = v.file_path.replace('\\', '/')
            if self.config.is_test_file(path):
                categories['test_files']['violations'].append(v)
                categories['test_files']['files'].add(path)
            elif any(path.startswith(f + '/') or path.startswith(f) for f in self.config.target_folders):
                categories['real_system']['violations'].append(v)
                categories['real_system']['files'].add(path)
            else:
                categories['other']['violations'].append(v)
                categories['other']['files'].add(path)
        
        return self._build_category_scores(categories)
    
    def _count_files_by_category(self) -> Dict[str, int]:
        """Count total files in each category"""
        import glob
        from pathlib import Path
        counts = {'real_system': 0, 'test_files': 0, 'other': 0}
        patterns = self.config.get_patterns()
        
        for pattern in patterns:
            files = glob.glob(str(self.config.root_path / pattern), recursive=True)
            for filepath in files:
                if self.config.should_skip_file(filepath):
                    continue
                # Get relative path for consistent comparison
                rel_path = str(Path(filepath).relative_to(self.config.root_path)).replace('\\', '/')
                
                if self.config.is_test_file(rel_path):
                    counts['test_files'] += 1
                elif any(rel_path.startswith(f + '/') or rel_path.startswith(f) for f in self.config.target_folders):
                    counts['real_system'] += 1
                else:
                    counts['other'] += 1
        return counts
    
    def _build_category_scores(self, categories: Dict) -> Dict[str, Dict]:
        """Build category score details"""
        scores = {}
        for name, data in categories.items():
            violation_count = len(data['violations'])
            files_with_violations = len(data['files'])
            total_files = data.get('total_files', 0)
            
            # Calculate proper compliance score
            if total_files == 0:
                score = 100.0  # No files to check = 100% compliant
            else:
                clean_files = total_files - files_with_violations
                score = (clean_files / total_files) * 100
            
            scores[name] = {
                'violations': violation_count,
                'files_with_violations': files_with_violations,
                'total_files': total_files,
                'score': score
            }
        return scores
    
    def generate_report(self) -> str:
        """Generate compliance report"""
        results = self.run_all_checks()
        return self.reporter.generate_report(results)
    
    def generate_test_splitting_suggestions(self) -> Dict[str, List[str]]:
        """Generate automated splitting suggestions for test violations"""
        if not self.test_limits_checker:
            return {}
        
        test_violations = []
        all_violations = self._collect_all_violations()
        
        for violation in all_violations:
            if violation.violation_type in ["test_file_size", "test_function_complexity"]:
                test_violations.append(violation)
        
        return self.test_limits_checker.generate_splitting_suggestions(test_violations)