#!/usr/bin/env python3
"""
SSOT Compliance Checker for ID Generation Patterns

This script addresses the Five Whys root cause by implementing systematic
validation of ID generation patterns across the entire codebase.

Root Cause Addressed:
- Inadequate change management during SSOT consolidation 
- Missing API contract enforcement
- Runtime failures instead of compile-time detection

Usage:
    python scripts/check_id_generation_ssot_compliance.py
    python scripts/check_id_generation_ssot_compliance.py --fix
"""

import ast
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.core.id_generation_contracts import validate_id_generation_contracts


@dataclass
class IDUsageViolation:
    """Represents a violation of SSOT ID generation patterns"""
    file_path: str
    line_number: int
    code_line: str
    violation_type: str
    description: str
    suggested_fix: str


class IDGenerationSSotChecker:
    """Checks SSOT compliance for ID generation across the codebase"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations: List[IDUsageViolation] = []
        self.checked_files = 0
        self.logger = logging.getLogger(__name__)
        
        # Patterns that violate SSOT
        self.anti_patterns = {
            'direct_uuid_usage': {
                'patterns': ['uuid.uuid4()', 'str(uuid.uuid4())'],
                'description': 'Direct UUID usage instead of UnifiedIDManager',
                'fix_template': 'Use get_id_manager().generate_id(IDType.{id_type}) instead'
            },
            'hardcoded_id_generation': {
                'patterns': ['f"thread_{', 'f"user_{', 'f"session_{', 'f"agent_{'],
                'description': 'Hardcoded ID string formatting instead of SSOT',
                'fix_template': 'Use UnifiedIDManager.generate_id() with proper IDType'
            },
            'deprecated_id_methods': {
                'patterns': ['generate_unique_id()', 'create_thread_id()', 'make_user_id()'],
                'description': 'Deprecated ID generation methods',
                'fix_template': 'Replace with UnifiedIDManager patterns'
            }
        }
        
        # SSOT compliant patterns (these are OK)
        self.compliant_patterns = {
            'get_id_manager().generate_id(',
            'UnifiedIDManager.generate_thread_id(',
            'UnifiedIDManager.generate_run_id(',
            'generate_thread_id()',  # Module-level convenience function
            'generate_user_id()',
            'generate_session_id()',
            'IDType.'
        }
        
    def check_codebase(self) -> Dict[str, Any]:
        """Check entire codebase for SSOT compliance"""
        self.logger.info("Starting SSOT compliance check for ID generation...")
        
        results = {
            'contract_validation': self._validate_contracts(),
            'code_violations': self._scan_code_violations(),
            'summary': {
                'total_files_checked': self.checked_files,
                'total_violations': len(self.violations),
                'contracts_valid': True,
                'compliance_score': 0.0
            }
        }
        
        # Calculate compliance score
        if self.checked_files > 0:
            results['summary']['compliance_score'] = max(0.0, 
                1.0 - (len(self.violations) / (self.checked_files * 2)))  # Penalize violations
        
        results['summary']['contracts_valid'] = results['contract_validation']['valid']
        
        return results
    
    def _validate_contracts(self) -> Dict[str, Any]:
        """Validate ID generation contracts"""
        self.logger.info("Validating ID generation contracts...")
        return validate_id_generation_contracts()
    
    def _scan_code_violations(self) -> List[IDUsageViolation]:
        """Scan codebase for SSOT violations"""
        self.logger.info("Scanning code for SSOT violations...")
        
        # Scan Python files
        python_files = self._find_python_files()
        
        for file_path in python_files:
            self._check_file(file_path)
        
        return self.violations
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files to check"""
        python_files = []
        
        # Define directories to scan
        scan_dirs = [
            'netra_backend',
            'auth_service', 
            'tests',
            'scripts'
        ]
        
        for scan_dir in scan_dirs:
            dir_path = self.project_root / scan_dir
            if dir_path.exists():
                for py_file in dir_path.rglob('*.py'):
                    # Skip __pycache__ and other generated files
                    if '__pycache__' not in str(py_file):
                        python_files.append(py_file)
        
        self.logger.info(f"Found {len(python_files)} Python files to scan")
        return python_files
    
    def _check_file(self, file_path: Path):
        """Check a single file for violations"""
        try:
            self.checked_files += 1
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST for detailed analysis
            try:
                tree = ast.parse(content)
                self._analyze_ast(tree, file_path, content)
            except SyntaxError:
                # If AST parsing fails, do text-based analysis
                self._analyze_text(content, file_path)
                
        except Exception as e:
            self.logger.warning(f"Error checking file {file_path}: {e}")
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path, content: str):
        """Analyze AST for ID generation patterns"""
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            # Check function calls
            if isinstance(node, ast.Call):
                self._check_function_call(node, file_path, lines)
            
            # Check string formatting
            elif isinstance(node, ast.JoinedStr):  # f-strings
                self._check_fstring(node, file_path, lines)
    
    def _analyze_text(self, content: str, file_path: Path):
        """Text-based analysis for patterns"""
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            # Check for anti-patterns
            for pattern_type, pattern_info in self.anti_patterns.items():
                for pattern in pattern_info['patterns']:
                    if pattern in line:
                        # Check if it's already using a compliant pattern
                        if any(compliant in line for compliant in self.compliant_patterns):
                            continue
                        
                        violation = IDUsageViolation(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            code_line=line.strip(),
                            violation_type=pattern_type,
                            description=pattern_info['description'],
                            suggested_fix=pattern_info['fix_template']
                        )
                        self.violations.append(violation)
    
    def _check_function_call(self, node: ast.Call, file_path: Path, lines: List[str]):
        """Check function calls for anti-patterns"""
        try:
            # Get function name
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    func_name = f"{node.func.value.id}.{node.func.attr}"
            
            if func_name:
                # Check for direct UUID usage
                if func_name in ['uuid4', 'uuid.uuid4']:
                    line_num = getattr(node, 'lineno', 0)
                    if line_num <= len(lines):
                        code_line = lines[line_num - 1].strip()
                        
                        # Skip if already using compliant patterns
                        if any(compliant in code_line for compliant in self.compliant_patterns):
                            return
                        
                        violation = IDUsageViolation(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            code_line=code_line,
                            violation_type='direct_uuid_usage',
                            description='Direct UUID usage instead of UnifiedIDManager',
                            suggested_fix='Use get_id_manager().generate_id(IDType.THREAD) or appropriate type'
                        )
                        self.violations.append(violation)
                        
        except Exception as e:
            self.logger.debug(f"Error analyzing function call: {e}")
    
    def _check_fstring(self, node: ast.JoinedStr, file_path: Path, lines: List[str]):
        """Check f-strings for hardcoded ID patterns"""
        try:
            line_num = getattr(node, 'lineno', 0)
            if line_num <= len(lines):
                code_line = lines[line_num - 1].strip()
                
                # Check for hardcoded ID prefixes in f-strings
                id_prefixes = ['thread_', 'user_', 'session_', 'agent_', 'run_']
                for prefix in id_prefixes:
                    if f'f"{prefix}' in code_line or f"f'{prefix}" in code_line:
                        # Skip if using compliant patterns
                        if any(compliant in code_line for compliant in self.compliant_patterns):
                            continue
                        
                        violation = IDUsageViolation(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            code_line=code_line,
                            violation_type='hardcoded_id_generation',
                            description=f'Hardcoded {prefix} ID formatting instead of SSOT',
                            suggested_fix=f'Use UnifiedIDManager with IDType for {prefix.rstrip("_")} IDs'
                        )
                        self.violations.append(violation)
                        
        except Exception as e:
            self.logger.debug(f"Error analyzing f-string: {e}")
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable report"""
        report = []
        
        report.append("=" * 80)
        report.append("SSOT COMPLIANCE REPORT - ID GENERATION PATTERNS")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        summary = results['summary']
        report.append(f"📊 SUMMARY:")
        report.append(f"  • Files Checked: {summary['total_files_checked']}")
        report.append(f"  • Violations Found: {summary['total_violations']}")
        report.append(f"  • Compliance Score: {summary['compliance_score']:.2%}")
        report.append(f"  • Contract Validation: {'✅ PASS' if summary['contracts_valid'] else '❌ FAIL'}")
        report.append("")
        
        # Contract validation details
        contract_results = results['contract_validation']
        if not contract_results['valid']:
            report.append("🚨 CONTRACT VALIDATION FAILURES:")
            for missing in contract_results.get('missing_methods', []):
                report.append(f"  • Missing: {missing}")
            for mismatch in contract_results.get('signature_mismatches', []):
                report.append(f"  • Signature: {mismatch}")
            report.append("")
        
        # Violations by type
        if self.violations:
            violations_by_type = {}
            for violation in self.violations:
                if violation.violation_type not in violations_by_type:
                    violations_by_type[violation.violation_type] = []
                violations_by_type[violation.violation_type].append(violation)
            
            report.append("🔍 VIOLATIONS BY TYPE:")
            for violation_type, violations in violations_by_type.items():
                report.append(f"\n  📋 {violation_type.replace('_', ' ').title()} ({len(violations)} violations):")
                for violation in violations[:5]:  # Show first 5 of each type
                    report.append(f"    📄 {violation.file_path}:{violation.line_number}")
                    report.append(f"       Code: {violation.code_line}")
                    report.append(f"       Fix: {violation.suggested_fix}")
                    report.append("")
                
                if len(violations) > 5:
                    report.append(f"    ... and {len(violations) - 5} more violations of this type")
                    report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS:")
        if summary['compliance_score'] < 0.8:
            report.append("  🔧 CRITICAL: Multiple SSOT violations detected")
            report.append("     • Run with --fix to auto-fix simple violations")
            report.append("     • Manually review complex ID generation patterns")
            report.append("     • Add contract validation to CI/CD pipeline")
        elif summary['compliance_score'] < 0.95:
            report.append("  ⚠️  MODERATE: Some violations need attention")
            report.append("     • Address remaining violations for full compliance")
        else:
            report.append("  ✅ GOOD: High compliance score achieved")
            report.append("     • Consider adding this check to pre-commit hooks")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main entry point for SSOT compliance checker"""
    parser = argparse.ArgumentParser(
        description="Check SSOT compliance for ID generation patterns"
    )
    parser.add_argument(
        '--fix', action='store_true',
        help='Attempt to auto-fix simple violations'
    )
    parser.add_argument(
        '--output', type=str,
        help='Output report to file'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run compliance check
    checker = IDGenerationSSotChecker(project_root)
    results = checker.check_codebase()
    
    # Generate report
    report = checker.generate_report(results)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)
    
    # Auto-fix if requested
    if args.fix:
        print("🔧 Auto-fix functionality not yet implemented")
        print("   Manual fixes required for SSOT compliance")
    
    # Exit code based on compliance
    if not results['summary']['contracts_valid']:
        sys.exit(2)  # Contract failures
    elif results['summary']['total_violations'] > 0:
        sys.exit(1)  # Violations found
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    main()