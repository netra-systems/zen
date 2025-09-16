#!/usr/bin/env python3
"""
Inline Import Validation for Netra Apex System

This script performs comprehensive import validation without requiring external command execution.
It directly tests imports, identifies failures, and generates a detailed report.

Created to address Issue #1176: Python command execution restrictions in Claude Code.
"""

import sys
import importlib.util
from pathlib import Path
from typing import List, Tuple, Dict, Any
import traceback
import os
from datetime import datetime


class InlineImportValidator:
    """Comprehensive import validation without external dependencies."""

    def __init__(self, base_path: str = None):
        """Initialize the validator with the project root path."""
        if base_path is None:
            self.base_path = Path(__file__).parent
        else:
            self.base_path = Path(base_path)

        self.results = {
            'total_modules': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'failures': [],
            'critical_modules': {},
            'warnings': []
        }

    def get_python_modules(self, service_dir: str) -> List[Tuple[str, Path]]:
        """Find all Python modules in a specific service directory.

        Args:
            service_dir: The service directory name (e.g., 'netra_backend', 'auth_service')

        Returns:
            List of tuples containing (module_name, file_path)
        """
        modules = []
        service_path = self.base_path / service_dir

        if not service_path.exists():
            self.results['warnings'].append(f"Service directory {service_dir} not found")
            return modules

        # Find all Python files
        for py_file in service_path.rglob('*.py'):
            # Skip test files, __pycache__, and migration files
            path_str = str(py_file)
            if any(skip in path_str for skip in [
                '__pycache__',
                '/tests/',
                '\\tests\\',
                '/migrations/',
                '\\migrations\\',
                'test_',
                '_test.py',
                'conftest.py',
                'setup.py',
                'inline_import_validator.py'  # Skip this file
            ]):
                continue

            # Convert file path to module name
            try:
                relative_path = py_file.relative_to(self.base_path)
                module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
                module_name = '.'.join(module_parts)
                modules.append((module_name, py_file))
            except ValueError:
                # File is outside base path
                continue

        return modules

    def test_module_import(self, module_name: str, file_path: Path) -> Tuple[bool, str]:
        """Test importing a single module.

        Args:
            module_name: The fully qualified module name
            file_path: The path to the Python file

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        # Clean up any cached imports
        modules_to_clean = [name for name in sys.modules.keys() if name.startswith(module_name)]
        for mod_name in modules_to_clean:
            del sys.modules[mod_name]

        try:
            # Create module spec
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None:
                return False, f"Could not create module spec for {module_name}"

            # Create module and add to sys.modules
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module

            # Execute the module (where import errors occur)
            spec.loader.exec_module(module)

            return True, ""

        except ImportError as e:
            return False, f"ImportError: {e}"
        except SyntaxError as e:
            return False, f"SyntaxError: {e}"
        except ModuleNotFoundError as e:
            return False, f"ModuleNotFoundError: {e}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
        finally:
            # Clean up sys.modules
            modules_to_clean = [name for name in sys.modules.keys() if name.startswith(module_name)]
            for mod_name in modules_to_clean:
                if mod_name in sys.modules:
                    del sys.modules[mod_name]

    def validate_critical_modules(self) -> Dict[str, Any]:
        """Test critical modules that are essential for system operation."""
        critical_results = {}

        critical_modules = [
            'netra_backend.app.config',
            'netra_backend.app.core.configuration.base',
            'netra_backend.app.websocket_core.manager',
            'netra_backend.app.agents.supervisor_agent_modern',
            'netra_backend.app.db.database_manager',
            'netra_backend.app.auth_integration.auth',
            'shared.isolated_environment',
            'shared.cors_config'
        ]

        for module_name in critical_modules:
            # Convert module name to file path
            path_parts = module_name.split('.')
            possible_paths = [
                self.base_path / '/'.join(path_parts[:-1]) / f"{path_parts[-1]}.py",
                self.base_path / '/'.join(path_parts) / '__init__.py'
            ]

            module_path = None
            for path in possible_paths:
                if path.exists():
                    module_path = path
                    break

            if module_path is None:
                critical_results[module_name] = {
                    'status': 'not_found',
                    'error': 'Module file not found'
                }
                continue

            success, error = self.test_module_import(module_name, module_path)
            critical_results[module_name] = {
                'status': 'success' if success else 'failed',
                'error': error if not success else None,
                'path': str(module_path)
            }

        return critical_results

    def validate_service(self, service_name: str) -> None:
        """Validate all modules in a specific service."""
        print(f"\n=== Validating {service_name} ===")

        modules = self.get_python_modules(service_name)
        if not modules:
            print(f"No modules found in {service_name}")
            return

        print(f"Found {len(modules)} modules to validate")

        service_failures = []
        service_successes = 0

        for module_name, file_path in modules:
            success, error = self.test_module_import(module_name, file_path)

            if success:
                print(f"[✓] {module_name}")
                service_successes += 1
            else:
                print(f"[✗] {module_name}: {error}")
                service_failures.append({
                    'module': module_name,
                    'path': str(file_path),
                    'error': error
                })

        # Update global results
        self.results['total_modules'] += len(modules)
        self.results['successful_imports'] += service_successes
        self.results['failed_imports'] += len(service_failures)
        self.results['failures'].extend(service_failures)

        print(f"\n{service_name} Results: {service_successes}/{len(modules)} modules imported successfully")
        if service_failures:
            print(f"Failed imports: {len(service_failures)}")

    def run_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation across all services."""
        print("🔍 Netra Apex Import Validation")
        print("=" * 50)
        print(f"Base path: {self.base_path}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        # Validate critical modules first
        print("\n🚨 CRITICAL MODULES VALIDATION")
        self.results['critical_modules'] = self.validate_critical_modules()

        for module_name, result in self.results['critical_modules'].items():
            status_icon = "✓" if result['status'] == 'success' else "✗"
            print(f"[{status_icon}] {module_name}: {result['status']}")
            if result['error']:
                print(f"    Error: {result['error']}")

        # Validate all services
        services = ['netra_backend', 'auth_service', 'shared', 'frontend']

        for service in services:
            if (self.base_path / service).exists():
                self.validate_service(service)

        return self.results

    def generate_report(self) -> str:
        """Generate a comprehensive validation report."""
        report = []
        report.append("# Netra Apex Import Validation Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        # Summary
        total = self.results['total_modules']
        success = self.results['successful_imports']
        failed = self.results['failed_imports']
        success_rate = (success / total * 100) if total > 0 else 0

        report.append("## Summary")
        report.append(f"- Total modules: {total}")
        report.append(f"- Successful imports: {success}")
        report.append(f"- Failed imports: {failed}")
        report.append(f"- Success rate: {success_rate:.1f}%")
        report.append("")

        # Critical modules
        report.append("## Critical Modules Status")
        critical_failed = 0
        for module_name, result in self.results['critical_modules'].items():
            status = "✓ PASS" if result['status'] == 'success' else "✗ FAIL"
            report.append(f"- {module_name}: {status}")
            if result['error']:
                report.append(f"  Error: {result['error']}")
            if result['status'] != 'success':
                critical_failed += 1
        report.append("")

        # Failed imports
        if self.results['failures']:
            report.append("## Failed Imports")
            for failure in self.results['failures']:
                report.append(f"### {failure['module']}")
                report.append(f"Path: `{failure['path']}`")
                report.append(f"Error: {failure['error']}")
                report.append("")

        # Warnings
        if self.results['warnings']:
            report.append("## Warnings")
            for warning in self.results['warnings']:
                report.append(f"- {warning}")
            report.append("")

        # Recommendations
        report.append("## Recommendations")
        if critical_failed > 0:
            report.append("🚨 **CRITICAL**: System has critical module failures that will prevent startup")
        elif failed > 0:
            report.append("⚠️ **WARNING**: Some modules failed to import - may cause runtime issues")
        else:
            report.append("✅ **SUCCESS**: All modules imported successfully")

        return "\n".join(report)


def main():
    """Main execution function."""
    print("Starting Netra Apex Import Validation...")

    # Initialize validator
    validator = InlineImportValidator()

    # Run validation
    results = validator.run_validation()

    # Generate and display report
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    report = validator.generate_report()
    print(report)

    # Write report to file
    report_path = validator.base_path / "import_validation_report.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\nDetailed report saved to: {report_path}")

    # Exit with appropriate code
    if results['failed_imports'] > 0:
        critical_failures = sum(1 for result in results['critical_modules'].values()
                              if result['status'] != 'success')
        if critical_failures > 0:
            print("\n🚨 CRITICAL FAILURES DETECTED - System will not start properly")
            return 1
        else:
            print("\n⚠️ Non-critical import failures detected")
            return 2
    else:
        print("\n✅ All imports successful!")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)