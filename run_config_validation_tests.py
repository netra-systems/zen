"""Run Configuration Validation Test Suites

This script runs all three test suites to validate configuration usage
across the codebase and reports violations.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'netra_backend'))

# Import test classes
from netra_backend.tests.test_config_central_usage import TestCentralConfigUsage, ConfigUsageAnalyzer
from netra_backend.tests.test_os_environ_violations import TestOSEnvironViolations, OSEnvironAnalyzer
from netra_backend.tests.test_config_isolation_patterns import TestConfigIsolationPatterns, ConfigIsolationAnalyzer


def run_central_config_tests():
    """Run central configuration usage tests."""
    print("\n" + "="*80)
    print("RUNNING TEST SUITE 1: Central Configuration Usage Validation")
    print("="*80)
    
    test_suite = TestCentralConfigUsage()
    project_root = Path(__file__).parent
    
    # Get Python files
    python_files = []
    for root, dirs, files in os.walk(project_root / 'netra_backend'):
        if 'venv' in root or '__pycache__' in root:
            continue
        for filename in files:
            if filename.endswith('.py'):
                python_files.append(os.path.join(root, filename))
    
    print(f"Analyzing {len(python_files)} Python files...")
    
    # Test 1: No direct config module imports
    print("\nTest 1: Checking for direct config module imports...")
    violations = []
    for filepath in python_files:  # Process all files
        if 'configuration' in filepath or 'config' in os.path.basename(filepath):
            continue
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import ast
                tree = ast.parse(f.read())
                analyzer = ConfigUsageAnalyzer(filepath)
                analyzer.visit(tree)
                
                if analyzer.violations:
                    for v in analyzer.violations:
                        if v['type'] == 'direct_config_import':
                            violations.append({
                                'file': filepath,
                                'line': v['line'],
                                'detail': v['detail']
                            })
        except:
            continue
    
    if violations:
        print(f"  [X] FAILED: Found {len(violations)} direct config imports")
        for v in violations[:5]:
            print(f"     - {v['file']}:{v['line']} - {v['detail']}")
    else:
        print("  [OK] PASSED: No direct config module imports found")
    
    return len(violations) == 0


def run_os_environ_tests():
    """Run OS environment variable access tests."""
    print("\n" + "="*80)
    print("RUNNING TEST SUITE 2: OS Environment Variable Access Validation")
    print("="*80)
    
    project_root = Path(__file__).parent
    allowed_files = [
        'configuration/base.py', 'configuration/database.py',
        'config_manager.py', 'config.py', 'conftest.py'
    ]
    
    violations = []
    justified = []
    
    print("Scanning for unauthorized os.environ access...")
    
    for root, dirs, files in os.walk(project_root / 'netra_backend'):
        if 'venv' in root or '__pycache__' in root:
            continue
            
        for filename in files:  # Process all files
            if not filename.endswith('.py'):
                continue
                
            filepath = os.path.join(root, filename)
            
            # Check if allowed
            if any(allowed in filepath.replace('\\', '/') for allowed in allowed_files):
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'os.environ' not in content and 'os.getenv' not in content:
                        continue
                    
                    import ast
                    tree = ast.parse(content)
                    analyzer = OSEnvironAnalyzer(filepath, content)
                    analyzer.visit(tree)
                    
                    all_violations = analyzer.get_all_violations()
                    if all_violations:
                        violations.extend([{
                            'file': filepath,
                            'line': v['line'],
                            'type': v['type'],
                            'code': v['code']
                        } for v in all_violations])
                    
                    if analyzer.justified_calls:
                        justified.extend(analyzer.justified_calls)
            except:
                continue
    
    print(f"\nTest Results:")
    if violations:
        print(f"  [X] FAILED: Found {len(violations)} unauthorized os.environ accesses")
        for v in violations[:5]:
            print(f"     - {v['file']}:{v['line']} ({v['type']})")
            print(f"       Code: {v['code']}")
    else:
        print("  [OK] PASSED: No unauthorized os.environ access found")
    
    if justified:
        print(f"  [i] Found {len(justified)} properly @marked justified accesses")
    
    return len(violations) == 0


def run_isolation_tests():
    """Run configuration isolation pattern tests."""
    print("\n" + "="*80)
    print("RUNNING TEST SUITE 3: Configuration Isolation Pattern Validation")
    print("="*80)
    
    project_root = Path(__file__).parent
    analyzer = ConfigIsolationAnalyzer(project_root)
    
    cross_service_violations = []
    config_leaks = []
    hardcoded_values = []
    
    print("Analyzing service boundaries and isolation...")
    
    # Test cross-service imports
    for root, dirs, files in os.walk(project_root):
        if 'venv' in root or '__pycache__' in root:
            continue
            
        for filename in files:  # Process all files
            if not filename.endswith('.py'):
                continue
                
            filepath = os.path.join(root, filename)
            service = analyzer._identify_service(filepath)
            
            if not service:
                continue
            
            violations = analyzer.analyze_file(filepath)
            
            if violations['cross_service']:
                cross_service_violations.extend(violations['cross_service'])
            if violations['config_leak']:
                config_leaks.extend(violations['config_leak'])
    
    # Test for hardcoded values
    import re
    patterns = [
        (r'["\']http://localhost:\d+', 'hardcoded localhost URL'),
        (r'api_key\s*=\s*["\'][^"\']+["\']', 'hardcoded API key'),
    ]
    
    for root, dirs, files in os.walk(project_root):
        if 'venv' in root or '__pycache__' in root or 'test' in root:
            continue
            
        for filename in files:  # Process all files
            if not filename.endswith('.py') or 'config' in filename:
                continue
                
            filepath = os.path.join(root, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern, description in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            hardcoded_values.append({
                                'file': filepath,
                                'type': description
                            })
            except:
                continue
    
    print(f"\nTest Results:")
    
    if cross_service_violations:
        print(f"  [X] Cross-service violations: {len(cross_service_violations)}")
        for v in cross_service_violations[:3]:
            print(f"     - {v['from_service']} -> {v['to_service']}: {v['import']}")
    else:
        print("  [OK] PASSED: No cross-service configuration violations")
    
    if config_leaks:
        print(f"  [X] Config leaks: {len(config_leaks)}")
    else:
        print("  [OK] PASSED: No configuration leaks detected")
    
    if hardcoded_values:
        print(f"  [!] WARNING: Found {len(hardcoded_values)} hardcoded values")
        for h in hardcoded_values[:3]:
            print(f"     - {h['file']}: {h['type']}")
    else:
        print("  [OK] PASSED: No hardcoded configuration values")
    
    return len(cross_service_violations) == 0 and len(config_leaks) == 0


def main():
    """Run all configuration validation test suites."""
    print("\n" + "="*80)
    print("CONFIGURATION VALIDATION TEST RUNNER")
    print("="*80)
    print("\nThis tool validates that:")
    print("1. All modules use the central configuration system")
    print("2. No direct os.environ calls exist outside central config")
    print("3. Configuration is properly isolated between services")
    print("\nViolations must be @marked with justification to be allowed.")
    
    results = {
        'Central Config Usage': run_central_config_tests(),
        'OS Environ Access': run_os_environ_tests(),
        'Config Isolation': run_isolation_tests()
    }
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "[OK] PASSED" if passed else "[X] FAILED"
        print(f"{test_name}: {status}")
    
    if all_passed:
        print("\n[SUCCESS] All configuration validation tests passed!")
    else:
        print("\n[WARNING] Some tests failed. Review violations and add @marked justifications where appropriate.")
        print("\nExample justification:")
        print("  # @marked: Bootstrap-only env access required for initial config")
        print("  value = os.environ.get('STARTUP_KEY')")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())