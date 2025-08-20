#!/usr/bin/env python3
"""
File size and naming compliance checker.
Enforces CLAUDE.md file size limits (500 lines max) and clean naming conventions.
"""

import glob
from pathlib import Path
from typing import List

from .core import Violation, ComplianceConfig, ViolationBuilder


class FileChecker:
    """Checks files for size compliance"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
    
    def check_file_sizes(self) -> List[Violation]:
        """Check all files for size violations"""
        violations = []
        patterns = self.config.get_patterns()
        for pattern in patterns:
            violations.extend(self._check_pattern(pattern))
        violations.extend(self.check_file_naming())
        return self._sort_violations(violations)
    
    def check_file_naming(self) -> List[Violation]:
        """Check for files with legacy suffixes"""
        violations = []
        bad_suffixes = ['_enhanced', '_fixed', '_backup', '_old', '_new', '_temp', '_copy']
        patterns = self.config.get_patterns()
        
        for pattern in patterns:
            filepaths = self._get_matching_files(pattern)
            for filepath in filepaths:
                if self.config.should_skip_file(filepath):
                    continue
                
                file_stem = Path(filepath).stem
                for suffix in bad_suffixes:
                    if file_stem.endswith(suffix):
                        rel_path = str(Path(filepath).relative_to(self.config.root_path))
                        violations.append(Violation(
                            file_path=rel_path,
                            violation_type="file_naming",
                            severity="medium",
                            description=f"File has legacy suffix '{suffix}'",
                            fix_suggestion="Remove suffix and ensure single clean implementation"
                        ))
                        break
        
        return violations
    
    def _check_pattern(self, pattern: str) -> List[Violation]:
        """Check files matching pattern for size violations"""
        violations = []
        filepaths = self._get_matching_files(pattern)
        for filepath in filepaths:
            if not self.config.should_skip_file(filepath):
                violations.extend(self._check_single_file(filepath))
        return violations
    
    def _get_matching_files(self, pattern: str) -> List[str]:
        """Get files matching pattern"""
        return glob.glob(str(self.config.root_path / pattern), recursive=True)
    
    def _check_single_file(self, filepath: str) -> List[Violation]:
        """Check single file for size violation"""
        try:
            line_count = self._count_file_lines(filepath)
            return self._create_violation_if_needed(filepath, line_count)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return []
    
    def _count_file_lines(self, filepath: str) -> int:
        """Count lines in file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    
    def _create_violation_if_needed(self, filepath: str, lines: int) -> List[Violation]:
        """Create violation if file exceeds limit"""
        if lines <= self.config.max_file_lines:
            return []
        rel_path = str(Path(filepath).relative_to(self.config.root_path))
        violation = ViolationBuilder.file_size_violation(
            rel_path, lines, self.config.max_file_lines
        )
        return [violation]
    
    def _sort_violations(self, violations: List[Violation]) -> List[Violation]:
        """Sort violations by actual value descending"""
        return sorted(violations, key=lambda x: x.actual_value or 0, reverse=True)


def count_total_files(config: ComplianceConfig) -> int:
    """Count total files that would be checked"""
    total_files = 0
    patterns = config.get_patterns()
    for pattern in patterns:
        total_files += _count_pattern_files(config, pattern)
    return total_files


def _count_pattern_files(config: ComplianceConfig, pattern: str) -> int:
    """Count files matching pattern"""
    count = 0
    filepaths = glob.glob(str(config.root_path / pattern), recursive=True)
    for filepath in filepaths:
        if not config.should_skip_file(filepath):
            count += 1
    return count