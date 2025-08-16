#!/usr/bin/env python3
"""
Secret loading utilities for dev launcher.
Provides Google Cloud Secret Manager integration and local env file management.
"""

import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional, List

from .dev_launcher_config import get_project_root


class EnhancedSecretLoader:
    """Enhanced secret loader with detailed visibility."""
    
    def __init__(self, project_id: Optional[str] = None, verbose: bool = False) -> None:
        # Determine project ID based on environment
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        default_project_id = "701982941522" if environment == "staging" else "304612253870"
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT', default_project_id)
        self.verbose = verbose
        self.loaded_secrets: Dict[str, str] = {}
        self.failed_secrets: List[Tuple[str, str]] = []
        
    def load_from_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load secrets from existing .env file."""
        env_file = get_project_root() / ".env"
        loaded = {}
        
        if env_file.exists():
            print("[ENV] Loading from existing .env file...")
            loaded = self._parse_env_file(env_file)
        
        return loaded
    
    def _parse_env_file(self, env_file: Path) -> Dict[str, Tuple[str, str]]:
        """Parse environment file and return key-value pairs."""
        loaded = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    loaded[key] = (value.strip('"\''), "env_file")
                    if self.verbose:
                        self._print_masked_secret(key, value, "env_file")
        return loaded
    
    def _print_masked_secret(self, key: str, value: str, source: str) -> None:
        """Print secret with masked value for security."""
        masked_value = value[:3] + "***" if len(value) > 3 else "***"
        print(f"   [OK] {key}: {masked_value} (from {source})")
    
    def load_from_google_secrets(self) -> Dict[str, Tuple[str, str]]:
        """Load secrets from Google Secret Manager with detailed feedback."""
        print(f"\n[SECRETS] Loading secrets from Google Cloud Secret Manager...")
        print(f"   Project ID: {self.project_id}")
        
        try:
            client = self._create_secret_manager_client()
            print("   [OK] Connected to Secret Manager")
        except ImportError:
            print("   ❌ Google Cloud SDK not installed")
            return {}
        except Exception as e:
            print(f"   ❌ Failed to connect: {e}")
            return {}
        
        return self._fetch_all_secrets(client)
    
    def _create_secret_manager_client(self):
        """Create Google Secret Manager client with timeout."""
        from google.cloud import secretmanager
        
        # Create client with timeout
        socket.setdefaulttimeout(10)
        return secretmanager.SecretManagerServiceClient()
    
    def _fetch_all_secrets(self, client) -> Dict[str, Tuple[str, str]]:
        """Fetch all required secrets from Google Cloud."""
        secret_mappings = self._get_secret_mappings()
        loaded = {}
        
        print(f"\n   Fetching {len(secret_mappings)} secrets:")
        
        for secret_name, env_var in secret_mappings.items():
            try:
                value = self._fetch_single_secret(client, secret_name)
                loaded[env_var] = (value, "google_secret")
                self._print_masked_secret(env_var, value, f"Google Secret: {secret_name}")
            except Exception as e:
                self.failed_secrets.append((env_var, str(e)))
                if self.verbose:
                    print(f"   [FAIL] {env_var}: Failed - {str(e)[:50]}")
        
        return loaded
    
    def _get_secret_mappings(self) -> Dict[str, str]:
        """Get mapping of secret names to environment variables."""
        return {
            "gemini-api-key": "GEMINI_API_KEY",
            "google-client-id": "GOOGLE_CLIENT_ID",
            "google-client-secret": "GOOGLE_CLIENT_SECRET",
            "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
            "langfuse-public-key": "LANGFUSE_PUBLIC_KEY",
            "clickhouse-default-password": "CLICKHOUSE_DEFAULT_PASSWORD",
            "clickhouse-development-password": "CLICKHOUSE_DEVELOPMENT_PASSWORD",
            "jwt-secret-key": "JWT_SECRET_KEY",
            "fernet-key": "FERNET_KEY",
            "redis-default": "REDIS_PASSWORD"
        }
    
    def _fetch_single_secret(self, client, secret_name: str) -> str:
        """Fetch a single secret from Google Cloud."""
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")
    
    def load_all_secrets(self) -> bool:
        """Load secrets from all sources with priority."""
        print("\n[SECRETS] Loading Process Started")
        print("=" * 60)
        
        # First, try to load from existing .env file
        env_secrets = self.load_from_env_file()
        
        # Then try Google Secret Manager
        google_secrets = self.load_from_google_secrets()
        
        # Merge with Google secrets taking priority
        all_secrets = {**env_secrets, **google_secrets}
        
        return self._finalize_secret_loading(all_secrets)
    
    def _finalize_secret_loading(self, all_secrets: Dict[str, Tuple[str, str]]) -> bool:
        """Finalize secret loading process."""
        # Add static configuration
        static_config = self._get_static_config()
        
        print("\n[CONFIG] Adding static configuration:")
        for key, (value, source) in static_config.items():
            if key not in all_secrets:
                all_secrets[key] = (value, source)
                if self.verbose:
                    print(f"   [OK] {key}: {value} (static config)")
        
        # Set environment variables
        self._set_environment_variables(all_secrets)
        
        # Print summary and write env file
        self._print_summary()
        self._write_env_file(all_secrets)
        
        print("=" * 60)
        return True
    
    def _get_static_config(self) -> Dict[str, Tuple[str, str]]:
        """Get static configuration values."""
        return {
            "CLICKHOUSE_HOST": ("xedvrr4c3r.us-central1.gcp.clickhouse.cloud", "static"),
            "CLICKHOUSE_PORT": ("8443", "static"),
            "CLICKHOUSE_USER": ("default", "static"),
            "CLICKHOUSE_DB": ("default", "static"),
            "ENVIRONMENT": ("development", "static")
        }
    
    def _set_environment_variables(self, all_secrets: Dict[str, Tuple[str, str]]) -> None:
        """Set environment variables from loaded secrets."""
        print("\n[ENV] Setting environment variables...")
        for key, (value, source) in all_secrets.items():
            os.environ[key] = value
            self.loaded_secrets[key] = source
    
    def _print_summary(self) -> None:
        """Print summary of loaded secrets."""
        print("\n" + "=" * 60)
        print("[SUMMARY] Secret Loading Summary:")
        
        sources = {}
        for key, source in self.loaded_secrets.items():
            sources[source] = sources.get(source, 0) + 1
        
        total = len(self.loaded_secrets)
        print(f"   Total secrets loaded: {total}")
        for source, count in sources.items():
            print(f"   - From {source}: {count}")
        
        if self.failed_secrets and self.verbose:
            self._print_failed_secrets()
    
    def _print_failed_secrets(self) -> None:
        """Print information about failed secret loads."""
        print(f"\n   [WARNING] Failed to load {len(self.failed_secrets)} secrets:")
        for secret, error in self.failed_secrets[:3]:
            print(f"      - {secret}: {error[:50]}")
    
    def _write_env_file(self, secrets: Dict[str, Tuple[str, str]]) -> None:
        """Write secrets to .env file ONLY if it doesn't exist."""
        env_file = get_project_root() / ".env"
        
        if env_file.exists():
            print(f"\n[PRESERVE] Keeping existing .env file at {env_file}")
            print("[INFO] Use .env.development for local overrides")
            return
        
        print(f"\n[CREATE] Creating initial .env file at {env_file}")
        
        with open(env_file, 'w') as f:
            self._write_env_file_header(f)
            self._write_env_file_categories(f, secrets)
    
    def _write_env_file_header(self, f) -> None:
        """Write header to env file."""
        f.write("# Initial .env file - created by dev_launcher\n")
        f.write("# This file will NOT be overwritten on subsequent runs\n")
        f.write(f"# Created at {datetime.now().isoformat()}\n")
        f.write("# Use .env.development for local overrides\n\n")
    
    def _write_env_file_categories(self, f, secrets: Dict[str, Tuple[str, str]]) -> None:
        """Write categorized secrets to env file."""
        categories = self._get_env_file_categories()
        
        for category, keys in categories.items():
            f.write(f"\n# {category}\n")
            for key in keys:
                if key in secrets:
                    value, source = secrets[key]
                    f.write(f"{key}={value}\n")
    
    def _get_env_file_categories(self) -> Dict[str, List[str]]:
        """Get categories for organizing env file."""
        return {
            "Google OAuth": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
            "API Keys": ["GEMINI_API_KEY"],
            "ClickHouse": ["CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER", 
                          "CLICKHOUSE_DEFAULT_PASSWORD", "CLICKHOUSE_DEVELOPMENT_PASSWORD", "CLICKHOUSE_DB"],
            "Langfuse": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
            "Security": ["JWT_SECRET_KEY", "FERNET_KEY"],
            "Redis": ["REDIS_PASSWORD"],
            "Environment": ["ENVIRONMENT"]
        }