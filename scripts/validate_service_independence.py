#!/usr/bin/env python3
"""
Validate Service Independence Script
Ensures microservices are truly independent from the main application
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class ServiceIndependenceValidator:
    """Validates that services are completely independent."""
    
    def __init__(self, service_path: str):
        self.service_path = Path(service_path)
        self.errors = []
        self.warnings = []
        
    def validate(self) -> bool:
        """Run all validation checks."""
        print(f"\n[VALIDATING] Service independence for: {self.service_path}")
        print("=" * 60)
        
        # Run all checks
        self._check_no_app_directory()
        self._check_no_main_app_imports()
        self._check_dockerfile_copies_entire_service()
        self._check_requirements_complete()
        self._check_service_can_import()
        self._check_unique_module_names()
        
        # Report results
        self._report_results()
        
        return len(self.errors) == 0
    
    def _check_no_app_directory(self):
        """Ensure service doesn't have an 'app' directory."""
        app_dir = self.service_path / "app"
        if app_dir.exists():
            self.errors.append(
                f"[ERROR] Service has 'app' directory - use unique name like '{self.service_path.name}_core'"
            )
        else:
            print("[OK] No 'app' directory found (good)")
    
    def _check_no_main_app_imports(self):
        """Check for imports from main app."""
        import_patterns = [
            "from netra_backend.app.",
            "from app import",
            "import app.",
            "import app"
        ]
        
        found_imports = []
        for py_file in self.service_path.rglob("*.py"):
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for line_no, line in enumerate(content.splitlines(), 1):
                        for pattern in import_patterns:
                            if pattern in line and not line.strip().startswith("#"):
                                found_imports.append(
                                    f"  {py_file.relative_to(self.service_path)}:{line_no} - {line.strip()}"
                                )
            except Exception as e:
                self.warnings.append(f"Could not read {py_file}: {e}")
        
        if found_imports:
            self.errors.append(
                f"[ERROR] Found {len(found_imports)} imports from main app:\n" + "\n".join(found_imports)
            )
        else:
            print("[OK] No imports from main app found (good)")
    
    def _check_dockerfile_copies_entire_service(self):
        """Check that Dockerfile copies entire service directory."""
        dockerfile_names = ["Dockerfile", f"Dockerfile.{self.service_path.name}"]
        
        for dockerfile_name in dockerfile_names:
            dockerfile = self.service_path.parent / dockerfile_name
            if not dockerfile.exists():
                continue
                
            try:
                with open(dockerfile, 'r') as f:
                    content = f.read()
                    
                # Check for proper COPY command
                service_name = self.service_path.name
                good_patterns = [
                    f"COPY {service_name}/ ./",
                    f"COPY {service_name} ."
                ]
                
                if any(pattern in content for pattern in good_patterns):
                    print(f"[OK] Dockerfile copies entire service directory (good)")
                else:
                    self.warnings.append(
                        f"[WARNING]  Dockerfile may not copy entire service - check {dockerfile_name}"
                    )
            except Exception as e:
                self.warnings.append(f"Could not read {dockerfile}: {e}")
    
    def _check_requirements_complete(self):
        """Check that requirements.txt includes all needed dependencies."""
        req_file = self.service_path / "requirements.txt"
        if not req_file.exists():
            self.errors.append("[ERROR] No requirements.txt found")
            return
            
        try:
            with open(req_file, 'r') as f:
                requirements = f.read().lower()
                
            # Check for common missing dependencies
            checks = {
                "gunicorn": "Uses gunicorn in Dockerfile",
                "fastapi": "FastAPI service",
                "uvicorn": "ASGI server"
            }
            
            missing = []
            for dep, description in checks.items():
                if dep not in requirements:
                    # Check if it's actually needed
                    if self._service_needs_dependency(dep):
                        missing.append(f"  - {dep} ({description})")
            
            if missing:
                self.warnings.append(
                    f"[WARNING]  Potentially missing dependencies:\n" + "\n".join(missing)
                )
            else:
                print("[OK] Requirements appear complete")
                
        except Exception as e:
            self.warnings.append(f"Could not read requirements.txt: {e}")
    
    def _service_needs_dependency(self, dep: str) -> bool:
        """Check if service actually needs a dependency."""
        # Check Dockerfile for gunicorn
        if dep == "gunicorn":
            for dockerfile in self.service_path.parent.glob("Dockerfile*"):
                try:
                    with open(dockerfile, 'r') as f:
                        if "gunicorn" in f.read():
                            return True
                except:
                    pass
        
        # Check for FastAPI usage
        if dep == "fastapi":
            for py_file in self.service_path.rglob("*.py"):
                try:
                    with open(py_file, 'r') as f:
                        if "from fastapi" in f.read() or "import fastapi" in f.read():
                            return True
                except:
                    pass
        
        return False
    
    def _check_service_can_import(self):
        """Test that service can be imported independently."""
        main_file = self.service_path / "main.py"
        if not main_file.exists():
            self.warnings.append("[WARNING]  No main.py found - cannot test imports")
            return
            
        # Try to import the service
        original_dir = os.getcwd()
        try:
            os.chdir(self.service_path)
            result = subprocess.run(
                [sys.executable, "-c", "from main import app; print('Import successful')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print("[OK] Service can be imported independently (good)")
            else:
                self.errors.append(
                    f"[ERROR] Service cannot be imported independently:\n  {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            self.warnings.append("[WARNING]  Import test timed out")
        except Exception as e:
            self.warnings.append(f"[WARNING]  Could not test imports: {e}")
        finally:
            os.chdir(original_dir)
    
    def _check_unique_module_names(self):
        """Check that service uses unique module names."""
        # Find all Python module directories
        module_dirs = [
            d for d in self.service_path.iterdir() 
            if d.is_dir() and not d.name.startswith(('.', '__'))
        ]
        
        # Check for common non-unique names
        non_unique = ["app", "core", "api", "services", "models", "routes"]
        problematic = []
        
        for module_dir in module_dirs:
            if module_dir.name in non_unique:
                # It's okay if it's nested under a unique parent
                if module_dir.parent == self.service_path:
                    problematic.append(module_dir.name)
        
        if problematic:
            self.warnings.append(
                f"[WARNING]  Consider more unique module names instead of: {', '.join(problematic)}"
            )
    
    def _report_results(self):
        """Report validation results."""
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        
        if not self.errors and not self.warnings:
            print("[OK] All checks passed! Service is properly independent.")
        else:
            if self.errors:
                print(f"\n[ERROR] ERRORS ({len(self.errors)}):")
                for error in self.errors:
                    print(error)
            
            if self.warnings:
                print(f"\n[WARNING]  WARNINGS ({len(self.warnings)}):")
                for warning in self.warnings:
                    print(warning)
        
        print("\n" + "=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate microservice independence"
    )
    parser.add_argument(
        "service_path",
        help="Path to the service directory (e.g., auth_service)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix issues automatically (not implemented yet)"
    )
    
    args = parser.parse_args()
    
    if not Path(args.service_path).exists():
        print(f"[ERROR] Service path does not exist: {args.service_path}")
        sys.exit(1)
    
    validator = ServiceIndependenceValidator(args.service_path)
    success = validator.validate()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()