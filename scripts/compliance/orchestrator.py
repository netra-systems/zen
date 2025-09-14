#!/usr/bin/env python3
"""
Architecture compliance orchestrator.
Coordinates all compliance checking modules and aggregates results.
"""

from collections import defaultdict
from typing import Dict, List

from scripts.compliance.core import (
    ComplianceConfig,
    ComplianceResults,
    Violation,
    create_compliance_results,
)
from scripts.compliance.file_checker import FileChecker, count_total_files
from scripts.compliance.function_checker import FunctionChecker
from scripts.compliance.mock_justification_checker import MockJustificationChecker
from scripts.compliance.mro_auditor import MROAuditor
from scripts.compliance.reporter import ComplianceReporter
from scripts.compliance.ssot_checker import SSOTChecker
from scripts.compliance.stub_checker import StubChecker
from scripts.compliance.test_limits_checker import TestLimitsChecker
from scripts.compliance.type_checker import TypeChecker


class ArchitectureEnforcer:
    """Orchestrates architectural rule enforcement"""
    
    def __init__(self, root_path: str = ".", max_file_lines: int = 500,
                 max_function_lines: int = 25, violation_limit: int = 10,
                 smart_limits: bool = True, use_emoji: bool = True,
                 target_folders: List[str] = None, ignore_folders: List[str] = None,
                 check_test_limits: bool = True, relaxed_mode: bool = True):
        self.config = ComplianceConfig(root_path, max_file_lines, max_function_lines,
                                      target_folders, ignore_folders)
        self.check_test_limits = check_test_limits
        self.relaxed_mode = relaxed_mode
        self.file_checker = FileChecker(self.config)
        self.function_checker = FunctionChecker(self.config)
        self.type_checker = TypeChecker(self.config)
        self.stub_checker = StubChecker(self.config)
        self.ssot_checker = SSOTChecker(self.config)
        self.test_limits_checker = TestLimitsChecker(self.config) if check_test_limits else None
        self.mock_justification_checker = MockJustificationChecker(self.config, relaxed_mode)
        self.mro_auditor = MROAuditor(self.config.root_path)
        self.reporter = ComplianceReporter(max_file_lines, max_function_lines,
                                          violation_limit, smart_limits, use_emoji, relaxed_mode)
    
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
        violations.extend(self.mock_justification_checker.check_mock_justifications())
        violations.extend(self._check_mro_complexity())

        # In relaxed mode, prioritize and limit violations
        if self.relaxed_mode:
            violations = self._prioritize_violations(violations)

        return violations

    def _prioritize_violations(self, violations: List[Violation]) -> List[Violation]:
        """Prioritize violations by severity and business impact"""
        # Filter out low-priority violations in relaxed mode
        if not violations:
            return violations

        # Severity priority order
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

        # Sort by severity first, then by actual_value (descending for size violations)
        prioritized = sorted(violations, key=lambda v: (
            severity_order.get(v.severity, 4),
            -(v.actual_value if isinstance(v.actual_value, int) else 0),  # Safe numeric sorting
            v.violation_type
        ))

        # In relaxed mode, focus on the most critical violations
        if len(prioritized) > 20:  # Only return top 20 instead of thousands
            critical_and_high = [v for v in prioritized if v.severity in ['critical', 'high']]
            if len(critical_and_high) >= 10:
                return critical_and_high[:15]  # Focus on most critical
            else:
                # Include some medium priority to reach 20 total
                return prioritized[:20]

        return prioritized
    
    def _check_mro_complexity(self) -> List[Violation]:
        """Check MRO complexity for all Python files in target folders"""
        mro_violations = []
        from pathlib import Path
        
        # Focus on agent modules where inheritance is complex
        agent_paths = [
            self.config.root_path / "netra_backend" / "app" / "agents",
            self.config.root_path / "auth_service" / "app" / "agents"
        ]
        
        for agent_path in agent_paths:
            if agent_path.exists():
                audit_result = self.mro_auditor.audit_module(agent_path)
                mro_violations.extend(audit_result.get("violations", []))
        
        return mro_violations
    
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