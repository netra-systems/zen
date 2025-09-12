#!/usr/bin/env python3
"""
Standalone Mock Policy Violation Test

This test script enforces the "MOCKS = Abomination" policy from CLAUDE.md
by scanning all test files and failing when mocks are detected.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from tests.mission_critical.test_mock_policy_violations import TestMockPolicyCompliance
from collections import defaultdict


def run_mock_violations_test():
    """Run the mock violations test without pytest framework."""
    
    # Create test instance
    test = TestMockPolicyCompliance()
    
    # Setup test directories manually
    test.project_root = project_root
    test.test_directories = [
        test.project_root / 'auth_service' / 'tests',
        test.project_root / 'analytics_service' / 'tests', 
        test.project_root / 'netra_backend' / 'tests',
        test.project_root / 'tests',
        test.project_root / 'dev_launcher' / 'tests',
    ]
    
    print("=" * 80)
    print("MOCK POLICY VIOLATION TEST")
    print("=" * 80)
    print("Testing CLAUDE.md policy: 'MOCKS = Abomination', 'MOCKS are FORBIDDEN'")
    print()
    
    # Run comprehensive mock audit
    all_violations = []
    service_violations = defaultdict(list)
    
    for test_dir in test.test_directories:
        if test_dir.exists():
            print(f"Scanning {test_dir}...")
            violations = test.scan_for_mock_usage(test_dir)
            all_violations.extend(violations)
            for v in violations:
                service_violations[v.service].append(v)
    
    if all_violations:
        print("\n" + "=" * 80)
        print("CRITICAL POLICY VIOLATIONS DETECTED!")
        print("=" * 80)
        print(f"Total Violations: {len(all_violations)}")
        print(f"Services Affected: {len(service_violations)}")
        print()
        
        for service, violations in service_violations.items():
            print(f"{service.upper()}: {len(violations)} violations")
            
            # Group by violation type
            by_type = defaultdict(list)
            for v in violations:
                by_type[v.violation_type].append(v)
            
            for vtype, vlist in by_type.items():
                print(f"  {vtype}: {len(vlist)} occurrences")
                # Show first 3 examples
                for v in vlist[:3]:
                    short_path = v.file_path.split('/netra-apex/')[-1] 
                    print(f"    [U+2022] {short_path}:{v.line_number}")
                if len(vlist) > 3:
                    print(f"    ... and {len(vlist) - 3} more")
            print()
        
        print("REQUIRED ACTIONS:")
        print("1. Replace ALL mocks with real service tests") 
        print("2. Use IsolatedEnvironment for test isolation")
        print("3. Use docker-compose for service dependencies")
        print("4. Implement real WebSocket/database connections")
        print("=" * 80)
        
        # This is a FAIL
        return False, len(all_violations)
    else:
        print(" PASS:  SUCCESS: No mock policy violations found!")
        return True, 0


if __name__ == '__main__':
    success, violation_count = run_mock_violations_test()
    
    if not success:
        print(f"\n FAIL:  TEST FAILED: {violation_count} mock violations found")
        print("The test suite MUST fail until all mocks are replaced with real services")
        sys.exit(1)
    else:
        print(f"\n PASS:  TEST PASSED: No mock violations")  
        sys.exit(0)