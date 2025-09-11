"""Redis Import Pattern Compliance Test

MISSION: Validate all Redis imports follow SSOT pattern to protect $500K+ ARR chat functionality.

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: System Stability & Golden Path Protection
- Value Impact: Prevents Redis connection chaos that breaks chat functionality
- Strategic Impact: Ensures unified Redis management prevents user experience degradation

CRITICAL PROTECTIONS:
- Golden Path chat functionality relies on consistent Redis operations
- Multiple Redis managers create connection pool exhaustion
- Import pattern violations lead to authentication failures
- Session management breaks when Redis patterns are inconsistent

This test validates:
1. All imports use SSOT pattern: `from netra_backend.app.redis_manager import redis_manager`
2. No deprecated auth service patterns: `from auth_service.auth_core.redis_manager import auth_redis_manager`
3. No direct RedisManager instantiation bypassing SSOT
4. Consistent import patterns across all services
"""

import unittest
import os
import ast
import logging
from pathlib import Path
from typing import List, Dict, Set, Tuple
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)

class RedisImportPatternComplianceTest(SSotBaseTestCase):
    """Test Redis import pattern compliance across entire codebase."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_root = Path(__file__).parent.parent.parent
        cls.ssot_import_pattern = "from netra_backend.app.redis_manager import redis_manager"
        cls.deprecated_patterns = [
            "from auth_service.auth_core.redis_manager import auth_redis_manager",
            "from analytics_service.analytics_core.database.redis_manager import RedisManager",
            "RedisManager()",  # Direct instantiation
        ]
        
        # Files critical for Golden Path functionality
        cls.golden_path_critical_files = [
            "netra_backend/app/auth_integration/auth.py",
            "netra_backend/app/websocket_core/manager.py", 
            "netra_backend/app/routes/websocket.py",
            "auth_service/auth_core/core/session_manager.py",
            "netra_backend/app/agents/supervisor/execution_engine.py",
        ]

    def test_ssot_import_pattern_usage(self):
        """Test that SSOT Redis import pattern is used correctly."""
        logger.info("Testing SSOT Redis import pattern usage...")
        
        violations = []
        python_files = self._find_python_files()
        
        for file_path in python_files:
            try:
                content = self._read_file_content(file_path)
                if self._contains_redis_imports(content):
                    import_violations = self._check_ssot_compliance(file_path, content)
                    violations.extend(import_violations)
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
                
        if violations:
            violation_summary = self._format_violation_report(violations)
            self.fail(f"Redis SSOT import pattern violations found:\n{violation_summary}")
            
        logger.info(f"✅ SSOT import pattern compliance verified across {len(python_files)} Python files")

    def test_deprecated_pattern_elimination(self):
        """Test that deprecated Redis import patterns are eliminated."""
        logger.info("Testing deprecated Redis import pattern elimination...")
        
        deprecated_violations = []
        python_files = self._find_python_files()
        
        for file_path in python_files:
            try:
                content = self._read_file_content(file_path)
                violations = self._check_deprecated_patterns(file_path, content)
                deprecated_violations.extend(violations)
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
                
        if deprecated_violations:
            violation_summary = self._format_violation_report(deprecated_violations)
            self.fail(f"Deprecated Redis import patterns found:\n{violation_summary}")
            
        logger.info("✅ No deprecated Redis import patterns found")

    def test_golden_path_critical_files_compliance(self):
        """Test that Golden Path critical files use correct Redis patterns."""
        logger.info("Testing Golden Path critical files Redis compliance...")
        
        critical_violations = []
        
        for critical_file in self.golden_path_critical_files:
            file_path = self.project_root / critical_file
            if file_path.exists():
                try:
                    content = self._read_file_content(file_path)
                    if self._contains_redis_imports(content):
                        violations = self._check_critical_file_compliance(file_path, content)
                        critical_violations.extend(violations)
                except Exception as e:
                    logger.warning(f"Could not analyze critical file {file_path}: {e}")
                    
        if critical_violations:
            violation_summary = self._format_violation_report(critical_violations)
            self.fail(f"CRITICAL: Golden Path files have Redis import violations:\n{violation_summary}")
            
        logger.info("✅ Golden Path critical files Redis compliance verified")

    def test_no_direct_redis_manager_instantiation(self):
        """Test that no code directly instantiates RedisManager bypassing SSOT."""
        logger.info("Testing for direct RedisManager instantiation violations...")
        
        direct_instantiation_violations = []
        python_files = self._find_python_files()
        
        for file_path in python_files:
            # Skip the SSOT redis_manager.py itself
            if "netra_backend/app/redis_manager.py" in str(file_path):
                continue
                
            try:
                content = self._read_file_content(file_path)
                violations = self._check_direct_instantiation(file_path, content)
                direct_instantiation_violations.extend(violations)
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
                
        if direct_instantiation_violations:
            violation_summary = self._format_violation_report(direct_instantiation_violations)
            self.fail(f"Direct RedisManager instantiation violations found:\n{violation_summary}")
            
        logger.info("✅ No direct RedisManager instantiation violations found")

    # Helper methods
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        # Key directories to check
        search_dirs = [
            self.project_root / "netra_backend",
            self.project_root / "auth_service", 
            self.project_root / "analytics_service",
            self.project_root / "tests",
            self.project_root / "test_framework"
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                python_files.extend(search_dir.rglob("*.py"))
                
        return python_files

    def _read_file_content(self, file_path: Path) -> str:
        """Read file content safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

    def _contains_redis_imports(self, content: str) -> bool:
        """Check if file contains Redis-related imports."""
        redis_keywords = ['redis_manager', 'RedisManager', 'from.*redis', 'import.*redis']
        return any(keyword.lower() in content.lower() for keyword in redis_keywords)

    def _check_ssot_compliance(self, file_path: Path, content: str) -> List[Dict]:
        """Check if file uses SSOT Redis import pattern."""
        violations = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Check for Redis imports
            if ('redis_manager' in line or 'RedisManager' in line) and 'import' in line:
                if not self._is_ssot_compliant_import(line):
                    violations.append({
                        'file': str(file_path),
                        'line': i,
                        'content': line,
                        'violation_type': 'Non-SSOT Redis import',
                        'severity': 'HIGH'
                    })
                    
        return violations

    def _is_ssot_compliant_import(self, line: str) -> bool:
        """Check if import line uses SSOT pattern."""
        # Allow SSOT pattern
        if "from netra_backend.app.redis_manager import" in line:
            return True
            
        # Allow test imports
        if "test" in line.lower() and ("mock" in line.lower() or "fake" in line.lower()):
            return True
            
        # Allow comments or disabled imports
        if line.strip().startswith('#'):
            return True
            
        return False

    def _check_deprecated_patterns(self, file_path: Path, content: str) -> List[Dict]:
        """Check for deprecated Redis import patterns."""
        violations = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments
            if line.startswith('#'):
                continue
                
            for deprecated_pattern in self.deprecated_patterns:
                if deprecated_pattern in line:
                    violations.append({
                        'file': str(file_path),
                        'line': i,
                        'content': line,
                        'violation_type': f'Deprecated pattern: {deprecated_pattern}',
                        'severity': 'CRITICAL'
                    })
                    
        return violations

    def _check_critical_file_compliance(self, file_path: Path, content: str) -> List[Dict]:
        """Check critical Golden Path files for Redis compliance."""
        violations = []
        
        # Critical files must use SSOT pattern if they use Redis
        if self._contains_redis_imports(content):
            ssot_violations = self._check_ssot_compliance(file_path, content)
            deprecated_violations = self._check_deprecated_patterns(file_path, content)
            
            # Mark as CRITICAL for Golden Path files
            for violation in ssot_violations + deprecated_violations:
                violation['severity'] = 'CRITICAL'
                violation['violation_type'] += ' (Golden Path Critical)'
                violations.append(violation)
                
        return violations

    def _check_direct_instantiation(self, file_path: Path, content: str) -> List[Dict]:
        """Check for direct RedisManager instantiation."""
        violations = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments
            if line.startswith('#'):
                continue
                
            # Check for direct instantiation patterns
            if 'RedisManager()' in line and 'redis_manager = RedisManager()' not in line:
                violations.append({
                    'file': str(file_path),
                    'line': i, 
                    'content': line,
                    'violation_type': 'Direct RedisManager instantiation bypasses SSOT',
                    'severity': 'HIGH'
                })
                
        return violations

    def _format_violation_report(self, violations: List[Dict]) -> str:
        """Format violations into a readable report."""
        if not violations:
            return "No violations found"
            
        report = []
        report.append(f"\n{'='*80}")
        report.append(f"REDIS IMPORT PATTERN VIOLATIONS ({len(violations)} total)")
        report.append(f"{'='*80}")
        
        # Group by severity
        by_severity = {}
        for violation in violations:
            severity = violation['severity']
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(violation)
            
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if severity in by_severity:
                report.append(f"\n{severity} VIOLATIONS ({len(by_severity[severity])}):")
                report.append("-" * 50)
                
                for violation in by_severity[severity]:
                    report.append(f"  📁 {violation['file']}")
                    report.append(f"  📍 Line {violation['line']}: {violation['violation_type']}")
                    report.append(f"  💻 Code: {violation['content']}")
                    report.append("")
                    
        report.append("🔧 REMEDIATION:")
        report.append("  1. Replace deprecated imports with SSOT pattern:")
        report.append("     from netra_backend.app.redis_manager import redis_manager")
        report.append("  2. Remove direct RedisManager() instantiation")
        report.append("  3. Use redis_manager singleton instance")
        report.append(f"{'='*80}")
        
        return '\n'.join(report)


if __name__ == '__main__':
    unittest.main()