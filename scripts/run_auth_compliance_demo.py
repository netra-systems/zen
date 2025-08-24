"""
Demonstration of Auth Service Compliance Tests
Shows how the tests detect violations in sample code.
"""

import re
from typing import Dict, List


class AuthComplianceDemo:
    """Demonstrates auth compliance violation detection."""
    
    SAMPLE_VIOLATIONS = [
        # OAuth library import violation
        {
            "code": "from oauthlib import oauth2",
            "violation": "Direct OAuth library import",
            "fix": "Use auth_service client instead"
        },
        # JWT operation violation
        {
            "code": "token = jwt.encode(payload, secret, algorithm='HS256')",
            "violation": "Direct JWT encoding",
            "fix": "Use auth_service.create_token() instead"
        },
        # Local auth endpoint
        {
            "code": "@app.route('/login')\ndef login_user():\n    # Custom login logic",
            "violation": "Local auth endpoint implementation",
            "fix": "Redirect to auth_service endpoints"
        },
        # Password hashing
        {
            "code": "hashed = bcrypt.hash(password)",
            "violation": "Direct password operation",
            "fix": "Use auth_service for password handling"
        },
        # Session management
        {
            "code": "session['user_id'] = user.id",
            "violation": "Local session management",
            "fix": "Use auth_service session management"
        }
    ]
    
    SAMPLE_ALLOWED = [
        # Marked with justification
        {
            "code": "# @auth_service_marked: Required for legacy integration\nfrom oauthlib import oauth2",
            "reason": "Has justification marker"
        },
        # Using auth service
        {
            "code": "from auth_service.client import AuthServiceClient\nauth = AuthServiceClient()",
            "reason": "Properly uses auth service"
        },
        # Auth routes import (allowed)
        {
            "code": "from netra_backend.app.routes.auth_routes import login_flow",
            "reason": "Auth routes are part of auth integration"
        }
    ]
    
    def demonstrate_violations(self):
        """Show examples of violations that would be caught."""
        print("\n" + "="*60)
        print("AUTH SERVICE COMPLIANCE VIOLATION EXAMPLES")
        print("="*60)
        
        print("\nThese patterns would be flagged as VIOLATIONS:")
        print("-" * 50)
        
        for i, sample in enumerate(self.SAMPLE_VIOLATIONS, 1):
            print(f"\n{i}. {sample['violation']}:")
            print(f"   Code: {sample['code']}")
            print(f"   Fix:  {sample['fix']}")
        
        print("\n\nThese patterns would be ALLOWED:")
        print("-" * 50)
        
        for i, sample in enumerate(self.SAMPLE_ALLOWED, 1):
            print(f"\n{i}. {sample['reason']}:")
            print(f"   Code: {sample['code']}")
    
    def run_quick_scan(self):
        """Run a quick scan on a few key files."""
        print("\n" + "="*60)
        print("QUICK SCAN OF KEY FILES")
        print("="*60)
        
        # Define key files to check
        key_files = [
            "netra_backend/app/main.py",
            "netra_backend/app/routes/websocket_secure.py",
            "netra_backend/app/auth_integration/auth.py",
        ]
        
        violations_found = []
        
        # Patterns to check
        violation_patterns = [
            (r"import\s+jwt", "Direct JWT import"),
            (r"from\s+oauthlib", "OAuth library import"),
            (r"bcrypt\.", "Direct password hashing"),
            (r"session\[", "Local session management"),
            (r"def\s+login_user\(", "Local login implementation"),
            (r"def\s+validate_token\(", "Local token validation"),
        ]
        
        for filepath in key_files:
            print(f"\nScanning: {filepath}")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                
                file_violations = []
                for i, line in enumerate(lines, 1):
                    for pattern, description in violation_patterns:
                        if re.search(pattern, line):
                            # Check for justification
                            if i > 1 and "@auth_service_marked:" in lines[i-2]:
                                continue
                            file_violations.append({
                                "line": i,
                                "description": description,
                                "code": line.strip()[:50]
                            })
                
                if file_violations:
                    print(f"  [VIOLATIONS FOUND]: {len(file_violations)}")
                    for v in file_violations[:3]:  # Show first 3
                        print(f"    Line {v['line']}: {v['description']}")
                else:
                    print(f"  [CLEAN]: No violations detected")
                    
            except FileNotFoundError:
                print(f"  [SKIPPED]: File not found")
            except Exception as e:
                print(f"  [ERROR]: {str(e)[:100]}")
    
    def show_test_summary(self):
        """Show summary of what the tests validate."""
        print("\n" + "="*60)
        print("TEST SUITE SUMMARY")
        print("="*60)
        
        suites = [
            {
                "name": "Suite 1: Direct OAuth Implementation Detection",
                "tests": [
                    "No direct OAuth library imports",
                    "No direct OAuth endpoint construction",
                    "No custom OAuth implementations",
                    "No direct OAuth config access",
                    "All auth imports use auth_service"
                ]
            },
            {
                "name": "Suite 2: Auth Service Bypass Detection",
                "tests": [
                    "No direct JWT operations",
                    "No local session management",
                    "No direct user validation",
                    "No direct password handling",
                    "No hardcoded auth logic"
                ]
            },
            {
                "name": "Suite 3: Local Reimplementation Detection",
                "tests": [
                    "No local User models",
                    "No local auth middleware",
                    "No local auth endpoints",
                    "No local token management",
                    "Architectural compliance verification"
                ]
            }
        ]
        
        for suite in suites:
            print(f"\n{suite['name']}:")
            for test in suite['tests']:
                print(f"  - {test}")
        
        print("\n" + "="*60)
        print("HOW TO MARK ALLOWED VIOLATIONS")
        print("="*60)
        print("\nIf a violation is intentional and justified, mark it with:")
        print("  # @auth_service_marked: <justification>")
        print("  <code that would normally violate>")
        print("\nExample:")
        print("  # @auth_service_marked: Legacy integration requirement")
        print("  import jwt  # This would normally be a violation")


def main():
    """Run the demonstration."""
    demo = AuthComplianceDemo()
    
    print("\n" + "="*70)
    print("AUTH SERVICE COMPLIANCE TEST DEMONSTRATION")
    print("="*70)
    
    # Show what violations look like
    demo.demonstrate_violations()
    
    # Run quick scan
    demo.run_quick_scan()
    
    # Show test summary
    demo.show_test_summary()
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("\nThe three test suites ensure:")
    print("1. No module bypasses the auth service")
    print("2. No module reimplements OAuth locally")
    print("3. All authentication goes through the centralized service")
    print("\nThis maintains architectural integrity and security.")


if __name__ == "__main__":
    main()