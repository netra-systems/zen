"""
Import Testing Module for Fast-Fail Import Error Detection

This module provides comprehensive import testing with clear error reporting
to catch import issues early in the development cycle.
"""

import importlib
import json
import os
import pkgutil
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class ImportResult:
    """Result of an import test"""
    module_path: str
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    import_time: float = 0.0
    missing_dependencies: List[str] = field(default_factory=list)
    circular_imports: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'module_path': self.module_path,
            'success': self.success,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'traceback': self.traceback,
            'import_time': self.import_time,
            'missing_dependencies': self.missing_dependencies,
            'circular_imports': self.circular_imports
        }


@dataclass 
class ImportTestReport:
    """Complete import test report"""
    total_modules: int = 0
    successful_imports: int = 0
    failed_imports: int = 0
    results: List[ImportResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_time: float = 0.0
    
    def add_result(self, result: ImportResult):
        self.results.append(result)
        self.total_modules += 1
        if result.success:
            self.successful_imports += 1
        else:
            self.failed_imports += 1
    
    def get_summary(self) -> str:
        return f"""
Import Test Summary
===================
Total Modules: {self.total_modules}
Successful: {self.successful_imports}
Failed: {self.failed_imports}
Success Rate: {(self.successful_imports/self.total_modules*100 if self.total_modules > 0 else 0):.2f}%
Total Time: {self.total_time:.2f}s
"""

    def get_failures_report(self) -> str:
        if not any(not r.success for r in self.results):
            return "No import failures detected!"
        
        report = "\nImport Failures Report\n" + "="*50 + "\n\n"
        
        # Group by error type
        errors_by_type: Dict[str, List[ImportResult]] = {}
        for result in self.results:
            if not result.success:
                error_type = result.error_type or "Unknown"
                if error_type not in errors_by_type:
                    errors_by_type[error_type] = []
                errors_by_type[error_type].append(result)
        
        for error_type, results in errors_by_type.items():
            report += f"\n{error_type} ({len(results)} modules):\n" + "-"*40 + "\n"
            for result in results[:5]:  # Show first 5 of each type
                report += f"\n  Module: {result.module_path}\n"
                report += f"  Error: {result.error_message}\n"
                if result.missing_dependencies:
                    report += f"  Missing: {', '.join(result.missing_dependencies)}\n"
            if len(results) > 5:
                report += f"\n  ... and {len(results) - 5} more\n"
        
        return report
    
    def save_json_report(self, filepath: str):
        """Save detailed JSON report"""
        report_data = {
            'summary': {
                'total_modules': self.total_modules,
                'successful_imports': self.successful_imports,
                'failed_imports': self.failed_imports,
                'success_rate': self.successful_imports/self.total_modules*100 if self.total_modules > 0 else 0,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'total_time': self.total_time
            },
            'results': [r.to_dict() for r in self.results]
        }
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)


class ImportTester:
    """Main import testing class"""
    
    def __init__(self, root_path: Optional[str] = None, verbose: bool = False):
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self.verbose = verbose
        self.report = ImportTestReport()
        self._tested_modules: Set[str] = set()
        self._import_stack: List[str] = []
        
    def test_module(self, module_path: str) -> ImportResult:
        """Test importing a single module"""
        if module_path in self._tested_modules:
            return ImportResult(module_path, True, import_time=0.0)
        
        self._tested_modules.add(module_path)
        
        # Check for circular imports
        if module_path in self._import_stack:
            circular_path = self._import_stack[self._import_stack.index(module_path):] + [module_path]
            return ImportResult(
                module_path=module_path,
                success=False,
                error_type="CircularImport",
                error_message=f"Circular import detected: {' -> '.join(circular_path)}",
                circular_imports=circular_path
            )
        
        self._import_stack.append(module_path)
        start_time = time.time()
        
        try:
            # Try to import the module
            module = importlib.import_module(module_path)
            import_time = time.time() - start_time
            
            result = ImportResult(
                module_path=module_path,
                success=True,
                import_time=import_time
            )
            
            if self.verbose:
                print(f"[OK] {module_path} ({import_time:.3f}s)")
                
        except ModuleNotFoundError as e:
            import_time = time.time() - start_time
            missing_deps = self._extract_missing_dependencies(str(e))
            
            result = ImportResult(
                module_path=module_path,
                success=False,
                error_type="ModuleNotFoundError",
                error_message=str(e),
                traceback=traceback.format_exc() if self.verbose else None,
                import_time=import_time,
                missing_dependencies=missing_deps
            )
            
            if self.verbose:
                print(f"[X] {module_path}: ModuleNotFoundError - {e}")
                
        except ImportError as e:
            import_time = time.time() - start_time
            
            result = ImportResult(
                module_path=module_path,
                success=False,
                error_type="ImportError",
                error_message=str(e),
                traceback=traceback.format_exc() if self.verbose else None,
                import_time=import_time
            )
            
            if self.verbose:
                print(f"[X] {module_path}: ImportError - {e}")
                
        except SyntaxError as e:
            import_time = time.time() - start_time
            
            result = ImportResult(
                module_path=module_path,
                success=False,
                error_type="SyntaxError",
                error_message=f"Line {e.lineno}: {e.msg}",
                traceback=traceback.format_exc() if self.verbose else None,
                import_time=import_time
            )
            
            if self.verbose:
                print(f"[X] {module_path}: SyntaxError at line {e.lineno}")
                
        except Exception as e:
            import_time = time.time() - start_time
            
            result = ImportResult(
                module_path=module_path,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
                import_time=import_time
            )
            
            if self.verbose:
                print(f"[X] {module_path}: {type(e).__name__} - {e}")
        
        finally:
            self._import_stack.pop()
        
        return result
    
    def _extract_missing_dependencies(self, error_message: str) -> List[str]:
        """Extract missing module names from error message"""
        missing = []
        if "No module named" in error_message:
            # Extract module name from error message
            parts = error_message.split("'")
            if len(parts) >= 2:
                missing.append(parts[1])
        return missing
    
    def test_package(self, package_path: str, recursive: bool = True) -> ImportTestReport:
        """Test all modules in a package"""
        self.report.start_time = datetime.now()
        package_dir = self.root_path / package_path.replace('.', '/')
        
        if not package_dir.exists():
            raise ValueError(f"Package directory not found: {package_dir}")
        
        # Add project root to sys.path if not present
        project_root_str = str(self.root_path)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
            
        modules_to_test = self._discover_modules(package_path, package_dir, recursive)
        
        print(f"\nTesting {len(modules_to_test)} modules from {package_path}...")
        print("="*60)
        
        for module_path in modules_to_test:
            result = self.test_module(module_path)
            self.report.add_result(result)
        
        self.report.end_time = datetime.now()
        self.report.total_time = (self.report.end_time - self.report.start_time).total_seconds()
        
        return self.report
    
    def _discover_modules(self, package_name: str, package_dir: Path, recursive: bool) -> List[str]:
        """Discover all Python modules in a package"""
        modules = []
        
        # Walk through the package directory
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ and test directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.pytest_cache']]
            
            # FIXED: Calculate relative path from project root, not package_dir.parent
            rel_path = Path(root).relative_to(self.root_path)
            module_base = str(rel_path).replace(os.sep, '.')
            
            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    if file == '__init__.py':
                        modules.append(module_base)
                    else:
                        module_name = file[:-3]  # Remove .py
                        modules.append(f"{module_base}.{module_name}")
            
            if not recursive:
                break
        
        return sorted(modules)
    
    def test_critical_imports(self) -> ImportTestReport:
        """Test critical application imports"""
        critical_modules = [
            # Core modules
            'netra_backend.app.main',
            'netra_backend.app.config',
            'netra_backend.app.startup_module',
            'netra_backend.app.shutdown',
            
            # Database
            'netra_backend.app.db.database_connectivity_master',
            'netra_backend.app.db.postgres_core',
            'netra_backend.app.db.clickhouse_init',
            
            # Services
            'netra_backend.app.services.agent_service',
            'netra_backend.app.services.websocket_service',
            'netra_backend.app.services.thread_service',
            'netra_backend.app.services.corpus_service',
            
            # Agents
            'netra_backend.app.agents.supervisor_consolidated',
            'netra_backend.app.agents.base_agent',
            'netra_backend.app.agents.triage_sub_agent.agent',
            'netra_backend.app.agents.corpus_admin.agent',
            'netra_backend.app.agents.data_sub_agent.agent',
            
            # Routes
            'netra_backend.app.routes.health',
            'netra_backend.app.routes.agent_route',
            'netra_backend.app.routes.websocket_secure',
            'netra_backend.app.routes.threads_route',
            
            # Core infrastructure
            'netra_backend.app.websocket.ws_manager',
            'netra_backend.app.core.error_handlers',
            'netra_backend.app.core.configuration.base',
        ]
        
        self.report.start_time = datetime.now()
        
        print("\nTesting Critical Imports...")
        print("="*60)
        
        for module_path in critical_modules:
            result = self.test_module(module_path)
            self.report.add_result(result)
        
        self.report.end_time = datetime.now()
        self.report.total_time = (self.report.end_time - self.report.start_time).total_seconds()
        
        return self.report
    
    def generate_import_graph(self) -> Dict[str, List[str]]:
        """Generate import dependency graph"""
        import_graph = {}
        
        for result in self.report.results:
            if result.success:
                try:
                    module = sys.modules.get(result.module_path)
                    if module and hasattr(module, '__file__'):
                        imports = []
                        # Extract imports from module
                        for name, obj in vars(module).items():
                            if hasattr(obj, '__module__'):
                                imports.append(obj.__module__)
                        import_graph[result.module_path] = list(set(imports))
                except:
                    pass
        
        return import_graph
    
    def run_fast_fail_test(self) -> bool:
        """Run fast-fail import test - stops on first error"""
        print("\nRunning Fast-Fail Import Test...")
        print("="*60)
        
        critical_modules = [
            'netra_backend.app.main',
            'netra_backend.app.config',
            'netra_backend.app.startup_module',
        ]
        
        for module_path in critical_modules:
            result = self.test_module(module_path)
            if not result.success:
                print(f"\n[X] IMPORT FAILURE - Fast Fail Triggered!\n")
                print(f"Module: {result.module_path}")
                print(f"Error Type: {result.error_type}")
                print(f"Error: {result.error_message}")
                if result.missing_dependencies:
                    print(f"Missing Dependencies: {', '.join(result.missing_dependencies)}")
                if result.traceback and self.verbose:
                    print(f"\nTraceback:\n{result.traceback}")
                return False
        
        print("\n[OK] All critical imports successful!")
        return True


def main():
    """Main entry point for import testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Python imports with detailed error reporting')
    parser.add_argument('--package', type=str, help='Package to test (e.g., netra_backend.app)')
    parser.add_argument('--critical', action='store_true', help='Test only critical imports')
    parser.add_argument('--fast-fail', action='store_true', help='Stop on first import error')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--json', type=str, help='Save JSON report to file')
    parser.add_argument('--no-recursive', action='store_true', help='Do not test subpackages')
    
    args = parser.parse_args()
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    
    tester = ImportTester(root_path=project_root, verbose=args.verbose)
    
    if args.fast_fail:
        success = tester.run_fast_fail_test()
        sys.exit(0 if success else 1)
    
    if args.critical:
        report = tester.test_critical_imports()
    elif args.package:
        report = tester.test_package(args.package, recursive=not args.no_recursive)
    else:
        # Default: test main netra_backend.app package
        report = tester.test_package('netra_backend.app', recursive=not args.no_recursive)
    
    # Print summary
    print(report.get_summary())
    
    # Print failures if any
    if report.failed_imports > 0:
        print(report.get_failures_report())
    
    # Save JSON report if requested
    if args.json:
        report.save_json_report(args.json)
        print(f"\nDetailed report saved to: {args.json}")
    
    # Exit with error code if there were failures
    sys.exit(1 if report.failed_imports > 0 else 0)


if __name__ == '__main__':
    main()