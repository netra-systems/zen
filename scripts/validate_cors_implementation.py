#!/usr/bin/env python3
"""
Validation script for CORS implementation.

Validates that all frontend API routes have been updated with proper CORS headers
and OPTIONS handlers.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class CORSImplementationValidator:
    """Validates CORS implementation across frontend API routes."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.frontend_api_dir = self.project_root / "frontend" / "app" / "api"
        self.cors_utils_file = self.project_root / "frontend" / "lib" / "cors-utils.ts"
        
    def find_api_routes(self) -> List[Path]:
        """Find all route.ts files in the frontend API directory."""
        routes = []
        if self.frontend_api_dir.exists():
            routes = list(self.frontend_api_dir.rglob("route.ts"))
        return sorted(routes)
    
    def check_cors_utils_exists(self) -> Tuple[bool, str]:
        """Check if CORS utilities file exists and has expected exports."""
        if not self.cors_utils_file.exists():
            return False, "CORS utilities file does not exist"
        
        try:
            content = self.cors_utils_file.read_text(encoding='utf-8')
            
            expected_exports = [
                'getCorsHeaders',
                'handleOptions', 
                'addCorsHeaders',
                'corsJsonResponse',
                'corsEmptyResponse'
            ]
            
            missing_exports = []
            for export in expected_exports:
                if f'export function {export}' not in content:
                    missing_exports.append(export)
            
            if missing_exports:
                return False, f"Missing exports in CORS utils: {', '.join(missing_exports)}"
            
            return True, "CORS utilities file is complete"
            
        except Exception as e:
            return False, f"Error reading CORS utilities file: {str(e)}"
    
    def check_route_cors_implementation(self, route_file: Path) -> Tuple[bool, List[str]]:
        """Check if a route file has proper CORS implementation."""
        try:
            content = route_file.read_text(encoding='utf-8')
            issues = []
            
            # Check for CORS imports
            cors_imports = [
                'corsJsonResponse',
                'handleOptions', 
                'addCorsHeaders',
                'corsEmptyResponse'
            ]
            
            has_cors_import = any(imp in content for imp in cors_imports)
            if not has_cors_import:
                issues.append("Missing CORS utility imports")
            
            # Check for OPTIONS handler
            if 'export async function OPTIONS' not in content:
                issues.append("Missing OPTIONS handler")
            
            # Check for handleOptions usage in OPTIONS handler
            if 'export async function OPTIONS' in content and 'handleOptions(request)' not in content:
                issues.append("OPTIONS handler doesn't use handleOptions utility")
            
            # Check for CORS response functions usage
            has_cors_response = any(func in content for func in ['corsJsonResponse', 'addCorsHeaders', 'corsEmptyResponse'])
            if not has_cors_response:
                issues.append("Not using CORS response functions")
            
            # Check for credentials: 'include' in fetch calls
            # Look for fetch calls and check if they have credentials: 'include'
            fetch_calls = re.findall(r'fetch\([^)]+,\s*\{[^}]*\}[^}]*\}', content, re.DOTALL)
            missing_credentials = False
            for fetch_call in fetch_calls:
                if "credentials: 'include'" not in fetch_call:
                    missing_credentials = True
                    break
            
            # Also check simpler pattern for cases where fetch options might be formatted differently
            if missing_credentials and "credentials: 'include'" in content:
                missing_credentials = False
            
            if missing_credentials and fetch_calls:
                issues.append("Fetch call missing credentials: 'include'")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            return False, [f"Error reading route file: {str(e)}"]
    
    def validate_all_routes(self) -> Dict[str, Tuple[bool, List[str]]]:
        """Validate CORS implementation across all API routes."""
        routes = self.find_api_routes()
        results = {}
        
        for route in routes:
            relative_path = route.relative_to(self.project_root)
            success, issues = self.check_route_cors_implementation(route)
            results[str(relative_path)] = (success, issues)
        
        return results
    
    def print_validation_results(self):
        """Print comprehensive validation results."""
        print("CORS Implementation Validation")
        print("=" * 60)
        
        # Check CORS utilities
        utils_ok, utils_msg = self.check_cors_utils_exists()
        status = "[OK]" if utils_ok else "[FAIL]"
        print(f"{status} CORS Utilities: {utils_msg}")
        
        if not utils_ok:
            print("\n[WARN] Cannot proceed with route validation - CORS utilities missing")
            return False
        
        print()
        
        # Check all routes
        route_results = self.validate_all_routes()
        
        if not route_results:
            print("[WARN] No API routes found to validate")
            return False
        
        total_routes = len(route_results)
        successful_routes = sum(1 for success, _ in route_results.values() if success)
        
        print(f"Route Validation Results: {successful_routes}/{total_routes} routes properly configured")
        print("-" * 60)
        
        for route_path, (success, issues) in route_results.items():
            status = "[OK]" if success else "[FAIL]"
            print(f"{status} {route_path}")
            
            if issues:
                for issue in issues:
                    print(f"  [WARN] {issue}")
        
        print("=" * 60)
        
        if successful_routes == total_routes:
            print("All routes have proper CORS implementation!")
            return True
        else:
            print(f"{total_routes - successful_routes} routes need CORS fixes")
            return False


def main():
    """Main validation execution."""
    project_root = os.getcwd()
    
    print("Frontend CORS Implementation Validator")
    print(f"Project root: {project_root}")
    print()
    
    validator = CORSImplementationValidator(project_root)
    success = validator.print_validation_results()
    
    if success:
        print("\nCORS implementation validation passed!")
        return 0
    else:
        print("\nCORS implementation validation failed!")
        print("Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    exit(main())