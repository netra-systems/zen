#!/usr/bin/env python3
"""
SSOT MIGRATION AUTOMATION - PHASE 3 PREPARATION
===============================================
Automated migration tools for converting pytest.main() usage to canonical SSOT UnifiedTestRunner.

BUSINESS PROTECTION:
- Golden Path tests migrated first (revenue protection priority)
- Zero business disruption during migration
- Comprehensive rollback capability
- Real-time migration validation

USAGE:
    python scripts/ssot_migration_automation.py --scan-violations
    python scripts/ssot_migration_automation.py --migrate-golden-path
    python scripts/ssot_migration_automation.py --migrate-category integration
    python scripts/ssot_migration_automation.py --validate-compliance
"""

import argparse
import ast
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import subprocess
import shutil
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
CANONICAL_SSOT_PATH = "tests/unified_test_runner.py"

class SSOTMigrationAutomator:
    """Automated SSOT migration with business continuity protection."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.violations_found = []
        self.migration_log = []
        self.rollback_data = {}
        
    def scan_ssot_violations(self) -> Dict[str, List[Dict]]:
        """
        Scan codebase for SSOT violations requiring migration.
        
        Returns:
            Dict mapping violation types to lists of violation details
        """
        logger.info("🔍 Scanning for SSOT violations requiring migration...")
        
        violations = {
            'pytest_main_usage': [],
            'deprecated_test_runner_imports': [],
            'hardcoded_test_execution': [],
            'ci_cd_violations': []
        }
        
        # Scan Python files for pytest.main() usage
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                violations.update(self._scan_file_violations(py_file, content, violations))
            except Exception as e:
                logger.warning(f"Error scanning {py_file}: {e}")
                
        # Scan CI/CD files
        ci_cd_violations = self._scan_ci_cd_violations()
        violations['ci_cd_violations'].extend(ci_cd_violations)
        
        self._log_violation_summary(violations)
        return violations
    
    def _scan_file_violations(self, file_path: Path, content: str, violations: Dict) -> Dict:
        """Scan individual file for violations."""
        
        # Check for pytest.main() usage
        if 'pytest.main(' in content:
            violations['pytest_main_usage'].append({
                'file': str(file_path),
                'lines': self._find_pattern_lines(content, r'pytest\.main\('),
                'severity': 'high' if 'golden_path' in str(file_path).lower() else 'medium'
            })
        
        # Check for deprecated test runner imports
        deprecated_patterns = [
            r'from test_framework\.runner import UnifiedTestRunner',
            r'import test_framework\.runner',
        ]
        
        for pattern in deprecated_patterns:
            if re.search(pattern, content):
                violations['deprecated_test_runner_imports'].append({
                    'file': str(file_path),
                    'pattern': pattern,
                    'lines': self._find_pattern_lines(content, pattern),
                    'severity': 'high'
                })
        
        # Check for hardcoded test execution
        hardcoded_patterns = [
            r'subprocess\.run\(\["python", "-m", "pytest"',
            r'subprocess\.call\(\["pytest"',
            r'os\.system\("pytest'
        ]
        
        for pattern in hardcoded_patterns:
            if re.search(pattern, content):
                violations['hardcoded_test_execution'].append({
                    'file': str(file_path),
                    'pattern': pattern,
                    'lines': self._find_pattern_lines(content, pattern),
                    'severity': 'medium'
                })
        
        return violations
    
    def _scan_ci_cd_violations(self) -> List[Dict]:
        """Scan CI/CD workflows for SSOT violations."""
        violations = []
        
        workflow_dir = self.project_root / ".github" / "workflows"
        if not workflow_dir.exists():
            return violations
            
        for workflow_file in workflow_dir.rglob("*.yml"):
            try:
                content = workflow_file.read_text(encoding='utf-8')
                
                # Check for deprecated test runner usage
                if 'test_framework.runner' in content:
                    violations.append({
                        'file': str(workflow_file),
                        'type': 'ci_cd_deprecated_import',
                        'severity': 'critical',
                        'description': 'CI/CD workflow uses deprecated test runner'
                    })
                    
            except Exception as e:
                logger.warning(f"Error scanning workflow {workflow_file}: {e}")
                
        return violations
    
    def migrate_golden_path_tests(self) -> bool:
        """
        Migrate Golden Path tests first for revenue protection.
        
        Returns:
            True if migration successful, False otherwise
        """
        logger.info("🚀 Starting Golden Path test migration (Revenue Protection Priority)")
        
        golden_path_patterns = [
            "**/golden_path/**/*.py",
            "**/test_golden_path*.py",
            "**/golden_path*.py"
        ]
        
        migrated_files = []
        
        for pattern in golden_path_patterns:
            for file_path in self.project_root.glob(pattern):
                if self._should_skip_file(file_path):
                    continue
                    
                logger.info(f"🔄 Migrating Golden Path file: {file_path}")
                
                if self._migrate_single_file(file_path):
                    migrated_files.append(file_path)
                    logger.info(f"✅ Successfully migrated: {file_path}")
                else:
                    logger.error(f"❌ Failed to migrate: {file_path}")
                    return False
        
        # Validate Golden Path still works after migration
        if not self._validate_golden_path_functionality():
            logger.error("❌ Golden Path validation failed after migration")
            self._rollback_migrations(migrated_files)
            return False
            
        logger.info(f"✅ Golden Path migration completed: {len(migrated_files)} files migrated")
        return True
    
    def migrate_category_tests(self, category: str) -> bool:
        """
        Migrate tests by category with validation.
        
        Args:
            category: Test category to migrate (e.g., 'integration', 'unit', 'e2e')
            
        Returns:
            True if migration successful, False otherwise
        """
        logger.info(f"🔄 Starting {category} test migration")
        
        category_patterns = [
            f"**/test_{category}*.py",
            f"**/{category}/**/*.py",
            f"**/test*{category}*.py"
        ]
        
        migrated_files = []
        
        for pattern in category_patterns:
            for file_path in self.project_root.glob(pattern):
                if self._should_skip_file(file_path):
                    continue
                    
                if self._contains_violations(file_path):
                    logger.info(f"🔄 Migrating {category} file: {file_path}")
                    
                    if self._migrate_single_file(file_path):
                        migrated_files.append(file_path)
                        logger.info(f"✅ Successfully migrated: {file_path}")
                    else:
                        logger.error(f"❌ Failed to migrate: {file_path}")
                        self._rollback_migrations(migrated_files)
                        return False
        
        # Validate category tests still work
        if not self._validate_category_tests(category):
            logger.error(f"❌ {category} test validation failed after migration")
            self._rollback_migrations(migrated_files)
            return False
            
        logger.info(f"✅ {category} migration completed: {len(migrated_files)} files migrated")
        return True
    
    def _migrate_single_file(self, file_path: Path) -> bool:
        """
        Migrate a single file from pytest.main() to canonical SSOT UnifiedTestRunner.
        
        Args:
            file_path: Path to file to migrate
            
        Returns:
            True if migration successful, False otherwise
        """
        try:
            # Backup original file
            backup_path = file_path.with_suffix(f"{file_path.suffix}.ssot_backup")
            shutil.copy2(file_path, backup_path)
            self.rollback_data[str(file_path)] = str(backup_path)
            
            # Read original content
            original_content = file_path.read_text(encoding='utf-8')
            
            # Apply migration transformations
            migrated_content = self._apply_migration_transformations(original_content)
            
            # Write migrated content
            file_path.write_text(migrated_content, encoding='utf-8')
            
            # Validate syntax
            if not self._validate_syntax(file_path):
                self._restore_from_backup(file_path)
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error migrating {file_path}: {e}")
            self._restore_from_backup(file_path)
            return False
    
    def _apply_migration_transformations(self, content: str) -> str:
        """Apply SSOT migration transformations to file content."""
        
        # 1. Replace deprecated imports
        content = re.sub(
            r'from test_framework\.runner import UnifiedTestRunner',
            'from tests.unified_test_runner import UnifiedTestRunner',
            content
        )
        
        # 2. Replace pytest.main() calls with canonical SSOT usage
        pytest_main_pattern = r'pytest\.main\((.*?)\)'
        
        def replace_pytest_main(match):
            args = match.group(1)
            return f"""
# SSOT MIGRATION: Using canonical UnifiedTestRunner instead of pytest.main()
runner = UnifiedTestRunner()
exit_code, output = runner.run_tests({args})
"""
        
        content = re.sub(pytest_main_pattern, replace_pytest_main, content, flags=re.DOTALL)
        
        # 3. Add canonical SSOT import if UnifiedTestRunner is used
        if 'UnifiedTestRunner' in content and 'from tests.unified_test_runner import' not in content:
            # Add import after existing imports
            import_insertion_point = self._find_import_insertion_point(content)
            if import_insertion_point:
                lines = content.split('\n')
                lines.insert(import_insertion_point, 'from tests.unified_test_runner import UnifiedTestRunner')
                content = '\n'.join(lines)
        
        # 4. Replace hardcoded subprocess pytest calls
        subprocess_patterns = [
            (r'subprocess\.run\(\["python", "-m", "pytest"(.*?)\]', 
             r'runner = UnifiedTestRunner(); exit_code, output = runner.run_tests(\1)'),
            (r'subprocess\.call\(\["pytest"(.*?)\]',
             r'runner = UnifiedTestRunner(); exit_code, output = runner.run_tests(\1)')
        ]
        
        for pattern, replacement in subprocess_patterns:
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        return content
    
    def _validate_golden_path_functionality(self) -> bool:
        """Validate Golden Path functionality after migration."""
        logger.info("🔍 Validating Golden Path functionality...")
        
        try:
            # Quick Golden Path smoke test
            result = subprocess.run([
                sys.executable, CANONICAL_SSOT_PATH,
                "--category", "smoke", 
                "--timeout", "30",
                "--golden-path-check"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("✅ Golden Path validation passed")
                return True
            else:
                logger.error(f"❌ Golden Path validation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Golden Path validation error: {e}")
            return False
    
    def _validate_category_tests(self, category: str) -> bool:
        """Validate category tests after migration."""
        logger.info(f"🔍 Validating {category} tests...")
        
        try:
            result = subprocess.run([
                sys.executable, CANONICAL_SSOT_PATH,
                "--category", category,
                "--timeout", "60",
                "--validation-mode"
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info(f"✅ {category} test validation passed")
                return True
            else:
                logger.error(f"❌ {category} test validation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ {category} test validation error: {e}")
            return False
    
    def validate_ssot_compliance(self) -> Tuple[bool, Dict]:
        """
        Validate overall SSOT compliance after migration.
        
        Returns:
            Tuple of (compliance_passed, compliance_report)
        """
        logger.info("📊 Validating SSOT compliance...")
        
        violations = self.scan_ssot_violations()
        
        total_violations = sum(len(v) for v in violations.values())
        
        compliance_report = {
            'total_violations': total_violations,
            'violation_breakdown': {k: len(v) for k, v in violations.items()},
            'compliance_percentage': max(0, 100 - total_violations),
            'business_impact': self._assess_business_impact(violations)
        }
        
        compliance_passed = total_violations < 10  # Allow some minor violations
        
        if compliance_passed:
            logger.info(f"✅ SSOT compliance validated: {compliance_report['compliance_percentage']}%")
        else:
            logger.error(f"❌ SSOT compliance failed: {total_violations} violations remaining")
            
        return compliance_passed, compliance_report
    
    def _assess_business_impact(self, violations: Dict) -> str:
        """Assess business impact of remaining violations."""
        golden_path_violations = sum(1 for v in violations.get('pytest_main_usage', []) 
                                   if v.get('severity') == 'high')
        
        if golden_path_violations > 0:
            return "HIGH: Golden Path functionality at risk"
        elif violations.get('ci_cd_violations'):
            return "MEDIUM: CI/CD infrastructure uses deprecated patterns"
        elif sum(len(v) for v in violations.values()) > 20:
            return "MEDIUM: Multiple SSOT violations affecting maintainability"
        else:
            return "LOW: Minor violations, business continuity maintained"
    
    def _rollback_migrations(self, migrated_files: List[Path]):
        """Rollback migrations for failed migration attempt."""
        logger.warning("🔄 Rolling back migrations due to validation failure...")
        
        for file_path in migrated_files:
            self._restore_from_backup(file_path)
            
        logger.warning("🔄 Rollback completed. System restored to previous state.")
    
    def _restore_from_backup(self, file_path: Path):
        """Restore file from backup."""
        backup_path = self.rollback_data.get(str(file_path))
        if backup_path and Path(backup_path).exists():
            shutil.copy2(backup_path, file_path)
            Path(backup_path).unlink()  # Remove backup
            del self.rollback_data[str(file_path)]
    
    # Helper methods
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during migration."""
        skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            '.pytest_cache',
            'venv',
            '.venv',
            'ssot_backup'
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _contains_violations(self, file_path: Path) -> bool:
        """Check if file contains SSOT violations."""
        try:
            content = file_path.read_text(encoding='utf-8')
            return ('pytest.main(' in content or 
                   'test_framework.runner' in content or
                   'subprocess.run(["python", "-m", "pytest"' in content)
        except:
            return False
    
    def _find_pattern_lines(self, content: str, pattern: str) -> List[int]:
        """Find line numbers where pattern occurs."""
        lines = content.split('\n')
        return [i + 1 for i, line in enumerate(lines) if re.search(pattern, line)]
    
    def _find_import_insertion_point(self, content: str) -> int:
        """Find where to insert new imports."""
        lines = content.split('\n')
        last_import_line = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                last_import_line = i
                
        return last_import_line + 1 if last_import_line >= 0 else 0
    
    def _validate_syntax(self, file_path: Path) -> bool:
        """Validate Python syntax of migrated file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                ast.parse(f.read())
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return False
    
    def _log_violation_summary(self, violations: Dict):
        """Log summary of violations found."""
        total = sum(len(v) for v in violations.values())
        logger.info(f"📊 SSOT Violation Scan Complete: {total} violations found")
        
        for violation_type, violation_list in violations.items():
            if violation_list:
                logger.info(f"  - {violation_type}: {len(violation_list)} violations")

def main():
    """Main CLI interface for SSOT migration automation."""
    parser = argparse.ArgumentParser(description="SSOT Migration Automation Tool")
    
    parser.add_argument('--scan-violations', action='store_true',
                       help='Scan for SSOT violations requiring migration')
    parser.add_argument('--migrate-golden-path', action='store_true',
                       help='Migrate Golden Path tests (revenue protection priority)')
    parser.add_argument('--migrate-category', type=str,
                       help='Migrate tests by category (unit, integration, e2e)')
    parser.add_argument('--validate-compliance', action='store_true',
                       help='Validate SSOT compliance after migration')
    parser.add_argument('--full-migration', action='store_true',
                       help='Perform complete migration (Golden Path → Integration → Unit → E2E)')
    
    args = parser.parse_args()
    
    migrator = SSOTMigrationAutomator()
    
    if args.scan_violations:
        violations = migrator.scan_ssot_violations()
        print("\n" + "="*60)
        print("SSOT VIOLATION SCAN RESULTS")
        print("="*60)
        for violation_type, violation_list in violations.items():
            print(f"\n{violation_type.upper()}: {len(violation_list)} violations")
            for violation in violation_list[:3]:  # Show first 3
                print(f"  - {violation.get('file', 'Unknown file')}")
            if len(violation_list) > 3:
                print(f"  ... and {len(violation_list) - 3} more")
    
    elif args.migrate_golden_path:
        success = migrator.migrate_golden_path_tests()
        sys.exit(0 if success else 1)
    
    elif args.migrate_category:
        success = migrator.migrate_category_tests(args.migrate_category)
        sys.exit(0 if success else 1)
    
    elif args.validate_compliance:
        compliance_passed, report = migrator.validate_ssot_compliance()
        print("\n" + "="*60)
        print("SSOT COMPLIANCE VALIDATION REPORT")
        print("="*60)
        print(f"Compliance: {'✅ PASSED' if compliance_passed else '❌ FAILED'}")
        print(f"Compliance Percentage: {report['compliance_percentage']}%")
        print(f"Total Violations: {report['total_violations']}")
        print(f"Business Impact: {report['business_impact']}")
        sys.exit(0 if compliance_passed else 1)
    
    elif args.full_migration:
        # Full migration workflow
        print("🚀 Starting Full SSOT Migration...")
        
        # Phase 3.1: Golden Path (Revenue Protection)
        if not migrator.migrate_golden_path_tests():
            sys.exit(1)
        
        # Phase 3.2: Integration Tests
        if not migrator.migrate_category_tests('integration'):
            sys.exit(1)
            
        # Phase 3.3: Unit Tests
        if not migrator.migrate_category_tests('unit'):
            sys.exit(1)
            
        # Phase 3.4: E2E Tests
        if not migrator.migrate_category_tests('e2e'):
            sys.exit(1)
        
        # Final validation
        compliance_passed, report = migrator.validate_ssot_compliance()
        if compliance_passed:
            print("✅ Full SSOT migration completed successfully!")
            print(f"Final compliance: {report['compliance_percentage']}%")
        else:
            print("❌ Full migration validation failed")
            sys.exit(1)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()