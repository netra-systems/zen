"""
Test Legacy Pattern Detection for SSOT Migration (Issue #1097)

Validates current state of legacy test files and identifies specific violations.
This test establishes the baseline for Issue #1097 SSOT Migration by cataloging
all mission-critical test files that need migration from unittest.TestCase to
SSotBaseTestCase patterns.

Business Value: Platform/Internal - System Stability & Test Infrastructure
- Protects $500K+ ARR through reliable test infrastructure
- Ensures proper SSOT compliance in mission-critical tests
- Establishes migration baseline for tracking progress

GitHub Issue: #1097 - SSOT Migration for mission-critical tests
"""

import pytest
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestLegacyPatternDetection(SSotBaseTestCase):
    """Detect and catalog legacy unittest.TestCase patterns for migration."""
    
    def test_identify_legacy_test_files(self):
        """Identify all files using unittest.TestCase in mission_critical/."""
        print("\n" + "="*60)
        print("Testing Legacy Test File Detection")
        print("="*60)
        
        mission_critical_dir = Path("tests/mission_critical")
        if not mission_critical_dir.exists():
            # Try relative path from current location
            mission_critical_dir = Path(__file__).parent.parent / "mission_critical"
        
        legacy_files = []
        total_test_files = 0
        
        print(f"\n1. Scanning directory: {mission_critical_dir}")
        
        for test_file in mission_critical_dir.glob("test_*.py"):
            total_test_files += 1
            try:
                content = test_file.read_text()
                if "unittest.TestCase" in content:
                    legacy_files.append(str(test_file))
                    print(f"   [LEGACY] {test_file.name}")
                else:
                    print(f"   [SSOT]   {test_file.name}")
            except Exception as e:
                print(f"   [ERROR]  {test_file.name}: {e}")
        
        print(f"\n2. Summary:")
        print(f"   Total test files found: {total_test_files}")
        print(f"   Legacy files (unittest.TestCase): {len(legacy_files)}")
        print(f"   SSOT compliant files: {total_test_files - len(legacy_files)}")
        
        # Record the specific files for tracking
        self.record_metric("total_test_files", total_test_files)
        self.record_metric("legacy_files_count", len(legacy_files))
        self.record_metric("legacy_files_list", legacy_files)
        self.record_metric("ssot_compliant_files", total_test_files - len(legacy_files))
        
        # Log expected vs actual for Issue #1097
        expected_legacy_files = 22
        if len(legacy_files) != expected_legacy_files:
            print(f"\n⚠️  NOTICE: Expected {expected_legacy_files} legacy files, found {len(legacy_files)}")
            print("   This may indicate files have already been migrated or new files added.")
        
        print(f"\n3. Legacy files requiring migration:")
        for legacy_file in legacy_files:
            print(f"   - {Path(legacy_file).name}")
        
        assert total_test_files > 0, "No test files found in mission_critical directory"
        
        print("\n" + "="*60)
        print(f"[OK] Detection complete: {len(legacy_files)} files need migration")
        print("="*60)
    
    def test_analyze_legacy_patterns(self):
        """Analyze specific legacy patterns in each file."""
        print("\n" + "="*60)
        print("Testing Legacy Pattern Analysis")
        print("="*60)
        
        patterns_found = {
            "unittest_testcase_inheritance": 0,
            "setup_teardown_methods": 0,
            "direct_os_environ_access": 0,
            "no_ssot_base_class": 0,
            "unittest_import": 0
        }
        
        pattern_files = {
            "unittest_testcase_inheritance": [],
            "setup_teardown_methods": [],
            "direct_os_environ_access": [],
            "no_ssot_base_class": [],
            "unittest_import": []
        }
        
        mission_critical_dir = Path("tests/mission_critical")
        if not mission_critical_dir.exists():
            mission_critical_dir = Path(__file__).parent.parent / "mission_critical"
        
        print(f"\n1. Analyzing patterns in: {mission_critical_dir}")
        
        for test_file in mission_critical_dir.glob("test_*.py"):
            try:
                content = test_file.read_text()
                file_name = test_file.name
                
                # Check for unittest.TestCase inheritance
                if "unittest.TestCase" in content:
                    patterns_found["unittest_testcase_inheritance"] += 1
                    pattern_files["unittest_testcase_inheritance"].append(file_name)
                
                # Check for setUp/tearDown methods
                if "def setUp(" in content or "def tearDown(" in content:
                    patterns_found["setup_teardown_methods"] += 1
                    pattern_files["setup_teardown_methods"].append(file_name)
                
                # Check for direct os.environ access
                if "os.environ" in content:
                    patterns_found["direct_os_environ_access"] += 1
                    pattern_files["direct_os_environ_access"].append(file_name)
                
                # Check for missing SSOT base class
                if ("class Test" in content or "def test_" in content) and \
                   "SSotBaseTestCase" not in content and "SSotAsyncTestCase" not in content:
                    patterns_found["no_ssot_base_class"] += 1
                    pattern_files["no_ssot_base_class"].append(file_name)
                
                # Check for unittest import
                if "import unittest" in content:
                    patterns_found["unittest_import"] += 1
                    pattern_files["unittest_import"].append(file_name)
                    
            except Exception as e:
                print(f"   [ERROR] Failed to analyze {test_file.name}: {e}")
        
        print(f"\n2. Pattern Analysis Results:")
        for pattern, count in patterns_found.items():
            print(f"   {pattern}: {count} files")
            if count > 0:
                print(f"      Files: {', '.join(pattern_files[pattern][:3])}")
                if len(pattern_files[pattern]) > 3:
                    print(f"             ... and {len(pattern_files[pattern]) - 3} more")
        
        # Record findings
        for pattern, count in patterns_found.items():
            self.record_metric(f"pattern_{pattern}", count)
            self.record_metric(f"pattern_{pattern}_files", pattern_files[pattern])
        
        print(f"\n3. Migration Priority Assessment:")
        high_priority = patterns_found["unittest_testcase_inheritance"]
        medium_priority = patterns_found["setup_teardown_methods"]
        low_priority = patterns_found["direct_os_environ_access"]
        
        print(f"   High Priority (unittest.TestCase): {high_priority} files")
        print(f"   Medium Priority (setUp/tearDown): {medium_priority} files")
        print(f"   Low Priority (os.environ): {low_priority} files")
        
        # For Issue #1097, we expect violations
        if patterns_found["unittest_testcase_inheritance"] > 0:
            print(f"\n✅ Confirmed: Found {patterns_found['unittest_testcase_inheritance']} files using unittest.TestCase")
            print("   These files are the target for Issue #1097 migration.")
        
        print("\n" + "="*60)
        print("[OK] Pattern analysis complete")
        print("="*60)
    
    def test_migration_complexity_assessment(self):
        """Assess the complexity of migration for each legacy file."""
        print("\n" + "="*60)
        print("Testing Migration Complexity Assessment")
        print("="*60)
        
        mission_critical_dir = Path("tests/mission_critical")
        if not mission_critical_dir.exists():
            mission_critical_dir = Path(__file__).parent.parent / "mission_critical"
        
        complexity_assessment = {
            "simple": [],      # Just inheritance change needed
            "moderate": [],    # Inheritance + setUp/tearDown conversion
            "complex": []      # Above + environment variable handling
        }
        
        print(f"\n1. Assessing migration complexity:")
        
        for test_file in mission_critical_dir.glob("test_*.py"):
            try:
                content = test_file.read_text()
                
                if "unittest.TestCase" not in content:
                    continue  # Skip non-legacy files
                
                complexity_score = 0
                file_name = test_file.name
                
                # Base complexity for unittest.TestCase
                complexity_score += 1
                
                # Add complexity for setUp/tearDown
                if "def setUp(" in content or "def tearDown(" in content:
                    complexity_score += 1
                
                # Add complexity for environment variables
                if "os.environ" in content:
                    complexity_score += 1
                
                # Add complexity for mocking
                if "Mock" in content or "@patch" in content:
                    complexity_score += 1
                
                # Add complexity for async patterns
                if "async def" in content or "asyncio" in content:
                    complexity_score += 1
                
                # Categorize by complexity
                if complexity_score <= 2:
                    complexity_assessment["simple"].append(file_name)
                    print(f"   [SIMPLE]   {file_name} (score: {complexity_score})")
                elif complexity_score <= 4:
                    complexity_assessment["moderate"].append(file_name)
                    print(f"   [MODERATE] {file_name} (score: {complexity_score})")
                else:
                    complexity_assessment["complex"].append(file_name)
                    print(f"   [COMPLEX]  {file_name} (score: {complexity_score})")
                    
            except Exception as e:
                print(f"   [ERROR] Failed to assess {test_file.name}: {e}")
        
        print(f"\n2. Complexity Summary:")
        total_files = sum(len(files) for files in complexity_assessment.values())
        print(f"   Simple migrations: {len(complexity_assessment['simple'])} files")
        print(f"   Moderate migrations: {len(complexity_assessment['moderate'])} files")
        print(f"   Complex migrations: {len(complexity_assessment['complex'])} files")
        print(f"   Total files to migrate: {total_files}")
        
        # Record complexity assessment
        for complexity, files in complexity_assessment.items():
            self.record_metric(f"complexity_{complexity}", len(files))
            self.record_metric(f"complexity_{complexity}_files", files)
        
        print(f"\n3. Migration Strategy Recommendation:")
        if len(complexity_assessment["simple"]) > 0:
            print(f"   1. Start with {len(complexity_assessment['simple'])} simple files")
            print(f"      Example: {complexity_assessment['simple'][0] if complexity_assessment['simple'] else 'None'}")
        
        if len(complexity_assessment["moderate"]) > 0:
            print(f"   2. Proceed with {len(complexity_assessment['moderate'])} moderate files")
            print(f"      Example: {complexity_assessment['moderate'][0] if complexity_assessment['moderate'] else 'None'}")
        
        if len(complexity_assessment["complex"]) > 0:
            print(f"   3. Handle {len(complexity_assessment['complex'])} complex files carefully")
            print(f"      Example: {complexity_assessment['complex'][0] if complexity_assessment['complex'] else 'None'}")
        
        print("\n" + "="*60)
        print("[OK] Complexity assessment complete")
        print("="*60)


if __name__ == "__main__":
    print("Running Legacy Pattern Detection for Issue #1097...")
    
    # Create test suite
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLegacyPatternDetection)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("LEGACY PATTERN DETECTION RESULTS")
    print("="*60)
    
    if result.wasSuccessful():
        print("✅ SUCCESS! Legacy pattern detection completed successfully")
        print("\nNext steps for Issue #1097:")
        print("1. Review detected legacy files")
        print("2. Create SSOT base class capability tests")
        print("3. Test migration pattern on sample file")
        print("4. Execute batch migration with proper backup")
        print("5. Validate post-migration SSOT compliance")
    else:
        print("❌ FAILURE! Legacy pattern detection encountered issues")
        if result.failures:
            print("   Failures:")
            for test, traceback in result.failures:
                print(f"   - {test}")
        if result.errors:
            print("   Errors:")
            for test, traceback in result.errors:
                print(f"   - {test}")