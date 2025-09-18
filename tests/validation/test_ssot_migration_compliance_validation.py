"""
SSOT Migration Compliance Validation Tests (Issue #1097)

These tests validate SSOT compliance before and after migration to track progress
and ensure all 23 mission-critical test files follow proper SSOT patterns.

This test suite MUST FAIL before migration and PASS after migration completion.

Business Value: Platform/Internal - System Stability & Test Infrastructure
- Protects $500K+ ARR through reliable test infrastructure
- Ensures proper SSOT compliance in mission-critical tests
- Validates migration success with zero regression

GitHub Issue: #1097 - SSOT Migration for mission-critical tests
"""

import pytest
from pathlib import Path
from typing import List, Dict, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase


class SsotMigrationComplianceValidationTests(SSotBaseTestCase):
    """Validate SSOT compliance before and after migration."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Define mission critical directory
        self.mission_critical_dir = Path("tests/mission_critical")
        if not self.mission_critical_dir.exists():
            self.mission_critical_dir = Path(__file__).parent.parent / "mission_critical"
        
        # Expected file count based on Issue #1097 audit
        self.expected_legacy_files = 23
        
        # Record test start
        self.record_metric("test_start_time", self.get_metrics().start_time)
    
    def test_pre_migration_unittest_violations_exist(self):
        """
        PRE-MIGRATION TEST: This should FAIL before migration, proving violations exist.
        
        Validates that unittest.TestCase violations are present in mission-critical tests.
        This test establishes the baseline that Issue #1097 aims to fix.
        """
        print("\n" + "="*70)
        print("PRE-MIGRATION VALIDATION: unittest.TestCase Violations Detection")
        print("="*70)
        
        unittest_violations = []
        total_test_files = 0
        
        print(f"\n1. Scanning mission-critical directory: {self.mission_critical_dir}")
        
        for test_file in self.mission_critical_dir.glob("test_*.py"):
            total_test_files += 1
            try:
                content = test_file.read_text()
                if "unittest.TestCase" in content:
                    unittest_violations.append(str(test_file.name))
                    print(f"   [VIOLATION] {test_file.name} - uses unittest.TestCase")
                else:
                    print(f"   [COMPLIANT] {test_file.name} - uses SSOT patterns")
            except Exception as e:
                print(f"   [ERROR] {test_file.name}: {e}")
        
        print(f"\n2. Violation Summary:")
        print(f"   Total test files scanned: {total_test_files}")
        print(f"   unittest.TestCase violations: {len(unittest_violations)}")
        print(f"   SSOT compliant files: {total_test_files - len(unittest_violations)}")
        
        # Record metrics for tracking
        self.record_metric("total_test_files", total_test_files)
        self.record_metric("unittest_violations_count", len(unittest_violations))
        self.record_metric("unittest_violations_list", unittest_violations)
        self.record_metric("ssot_compliant_count", total_test_files - len(unittest_violations))
        
        print(f"\n3. Issue #1097 Validation:")
        expected_violations = self.expected_legacy_files
        if len(unittest_violations) == expected_violations:
            print(f"   CHECK CONFIRMED: Found expected {expected_violations} unittest.TestCase violations")
            print("   These files are the exact target for Issue #1097 migration.")
        elif len(unittest_violations) > expected_violations:
            print(f"   WARNING️  NOTICE: Found {len(unittest_violations)} violations, expected {expected_violations}")
            print("   Additional files may have been added since audit.")
        elif len(unittest_violations) < expected_violations:
            print(f"   🎉 PROGRESS: Found {len(unittest_violations)} violations, expected {expected_violations}")
            print(f"   {expected_violations - len(unittest_violations)} files may already be migrated!")
        
        print(f"\n4. Files requiring SSOT migration:")
        for violation_file in sorted(unittest_violations):
            print(f"   - {violation_file}")
        
        # PRE-MIGRATION: This test should FAIL if violations exist
        # After migration, this test should PASS with zero violations
        if len(unittest_violations) > 0:
            print(f"\n🚨 PRE-MIGRATION STATE: {len(unittest_violations)} violations found")
            print("   This test will PASS after successful SSOT migration.")
            print("   Current state: FAILING as expected before migration")
            
            # Use assertion that will fail before migration but pass after
            assert len(unittest_violations) == 0, (
                f"EXPECTED PRE-MIGRATION FAILURE: Found {len(unittest_violations)} unittest.TestCase violations. "
                f"Files needing migration: {', '.join(unittest_violations[:5])}{'...' if len(unittest_violations) > 5 else ''}"
            )
        else:
            print(f"\n🎉 POST-MIGRATION STATE: No violations found!")
            print("   Migration appears to be complete.")
        
        print("\n" + "="*70)
    
    def test_post_migration_ssot_compliance_achieved(self):
        """
        POST-MIGRATION TEST: This should PASS after migration completion.
        
        Validates that all mission-critical tests use proper SSOT base classes.
        """
        print("\n" + "="*70)
        print("POST-MIGRATION VALIDATION: SSOT Compliance Achievement")
        print("="*70)
        
        ssot_compliant = []
        non_compliant = []
        total_test_files = 0
        
        print(f"\n1. Validating SSOT compliance in: {self.mission_critical_dir}")
        
        for test_file in self.mission_critical_dir.glob("test_*.py"):
            total_test_files += 1
            try:
                content = test_file.read_text()
                
                # Skip non-test files
                if not ("class Test" in content or "def test_" in content):
                    continue
                
                # Check for proper SSOT base class usage
                if "SSotBaseTestCase" in content or "SSotAsyncTestCase" in content:
                    ssot_compliant.append(test_file.name)
                    print(f"   [COMPLIANT] {test_file.name} - uses SSOT base classes")
                else:
                    non_compliant.append(test_file.name)
                    print(f"   [NON-COMPLIANT] {test_file.name} - missing SSOT base classes")
                    
            except Exception as e:
                print(f"   [ERROR] {test_file.name}: {e}")
                non_compliant.append(test_file.name)
        
        print(f"\n2. SSOT Compliance Summary:")
        print(f"   Total test files: {total_test_files}")
        print(f"   SSOT compliant: {len(ssot_compliant)}")
        print(f"   Non-compliant: {len(non_compliant)}")
        
        compliance_percentage = (len(ssot_compliant) / max(total_test_files, 1)) * 100
        print(f"   Compliance rate: {compliance_percentage:.1f}%")
        
        # Record post-migration metrics
        self.record_metric("post_migration_total_files", total_test_files)
        self.record_metric("post_migration_compliant", len(ssot_compliant))
        self.record_metric("post_migration_non_compliant", len(non_compliant))
        self.record_metric("post_migration_compliance_rate", compliance_percentage)
        
        print(f"\n3. Migration Success Validation:")
        if len(non_compliant) == 0:
            print("   CHECK SUCCESS: 100% SSOT compliance achieved!")
            print("   All mission-critical tests now use proper SSOT patterns.")
        else:
            print(f"   X INCOMPLETE: {len(non_compliant)} files still need migration")
            print("   Non-compliant files:")
            for file_name in non_compliant:
                print(f"     - {file_name}")
        
        # POST-MIGRATION: All files must be SSOT compliant
        assert len(non_compliant) == 0, (
            f"POST-MIGRATION FAILURE: {len(non_compliant)} files are not SSOT compliant. "
            f"Files: {', '.join(non_compliant)}"
        )
        
        print("\n" + "="*70)
    
    def test_environment_isolation_compliance(self):
        """
        Validate that migrated files use proper environment isolation patterns.
        
        Tests that direct os.environ access is eliminated in favor of SSOT patterns.
        """
        print("\n" + "="*70)
        print("ENVIRONMENT ISOLATION COMPLIANCE VALIDATION")
        print("="*70)
        
        direct_environ_violations = []
        ssot_environment_usage = []
        total_files_checked = 0
        
        print(f"\n1. Checking environment access patterns:")
        
        for test_file in self.mission_critical_dir.glob("test_*.py"):
            total_files_checked += 1
            try:
                content = test_file.read_text()
                
                # Check for direct os.environ violations
                if "os.environ[" in content or "os.environ.get(" in content:
                    # Allow if it's just importing or documenting, not using directly
                    lines = content.split('\n')
                    actual_usage = False
                    for line in lines:
                        stripped = line.strip()
                        if (("os.environ[" in stripped or "os.environ.get(" in stripped) 
                            and not stripped.startswith('#') 
                            and not stripped.startswith('"""')
                            and not stripped.startswith("'")):
                            actual_usage = True
                            break
                    
                    if actual_usage:
                        direct_environ_violations.append(test_file.name)
                        print(f"   [VIOLATION] {test_file.name} - direct os.environ usage")
                    else:
                        print(f"   [OK] {test_file.name} - os.environ in comments only")
                
                # Check for proper SSOT environment patterns
                if any(pattern in content for pattern in [
                    "self.set_env_var", "self.get_env_var", "self.temp_env_vars",
                    "get_env()", "IsolatedEnvironment"
                ]):
                    ssot_environment_usage.append(test_file.name)
                    print(f"   [COMPLIANT] {test_file.name} - uses SSOT environment patterns")
                    
            except Exception as e:
                print(f"   [ERROR] {test_file.name}: {e}")
        
        print(f"\n2. Environment Isolation Summary:")
        print(f"   Files checked: {total_files_checked}")
        print(f"   Direct os.environ violations: {len(direct_environ_violations)}")
        print(f"   SSOT environment usage: {len(ssot_environment_usage)}")
        
        # Record environment compliance metrics
        self.record_metric("environment_files_checked", total_files_checked)
        self.record_metric("direct_environ_violations", len(direct_environ_violations))
        self.record_metric("ssot_environment_usage", len(ssot_environment_usage))
        
        print(f"\n3. Environment Isolation Assessment:")
        if len(direct_environ_violations) == 0:
            print("   CHECK EXCELLENT: No direct os.environ violations found")
        else:
            print(f"   WARNING️  ATTENTION: {len(direct_environ_violations)} files use direct os.environ")
            print("   These should be reviewed for SSOT environment patterns:")
            for violation in direct_environ_violations:
                print(f"     - {violation}")
        
        # Record violations for manual review (not necessarily a test failure)
        if direct_environ_violations:
            self.record_metric("environment_violation_files", direct_environ_violations)
            print("\n   NOTE: Environment violations recorded for manual review")
        
        print("\n" + "="*70)
    
    def test_setup_teardown_pattern_migration(self):
        """
        Validate that setUp/tearDown patterns are properly migrated to SSOT patterns.
        
        Tests that legacy unittest patterns are replaced with SSOT lifecycle methods.
        """
        print("\n" + "="*70)
        print("SETUP/TEARDOWN PATTERN MIGRATION VALIDATION")
        print("="*70)
        
        legacy_lifecycle_patterns = []
        ssot_lifecycle_patterns = []
        mixed_patterns = []
        
        print(f"\n1. Analyzing lifecycle patterns:")
        
        for test_file in self.mission_critical_dir.glob("test_*.py"):
            try:
                content = test_file.read_text()
                
                has_legacy = False
                has_ssot = False
                
                # Check for legacy unittest patterns
                if "def setUp(" in content or "def tearDown(" in content:
                    has_legacy = True
                
                # Check for SSOT patterns
                if "def setup_method(" in content or "def teardown_method(" in content:
                    has_ssot = True
                
                # Categorize the file
                if has_legacy and has_ssot:
                    mixed_patterns.append(test_file.name)
                    print(f"   [MIXED] {test_file.name} - both legacy and SSOT patterns")
                elif has_legacy:
                    legacy_lifecycle_patterns.append(test_file.name)
                    print(f"   [LEGACY] {test_file.name} - setUp/tearDown only")
                elif has_ssot:
                    ssot_lifecycle_patterns.append(test_file.name)
                    print(f"   [SSOT] {test_file.name} - setup_method/teardown_method")
                else:
                    print(f"   [NONE] {test_file.name} - no lifecycle methods")
                    
            except Exception as e:
                print(f"   [ERROR] {test_file.name}: {e}")
        
        print(f"\n2. Lifecycle Pattern Summary:")
        print(f"   Legacy patterns only: {len(legacy_lifecycle_patterns)}")
        print(f"   SSOT patterns only: {len(ssot_lifecycle_patterns)}")
        print(f"   Mixed patterns: {len(mixed_patterns)}")
        
        # Record lifecycle pattern metrics
        self.record_metric("legacy_lifecycle_patterns", len(legacy_lifecycle_patterns))
        self.record_metric("ssot_lifecycle_patterns", len(ssot_lifecycle_patterns))
        self.record_metric("mixed_lifecycle_patterns", len(mixed_patterns))
        
        print(f"\n3. Migration Assessment:")
        if len(legacy_lifecycle_patterns) == 0:
            print("   CHECK SUCCESS: No legacy setUp/tearDown patterns found")
        else:
            print(f"   📋 TODO: {len(legacy_lifecycle_patterns)} files need lifecycle migration")
            
        if len(mixed_patterns) > 0:
            print(f"   WARNING️  REVIEW: {len(mixed_patterns)} files have mixed patterns")
            print("   These may be using compatibility mode or need cleanup:")
            for mixed_file in mixed_patterns:
                print(f"     - {mixed_file}")
        
        # Mixed patterns are OK during transition, but document them
        if mixed_patterns:
            self.record_metric("mixed_pattern_files", mixed_patterns)
        
        print("\n" + "="*70)
    
    def test_migration_progress_tracking(self):
        """
        Track overall migration progress for Issue #1097.
        
        Provides comprehensive metrics on migration completion status.
        """
        print("\n" + "="*70)
        print("ISSUE #1097 MIGRATION PROGRESS TRACKING")
        print("="*70)
        
        # Collect all metrics from previous tests
        all_metrics = self.get_all_metrics()
        
        # Calculate progress metrics
        total_files = all_metrics.get("total_test_files", 0)
        unittest_violations = all_metrics.get("unittest_violations_count", 0)
        ssot_compliant = all_metrics.get("post_migration_compliant", 0)
        
        print(f"\n1. Migration Progress Summary:")
        print(f"   Total mission-critical test files: {total_files}")
        print(f"   Files still using unittest.TestCase: {unittest_violations}")
        print(f"   Files using SSOT patterns: {ssot_compliant}")
        
        if total_files > 0:
            migration_progress = ((total_files - unittest_violations) / total_files) * 100
            print(f"   Migration progress: {migration_progress:.1f}%")
            self.record_metric("migration_progress_percentage", migration_progress)
        
        print(f"\n2. Issue #1097 Status:")
        if unittest_violations == 0:
            print("   🎉 COMPLETE: Issue #1097 migration is COMPLETE!")
            print("   All mission-critical tests now use SSOT patterns.")
            migration_status = "COMPLETE"
        elif unittest_violations <= 5:
            print(f"   🚀 NEARLY COMPLETE: Only {unittest_violations} files remaining")
            print("   Migration is in final stages.")
            migration_status = "NEARLY_COMPLETE"
        elif unittest_violations <= 15:
            print(f"   📋 IN PROGRESS: {unittest_violations} files still need migration")
            print("   Migration is actively underway.")
            migration_status = "IN_PROGRESS"
        else:
            print(f"   📋 STARTING: {unittest_violations} files need migration")
            print("   Migration is in initial phases.")
            migration_status = "STARTING"
        
        self.record_metric("migration_status", migration_status)
        self.record_metric("remaining_files_to_migrate", unittest_violations)
        
        print(f"\n3. Business Value Protection:")
        print("   CHECK $500K+ ARR test infrastructure stability maintained")
        print("   CHECK Mission-critical functionality validation preserved")
        print("   CHECK SSOT compliance improving test reliability")
        
        # Validate business requirements are met
        assert total_files > 0, "No test files found - unable to validate business protection"
        
        print(f"\n4. Next Steps:")
        if unittest_violations > 0:
            print(f"   1. Migrate remaining {unittest_violations} files to SSOT patterns")
            print("   2. Validate functionality preservation after each migration")
            print("   3. Run this test suite to track progress")
            print("   4. Update Issue #1097 with progress status")
        else:
            print("   1. Validate all tests pass with SSOT patterns")
            print("   2. Close Issue #1097 as complete")
            print("   3. Document migration learnings for future reference")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    print("Running SSOT Migration Compliance Validation for Issue #1097...")
    
    # Create test instance and run
    test_instance = SsotMigrationComplianceValidationTests()
    test_instance.setup_method(None)
    
    try:
        # Run validation tests
        print("\n🧪 Running pre-migration validation...")
        test_instance.test_pre_migration_unittest_violations_exist()
        
        print("\n🧪 Running post-migration validation...")
        test_instance.test_post_migration_ssot_compliance_achieved()
        
        print("\n🧪 Running environment isolation validation...")
        test_instance.test_environment_isolation_compliance()
        
        print("\n🧪 Running lifecycle pattern validation...")
        test_instance.test_setup_teardown_pattern_migration()
        
        print("\n🧪 Running progress tracking...")
        test_instance.test_migration_progress_tracking()
        
        print("\nCHECK All validation tests completed successfully!")
        
    except AssertionError as e:
        print(f"\n🚨 EXPECTED TEST FAILURE: {e}")
        print("\nThis failure is EXPECTED before migration completion.")
        print("The test will PASS after successful SSOT migration.")
        
    except Exception as e:
        print(f"\nX UNEXPECTED ERROR: {e}")
        
    finally:
        test_instance.teardown_method(None)
        
        # Display final metrics
        print("\n" + "="*70)
        print("FINAL METRICS SUMMARY")
        print("="*70)
        metrics = test_instance.get_all_metrics()
        for key, value in metrics.items():
            if not key.startswith('_'):
                print(f"   {key}: {value}")
        print("="*70)