#!/usr/bin/env python3
"""
Token Validation Issues Diagnostic Tool
Identifies JWT secret key mismatches and token validation inconsistencies between services.
"""

import os
import sys
import asyncio
from typing import Dict, List, Optional
import jwt
from datetime import datetime, timedelta, timezone

class TokenValidationDiagnostic:
    """Diagnose token validation issues between services."""
    
    def __init__(self):
        self.issues_found: List[str] = []
        self.auth_service_secret = None
        self.backend_secret = None
        
    def check_jwt_secret_consistency(self) -> Dict[str, str]:
        """Check JWT secret configuration across different environment files."""
        secrets_found = {}
        
        # Auth service expects JWT_SECRET
        auth_secret = os.getenv("JWT_SECRET")
        if auth_secret:
            secrets_found["JWT_SECRET"] = auth_secret
            
        # Backend expects JWT_SECRET_KEY  
        backend_secret = os.getenv("JWT_SECRET_KEY")
        if backend_secret:
            secrets_found["JWT_SECRET_KEY"] = backend_secret
            
        self.auth_service_secret = auth_secret
        self.backend_secret = backend_secret
        
        return secrets_found
        
    def validate_secret_consistency(self, secrets: Dict[str, str]) -> None:
        """Validate that JWT secrets are consistent between services."""
        if not secrets:
            self.issues_found.append("❌ No JWT secrets found in environment")
            return
            
        jwt_secret = secrets.get("JWT_SECRET")
        jwt_secret_key = secrets.get("JWT_SECRET_KEY")
        
        if jwt_secret and jwt_secret_key:
            if jwt_secret != jwt_secret_key:
                self.issues_found.append(
                    f"FAIL JWT secret mismatch: AUTH_SERVICE uses JWT_SECRET='{jwt_secret[:10]}...' "
                    f"but BACKEND uses JWT_SECRET_KEY='{jwt_secret_key[:10]}...'"
                )
            else:
                print("PASS JWT secrets match between services")
        elif jwt_secret and not jwt_secret_key:
            self.issues_found.append(
                "FAIL Auth service has JWT_SECRET but backend expects JWT_SECRET_KEY"
            )
        elif jwt_secret_key and not jwt_secret:
            self.issues_found.append(
                "FAIL Backend has JWT_SECRET_KEY but auth service expects JWT_SECRET" 
            )
        else:
            self.issues_found.append("FAIL No JWT secrets configured for either service")
            
    def test_token_encoding_decoding(self) -> None:
        """Test JWT token encoding/decoding with both secrets."""
        if not self.auth_service_secret and not self.backend_secret:
            self.issues_found.append("FAIL Cannot test token encoding - no secrets available")
            return
            
        # Test data
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "token_type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iss": "netra-auth-service"
        }
        
        # Test auth service secret
        if self.auth_service_secret:
            try:
                token = jwt.encode(test_payload, self.auth_service_secret, algorithm="HS256")
                decoded = jwt.decode(token, self.auth_service_secret, algorithms=["HS256"])
                print(f"PASS Auth service secret can encode/decode tokens: {token[:30]}...")
            except Exception as e:
                self.issues_found.append(f"FAIL Auth service secret encoding failed: {e}")
                
        # Test backend secret  
        if self.backend_secret:
            try:
                token = jwt.encode(test_payload, self.backend_secret, algorithm="HS256")
                decoded = jwt.decode(token, self.backend_secret, algorithms=["HS256"])
                print(f"PASS Backend secret can encode/decode tokens: {token[:30]}...")
            except Exception as e:
                self.issues_found.append(f"FAIL Backend secret encoding failed: {e}")
                
        # Cross-service token validation test
        if self.auth_service_secret and self.backend_secret and self.auth_service_secret != self.backend_secret:
            try:
                # Token created with auth service secret
                auth_token = jwt.encode(test_payload, self.auth_service_secret, algorithm="HS256")
                # Try to decode with backend secret
                jwt.decode(auth_token, self.backend_secret, algorithms=["HS256"])
                print("PASS Cross-service token validation works")
            except Exception as e:
                self.issues_found.append(
                    f"FAIL Cross-service token validation fails: Auth-created token cannot be validated by backend: {e}"
                )
                
    def check_environment_files(self) -> None:
        """Check environment files for JWT secret configurations."""
        env_files = [
            ".env",
            ".env.local", 
            ".env.development",
            ".env.staging",
            ".env.production",
            ".env.auth.example",
            "config/staging.env"
        ]
        
        base_path = "C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1"
        found_configs = {}
        
        for env_file in env_files:
            file_path = os.path.join(base_path, env_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if "JWT_SECRET=" in content:
                            # Extract the value
                            for line in content.split('\n'):
                                if line.startswith('JWT_SECRET='):
                                    value = line.split('=', 1)[1]
                                    found_configs[env_file] = ('JWT_SECRET', value)
                                    break
                        elif "JWT_SECRET_KEY=" in content:
                            for line in content.split('\n'):
                                if line.startswith('JWT_SECRET_KEY='):
                                    value = line.split('=', 1)[1]
                                    found_configs[env_file] = ('JWT_SECRET_KEY', value)
                                    break
                except Exception as e:
                    print(f"Warning: Could not read {env_file}: {e}")
                    
        print("\\nEnvironment File Analysis:")
        for file, (var_name, value) in found_configs.items():
            print(f"  {file}: {var_name}={value[:20]}...")
            
        # Check for inconsistencies
        jwt_secret_files = [f for f, (var, val) in found_configs.items() if var == 'JWT_SECRET']
        jwt_secret_key_files = [f for f, (var, val) in found_configs.items() if var == 'JWT_SECRET_KEY']
        
        if jwt_secret_files and jwt_secret_key_files:
            self.issues_found.append(
                f"FAIL Mixed JWT secret variable names: {jwt_secret_files} use JWT_SECRET, "
                f"{jwt_secret_key_files} use JWT_SECRET_KEY"
            )
            
    def run_diagnostics(self) -> None:
        """Run complete token validation diagnostics."""
        print("Token Validation Issues Diagnostic")
        print("=" * 50)
        
        # Check current environment variables
        print("\\n1. Environment Variable Check:")
        secrets = self.check_jwt_secret_consistency()
        for var, value in secrets.items():
            print(f"  {var}: {value[:20]}...")
            
        # Validate consistency
        print("\\n2. Secret Consistency Validation:")
        self.validate_secret_consistency(secrets)
        
        # Test encoding/decoding
        print("\\n3. Token Encoding/Decoding Test:")
        self.test_token_encoding_decoding()
        
        # Check environment files
        print("\\n4. Environment Files Analysis:")
        self.check_environment_files()
        
        # Report findings
        print("\\n" + "=" * 50)
        print("DIAGNOSTIC RESULTS")
        print("=" * 50)
        
        if self.issues_found:
            print("\\nISSUES FOUND:")
            for issue in self.issues_found:
                print(f"  {issue}")
        else:
            print("\\nNo token validation issues detected!")
            
        print("\\n" + "=" * 50)

def main():
    """Run token validation diagnostics."""
    diagnostic = TokenValidationDiagnostic()
    diagnostic.run_diagnostics()

if __name__ == "__main__":
    main()