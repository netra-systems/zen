#!/usr/bin/env python3
"""
Unified Import Management System for Netra Backend

This script provides a centralized interface for all import-related operations:
- Checking import compliance
- Fixing import issues automatically
- Pre-commit hook integration
- Comprehensive reporting

Usage:
    python scripts/unified_import_manager.py check      # Check compliance only
    python scripts/unified_import_manager.py fix       # Fix issues automatically
    python scripts/unified_import_manager.py report    # Generate detailed report
    python scripts/unified_import_manager.py all       # Check, fix, and report
    python scripts/unified_import_manager.py precommit # Pre-commit hook mode
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import existing fixers
from scripts.fix_netra_backend_imports import ImportFixer as BackendImportFixer
from scripts.align_test_imports import TestImportAligner
from scripts.check_netra_backend_imports import ImportAnalyzer
from scripts.fix_import_issues import (
    fix_validate_token_imports,
    fix_websockets_import, 
    fix_connection_manager_specs
)

@dataclass
class ImportCheckResult:
    """Result of an import check operation."""
    component: str
    files_checked: int
    issues_found: int
    issues_fixed: int
    errors: List[str]
    warnings: List[str]
    status: str  # "success", "issues_found", "issues_fixed", "error"

@dataclass
class UnifiedImportReport:
    """Comprehensive import management report."""
    timestamp: str
    mode: str
    overall_status: str
    summary: Dict[str, int]
    component_results: List[ImportCheckResult]
    recommendations: List[str]
    
class UnifiedImportManager:
    """Centralized import management system."""
    
    def __init__(self, project_root: Path, dry_run: bool = False, verbose: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.verbose = verbose
        self.results: List[ImportCheckResult] = []
        
        # Configure logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Component paths
        self.backend_path = self.project_root / "netra_backend"
        self.test_framework_path = self.project_root / "test_framework"
        self.scripts_path = self.project_root / "scripts"
        
    def check_compliance(self) -> bool:
        """Check import compliance across all components."""
        self.logger.info("Starting comprehensive import compliance check...")
        
        overall_success = True
        
        # 1. Check backend imports
        backend_result = self._check_backend_imports()
        self.results.append(backend_result)
        if backend_result.status in ["issues_found", "error"]:
            overall_success = False
            
        # 2. Check test imports  
        test_result = self._check_test_imports()
        self.results.append(test_result)
        if test_result.status in ["issues_found", "error"]:
            overall_success = False
            
        # 3. Check specific import issues
        specific_result = self._check_specific_issues()
        self.results.append(specific_result)
        if specific_result.status in ["issues_found", "error"]:
            overall_success = False
            
        return overall_success
        
    def fix_all_imports(self) -> bool:
        """Fix all import issues across components."""
        self.logger.info("Starting comprehensive import fixing...")
        
        overall_success = True
        
        # 1. Fix backend imports
        backend_result = self._fix_backend_imports()
        self.results.append(backend_result)
        if backend_result.status == "error":
            overall_success = False
            
        # 2. Fix test imports
        test_result = self._fix_test_imports()
        self.results.append(test_result)
        if test_result.status == "error":
            overall_success = False
            
        # 3. Fix specific import issues
        specific_result = self._fix_specific_issues()
        self.results.append(specific_result)
        if specific_result.status == "error":
            overall_success = False
            
        return overall_success
        
    def _check_backend_imports(self) -> ImportCheckResult:
        """Check backend import compliance using existing analyzer."""
        self.logger.info("Checking backend imports...")
        
        try:
            analyzer = ImportAnalyzer(self.project_root)
            
            # Analyze app directory
            app_analyses = analyzer.analyze_directory(analyzer.app_path) if analyzer.app_path.exists() else {}
            
            # Analyze tests directory  
            tests_analyses = analyzer.analyze_directory(analyzer.tests_path) if analyzer.tests_path.exists() else {}
            
            all_analyses = {**app_analyses, **tests_analyses}
            
            files_checked = len(all_analyses)
            total_issues = sum(len(analysis.incorrect_imports) for analysis in all_analyses.values())
            
            errors = []
            warnings = []
            for analysis in all_analyses.values():
                errors.extend([f"Error in {Path(analysis.file_path).name}: {w}" for w in analysis.warnings if "Error" in w])
                warnings.extend([f"Warning in {Path(analysis.file_path).name}: {w}" for w in analysis.warnings if "Warning" in w])
            
            status = "success" if total_issues == 0 else "issues_found"
            
            return ImportCheckResult(
                component="backend",
                files_checked=files_checked,
                issues_found=total_issues,
                issues_fixed=0,
                errors=errors,
                warnings=warnings,
                status=status
            )
            
        except Exception as e:
            self.logger.error(f"Error checking backend imports: {e}")
            return ImportCheckResult(
                component="backend",
                files_checked=0,
                issues_found=0,
                issues_fixed=0,
                errors=[str(e)],
                warnings=[],
                status="error"
            )
            
    def _fix_backend_imports(self) -> ImportCheckResult:
        """Fix backend imports using existing fixer."""
        self.logger.info("Fixing backend imports...")
        
        try:
            fixer = BackendImportFixer(self.project_root, dry_run=self.dry_run)
            
            all_fixes = {}
            
            # Fix app directory
            if fixer.netra_backend_path.exists() and (fixer.netra_backend_path / "app").exists():
                app_fixes = fixer.fix_directory(fixer.netra_backend_path / "app")
                all_fixes.update(app_fixes)
                
            # Fix tests directory
            if fixer.netra_backend_path.exists() and (fixer.netra_backend_path / "tests").exists():
                tests_fixes = fixer.fix_directory(fixer.netra_backend_path / "tests")
                all_fixes.update(tests_fixes)
            
            files_fixed = len(all_fixes)
            total_fixes = sum(len(fixes) for fixes in all_fixes.values())
            
            status = "issues_fixed" if total_fixes > 0 else "success"
            
            return ImportCheckResult(
                component="backend",
                files_checked=files_fixed + fixer.files_fixed,  # Include files that were actually processed
                issues_found=total_fixes,
                issues_fixed=total_fixes if not self.dry_run else 0,
                errors=fixer.errors,
                warnings=[],
                status=status
            )
            
        except Exception as e:
            self.logger.error(f"Error fixing backend imports: {e}")
            return ImportCheckResult(
                component="backend",
                files_checked=0,
                issues_found=0,
                issues_fixed=0,
                errors=[str(e)],
                warnings=[],
                status="error"
            )
            
    def _check_test_imports(self) -> ImportCheckResult:
        """Check test import alignment (read-only analysis)."""
        self.logger.info("Checking test imports...")
        
        try:
            # We'll do a lightweight check by scanning test files for common issues
            test_files = []
            
            # Backend tests
            backend_tests = self.backend_path / "tests"
            if backend_tests.exists():
                test_files.extend(list(backend_tests.rglob("test_*.py")))
                test_files.extend(list(backend_tests.rglob("*_test.py")))
                
            # Test framework files
            if self.test_framework_path.exists():
                test_files.extend(list(self.test_framework_path.rglob("test_*.py")))
            
            issues_found = 0
            warnings = []
            
            for test_file in test_files:
                try:
                    content = test_file.read_text(encoding='utf-8')
                    
                    # Check for common issues
                    if 'from app.' in content and 'from netra_backend.app.' not in content:
                        issues_found += 1
                        
                    if 'from netra_backend.tests.' in content and 'from netra_backend.tests.' not in content:
                        issues_found += 1
                        
                    if 'from .. import' in content or 'from . import' in content:
                        warnings.append(f"Relative imports found in {test_file.name}")
                        
                except Exception as e:
                    warnings.append(f"Could not read {test_file.name}: {e}")
            
            status = "success" if issues_found == 0 else "issues_found"
            
            return ImportCheckResult(
                component="tests",
                files_checked=len(test_files),
                issues_found=issues_found,
                issues_fixed=0,
                errors=[],
                warnings=warnings,
                status=status
            )
            
        except Exception as e:
            self.logger.error(f"Error checking test imports: {e}")
            return ImportCheckResult(
                component="tests",
                files_checked=0,
                issues_found=0,
                issues_fixed=0,
                errors=[str(e)],
                warnings=[],
                status="error"
            )
            
    def _fix_test_imports(self) -> ImportCheckResult:
        """Fix test imports using existing aligner."""
        self.logger.info("Fixing test imports...")
        
        try:
            # Create a temporary aligner to capture its results
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            
            if not self.dry_run:
                aligner = TestImportAligner()
                aligner.run()
                
                # Extract results from aligner
                files_fixed = len(aligner.import_fixes) + len(aligner.config_fixes) + len(aligner.file_fixes)
                total_fixes = files_fixed
                
                return ImportCheckResult(
                    component="tests",
                    files_checked=files_fixed,
                    issues_found=total_fixes,
                    issues_fixed=total_fixes,
                    errors=[],
                    warnings=[],
                    status="issues_fixed" if total_fixes > 0 else "success"
                )
            else:
                # In dry run mode, just check what would be fixed
                test_result = self._check_test_imports()
                test_result.status = "issues_found" if test_result.issues_found > 0 else "success"
                return test_result
                
        except Exception as e:
            self.logger.error(f"Error fixing test imports: {e}")
            return ImportCheckResult(
                component="tests",
                files_checked=0,
                issues_found=0,
                issues_fixed=0,
                errors=[str(e)],
                warnings=[],
                status="error"
            )
            
    def _check_specific_issues(self) -> ImportCheckResult:
        """Check for specific import issues (validate_token, websockets, etc.)."""
        self.logger.info("Checking specific import issues...")
        
        try:
            issues_found = 0
            files_with_issues = []
            
            # Check for validate_token issues
            for pattern in ["netra_backend/**/*.py", "test_framework/**/*.py"]:
                for file_path in self.project_root.glob(pattern):
                    if file_path.is_file():
                        try:
                            content = file_path.read_text(encoding='utf-8')
                            
                            # Check for old validate_token import
                            if 'validate_token' in content and 'validate_token_jwt' not in content:
                                if 'from netra_backend.app.auth_integration.auth import' in content:
                                    issues_found += 1
                                    files_with_issues.append(str(file_path.relative_to(self.project_root)))
                                    
                            # Check for old websocket imports
                            if 'from netra_backend.app.routes.websockets import websocket_endpoint' in content:
                                issues_found += 1
                                files_with_issues.append(str(file_path.relative_to(self.project_root)))
                                
                        except Exception:
                            pass  # Skip files that can't be read
            
            status = "success" if issues_found == 0 else "issues_found"
            
            return ImportCheckResult(
                component="specific_issues",
                files_checked=len(files_with_issues),
                issues_found=issues_found,
                issues_fixed=0,
                errors=[],
                warnings=[f"Issues found in: {', '.join(files_with_issues[:5])}" + ("..." if len(files_with_issues) > 5 else "")],
                status=status
            )
            
        except Exception as e:
            self.logger.error(f"Error checking specific issues: {e}")
            return ImportCheckResult(
                component="specific_issues",
                files_checked=0,
                issues_found=0,
                issues_fixed=0,
                errors=[str(e)],
                warnings=[],
                status="error"
            )
            
    def _fix_specific_issues(self) -> ImportCheckResult:
        """Fix specific import issues using existing fixers."""
        self.logger.info("Fixing specific import issues...")
        
        try:
            fixed_files = []
            
            if not self.dry_run:
                # Fix validate_token imports
                for pattern in ["netra_backend/**/*.py", "test_framework/**/*.py", "SPEC/*.xml"]:
                    for file_path in self.project_root.glob(pattern):
                        if file_path.is_file():
                            if fix_validate_token_imports(str(file_path)):
                                fixed_files.append(f"validate_token: {file_path}")
                                
                # Fix websocket imports
                for pattern in ["netra_backend/**/*.py", "test_framework/**/*.py"]:
                    for file_path in self.project_root.glob(pattern):
                        if file_path.is_file():
                            if fix_websockets_import(str(file_path)):
                                fixed_files.append(f"websocket_endpoint: {file_path}")
                                
                # Fix connection manager specs
                for pattern in ["netra_backend/**/*.py", "test_framework/**/*.py"]:
                    for file_path in self.project_root.glob(pattern):
                        if file_path.is_file():
                            if fix_connection_manager_specs(str(file_path)):
                                fixed_files.append(f"ConnectionManager spec: {file_path}")
            
            total_fixes = len(fixed_files)
            status = "issues_fixed" if total_fixes > 0 else "success"
            
            return ImportCheckResult(
                component="specific_issues",
                files_checked=total_fixes,
                issues_found=total_fixes,
                issues_fixed=total_fixes if not self.dry_run else 0,
                errors=[],
                warnings=[],
                status=status
            )
            
        except Exception as e:
            self.logger.error(f"Error fixing specific issues: {e}")
            return ImportCheckResult(
                component="specific_issues",
                files_checked=0,
                issues_found=0,
                issues_fixed=0,
                errors=[str(e)],
                warnings=[],
                status="error"
            )
            
    def generate_report(self, mode: str = "check") -> UnifiedImportReport:
        """Generate comprehensive import management report."""
        total_files = sum(r.files_checked for r in self.results)
        total_issues = sum(r.issues_found for r in self.results)
        total_fixed = sum(r.issues_fixed for r in self.results)
        total_errors = sum(len(r.errors) for r in self.results)
        
        # Determine overall status
        if total_errors > 0:
            overall_status = "error"
        elif total_issues > 0 and mode == "check":
            overall_status = "issues_found"
        elif total_fixed > 0 and mode == "fix":
            overall_status = "issues_fixed"
        else:
            overall_status = "success"
            
        # Generate recommendations
        recommendations = []
        if overall_status == "issues_found":
            recommendations.append("Run 'python scripts/unified_import_manager.py fix' to automatically fix import issues")
        if any(r.component == "backend" and r.status == "issues_found" for r in self.results):
            recommendations.append("Focus on backend import patterns - ensure all imports use 'netra_backend.app.*' prefix")
        if any(r.component == "tests" and r.status == "issues_found" for r in self.results):
            recommendations.append("Review test imports - use 'netra_backend.tests.*' for test utilities")
        if total_errors > 0:
            recommendations.append("Review error details and fix any file access or parsing issues")
            
        return UnifiedImportReport(
            timestamp=datetime.now().isoformat(),
            mode=mode,
            overall_status=overall_status,
            summary={
                "files_checked": total_files,
                "issues_found": total_issues,
                "issues_fixed": total_fixed,
                "errors": total_errors
            },
            component_results=self.results,
            recommendations=recommendations
        )
        
    def save_report(self, report: UnifiedImportReport, output_path: Optional[Path] = None) -> Path:
        """Save report to JSON file."""
        if output_path is None:
            reports_dir = self.project_root / "test_reports"
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = reports_dir / f"unified_import_report_{timestamp}.json"
            
        # Convert dataclasses to dict for JSON serialization
        report_dict = asdict(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
        return output_path
        
    def print_report_summary(self, report: UnifiedImportReport):
        """Print a human-readable summary of the report."""
        print("\n" + "=" * 80)
        print("UNIFIED IMPORT MANAGEMENT REPORT")
        print("=" * 80)
        print(f"Mode: {report.mode.upper()}")
        print(f"Status: {report.overall_status.upper()}")
        print(f"Timestamp: {report.timestamp}")
        print()
        
        # Summary
        print("SUMMARY")
        print("-" * 40)
        print(f"Files checked: {report.summary['files_checked']}")
        print(f"Issues found: {report.summary['issues_found']}")
        print(f"Issues fixed: {report.summary['issues_fixed']}")
        print(f"Errors: {report.summary['errors']}")
        print()
        
        # Component details
        print("COMPONENT RESULTS")
        print("-" * 40)
        for result in report.component_results:
            status_icon = "[OK]" if result.status == "success" else "[WARN]" if result.status == "issues_found" else "[ERR]"
            print(f"{status_icon} {result.component.upper()}")
            print(f"  Files: {result.files_checked}, Issues: {result.issues_found}, Fixed: {result.issues_fixed}")
            
            if result.errors:
                print(f"  Errors: {len(result.errors)}")
                for error in result.errors[:2]:  # Show first 2 errors
                    print(f"    - {error}")
                if len(result.errors) > 2:
                    print(f"    ... and {len(result.errors) - 2} more")
                    
            if result.warnings:
                print(f"  Warnings: {len(result.warnings)}")
                for warning in result.warnings[:2]:  # Show first 2 warnings
                    print(f"    - {warning}")
                if len(result.warnings) > 2:
                    print(f"    ... and {len(result.warnings) - 2} more")
        print()
        
        # Recommendations
        if report.recommendations:
            print("RECOMMENDATIONS")
            print("-" * 40)
            for i, rec in enumerate(report.recommendations, 1):
                print(f"{i}. {rec}")
            print()
            
        # Success/failure message
        if report.overall_status == "success":
            print("[SUCCESS] All imports are compliant with Netra backend standards!")
        elif report.overall_status == "issues_fixed":
            print("[FIXED] Import issues have been automatically fixed!")
            print("        Run tests to ensure everything still works correctly.")
        elif report.overall_status == "issues_found":
            print("[WARNING] Import issues found. Run with 'fix' mode to resolve them.")
        else:
            print("[ERROR] Errors encountered during import management.")


def run_precommit_check() -> int:
    """Run import checks in pre-commit hook mode."""
    manager = UnifiedImportManager(PROJECT_ROOT, dry_run=True, verbose=False)
    
    # Only check compliance, don't fix
    success = manager.check_compliance()
    
    if not success:
        report = manager.generate_report("precommit")
        print("\n[ERROR] PRE-COMMIT: Import compliance violations found!")
        manager.print_report_summary(report)
        print("\nFix these issues before committing:")
        print("  python scripts/unified_import_manager.py fix")
        return 1
    
    print("[SUCCESS] PRE-COMMIT: All imports are compliant.")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Import Management System for Netra Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/unified_import_manager.py check        # Check compliance only
  python scripts/unified_import_manager.py fix         # Fix issues automatically  
  python scripts/unified_import_manager.py report      # Generate detailed report
  python scripts/unified_import_manager.py all         # Check, fix, and report
  python scripts/unified_import_manager.py precommit   # Pre-commit hook mode
        """
    )
    
    parser.add_argument(
        'command',
        choices=['check', 'fix', 'report', 'all', 'precommit'],
        help='Command to execute'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for report (JSON format)'
    )
    
    args = parser.parse_args()
    
    # Special handling for precommit
    if args.command == 'precommit':
        return run_precommit_check()
    
    # Verify project structure
    if not (PROJECT_ROOT / "netra_backend").exists():
        print("Error: netra_backend directory not found. Please run from project root.")
        return 1
    
    print(f"Unified Import Manager - {args.command.upper()} mode")
    print(f"Project root: {PROJECT_ROOT}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print()
    
    manager = UnifiedImportManager(PROJECT_ROOT, dry_run=args.dry_run, verbose=args.verbose)
    
    success = True
    
    # Execute commands
    if args.command in ['check', 'all']:
        success = manager.check_compliance()
        
    if args.command in ['fix', 'all'] and not args.dry_run:
        fix_success = manager.fix_all_imports()
        success = success and fix_success
        
    # Generate report
    mode = "fix" if args.command == "fix" else "check"
    report = manager.generate_report(mode)
    
    # Save report if requested
    if args.output:
        report_path = manager.save_report(report, args.output)
        print(f"Report saved to: {report_path}")
        
    if args.command in ['report', 'all']:
        # Always save report for these commands
        report_path = manager.save_report(report)
        print(f"Report saved to: {report_path}")
    
    # Print summary
    manager.print_report_summary(report)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())