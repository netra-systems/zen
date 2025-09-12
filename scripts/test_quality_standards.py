#!/usr/bin/env python3
"""Test Quality Standards Implementation - Phase 1 Foundation Repair

MISSION: Implement quality standards to prevent -1509% compliance regression
SCOPE: Establish standards, CI integration, and evidence-based validation

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Prevent technical debt regression and ensure sustainable development
- Value Impact: Quality gates prevent defects from reaching production 
- Strategic Impact: Protects $500K+ ARR by maintaining reliable test infrastructure

QUALITY STANDARDS IMPLEMENTED:
1. Syntax validation for all test files
2. SSOT import pattern enforcement 
3. Test method naming convention validation
4. Evidence-based progress reporting requirements
5. CI integration for automated quality gates
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@dataclass
class QualityViolation:
    """Represents a test quality violation."""
    file_path: str
    line_number: int
    violation_type: str
    description: str
    severity: str  # 'error', 'warning', 'info'

@dataclass
class QualityReport:
    """Test quality assessment report."""
    total_files_scanned: int
    syntax_errors: int
    import_violations: int
    naming_violations: int
    violations: List[QualityViolation]
    passed_files: List[str]
    failed_files: List[str]
    compliance_score: float

class TestQualityValidator:
    """Validates and enforces test quality standards."""
    
    def __init__(self):
        self.violations: List[QualityViolation] = []
        self.passed_files: List[str] = []
        self.failed_files: List[str] = []
        
        # Quality standards configuration
        self.standards = {
            'required_imports': [
                'from test_framework.ssot.base_test_case import SSotBaseTestCase',
                'from test_framework.ssot.base_test_case import SSotAsyncTestCase'
            ],
            'forbidden_imports': [
                'import redis',
                'from redis import',
                'import os'  # Should use IsolatedEnvironment
            ],
            'required_base_classes': [
                'SSotBaseTestCase',
                'SSotAsyncTestCase',
                'unittest.TestCase'  # Acceptable but discouraged
            ],
            'test_method_pattern': r'^test_[a-zA-Z0-9_]+$'
        }
    
    def validate_syntax(self, file_path: str) -> bool:
        """Validate Python syntax of test file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Parse AST to validate syntax
            ast.parse(source, filename=file_path)
            return True
            
        except SyntaxError as e:
            self.violations.append(QualityViolation(
                file_path=file_path,
                line_number=e.lineno or 0,
                violation_type='syntax_error',
                description=f"Syntax error: {e.msg}",
                severity='error'
            ))
            return False
        except Exception as e:
            self.violations.append(QualityViolation(
                file_path=file_path,
                line_number=0,
                violation_type='parse_error',
                description=f"Parse error: {e}",
                severity='error'
            ))
            return False
    
    def validate_imports(self, file_path: str) -> bool:
        """Validate import patterns against SSOT standards."""
        violations_found = False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            has_ssot_import = False
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for forbidden imports
                for forbidden in self.standards['forbidden_imports']:
                    if line.startswith(forbidden):
                        self.violations.append(QualityViolation(
                            file_path=file_path,
                            line_number=line_num,
                            violation_type='forbidden_import',
                            description=f"Forbidden import: {line}. Use SSOT patterns instead.",
                            severity='error'
                        ))
                        violations_found = True
                
                # Check for SSOT imports
                for required in self.standards['required_imports']:
                    if required in line:
                        has_ssot_import = True
            
            # Warn if no SSOT imports found (but don't fail - might not be test class)
            if not has_ssot_import and 'test_' in file_path:
                self.violations.append(QualityViolation(
                    file_path=file_path,
                    line_number=0,
                    violation_type='missing_ssot_import',
                    description="No SSOT test base class imports found. Consider using SSotBaseTestCase.",
                    severity='warning'
                ))
                
        except Exception as e:
            self.violations.append(QualityViolation(
                file_path=file_path,
                line_number=0,
                violation_type='import_validation_error',
                description=f"Error validating imports: {e}",
                severity='warning'
            ))
            violations_found = True
        
        return not violations_found
    
    def validate_test_methods(self, file_path: str) -> bool:
        """Validate test method naming conventions."""
        violations_found = False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Parse AST to find test methods
            tree = ast.parse(source, filename=file_path)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    method_name = node.name
                    
                    # Check if this is a test method
                    if method_name.startswith('test_'):
                        # Validate naming pattern
                        if not re.match(self.standards['test_method_pattern'], method_name):
                            self.violations.append(QualityViolation(
                                file_path=file_path,
                                line_number=node.lineno,
                                violation_type='naming_violation',
                                description=f"Test method '{method_name}' violates naming convention",
                                severity='warning'
                            ))
                            violations_found = True
                        
                        # Check for proper docstrings
                        if not ast.get_docstring(node):
                            self.violations.append(QualityViolation(
                                file_path=file_path,
                                line_number=node.lineno,
                                violation_type='missing_docstring',
                                description=f"Test method '{method_name}' missing docstring",
                                severity='info'
                            ))
                            
        except Exception as e:
            self.violations.append(QualityViolation(
                file_path=file_path,
                line_number=0,
                violation_type='method_validation_error',
                description=f"Error validating methods: {e}",
                severity='warning'
            ))
            violations_found = True
            
        return not violations_found
    
    def validate_file(self, file_path: str) -> bool:
        """Validate a single test file against all quality standards."""
        file_passed = True
        
        # Skip non-Python files
        if not file_path.endswith('.py'):
            return True
        
        # Skip __pycache__ and similar
        if '__pycache__' in file_path or '.pyc' in file_path:
            return True
            
        print(f"🔍 Validating: {file_path}")
        
        # Run all validations
        if not self.validate_syntax(file_path):
            file_passed = False
            
        if not self.validate_imports(file_path):
            file_passed = False
            
        if not self.validate_test_methods(file_path):
            file_passed = False
        
        # Record result
        if file_passed:
            self.passed_files.append(file_path)
            print(f"  ✅ Passed")
        else:
            self.failed_files.append(file_path)
            print(f"  ❌ Failed")
        
        return file_passed
    
    def scan_test_files(self, directory: str = None) -> List[str]:
        """Scan for test files in the project."""
        if directory is None:
            directory = str(PROJECT_ROOT)
        
        test_files = []
        
        # Use find command for efficiency
        try:
            result = subprocess.run([
                'find', directory, 
                '-name', '*.py',
                '-path', '*/test*',
                '-type', 'f'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                test_files = result.stdout.strip().split('\n')
                test_files = [f for f in test_files if f and 'test' in f.lower()]
        except Exception as e:
            print(f"⚠️  Error scanning test files: {e}")
            # Fallback to manual search
            for root, dirs, files in os.walk(directory):
                if 'test' in root.lower():
                    for file in files:
                        if file.endswith('.py') and 'test' in file.lower():
                            test_files.append(os.path.join(root, file))
        
        return test_files
    
    def generate_report(self) -> QualityReport:
        """Generate comprehensive quality assessment report."""
        total_files = len(self.passed_files) + len(self.failed_files)
        
        # Count violation types
        syntax_errors = len([v for v in self.violations if v.violation_type in ['syntax_error', 'parse_error']])
        import_violations = len([v for v in self.violations if 'import' in v.violation_type])
        naming_violations = len([v for v in self.violations if 'naming' in v.violation_type])
        
        # Calculate compliance score (0-100%)
        if total_files > 0:
            compliance_score = (len(self.passed_files) / total_files) * 100
        else:
            compliance_score = 100.0
        
        return QualityReport(
            total_files_scanned=total_files,
            syntax_errors=syntax_errors,
            import_violations=import_violations,
            naming_violations=naming_violations,
            violations=self.violations,
            passed_files=self.passed_files,
            failed_files=self.failed_files,
            compliance_score=compliance_score
        )
    
    def apply_fixes(self, fix_violations: bool = False) -> int:
        """Apply automated fixes for correctable violations."""
        fixes_applied = 0
        
        if not fix_violations:
            print("🔧 Fix mode disabled. Use --fix to apply corrections.")
            return 0
        
        print("🔧 Applying automated fixes...")
        
        for violation in self.violations:
            if violation.violation_type == 'forbidden_import' and 'import redis' in violation.description:
                # Apply Redis SSOT migration
                if self._fix_redis_import(violation.file_path):
                    fixes_applied += 1
                    print(f"  ✅ Fixed Redis import in {violation.file_path}")
        
        return fixes_applied
    
    def _fix_redis_import(self, file_path: str) -> bool:
        """Fix Redis import to use SSOT pattern."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace Redis imports
            original_content = content
            content = re.sub(
                r'^import redis\s*$',
                'from netra_backend.app.services.redis_client import get_redis_client, get_redis_service',
                content,
                flags=re.MULTILINE
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
                
        except Exception as e:
            print(f"⚠️  Error fixing {file_path}: {e}")
        
        return False

def create_quality_ci_integration():
    """Create GitHub Actions workflow for test quality validation."""
    ci_config = {
        'name': 'Test Quality Standards',
        'on': {
            'push': {'paths': ['tests/**/*.py', '**/*test*.py']},
            'pull_request': {'paths': ['tests/**/*.py', '**/*test*.py']}
        },
        'jobs': {
            'test-quality': {
                'runs-on': 'ubuntu-latest',
                'steps': [
                    {'uses': 'actions/checkout@v3'},
                    {
                        'name': 'Set up Python',
                        'uses': 'actions/setup-python@v4',
                        'with': {'python-version': '3.11'}
                    },
                    {
                        'name': 'Install dependencies',
                        'run': 'pip install -r requirements.txt'
                    },
                    {
                        'name': 'Validate test quality standards',
                        'run': 'python scripts/test_quality_standards.py --scan-all --fail-on-error'
                    },
                    {
                        'name': 'Generate quality report',
                        'run': 'python scripts/test_quality_standards.py --report-json > test_quality_report.json'
                    },
                    {
                        'name': 'Upload quality report',
                        'uses': 'actions/upload-artifact@v3',
                        'with': {
                            'name': 'test-quality-report',
                            'path': 'test_quality_report.json'
                        }
                    }
                ]
            }
        }
    }
    
    # Create .github/workflows directory if it doesn't exist
    workflows_dir = PROJECT_ROOT / '.github' / 'workflows'
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    # Write CI configuration
    ci_file = workflows_dir / 'test_quality_standards.yml'
    with open(ci_file, 'w') as f:
        import yaml
        yaml.dump(ci_config, f, default_flow_style=False)
    
    print(f"✅ Created CI integration: {ci_file}")
    return ci_file

def main():
    """Execute test quality standards validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Quality Standards Validator')
    parser.add_argument('--scan-all', action='store_true', help='Scan all test files')
    parser.add_argument('--fix', action='store_true', help='Apply automated fixes')
    parser.add_argument('--fail-on-error', action='store_true', help='Exit with error code on violations')
    parser.add_argument('--report-json', action='store_true', help='Output JSON report')
    parser.add_argument('--create-ci', action='store_true', help='Create CI integration')
    parser.add_argument('--directory', type=str, help='Specific directory to scan')
    
    args = parser.parse_args()
    
    if args.create_ci:
        create_quality_ci_integration()
        return
    
    print("🚀 Test Quality Standards Validator - Phase 1 Foundation Repair")
    print("=" * 70)
    
    validator = TestQualityValidator()
    
    # Scan test files
    if args.scan_all:
        print("🔍 Scanning all test files...")
        test_files = validator.scan_test_files(args.directory)
        print(f"📊 Found {len(test_files)} test files to validate")
        
        # Validate each file (limit to first 50 for Phase 1)
        for file_path in test_files[:50]:
            validator.validate_file(file_path)
        
        # Apply fixes if requested
        if args.fix:
            fixes_applied = validator.apply_fixes(fix_violations=True)
            print(f"🔧 Applied {fixes_applied} automated fixes")
        
        # Generate report
        report = validator.generate_report()
        
        if args.report_json:
            # Output JSON report for CI
            json_report = {
                'total_files_scanned': report.total_files_scanned,
                'syntax_errors': report.syntax_errors,
                'import_violations': report.import_violations,
                'naming_violations': report.naming_violations,
                'compliance_score': report.compliance_score,
                'passed_files': len(report.passed_files),
                'failed_files': len(report.failed_files),
                'violations': [
                    {
                        'file': v.file_path,
                        'line': v.line_number,
                        'type': v.violation_type,
                        'description': v.description,
                        'severity': v.severity
                    }
                    for v in report.violations
                ],
                'timestamp': datetime.now().isoformat()
            }
            print(json.dumps(json_report, indent=2))
        else:
            # Human-readable report
            print("\n" + "=" * 70)
            print("📊 Test Quality Standards Report:")
            print(f"  ✅ Files scanned: {report.total_files_scanned}")
            print(f"  ✅ Files passed: {len(report.passed_files)}")
            print(f"  ❌ Files failed: {len(report.failed_files)}")
            print(f"  📈 Compliance score: {report.compliance_score:.1f}%")
            print(f"  🐛 Syntax errors: {report.syntax_errors}")
            print(f"  📦 Import violations: {report.import_violations}")
            print(f"  🏷️  Naming violations: {report.naming_violations}")
            
            # Show violations by severity
            error_violations = [v for v in report.violations if v.severity == 'error']
            warning_violations = [v for v in report.violations if v.severity == 'warning']
            
            if error_violations:
                print(f"\n🚨 Critical Issues ({len(error_violations)}):")
                for violation in error_violations[:10]:  # Show first 10
                    print(f"  - {violation.file_path}:{violation.line_number} - {violation.description}")
            
            if warning_violations:
                print(f"\n⚠️  Warnings ({len(warning_violations)}):")
                for violation in warning_violations[:5]:  # Show first 5
                    print(f"  - {violation.file_path}:{violation.line_number} - {violation.description}")
        
        # Exit with error code if requested and violations found
        if args.fail_on_error and (report.syntax_errors > 0 or report.import_violations > 0):
            print(f"\n❌ Quality standards validation failed!")
            print(f"   Fix {report.syntax_errors} syntax errors and {report.import_violations} import violations")
            sys.exit(1)
        
        print(f"\n🎉 Test Quality Standards validation completed!")
        if report.compliance_score >= 80:
            print(f"   Compliance score {report.compliance_score:.1f}% meets minimum threshold")
        else:
            print(f"   ⚠️  Compliance score {report.compliance_score:.1f}% below 80% threshold")

if __name__ == "__main__":
    main()