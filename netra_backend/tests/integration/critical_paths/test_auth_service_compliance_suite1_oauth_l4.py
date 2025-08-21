"""
Test Suite 1: Direct OAuth Implementation Detection
BVJ: Platform/Internal - Stability - Ensures all services use centralized auth service

This test suite validates that no module is implementing OAuth directly,
bypassing the centralized auth service. All OAuth operations MUST go through
the auth service unless explicitly marked with justification.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Tuple
import re


class TestDirectOAuthImplementationDetection:
    """Detects unauthorized direct OAuth implementations."""
    
    OAUTH_VIOLATION_PATTERNS = {
        "oauth_libraries": [
            r"from\s+oauthlib",
            r"import\s+oauthlib",
            r"from\s+authlib",
            r"import\s+authlib",
            r"from\s+google\.auth",
            r"import\s+google\.auth",
            r"from\s+requests_oauthlib",
            r"import\s+requests_oauthlib",
        ],
        "oauth_endpoints": [
            r"\/oauth\/authorize",
            r"\/oauth\/token",
            r"\/oauth2\/v1\/",
            r"\/oauth2\/authorize",
            r"accounts\.google\.com\/o\/oauth2",
            r"github\.com\/login\/oauth",
        ],
        "oauth_functions": [
            r"def\s+.*oauth.*\(",
            r"def\s+.*authorize.*\(",
            r"def\s+.*get_access_token.*\(",
            r"def\s+.*refresh_token.*\(",
            r"def\s+.*validate_oauth.*\(",
        ],
        "oauth_classes": [
            r"class\s+.*OAuth.*:",
            r"class\s+.*OAuthProvider.*:",
            r"class\s+.*TokenHandler.*:",
            r"class\s+.*AuthorizationFlow.*:",
        ],
        "oauth_configs": [
            r"OAUTH_.*_ID",
            r"OAUTH_.*_SECRET",
            r"CLIENT_ID",
            r"CLIENT_SECRET",
            r"GOOGLE_CLIENT_ID",
            r"GITHUB_CLIENT_SECRET",
        ]
    }
    
    ALLOWED_MARKER = r"@auth_service_marked:"
    EXCLUSION_PATHS = {
        "auth_service",  # Auth service itself is allowed
        "tests",  # Test files may mock OAuth
        "__pycache__",
        ".git",
        "venv",
        ".venv",
    }
    
    def _scan_file(self, filepath: Path) -> List[Dict[str, any]]:
        """Scan a single file for OAuth violations."""
        violations = []
        
        # Skip excluded paths
        if any(excl in str(filepath) for excl in self.EXCLUSION_PATHS):
            return violations
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            for category, patterns in self.OAUTH_VIOLATION_PATTERNS.items():
                for pattern in patterns:
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check if marked with justification
                            if i > 1 and self.ALLOWED_MARKER in lines[i-2]:
                                continue  # Allowed with justification
                            
                            violations.append({
                                "file": str(filepath),
                                "line": i,
                                "category": category,
                                "pattern": pattern,
                                "content": line.strip(),
                                "severity": "CRITICAL"
                            })
                            
        except Exception as e:
            pass  # Skip files that can't be read
            
        return violations
    
    def test_no_direct_oauth_library_imports(self):
        """Test 1: No direct OAuth library imports without justification."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            oauth_lib_violations = [v for v in file_violations if v["category"] == "oauth_libraries"]
            violations.extend(oauth_lib_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} unauthorized OAuth library imports:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_direct_oauth_endpoint_construction(self):
        """Test 2: No direct OAuth endpoint construction without auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            endpoint_violations = [v for v in file_violations if v["category"] == "oauth_endpoints"]
            violations.extend(endpoint_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} direct OAuth endpoint constructions:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_custom_oauth_implementations(self):
        """Test 3: No custom OAuth flow implementations outside auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            custom_violations = [v for v in file_violations 
                               if v["category"] in ["oauth_functions", "oauth_classes"]]
            violations.extend(custom_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} custom OAuth implementations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_no_direct_oauth_config_access(self):
        """Test 4: No direct OAuth configuration access outside auth service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        for filepath in root_path.rglob("*.py"):
            file_violations = self._scan_file(filepath)
            config_violations = [v for v in file_violations if v["category"] == "oauth_configs"]
            violations.extend(config_violations)
        
        assert len(violations) == 0, (
            f"Found {len(violations)} direct OAuth config accesses:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )
    
    def test_all_auth_imports_use_service(self):
        """Test 5: All authentication imports must reference auth_service."""
        violations = []
        root_path = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend")
        
        # Patterns that indicate local auth implementation
        local_auth_patterns = [
            r"from\s+\.auth\s+import",
            r"from\s+app\.auth\s+import",
            r"from\s+core\.auth\s+import",
            r"from\s+utils\.auth\s+import",
            r"from\s+services\.auth\s+import",
        ]
        
        for filepath in root_path.rglob("*.py"):
            if any(excl in str(filepath) for excl in self.EXCLUSION_PATHS):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    
                for i, line in enumerate(lines, 1):
                    for pattern in local_auth_patterns:
                        if re.search(pattern, line):
                            # Check if it's importing from auth_service
                            if "auth_service" not in line and "auth_routes" not in line:
                                # Check for justification marker
                                if i > 1 and self.ALLOWED_MARKER in lines[i-2]:
                                    continue
                                    
                                violations.append({
                                    "file": str(filepath),
                                    "line": i,
                                    "content": line.strip()
                                })
                                
            except Exception:
                pass
                
        assert len(violations) == 0, (
            f"Found {len(violations)} local auth implementations:\n" +
            "\n".join([f"  - {v['file']}:{v['line']} - {v['content']}" for v in violations[:5]])
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])