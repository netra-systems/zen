"""
Test Suite 3: Local Authentication Reimplementation Detection
BVJ: Platform/Internal - Architecture Integrity - Maintains microservice independence

This test suite validates that modules are not reimplementing authentication
logic locally. All auth functionality must be delegated to the centralized
auth service to maintain architectural integrity and security.
"""

import pytest
import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
import re
import json


class TestLocalAuthReimplementationDetection:
    """Detects local reimplementation of authentication functionality."""
    
    REIMPLEMENTATION_PATTERNS = {
        "auth_models": [
            r"class\s+User\s*\(",
            r"class\s+UserModel\s*\(",
            r"class\s+AuthUser\s*\(",
            r"class\s+Account\s*\(",
            r"class\s+UserProfile\s*\(",
            r"class\s+UserCredentials\s*\(",
        ],
        "auth_tables": [
            r"CREATE\s+TABLE.*users",
            r"CREATE\s+TABLE.*accounts",
            r"CREATE\s+TABLE.*sessions",
            r"CREATE\s+TABLE.*tokens",
            r"Table\([\"']users[\"']",
            r"Table\([\"']user_sessions[\"']",
        ],
        "auth_middleware": [
            r"class\s+.*AuthMiddleware",
            r"class\s+.*AuthenticationMiddleware",
            r"def\s+auth_middleware\(",
            r"def\s+authentication_middleware\(",
            r"@app\.middleware\(.*auth",
            r"Middleware.*auth",
        ],
        "auth_decorators": [
            r"@login_required",
            r"@auth_required",
            r"@authenticated",
            r"@requires_auth",
            r"def\s+login_required\(",
            r"def\s+auth_required\(",
        ],
        "auth_endpoints": [
            r"@.*\.route\(.*[\"']/login[\"']",
            r"@.*\.route\(.*[\"']/logout[\"']",
            r"@.*\.route\(.*[\"']/register[\"']",
            r"@.*\.route\(.*[\"']/auth[\"']",
            r"@.*\.route\(.*[\"']/token[\"']",
            r"@.*\.route\(.*[\"']/refresh[\"']",
        ],
        "auth_utilities": [
            r"def\s+generate_token\(",
            r"def\s+create_token\(",
            r"def\s+validate_token\(",
            r"def\s+decode_token\(",
            r"def\s+refresh_token\(",
            r"def\s+revoke_token\(",
            r"def\s+hash_password\(",
            r"def\s+verify_password\(",
        ],
        "auth_stores": [
            r"user_store\s*=",
            r"token_store\s*=",
            r"session_store\s*=",
            r"auth_cache\s*=",
            r"UserStore\(",
            r"TokenStore\(",
            r"SessionStore\(",
        ]
    }
    
    ARCHITECTURAL_VIOLATIONS = {
        "cross_service_imports": [
            r"from\s+app\.models\.user",
            r"from\s+app\.auth\.",
            r"from\s+core\.auth\.",
            r"from\s+utils\.auth\.",
            r"from\s+services\.authentication",
        ],
        "auth_configuration": [
            r"AUTH_SECRET_KEY\s*=",
            r"JWT_SECRET\s*=",
            r"SESSION_SECRET\s*=",
            r"TOKEN_EXPIRY\s*=",
            r"AUTH_ALGORITHM\s*=",
        ],
        "database_queries": [
            r"SELECT.*FROM\s+users",
            r"INSERT\s+INTO\s+users",
            r"UPDATE\s+users\s+SET",
            r"DELETE\s+FROM\s+users",
            r"db\.query\(.*users",
        ]
    }
    
    ALLOWED_MARKER = r"@auth_service_marked:"
    REQUIRED_AUTH_SERVICE_IMPORT = r"from.*auth_service|import.*auth_service|AUTH_SERVICE"
    
    EXCLUSION_PATHS = {
        "auth_service",  # Auth service itself
        "tests",  # Test files
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "migrations",  # Database migrations
    }
    
    def _analyze_file_structure(self, filepath: Path) -> Dict[str, any]:
        """Analyze file structure for auth patterns."""
        analysis = {
            "has_auth_service_import": False,
            "has_auth_patterns": False,
            "auth_pattern_count": 0,
            "violations": []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for auth service import
            if re.search(self.REQUIRED_AUTH_SERVICE_IMPORT, content):
                analysis["has_auth_service_import"] = True
            
            # Count auth-related patterns
            for category, patterns in {**self.REIMPLEMENTATION_PATTERNS, **self.ARCHITECTURAL_VIOLATIONS}.items():
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        analysis["has_auth_patterns"] = True
                        analysis["auth_pattern_count"] += len(matches)
                        
        except Exception:
            pass
            
        return analysis
    
    def _scan_file(self, filepath: Path) -> List[Dict[str, any]]:
        """Scan file for local auth reimplementation."""
        violations = []
        
        # Skip excluded paths
        if any(excl in str(filepath) for excl in self.EXCLUSION_PATHS):
            return violations
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            file_analysis = self._analyze_file_structure(filepath)
            
            # Check reimplementation patterns
            for category, patterns in self.REIMPLEMENTATION_PATTERNS.items():
                for pattern in patterns:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check for justification
                            if i > 1 and self.ALLOWED_MARKER in lines[i-2]:
                                continue
                            
                            # Determine severity based on context
                            severity = "CRITICAL"
                            if file_analysis["has_auth_service_import"]:
                                severity = "HIGH"  # Less severe if auth service is used
                            
                            violations.append({
                                "file": str(filepath),
                                "line": i,
                                "category": category,
                                "pattern": pattern,
                                "content": line.strip(),
                                "severity": severity,
                                "has_auth_service": file_analysis["has_auth_service_import"]
                            })
                            
        except Exception:
            pass
            
        return violations
    
    def test_no_local_user_models(self):
        """Test 1: No local User model implementations outside auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            model_violations = [v for v in file_violations 
                              if v["category"] in ["auth_models", "auth_tables"]]
            violations.extend(model_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} local User model implementations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_local_auth_middleware(self):
        """Test 2: No local authentication middleware implementations."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            middleware_violations = [v for v in file_violations 
                                   if v["category"] == "auth_middleware"]
            violations.extend(middleware_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} local auth middleware implementations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_local_auth_endpoints(self):
        """Test 3: No local auth endpoints (login/logout/register) outside auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            endpoint_violations = [v for v in file_violations 
                                 if v["category"] in ["auth_endpoints", "auth_decorators"]]
            violations.extend(endpoint_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} local auth endpoint implementations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_local_token_management(self):
        """Test 4: No local token generation or validation utilities."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            token_violations = [v for v in file_violations 
                              if v["category"] in ["auth_utilities", "auth_stores"]]
            violations.extend(token_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} local token management implementations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_architectural_compliance(self):
        """Test 5: Verify architectural compliance - no cross-service auth imports."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            # Skip excluded paths
            if any(excl in str(filepath) for excl in self.EXCLUSION_PATHS):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    
                # Check architectural violations
                for category, patterns in self.ARCHITECTURAL_VIOLATIONS.items():
                    for pattern in patterns:
                        for i, line in enumerate(lines, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                # Check for justification
                                if i > 1 and self.ALLOWED_MARKER in lines[i-2]:
                                    continue
                                
                                # Check if it's using auth_service properly
                                if "auth_service" in line or "auth_routes" in line:
                                    continue
                                    
                                violations.append({
                                    "file": str(filepath),
                                    "line": i,
                                    "category": category,
                                    "content": line.strip()
                                })
                                
            except Exception:
                pass
        
        assert len(violations) == 0, (
            f"Found {len(violations)} architectural compliance violations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])