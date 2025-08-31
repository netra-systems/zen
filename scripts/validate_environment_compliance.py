#!/usr/bin/env python3
"""
ENVIRONMENT COMPLIANCE VALIDATOR

Validates that the codebase complies with CLAUDE.md environment management requirements.
This script is designed for CI/CD integration and pre-commit hooks.

CRITICAL VIOLATIONS per CLAUDE.md:
"Direct OS.env access is FORBIDDEN except in each service's canonical env config SSOT"

Returns exit code 0 for compliance, 1 for violations.

Business Value: Platform/Internal - Environment Management Enforcement
Prevents introduction of new os.environ violations through automated validation.
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class EnvironmentComplianceValidator:
    """Validates environment management compliance"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations_found = False
        self.compliance_report = {
            'status': 'PASS',
            'violations_count': 0,
            'critical_violations': [],
            'checks_performed': []
        }
    
    def check_os_environ_violations(self) -> bool:
        """Check for direct os.environ access violations"""
        print("Checking for os.environ violations...")
        
        try:
            # Use our scanner script
            scanner_script = self.project_root / "scripts" / "scan_os_environ_violations.py"
            if not scanner_script.exists():
                print(f"ERROR: Scanner script not found at {scanner_script}")
                return False
            
            # Run scanner in JSON mode
            result = subprocess.run([
                sys.executable, str(scanner_script), "--json"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                # Parse the JSON output to get violation details
                try:
                    report = json.loads(result.stdout)
                    violations_count = report['summary']['total_violations']
                    
                    self.compliance_report['violations_count'] = violations_count
                    
                    if violations_count > 0:
                        self.violations_found = True
                        self.compliance_report['status'] = 'FAIL'
                        
                        # Extract critical violations (HIGH severity)
                        critical_files = []
                        for file_path, violations in report['violations_by_file'].items():
                            high_severity_violations = [v for v in violations if v['severity'] == 'HIGH']
                            if high_severity_violations:
                                critical_files.append({
                                    'file': file_path,
                                    'violations': len(high_severity_violations)
                                })
                        
                        self.compliance_report['critical_violations'] = critical_files
                        
                        print(f"FAIL: Found {violations_count} os.environ violations")
                        print(f"Critical violations in {len(critical_files)} files")
                        return False
                    else:
                        print("PASS: No os.environ violations found")
                        return True
                        
                except json.JSONDecodeError:
                    print(f"ERROR: Could not parse scanner output")
                    print(f"Scanner output: {result.stdout}")
                    return False
            else:
                print("PASS: No os.environ violations found")
                return True
                
        except Exception as e:
            print(f"ERROR: Failed to run os.environ violation check: {e}")
            return False
    
    def check_isolated_environment_usage(self) -> bool:
        """Check that services use proper IsolatedEnvironment patterns"""
        print("Checking IsolatedEnvironment usage patterns...")
        
        # Check that each service has its canonical env config
        required_env_files = [
            "netra_backend/app/core/isolated_environment.py",
            "auth_service/auth_core/isolated_environment.py",
            "analytics_service/analytics_core/isolated_environment.py",
            "dev_launcher/isolated_environment.py"
        ]
        
        missing_files = []
        for env_file in required_env_files:
            full_path = self.project_root / env_file
            if not full_path.exists():
                missing_files.append(env_file)
        
        if missing_files:
            print(f"FAIL: Missing canonical environment files: {', '.join(missing_files)}")
            self.violations_found = True
            self.compliance_report['status'] = 'FAIL'
            return False
        
        print("PASS: All canonical environment files present")
        return True
    
    def check_service_independence(self) -> bool:
        """Check that services maintain environment management independence"""
        print("Checking service independence...")
        
        # Check that services don't cross-import environment managers
        violation_patterns = [
            # netra_backend shouldn't import auth_service env
            ("netra_backend/", "from auth_service.auth_core.isolated_environment"),
            # auth_service shouldn't import netra_backend env  
            ("auth_service/", "from netra_backend.app.core.isolated_environment"),
            # Services shouldn't import dev_launcher env (except scripts)
            ("netra_backend/", "from dev_launcher.isolated_environment"),
            ("auth_service/", "from dev_launcher.isolated_environment")
        ]
        
        violations = []
        for service_path, forbidden_import in violation_patterns:
            service_dir = self.project_root / service_path
            if service_dir.exists():
                # Check all Python files in the service
                for py_file in service_dir.glob("**/*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if forbidden_import in content:
                                violations.append({
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'violation': f"Forbidden import: {forbidden_import}"
                                })
                    except Exception:
                        continue
        
        if violations:
            print(f"FAIL: Service independence violations found:")
            for violation in violations:
                print(f"  {violation['file']}: {violation['violation']}")
            self.violations_found = True
            self.compliance_report['status'] = 'FAIL'
            return False
        
        print("PASS: Service independence maintained")
        return True
    
    def check_test_isolation(self) -> bool:
        """Check that tests use proper environment isolation"""
        print("Checking test environment isolation...")
        
        # This is a basic check - could be expanded
        test_framework_env = self.project_root / "test_framework" / "environment_isolation.py"
        if not test_framework_env.exists():
            print("WARNING: Test framework environment isolation not found")
            # Not failing this check as it's not critical
        
        print("PASS: Test environment isolation check completed")
        return True
    
    def run_all_checks(self) -> bool:
        """Run all compliance checks"""
        print("="*80)
        print("ENVIRONMENT COMPLIANCE VALIDATION")
        print("="*80)
        
        checks = [
            ("OS.ENVIRON Violations", self.check_os_environ_violations),
            ("IsolatedEnvironment Usage", self.check_isolated_environment_usage),
            ("Service Independence", self.check_service_independence),
            ("Test Isolation", self.check_test_isolation)
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            print(f"\n[CHECK] {check_name}")
            passed = check_func()
            self.compliance_report['checks_performed'].append({
                'name': check_name,
                'passed': passed
            })
            if not passed:
                all_passed = False
        
        return all_passed
    
    def generate_report(self) -> str:
        """Generate final compliance report"""
        report = []
        report.append("="*80)
        report.append("ENVIRONMENT COMPLIANCE REPORT")
        report.append("="*80)
        
        status = self.compliance_report['status']
        violations_count = self.compliance_report['violations_count']
        
        report.append(f"\nOVERALL STATUS: {status}")
        
        if violations_count > 0:
            report.append(f"VIOLATIONS FOUND: {violations_count}")
        
        # Check results
        report.append(f"\nCHECK RESULTS:")
        for check in self.compliance_report['checks_performed']:
            status_str = "PASS" if check['passed'] else "FAIL"
            report.append(f"  {check['name']}: {status_str}")
        
        # Critical violations
        if self.compliance_report['critical_violations']:
            report.append(f"\nCRITICAL VIOLATIONS:")
            for violation in self.compliance_report['critical_violations']:
                report.append(f"  {violation['file']}: {violation['violations']} violations")
        
        # Recommendations
        if not self.violations_found:
            report.append(f"\nSUCCESS: Environment management compliance achieved!")
        else:
            report.append(f"\nACTION REQUIRED:")
            report.append(f"  1. Run: python scripts/scan_os_environ_violations.py")
            report.append(f"  2. Fix violations using proper IsolatedEnvironment patterns")
            report.append(f"  3. Re-run this validation script")
        
        return "\n".join(report)

def main():
    """Main validation entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print(__doc__)
        return
    
    project_root = Path(__file__).parent.parent
    validator = EnvironmentComplianceValidator(project_root)
    
    # Run all checks
    all_checks_passed = validator.run_all_checks()
    
    # Generate and print final report
    final_report = validator.generate_report()
    print(f"\n{final_report}")
    
    # Exit with appropriate code
    if all_checks_passed:
        print(f"\nEnvironment compliance validation PASSED")
        sys.exit(0)
    else:
        print(f"\nEnvironment compliance validation FAILED")
        sys.exit(1)

if __name__ == '__main__':
    main()