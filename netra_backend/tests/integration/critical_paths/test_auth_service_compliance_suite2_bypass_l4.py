"""
Test Suite 2: Auth Service Bypass Detection
BVJ: Platform/Internal - Security - Prevents security vulnerabilities from auth bypass

This test suite validates that no module is bypassing the auth service
for authentication and authorization operations. All auth operations
MUST use the centralized auth service.
"""

import pytest
import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Optional
import re
import json


class TestAuthServiceBypassDetection:
    """Detects attempts to bypass the centralized auth service."""
    
    BYPASS_VIOLATION_PATTERNS = {
        "direct_jwt_operations": [
            r"import\s+jwt",
            r"from\s+jose\s+import",
            r"import\s+pyjwt",
            r"jwt\.encode\(",
            r"jwt\.decode\(",
            r"JWTManager\(",
            r"create_access_token\(",
            r"verify_token\(",
        ],
        "direct_session_management": [
            r"session\[.*user.*\]",
            r"session\[.*auth.*\]",
            r"request\.session\.",
            r"SessionMiddleware\(",
            r"def\s+.*session.*\(",
            r"class\s+.*Session.*:",
        ],
        "direct_user_validation": [
            r"def\s+validate_user\(",
            r"def\s+authenticate_user\(",
            r"def\s+check_permissions\(",
            r"def\s+verify_credentials\(",
            r"def\s+login_user\(",
            r"def\s+logout_user\(",
        ],
        "direct_password_operations": [
            r"bcrypt\.hash",
            r"bcrypt\.verify",
            r"hashlib\.",
            r"pbkdf2_hmac\(",
            r"scrypt\(",
            r"argon2\.",
            r"werkzeug\.security",
            r"passlib\.",
        ],
        "hardcoded_auth_logic": [
            r"if\s+.*username.*==.*and.*password.*==",
            r"if\s+request\.headers\.\s*get\(.*[Aa]uthorization",
            r"Bearer\s+[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
            r"api_key\s*=\s*[\"'][a-zA-Z0-9]{20,}[\"']",
        ],
        "direct_role_checks": [
            r"if\s+.*role.*==.*admin",
            r"if\s+.*user\.is_admin",
            r"@requires_role\(",
            r"@admin_required",
            r"check_admin_role\(",
            r"has_permission\(",
        ]
    }
    
    AUTH_SERVICE_PATTERNS = [
        r"auth_service",
        r"AUTH_SERVICE",
        r"from\s+.*auth_routes",
        r"AuthServiceClient",
    ]
    
    ALLOWED_MARKER = r"@auth_service_marked:"
    EXCLUSION_PATHS = {
        "auth_service",  # Auth service itself
        "tests",  # Test files
        "__pycache__",
        ".git",
        "venv",
        ".venv",
    }
    
    def _check_auth_service_usage(self, filepath: Path) -> bool:
        """Check if file properly uses auth service."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in self.AUTH_SERVICE_PATTERNS:
                if re.search(pattern, content):
                    return True
            return False
        except Exception:
            return False
    
    def _scan_file(self, filepath: Path) -> List[Dict[str, any]]:
        """Scan file for auth bypass violations."""
        violations = []
        
        # Skip excluded paths
        if any(excl in str(filepath) for excl in self.EXCLUSION_PATHS):
            return violations
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Check if file uses auth service
            uses_auth_service = self._check_auth_service_usage(filepath)
            
            for category, patterns in self.BYPASS_VIOLATION_PATTERNS.items():
                for pattern in patterns:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check for justification marker
                            if i > 1 and self.ALLOWED_MARKER in lines[i-2]:
                                continue
                            
                            # If file doesn't use auth service, it's more severe
                            severity = "CRITICAL" if not uses_auth_service else "HIGH"
                            
                            violations.append({
                                "file": str(filepath),
                                "line": i,
                                "category": category,
                                "pattern": pattern,
                                "content": line.strip(),
                                "severity": severity,
                                "uses_auth_service": uses_auth_service
                            })
                            
        except Exception as e:
            pass
            
        return violations
    
    def test_no_direct_jwt_operations(self):
        """Test 1: No direct JWT encoding/decoding outside auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            jwt_violations = [v for v in file_violations if v["category"] == "direct_jwt_operations"]
            violations.extend(jwt_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} direct JWT operations bypassing auth service:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_local_session_management(self):
        """Test 2: No local session management bypassing auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            session_violations = [v for v in file_violations if v["category"] == "direct_session_management"]
            violations.extend(session_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} local session management implementations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_direct_user_validation(self):
        """Test 3: No direct user validation logic outside auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            validation_violations = [v for v in file_violations if v["category"] == "direct_user_validation"]
            violations.extend(validation_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} direct user validation implementations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_direct_password_handling(self):
        """Test 4: No direct password hashing/verification outside auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            password_violations = [v for v in file_violations if v["category"] == "direct_password_operations"]
            violations.extend(password_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} direct password operations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_hardcoded_auth_logic(self):
        """Test 5: No hardcoded authentication logic or credentials."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            hardcoded_violations = [v for v in file_violations 
                                   if v["category"] in ["hardcoded_auth_logic", "direct_role_checks"]]
            violations.extend(hardcoded_violations)
        
        # Critical violations are those without auth service usage
        critical_violations = [v for v in violations if v["severity"] == "CRITICAL"]
        
        assert len(critical_violations) == 0, (
            f"Found {len(critical_violations)} critical auth bypass violations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in critical_violations[:5]])
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])