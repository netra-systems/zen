#!/usr/bin/env python3
"""
Centralized GCP Service Account Authentication Configuration
This module provides consistent service account authentication for all GCP operations.

Business Value: Ensures secure, consistent authentication across all GCP operations,
reducing authentication failures and improving deployment reliability.
"""

import os
import sys

# Fix Unicode encoding issues on Windows - MUST be done early
if sys.platform == "win32":
    import io
    # Set UTF-8 for subprocess and all Python I/O
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # Force Windows console to use UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass
    
    # Reconfigure stdout/stderr for UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from shared.isolated_environment import get_env


class GCPAuthConfig:
    """Centralized configuration for GCP service account authentication."""
    
    # Get project root directory (parent of scripts directory)
    PROJECT_ROOT = Path(__file__).parent.parent
    
    # Primary service account key path - MUST be used for all GCP operations
    PRIMARY_KEY_PATH = PROJECT_ROOT / "config" / "netra-staging-7a1059b7cf26.json"
    
    # Alternative key locations in priority order
    KEY_SEARCH_PATHS = [
        PRIMARY_KEY_PATH,
        PROJECT_ROOT / "config" / "netra-staging-7a1059b7cf26.json",
        Path.home() / ".netra" / "gcp-staging-sa-key.json",
        Path.home() / ".gcp" / "netra-deployer.json",
        PROJECT_ROOT / "netra-deployer-netra-staging.json",
        PROJECT_ROOT / "service-account.json",
        PROJECT_ROOT / "gcp-key.json",
    ]
    
    @classmethod
    def find_service_account_key(cls) -> Optional[Path]:
        """
        Find the service account key file.
        
        Returns:
            Path to the service account key file, or None if not found.
        """
        # Check environment variable first
        env_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if env_key:
            env_path = Path(env_key)
            if env_path.exists():
                print(f" PASS:  Using service account from environment: {env_path}")
                return env_path
            else:
                print(f" WARNING: [U+FE0F] GOOGLE_APPLICATION_CREDENTIALS points to non-existent file: {env_key}")
        
        # Check predefined paths
        for key_path in cls.KEY_SEARCH_PATHS:
            if key_path.exists():
                print(f" PASS:  Found service account key: {key_path}")
                return key_path
        
        # Search for any JSON file with service account structure
        for json_file in Path(".").glob("*.json"):
            if cls._is_service_account_key(json_file):
                print(f" PASS:  Found service account key by content: {json_file}")
                return json_file
        
        return None
    
    @staticmethod
    def _is_service_account_key(file_path: Path) -> bool:
        """Check if a JSON file is a service account key."""
        try:
            with open(file_path) as f:
                data = json.load(f)
                return (
                    data.get("type") == "service_account" and
                    "private_key" in data and
                    "client_email" in data
                )
        except (json.JSONDecodeError, IOError):
            return False
    
    @classmethod
    def setup_authentication(cls, key_path: Optional[Path] = None) -> bool:
        """
        Set up GCP authentication using service account.
        
        Args:
            key_path: Optional path to service account key. If not provided,
                     will search for key automatically.
        
        Returns:
            True if authentication was successful, False otherwise.
        """
        # Find key if not provided
        if not key_path:
            key_path = cls.find_service_account_key()
            if not key_path:
                print(" FAIL:  No service account key found!")
                print("\n[U+1F4CB] To fix this:")
                print(f"  1. Place your service account key at: {cls.PRIMARY_KEY_PATH}")
                print("  2. Or set GOOGLE_APPLICATION_CREDENTIALS environment variable")
                print("  3. Or run: python scripts/setup_gcp_service_account.py")
                return False
        
        # Verify key exists
        if not key_path.exists():
            print(f" FAIL:  Service account key file not found: {key_path}")
            return False
        
        # Set environment variable for Application Default Credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path)
        print(f" PASS:  Set GOOGLE_APPLICATION_CREDENTIALS to: {key_path}")
        
        # Activate service account in gcloud
        if not cls._activate_gcloud_service_account(key_path):
            return False
        
        return True
    
    @staticmethod
    def _activate_gcloud_service_account(key_path: Path) -> bool:
        """Activate service account in gcloud CLI."""
        gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        use_shell = sys.platform == "win32"
        
        try:
            # Extract service account email from key file
            with open(key_path) as f:
                key_data = json.load(f)
                service_account_email = key_data.get("client_email")
            
            if not service_account_email:
                print(" WARNING: [U+FE0F] Could not extract service account email from key file")
                return True  # Continue anyway, ADC will work
            
            print(f"[U+1F510] Activating service account: {service_account_email}")
            
            # Activate service account
            result = subprocess.run(
                [
                    gcloud_cmd, "auth", "activate-service-account",
                    service_account_email,
                    "--key-file", str(key_path)
                ],
                capture_output=True,
                text=True,
                shell=use_shell
            )
            
            if result.returncode == 0:
                print(" PASS:  Service account activated in gcloud")
                return True
            else:
                # Check if gcloud is not installed
                if "not found" in result.stderr or "not recognized" in result.stderr:
                    print(" WARNING: [U+FE0F] gcloud CLI not installed - using Application Default Credentials only")
                    return True  # ADC will still work
                else:
                    print(f" WARNING: [U+FE0F] Failed to activate service account in gcloud: {result.stderr}")
                    return True  # Continue anyway, ADC might work
                    
        except FileNotFoundError:
            print(" WARNING: [U+FE0F] gcloud CLI not installed - using Application Default Credentials only")
            return True  # ADC will still work
        except Exception as e:
            print(f" WARNING: [U+FE0F] Error activating service account: {e}")
            return True  # Continue anyway
    
    @classmethod
    def get_authenticated_project_id(cls) -> Optional[str]:
        """Get the project ID from the service account key."""
        key_path = cls.find_service_account_key()
        if not key_path:
            return None
        
        try:
            with open(key_path) as f:
                data = json.load(f)
                return data.get("project_id")
        except (json.JSONDecodeError, IOError):
            return None
    
    @classmethod
    def ensure_authentication(cls) -> bool:
        """
        Ensure GCP authentication is properly configured.
        This should be called at the start of any script that needs GCP access.
        
        Returns:
            True if authentication is ready, False otherwise.
        """
        # Check if already authenticated
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            creds_path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
            if creds_path.exists():
                print(f" PASS:  Already authenticated with: {creds_path}")
                return True
        
        # Set up authentication
        return cls.setup_authentication()
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """Get a summary of the current authentication configuration."""
        key_path = cls.find_service_account_key()
        
        config = {
            "authenticated": False,
            "key_path": None,
            "service_account_email": None,
            "project_id": None,
            "env_var_set": False
        }
        
        if key_path and key_path.exists():
            config["key_path"] = str(key_path)
            config["authenticated"] = True
            
            try:
                with open(key_path) as f:
                    data = json.load(f)
                    config["service_account_email"] = data.get("client_email")
                    config["project_id"] = data.get("project_id")
            except (json.JSONDecodeError, IOError):
                pass
        
        config["env_var_set"] = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
        
        return config


def main():
    """Test the authentication configuration."""
    print(" SEARCH:  GCP Authentication Configuration Check\n")
    print("=" * 60)
    
    # Get configuration summary
    config = GCPAuthConfig.get_config_summary()
    
    print("\n CHART:  Current Configuration:")
    print(f"  Authenticated: {' PASS:  Yes' if config['authenticated'] else ' FAIL:  No'}")
    print(f"  Key Path: {config['key_path'] or 'Not found'}")
    print(f"  Service Account: {config['service_account_email'] or 'Unknown'}")
    print(f"  Project ID: {config['project_id'] or 'Unknown'}")
    print(f"  Environment Variable Set: {' PASS:  Yes' if config['env_var_set'] else ' FAIL:  No'}")
    
    print("\n" + "=" * 60)
    print("\n[U+1F510] Testing Authentication Setup...")
    
    if GCPAuthConfig.ensure_authentication():
        print("\n PASS:  Authentication setup successful!")
        print("\n[U+1F4CB] You can now use any GCP script with proper authentication.")
    else:
        print("\n FAIL:  Authentication setup failed!")
        print("\n[U+1F4CB] Please follow the instructions above to configure authentication.")
        sys.exit(1)


if __name__ == "__main__":
    main()
