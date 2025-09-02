from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Setup development OAuth credentials securely.
This script helps configure OAuth credentials for local development.
"""
import os
import sys
from pathlib import Path
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_oauth_credentials():
    """Setup OAuth credentials for development environment."""
    print("Setting up OAuth credentials for development environment...")
    print("-" * 60)
    
    # OAuth credentials for development
    # TOMBSTONE: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET superseded by environment-specific variables
    GOOGLE_OAUTH_CLIENT_ID_DEV = "304612253870-bqie9nvlaokfc2noos1nu5st614vlqam.apps.googleusercontent.com"
    GOOGLE_OAUTH_CLIENT_SECRET_DEV = "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"
    
    # Path to .env file
    env_file = project_root / ".env"
    env_template = project_root / ".env.unified.template"
    
    # Check if .env exists, if not create from template
    if not env_file.exists():
        print(f"Creating .env file from template...")
        if env_template.exists():
            shutil.copy(env_template, env_file)
            print(f"  Created .env from template")
        else:
            print(f"  Creating new .env file")
            env_file.touch()
    
    # Read existing .env content
    existing_content = env_file.read_text()
    lines = existing_content.splitlines()
    
    # OAuth variables to set
    # TOMBSTONE: Removed generic GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
    # Only set environment-specific variables
    oauth_vars = {
        "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": GOOGLE_OAUTH_CLIENT_ID_DEV,
        "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT": GOOGLE_OAUTH_CLIENT_SECRET_DEV,
    }
    
    # Update or add OAuth variables
    updated_lines = []
    vars_updated = set()
    
    for line in lines:
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith("#"):
            updated_lines.append(line)
            continue
        
        # Check if this line contains one of our OAuth variables
        for var_name, var_value in oauth_vars.items():
            if line.startswith(f"{var_name}="):
                updated_lines.append(f"{var_name}={var_value}")
                vars_updated.add(var_name)
                print(f"  Updated: {var_name}")
                break
        else:
            # Line doesn't contain OAuth variable, keep it as is
            updated_lines.append(line)
    
    # Add any missing OAuth variables
    for var_name, var_value in oauth_vars.items():
        if var_name not in vars_updated:
            updated_lines.append(f"{var_name}={var_value}")
            print(f"  Added: {var_name}")
    
    # Write back to .env
    env_file.write_text("\n".join(updated_lines) + "\n")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] OAuth credentials configured for development!")
    print("=" * 60)
    print("\nConfiguration details:")
    print(f"  Client ID: {GOOGLE_OAUTH_CLIENT_ID_DEV[:40]}...")
    print(f"  Client Secret: {GOOGLE_OAUTH_CLIENT_SECRET_DEV[:10]}... (hidden)")
    print("\nGoogle OAuth Console Configuration:")
    print("  Authorized JavaScript origins:")
    print("    - http://localhost:3000")
    print("    - http://localhost:8000")
    print("    - http://localhost:8081")
    print("  Authorized redirect URIs:")
    print("    - http://localhost:3000/auth/callback")
    print("\nYou can now run:")
    print("  python scripts/dev_launcher.py")
    print("\nAnd OAuth login should work at:")
    print("  http://localhost:3000/login")
    
    return True

def verify_oauth_setup():
    """Verify OAuth is properly configured."""
    print("\nVerifying OAuth setup...")
    print("-" * 40)
    
    try:
        # Set environment to development for testing
        os.environ["ENVIRONMENT"] = "development"
        
        # Import and test
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        client_id = AuthSecretLoader.get_google_client_id()
        client_secret = AuthSecretLoader.get_google_client_secret()
        
        if client_id and len(client_id) > 40:
            print(f"  [OK] Client ID loaded: {client_id[:40]}...")
        else:
            print(f"  [WARN] Client ID not properly loaded")
            return False
            
        if client_secret and len(client_secret) > 10:
            print(f"  [OK] Client Secret loaded: {'*' * 10}")
        else:
            print(f"  [WARN] Client Secret not properly loaded")
            return False
            
        print("\n[SUCCESS] OAuth verification passed!")
        return True
        
    except Exception as e:
        print(f"  [ERROR] OAuth verification failed: {e}")
        return False

if __name__ == "__main__":
    success = setup_oauth_credentials()
    if success:
        verify_oauth_setup()
    sys.exit(0 if success else 1)
