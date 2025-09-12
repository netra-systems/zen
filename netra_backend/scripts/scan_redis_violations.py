#!/usr/bin/env python3
"""Redis SSOT Violation Scanner - Issue #226

Scans the codebase for Redis import violations and provides
specific guidance on converting to SSOT patterns.

Usage:
    python scripts/scan_redis_violations.py
    python scripts/scan_redis_violations.py --detailed
    python scripts/scan_redis_violations.py --json > violations.json
    
Business Value:
- Accelerates Redis SSOT migration by providing automated detection
- Reduces developer time spent manually searching for violations
- Provides actionable guidance for each violation type
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict


@dataclass
class Violation:
    """Represents a single Redis import violation."""
    file_path: str
    line_number: int
    violation_type: str
    pattern_matched: str
    line_content: str
    suggested_fix: str


class RedisViolationScanner:
    """Scanner for Redis SSOT import violations."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
        # Deprecated import patterns
        self.deprecated_patterns = {
            'auth_service_import': {
                'pattern': r'from\s+auth_service\.auth_core\.redis_manager\s+import',
                'fix': 'from netra_backend.app.redis_manager import redis_manager'
            },
            'cache_manager_import': {
                'pattern': r'from\s+netra_backend\.app\.cache\.redis_cache_manager\s+import',
                'fix': 'from netra_backend.app.redis_manager import redis_manager'
            },
            'test_redis_import': {
                'pattern': r'from\s+test_framework\.redis_test_utils\.test_redis_manager\s+import',
                'fix': 'from netra_backend.app.redis_manager import redis_manager'
            },
            'managers_redis_import': {
                'pattern': r'from\s+.*\.managers\.redis_manager\s+import',
                'fix': 'from netra_backend.app.redis_manager import redis_manager'
            },
            'db_redis_import': {
                'pattern': r'from\s+.*\.db\.redis_manager\s+import',
                'fix': 'from netra_backend.app.redis_manager import redis_manager'
            }
        }
        
        # Direct instantiation patterns
        self.instantiation_patterns = {
            'redis_manager_direct': {
                'pattern': r'RedisManager\(\)',
                'fix': 'Use singleton: from netra_backend.app.redis_manager import redis_manager'
            },
            'redis_manager_with_args': {
                'pattern': r'RedisManager\(\s*[^)]+\)',
                'fix': 'Use singleton: from netra_backend.app.redis_manager import redis_manager'
            },
            'auth_redis_direct': {
                'pattern': r'AuthRedisManager\(\)',
                'fix': 'Use SSOT: from netra_backend.app.redis_manager import redis_manager'
            },
            'cache_redis_direct': {
                'pattern': r'RedisCacheManager\(\)',
                'fix': 'Use SSOT: from netra_backend.app.redis_manager import redis_manager'
            },
            'test_redis_direct': {
                'pattern': r'RedisTestManager\(\)',
                'fix': 'Use SSOT: from netra_backend.app.redis_manager import redis_manager'
            }
        }
        
        # Files to exclude
        self.exclude_patterns = [
            '__pycache__',
            '.pyc',
            'node_modules',
            '.git',
            'venv',
            '.env',
            'migrations/',
            # Exclude the SSOT files themselves
            'netra_backend/app/redis_manager.py',
            # Exclude compatibility layers (they're supposed to have these patterns)
            'auth_service/auth_core/redis_manager.py',
            'netra_backend/app/cache/redis_cache_manager.py',
            'netra_backend/app/managers/redis_manager.py',
            'netra_backend/app/db/redis_manager.py',
        ]

    def scan_all_violations(self) -> List[Violation]:
        """Scan for all Redis import violations."""
        violations = []
        
        # Scan for deprecated imports
        violations.extend(self._scan_for_pattern_violations(
            self.deprecated_patterns, 
            "deprecated_import"
        ))
        
        # Scan for direct instantiations
        violations.extend(self._scan_for_pattern_violations(
            self.instantiation_patterns,
            "direct_instantiation"
        ))
        
        return violations

    def _scan_for_pattern_violations(self, patterns: Dict[str, Dict[str, str]], violation_type: str) -> List[Violation]:
        """Scan for specific pattern violations."""
        violations = []
        
        for python_file in self._get_python_files():
            violations.extend(self._scan_file_for_patterns(
                python_file,
                patterns,
                violation_type
            ))
        
        return violations

    def _get_python_files(self) -> List[Path]:
        """Get all Python files to scan."""
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                pattern in os.path.join(root, d) for pattern in self.exclude_patterns
            )]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    
                    # Skip excluded files
                    if not any(pattern in str(file_path) for pattern in self.exclude_patterns):
                        python_files.append(file_path)
        
        return python_files

    def _scan_file_for_patterns(self, file_path: Path, patterns: Dict[str, Dict[str, str]], violation_type: str) -> List[Violation]:
        """Scan a single file for pattern violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                for pattern_name, pattern_config in patterns.items():
                    pattern = pattern_config['pattern']
                    fix = pattern_config['fix']
                    
                    if re.search(pattern, line_stripped):
                        rel_path = str(file_path.relative_to(self.project_root))
                        violations.append(Violation(
                            file_path=rel_path,
                            line_number=line_num,
                            violation_type=violation_type,
                            pattern_matched=pattern_name,
                            line_content=line_stripped,
                            suggested_fix=fix
                        ))
                        
        except (IOError, UnicodeDecodeError) as e:
            print(f"Warning: Could not scan file {file_path}: {e}", file=sys.stderr)
            
        return violations

    def generate_report(self, violations: List[Violation], detailed: bool = False) -> str:
        """Generate a human-readable violation report."""
        if not violations:
            return " PASS:  No Redis import violations found! SSOT compliance achieved."
        
        # Group violations by type and file
        by_type = {}
        by_file = {}
        
        for violation in violations:
            # Group by type
            if violation.violation_type not in by_type:
                by_type[violation.violation_type] = []
            by_type[violation.violation_type].append(violation)
            
            # Group by file
            if violation.file_path not in by_file:
                by_file[violation.file_path] = []
            by_file[violation.file_path].append(violation)
        
        report_lines = [
            " ALERT:  Redis SSOT Violation Report - Issue #226",
            "=" * 60,
            f"Total Violations: {len(violations)}",
            f"Files Affected: {len(by_file)}",
            ""
        ]
        
        # Summary by type
        report_lines.append(" CHART:  Violations by Type:")
        for violation_type, type_violations in by_type.items():
            report_lines.append(f"  {violation_type}: {len(type_violations)}")
        report_lines.append("")
        
        if detailed:
            # Detailed breakdown by file
            report_lines.append("[U+1F4C1] Detailed Violations by File:")
            for file_path, file_violations in sorted(by_file.items()):
                report_lines.append(f"\n{file_path}")
                for violation in file_violations:
                    report_lines.append(f"   FAIL:  Line {violation.line_number}: {violation.line_content}")
                    report_lines.append(f"     Fix: {violation.suggested_fix}")
        else:
            # Summary by file
            report_lines.append("[U+1F4C1] Files with Violations:")
            for file_path, file_violations in sorted(by_file.items()):
                report_lines.append(f"  {file_path}: {len(file_violations)} violations")
        
        report_lines.extend([
            "",
            "[U+1F527] Quick Fix Guide:",
            "=" * 30,
            "1. Replace deprecated imports with:",
            "   from netra_backend.app.redis_manager import redis_manager",
            "",
            "2. Replace direct instantiation with singleton usage:",
            "   # Instead of: manager = RedisManager()",
            "   # Use: from netra_backend.app.redis_manager import redis_manager",
            "",
            "3. Update usage patterns:",
            "   # Old: manager.get(key)",
            "   # New: redis_manager.get(key)",
            "",
            "See issue #226 for complete migration guidance."
        ])
        
        return "\n".join(report_lines)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Scan for Redis SSOT violations")
    parser.add_argument(
        '--detailed', 
        action='store_true',
        help="Show detailed violation information"
    )
    parser.add_argument(
        '--json',
        action='store_true', 
        help="Output results in JSON format"
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path(__file__).parent.parent,
        help="Project root directory to scan"
    )
    
    args = parser.parse_args()
    
    # Initialize scanner
    scanner = RedisViolationScanner(args.project_root)
    
    # Scan for violations
    violations = scanner.scan_all_violations()
    
    # Output results
    if args.json:
        # JSON output for machine processing
        violation_data = [asdict(v) for v in violations]
        result = {
            'total_violations': len(violations),
            'violations': violation_data,
            'scan_timestamp': str(Path(__file__).stat().st_mtime)
        }
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        report = scanner.generate_report(violations, detailed=args.detailed)
        print(report)
    
    # Exit with error code if violations found (for CI/CD)
    sys.exit(len(violations))


if __name__ == "__main__":
    main()