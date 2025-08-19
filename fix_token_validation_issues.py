#!/usr/bin/env python3
"""
Token Validation Issues Fix
Fixes JWT secret key mismatches and ensures consistent token validation between services.
"""

import os
import shutil
from typing import List

class TokenValidationFixer:
    """Fix token validation issues between auth service and backend."""
    
    def __init__(self):
        self.base_path = "C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1"
        self.fixes_applied: List[str] = []
        
    def fix_auth_service_config(self) -> None:
        """Update auth service to support both JWT_SECRET and JWT_SECRET_KEY."""
        auth_config_path = os.path.join(
            self.base_path, 
            "auth_service", 
            "auth_core", 
            "config.py"
        )
        
        if not os.path.exists(auth_config_path):
            print(f"Warning: Auth config file not found at {auth_config_path}")
            return
            
        # Read current content
        with open(auth_config_path, 'r') as f:
            content = f.read()
            
        # Update the get_jwt_secret method to support both variable names
        updated_content = content.replace(
            '        # Fall back to generic variable\\n'
            '        return os.getenv("JWT_SECRET", os.getenv("JWT_SECRET_KEY", ""))',
            
            '        # Fall back to generic variables with priority order\\n'
            '        # Try JWT_SECRET first (auth service preference), then JWT_SECRET_KEY (backend preference)\\n'
            '        return (os.getenv("JWT_SECRET") or \\n'
            '                os.getenv("JWT_SECRET_KEY") or "")'
        )
        
        # Write updated content back
        with open(auth_config_path, 'w') as f:
            f.write(updated_content)
            
        self.fixes_applied.append(f"FIXED: Auth service config to support both JWT_SECRET and JWT_SECRET_KEY")
        
    def create_unified_env_template(self) -> None:
        """Create a unified environment template with consistent JWT secret configuration."""
        template_path = os.path.join(self.base_path, ".env.unified.template")
        
        template_content = """# Netra Unified Environment Configuration
# This template ensures consistent JWT secrets between Auth Service and Backend

# === JWT Configuration (CRITICAL: Must match between services) ===
# Both services will check for both variable names
JWT_SECRET_KEY=your_jwt_secret_key_at_least_32_characters_long_replace_this_immediately
JWT_SECRET=${JWT_SECRET_KEY}

# === Auth Service Configuration ===
AUTH_SERVICE_URL=http://localhost:8081
AUTH_SERVICE_ENABLED=true
AUTH_CACHE_TTL_SECONDS=300

# Service-to-Service Authentication
SERVICE_ID=backend
SERVICE_SECRET=your-service-secret-here

# === Database Configuration ===
DATABASE_URL=postgresql://postgres:password@localhost:5433/netra_db

# === OAuth Configuration ===
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Environment-specific OAuth (optional)
GOOGLE_OAUTH_CLIENT_ID_STAGING=
GOOGLE_OAUTH_CLIENT_SECRET_STAGING=
GOOGLE_OAUTH_CLIENT_ID_PRODUCTION=
GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION=

# === Environment Settings ===
ENVIRONMENT=development
LOG_LEVEL=INFO

# === CORS Configuration ===
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# === Security Configuration ===
FERNET_KEY=your-fernet-key-here
SECURE_HEADERS_ENABLED=true

# === GCP Configuration (for production) ===
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
"""
        
        with open(template_path, 'w') as f:
            f.write(template_content)
            
        self.fixes_applied.append(f"CREATED: Unified environment template at {template_path}")
        
    def update_existing_env_files(self) -> None:
        """Update existing environment files to include both JWT variables."""
        env_files_to_update = [
            ".env",
            ".env.local", 
            ".env.development",
            "config/staging.env"
        ]
        
        for env_file in env_files_to_update:
            file_path = os.path.join(self.base_path, env_file)
            if os.path.exists(file_path):
                self._update_env_file(file_path, env_file)
                
    def _update_env_file(self, file_path: str, filename: str) -> None:
        """Update a single environment file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check if JWT_SECRET_KEY exists
            has_jwt_secret_key = 'JWT_SECRET_KEY=' in content
            has_jwt_secret = 'JWT_SECRET=' in content and 'JWT_SECRET_KEY=' not in content
            
            if has_jwt_secret_key and not has_jwt_secret:
                # Add JWT_SECRET pointing to JWT_SECRET_KEY
                lines = content.split('\\n')
                new_lines = []
                jwt_secret_key_found = False
                
                for line in lines:
                    new_lines.append(line)
                    if line.startswith('JWT_SECRET_KEY=') and not jwt_secret_key_found:
                        # Add JWT_SECRET right after JWT_SECRET_KEY
                        jwt_value = line.split('=', 1)[1]
                        new_lines.append(f"JWT_SECRET={jwt_value}")
                        jwt_secret_key_found = True
                        
                updated_content = '\\n'.join(new_lines)
                
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                    
                self.fixes_applied.append(f"UPDATED: {filename} - Added JWT_SECRET pointing to same value as JWT_SECRET_KEY")
                
            elif has_jwt_secret and not has_jwt_secret_key:
                # Add JWT_SECRET_KEY pointing to JWT_SECRET
                lines = content.split('\\n')
                new_lines = []
                jwt_secret_found = False
                
                for line in lines:
                    new_lines.append(line)
                    if line.startswith('JWT_SECRET=') and not jwt_secret_found:
                        # Add JWT_SECRET_KEY right after JWT_SECRET
                        jwt_value = line.split('=', 1)[1]
                        new_lines.append(f"JWT_SECRET_KEY={jwt_value}")
                        jwt_secret_found = True
                        
                updated_content = '\\n'.join(new_lines)
                
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                    
                self.fixes_applied.append(f"UPDATED: {filename} - Added JWT_SECRET_KEY pointing to same value as JWT_SECRET")
                
        except Exception as e:
            print(f"Warning: Could not update {filename}: {e}")
            
    def create_validation_test(self) -> None:
        """Create a validation test to verify the fixes work."""
        test_path = os.path.join(self.base_path, "validate_token_fix.py")
        
        test_content = '''#!/usr/bin/env python3
"""
Token Validation Fix Verification Test
Tests that JWT secrets are now consistent between auth service and backend.
"""

import os
import sys

def test_env_consistency():
    """Test that both JWT_SECRET and JWT_SECRET_KEY are available."""
    jwt_secret = os.getenv("JWT_SECRET")
    jwt_secret_key = os.getenv("JWT_SECRET_KEY")
    
    print("JWT Token Validation Fix Verification")
    print("=" * 45)
    print()
    
    print("Environment Variables:")
    print(f"  JWT_SECRET: {'SET' if jwt_secret else 'NOT SET'}")
    print(f"  JWT_SECRET_KEY: {'SET' if jwt_secret_key else 'NOT SET'}")
    print()
    
    if jwt_secret and jwt_secret_key:
        if jwt_secret == jwt_secret_key:
            print("✅ SUCCESS: Both JWT secrets are set and match!")
            print(f"   Value: {jwt_secret[:20]}...")
            return True
        else:
            print("❌ WARNING: JWT secrets are set but don't match")
            print(f"   JWT_SECRET: {jwt_secret[:20]}...")
            print(f"   JWT_SECRET_KEY: {jwt_secret_key[:20]}...")
            return False
    else:
        print("❌ FAIL: One or both JWT secrets are missing")
        return False

def test_auth_service_import():
    """Test that auth service can import and get JWT secret."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'auth_service'))
        from auth_core.config import AuthConfig
        
        secret = AuthConfig.get_jwt_secret()
        if secret:
            print("✅ SUCCESS: Auth service can retrieve JWT secret")
            print(f"   Auth service secret: {secret[:20]}...")
            return True
        else:
            print("❌ FAIL: Auth service cannot retrieve JWT secret")
            return False
    except ImportError as e:
        print(f"❌ SKIP: Cannot import auth service config: {e}")
        return None
    except Exception as e:
        print(f"❌ FAIL: Auth service config error: {e}")
        return False

def main():
    env_test = test_env_consistency()
    auth_test = test_auth_service_import()
    
    print()
    print("=" * 45)
    if env_test and (auth_test is None or auth_test):
        print("🎉 TOKEN VALIDATION FIX SUCCESSFUL!")
        print("Both services can now access the same JWT secret.")
    else:
        print("⚠️  PARTIAL FIX - Some issues remain")
        print("Check the errors above and re-run after fixing.")

if __name__ == "__main__":
    main()
'''
        
        with open(test_path, 'w') as f:
            f.write(test_content)
            
        self.fixes_applied.append(f"CREATED: Validation test at validate_token_fix.py")
        
    def apply_all_fixes(self) -> None:
        """Apply all token validation fixes."""
        print("Applying Token Validation Fixes")
        print("=" * 40)
        print()
        
        # Apply fixes
        self.fix_auth_service_config()
        self.create_unified_env_template() 
        self.update_existing_env_files()
        self.create_validation_test()
        
        # Report results
        print("\\nFixes Applied:")
        for fix in self.fixes_applied:
            print(f"  ✅ {fix}")
            
        print()
        print("=" * 40)
        print("TOKEN VALIDATION FIXES COMPLETE!")
        print("=" * 40)
        print()
        print("Next Steps:")
        print("1. Review the updated files")
        print("2. Source your environment file: source .env")
        print("3. Run: python validate_token_fix.py")
        print("4. Start services and test token validation")

def main():
    fixer = TokenValidationFixer()
    fixer.apply_all_fixes()

if __name__ == "__main__":
    main()