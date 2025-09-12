#!/usr/bin/env python3
"""
Check for service independence violations.

CRITICAL: Microservices MUST be 100% independent. 
Cross-service imports cause catastrophic failures in production.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def check_service_independence() -> Tuple[bool, List[str]]:
    """Check for service independence violations."""
    violations = []
    
    # Define service boundaries
    services = {
        'auth_service': Path('auth_service'),
        'netra_backend': Path('netra_backend'),
        'frontend': Path('frontend')
    }
    
    # Check each service for violations
    for service_name, service_path in services.items():
        if not service_path.exists():
            continue
            
        # Define what this service should NOT import
        forbidden_imports = []
        if service_name == 'auth_service':
            forbidden_imports = ['from netra_backend', 'import netra_backend']
        elif service_name == 'netra_backend':
            forbidden_imports = ['from auth_service', 'import auth_service']
        # Frontend is allowed to import from services (it's not a microservice)
        
        # Search for violations
        for root, dirs, files in os.walk(service_path):
            # Skip test files and __pycache__
            if '__pycache__' in root or 'venv' in root:
                continue
                
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for line_num, line in enumerate(content.splitlines(), 1):
                        # Skip comments and docstrings
                        stripped = line.strip()
                        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                            continue
                        
                        # Skip lines that are just warning text without actual imports    
                        if 'NEVER import from' in line or 'must be independent' in line.lower():
                            if not line.strip().startswith('from ') and not line.strip().startswith('import '):
                                continue
                                
                        for forbidden in forbidden_imports:
                            if forbidden in line:
                                # Check if it's an actual import statement
                                if line.strip().startswith('from ') or line.strip().startswith('import '):
                                    violations.append(
                                        f"{filepath}:{line_num} - VIOLATION: {line.strip()}"
                                    )
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return len(violations) == 0, violations

def main():
    """Main entry point."""
    print("=" * 80)
    print("SERVICE INDEPENDENCE CHECK")
    print("=" * 80)
    print("\nChecking for cross-service import violations...\n")
    
    passed, violations = check_service_independence()
    
    if passed:
        print(" PASS:  SUCCESS: No service independence violations found!")
        print("\nAll microservices are properly independent.")
        return 0
    else:
        print(" FAIL:  CRITICAL VIOLATIONS FOUND!\n")
        print("The following cross-service imports will cause CATASTROPHIC FAILURES in production:")
        print("-" * 80)
        
        for violation in violations:
            print(f"  [U+2022] {violation}")
        
        print("-" * 80)
        print(f"\nTotal violations: {len(violations)}")
        print("\n WARNING: [U+FE0F]  These violations MUST be fixed before deployment!")
        print(" WARNING: [U+FE0F]  Services run in isolated containers in production.")
        print(" WARNING: [U+FE0F]  Cross-service imports will cause complete service failure.")
        
        print("\nTo fix:")
        print("1. Remove all cross-service imports")
        print("2. Implement service-specific versions of needed functionality")
        print("3. Use /shared directory for truly universal utilities")
        print("4. See SPEC/independent_services.xml for details")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())