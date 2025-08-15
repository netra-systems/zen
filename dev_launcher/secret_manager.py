"""
Secret management for development environment.
"""

import os
import sys
import json
import socket
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SecretLoader:
    """
    Enhanced secret loader with support for multiple sources.
    
    This class loads secrets from environment files and Google Cloud Secret Manager,
    providing detailed visibility into the loading process.
    """
    
    def __init__(self, 
                 project_id: Optional[str] = None, 
                 verbose: bool = False,
                 project_root: Optional[Path] = None):
        """
        Initialize the secret loader.
        
        Args:
            project_id: Google Cloud project ID
            verbose: Whether to show verbose output
            project_root: Project root directory
        """
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT', "304612253870")
        self.verbose = verbose
        self.project_root = project_root or Path.cwd()
        self.loaded_secrets: Dict[str, str] = {}
        self.failed_secrets: List[Tuple[str, str]] = []
        
    def load_from_env_file(self, env_file: Optional[Path] = None) -> Dict[str, Tuple[str, str]]:
        """
        Load secrets from an environment file.
        
        Args:
            env_file: Path to the .env file
        
        Returns:
            Dictionary mapping environment variable names to (value, source) tuples
        """
        if env_file is None:
            env_file = self.project_root / ".env"
        
        loaded = {}
        
        if env_file.exists():
            logger.info(f"Loading from existing .env file: {env_file}")
            
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        loaded[key] = (value.strip('"\''), "env_file")
                        
                        if self.verbose:
                            # Show masked value for sensitive data
                            masked_value = self._mask_value(value)
                            logger.debug(f"  Loaded {key}: {masked_value} (from .env file)")
        else:
            logger.debug(f"No .env file found at {env_file}")
        
        return loaded
    
    def load_from_google_secrets(self) -> Dict[str, Tuple[str, str]]:
        """
        Load secrets from Google Secret Manager.
        
        Returns:
            Dictionary mapping environment variable names to (value, source) tuples
        """
        logger.info(f"Loading secrets from Google Cloud Secret Manager")
        logger.info(f"  Project ID: {self.project_id}")
        
        try:
            from google.cloud import secretmanager
            
            # Create client with timeout
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(10)
            
            try:
                client = secretmanager.SecretManagerServiceClient()
                logger.info("  Connected to Secret Manager")
            finally:
                socket.setdefaulttimeout(original_timeout)
                
        except ImportError:
            logger.error("  Google Cloud SDK not installed")
            return {}
        except Exception as e:
            logger.error(f"  Failed to connect: {e}")
            return {}
        
        # Define the secrets to fetch
        secret_mappings = self._get_secret_mappings()
        
        loaded = {}
        logger.info(f"  Fetching {len(secret_mappings)} secrets...")
        
        for secret_name, env_var in secret_mappings.items():
            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(name=name)
                value = response.payload.data.decode("UTF-8")
                loaded[env_var] = (value, "google_secret")
                
                # Show success with masked value
                masked_value = self._mask_value(value)
                logger.info(f"  Loaded {env_var}: {masked_value} (from Google Secret: {secret_name})")
                
            except Exception as e:
                self.failed_secrets.append((env_var, str(e)))
                if self.verbose:
                    logger.warning(f"  Failed to load {env_var}: {str(e)[:50]}")
        
        return loaded
    
    def _get_secret_mappings(self) -> Dict[str, str]:
        """Get the mapping of secret names to environment variables."""
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
            "redis-default": "REDIS_PASSWORD",
            "anthropic-api-key": "ANTHROPIC_API_KEY",
            "openai-api-key": "OPENAI_API_KEY",
        }
    
    def _get_static_config(self) -> Dict[str, Tuple[str, str]]:
        """Get static configuration values - only non-sensitive defaults."""
        return {
            # Environment setting
            "ENVIRONMENT": ("development", "static"),
            
            # Service hosts and ports only - no credentials
            "REDIS_HOST": ("localhost", "static"),
            "REDIS_PORT": ("6379", "static"),
            
            # Note: DATABASE_URL should come from .env files only
            # Removed hardcoded credentials for security
        }
    
    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value for display."""
        if len(value) > 8:
            return value[:3] + "***" + value[-3:]
        elif len(value) > 3:
            return value[:3] + "***"
        else:
            return "***"
    
    def load_all_secrets(self) -> bool:
        """
        Load secrets from all sources with priority.
        Priority order:
        1. Existing OS environment variables (highest priority)
        2. .env.development.local (Terraform-generated)
        3. .env.development (development overrides)
        4. .env file (base configuration)
        5. Google Secret Manager
        6. Static config (fallback)
        
        Returns:
            True if secrets were loaded successfully
        """
        logger.info("=" * 70)
        # Use ASCII for Windows compatibility
        logger.info("[LOCK] SECRET AND ENVIRONMENT VARIABLE LOADING PROCESS")
        logger.info("=" * 70)
        
        # Track all environment variables and their sources
        env_tracking = {}
        
        # 1. First capture existing OS environment variables
        logger.info("\n[STEP 1] Checking existing OS environment variables...")
        existing_env = {}
        relevant_keys = set(self._get_secret_mappings().values()) | set(self._get_static_config().keys())
        for key in os.environ:
            if key in relevant_keys or key.startswith(("CLICKHOUSE_", "REDIS_", "GOOGLE_", "JWT_", "LANGFUSE_")):
                existing_env[key] = (os.environ[key], "os_environment")
                logger.info(f"  [OK] Found {key} in OS environment")
        
        # 2. Load from .env file (base configuration)
        logger.info("\n[STEP 2] Loading from .env file...")
        env_file = self.project_root / ".env"
        env_secrets = {}
        if env_file.exists():
            logger.info(f"  [FILE] Reading: {env_file}")
            env_secrets = self.load_from_env_file(env_file)
            logger.info(f"  [OK] Loaded {len(env_secrets)} variables from .env")
        else:
            logger.info(f"  [WARN] No .env file found at {env_file}")
        
        # 3. Load from .env.development (development overrides)
        logger.info("\n[STEP 3] Loading from .env.development...")
        dev_env_file = self.project_root / ".env.development"
        dev_secrets = {}
        if dev_env_file.exists():
            logger.info(f"  [FILE] Reading: {dev_env_file}")
            dev_secrets = self.load_from_env_file(dev_env_file)
            logger.info(f"  [OK] Loaded {len(dev_secrets)} variables from .env.development")
        else:
            logger.info(f"  [WARN] No .env.development file found")
        
        # 4. Load from Terraform-generated .env.development.local
        logger.info("\n[STEP 4] Loading from .env.development.local (Terraform)...")
        terraform_env_file = self.project_root / ".env.development.local"
        terraform_secrets = {}
        if terraform_env_file.exists():
            logger.info(f"  [FILE] Reading: {terraform_env_file}")
            terraform_secrets = self.load_from_env_file(terraform_env_file)
            logger.info(f"  [OK] Loaded {len(terraform_secrets)} variables from Terraform config")
        else:
            logger.info(f"  [WARN] No Terraform-generated file found")
        
        # 5. Try Google Secret Manager (if no Terraform config)
        logger.info("\n[STEP 5] Loading from Google Secret Manager...")
        google_secrets = {}
        if self.project_id and not terraform_secrets:
            google_secrets = self.load_from_google_secrets()
            logger.info(f"  [OK] Loaded {len(google_secrets)} secrets from Google")
        elif terraform_secrets:
            logger.info("  [SKIP] Skipping (using Terraform config instead)")
        else:
            logger.info("  [WARN] No project ID configured")
        
        # 6. Add static configuration (fallback)
        logger.info("\n[STEP 6] Adding static configuration defaults...")
        static_config = self._get_static_config()
        logger.info(f"  [OK] {len(static_config)} static defaults available")
        
        # Merge with proper precedence (reverse order - last wins)
        logger.info("\n[MERGE] MERGING WITH PRECEDENCE (highest to lowest):")
        logger.info("  1. OS Environment Variables (highest)")
        logger.info("  2. .env.development.local (Terraform)")
        logger.info("  3. .env.development")
        logger.info("  4. .env")
        logger.info("  5. Google Secret Manager")
        logger.info("  6. Static defaults (lowest)")
        
        # Start with static, then layer on top
        all_secrets = {}
        
        # Add in reverse precedence order
        for source, secrets, name in [
            ("static", static_config, "Static defaults"),
            ("google", google_secrets, "Google Secret Manager"),
            ("env", env_secrets, ".env file"),
            ("dev", dev_secrets, ".env.development"),
            ("terraform", terraform_secrets, ".env.development.local"),
            ("os", existing_env, "OS Environment")
        ]:
            if secrets:
                for key, value_tuple in secrets.items():
                    if isinstance(value_tuple, tuple):
                        value, _ = value_tuple
                    else:
                        value = value_tuple
                    
                    if key in all_secrets:
                        old_value, old_source = all_secrets[key]
                        if old_value != value:
                            logger.debug(f"  [OVERRIDE] {key}: overridden by {name}")
                    
                    all_secrets[key] = (value, source)
        
        # Set environment variables and track
        logger.info("\n[FINAL] ENVIRONMENT VARIABLES:")
        logger.info("-" * 60)
        
        categories = self._get_secret_categories()
        for category, keys in categories.items():
            has_vars = any(k in all_secrets for k in keys)
            if has_vars:
                logger.info(f"\n{category}:")
                for key in keys:
                    if key in all_secrets:
                        value, source = all_secrets[key]
                        os.environ[key] = value
                        self.loaded_secrets[key] = source
                        masked = self._mask_value(value)
                        logger.info(f"  {key}: {masked} (from: {source})")
        
        # Log any uncategorized variables
        categorized = set()
        for keys in categories.values():
            categorized.update(keys)
        
        uncategorized = {k: v for k, v in all_secrets.items() if k not in categorized}
        if uncategorized:
            logger.info("\nOther:")
            for key, (value, source) in uncategorized.items():
                os.environ[key] = value
                self.loaded_secrets[key] = source
                masked = self._mask_value(value)
                logger.info(f"  {key}: {masked} (from: {source})")
        
        # Summary
        self._print_detailed_summary()
        
        return True
    
    def _print_summary(self):
        """Print a summary of loaded secrets."""
        logger.info("=" * 60)
        logger.info("Secret Loading Summary:")
        
        sources: Dict[str, int] = {}
        for source in self.loaded_secrets.values():
            sources[source] = sources.get(source, 0) + 1
        
        total = len(self.loaded_secrets)
        logger.info(f"  Total secrets loaded: {total}")
        
        for source, count in sources.items():
            logger.info(f"  - From {source}: {count}")
        
        if self.failed_secrets and self.verbose:
            logger.warning(f"  Failed to load {len(self.failed_secrets)} secrets:")
            for secret, error in self.failed_secrets[:3]:
                logger.warning(f"    - {secret}: {error[:50]}")
        
        logger.info("=" * 60)
    
    def _print_detailed_summary(self):
        """Print a detailed summary of loaded environment variables."""
        logger.info("\n" + "=" * 70)
        logger.info("[STATS] ENVIRONMENT VARIABLE LOADING SUMMARY")
        logger.info("=" * 70)
        
        # Count by source
        sources: Dict[str, int] = {}
        for source in self.loaded_secrets.values():
            readable_source = {
                "os": "OS Environment",
                "terraform": ".env.development.local (Terraform)",
                "dev": ".env.development",
                "env": ".env file",
                "env_file": ".env file",
                "google": "Google Secret Manager",
                "google_secret": "Google Secret Manager",
                "static": "Static defaults"
            }.get(source, source)
            sources[readable_source] = sources.get(readable_source, 0) + 1
        
        total = len(self.loaded_secrets)
        logger.info(f"\n[SUCCESS] Total environment variables set: {total}")
        logger.info("\n[CHART] Variables by source:")
        
        # Sort by count (descending)
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            bar_length = int(percentage / 2)
            bar = "#" * bar_length + "-" * (50 - bar_length)
            logger.info(f"  {source:35} {count:3} vars [{bar}] {percentage:.1f}%")
        
        if self.failed_secrets:
            logger.warning(f"\n[WARNING] Failed to load {len(self.failed_secrets)} secrets:")
            for secret, error in self.failed_secrets[:5]:
                logger.warning(f"  - {secret}: {error[:80]}")
        
        logger.info("\n[TIP] Environment variables from OS have highest priority")
        logger.info("[TIP] Use .env.development for local overrides")
        logger.info("=" * 70)
    
    def write_env_file_if_missing(self, secrets: Dict[str, Tuple[str, str]]) -> bool:
        """
        Write a .env file ONLY if it doesn't exist (for initial setup).
        
        Args:
            secrets: Dictionary of secrets to write
            
        Returns:
            True if file was written, False if it already exists
        """
        env_file = self.project_root / ".env"
        
        if env_file.exists():
            logger.info(f"[PRESERVE] Keeping existing .env file at {env_file}")
            return False
        
        logger.info(f"[CREATE] Creating initial .env file at {env_file}")
        
        with open(env_file, 'w') as f:
            f.write("# Initial .env file - created by dev_launcher\n")
            f.write("# This file will NOT be overwritten on subsequent runs\n")
            f.write(f"# Created at {datetime.now().isoformat()}\n")
            f.write("#\n")
            f.write("# Priority order (highest to lowest):\n")
            f.write("# 1. OS Environment Variables\n")
            f.write("# 2. .env.development.local (Terraform-generated)\n") 
            f.write("# 3. .env.development (your local overrides)\n")
            f.write("# 4. .env (this file - base configuration)\n")
            f.write("# 5. Google Secret Manager\n")
            f.write("# 6. Static defaults\n\n")
            
            # Group by category
            categories = self._get_secret_categories()
            
            for category, keys in categories.items():
                has_values = any(k in secrets for k in keys)
                if has_values:
                    f.write(f"\n# {category}\n")
                    for key in keys:
                        if key in secrets:
                            value, source = secrets[key]
                            f.write(f"{key}={value}  # from: {source}\n")
            
            # Write any remaining secrets not in categories
            categorized_keys = set()
            for keys in categories.values():
                categorized_keys.update(keys)
            
            remaining = {k: v for k, v in secrets.items() if k not in categorized_keys}
            if remaining:
                f.write("\n# Other\n")
                for key, (value, source) in remaining.items():
                    f.write(f"{key}={value}  # from: {source}\n")
        
        logger.info("[SUCCESS] Initial .env file created successfully")
        return True
    
    def _get_secret_categories(self) -> Dict[str, List[str]]:
        """Get categorized grouping of secrets."""
        return {
            "Google OAuth": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
            "API Keys": ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "ClickHouse": [
                "CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER",
                "CLICKHOUSE_DEFAULT_PASSWORD", "CLICKHOUSE_DEVELOPMENT_PASSWORD", 
                "CLICKHOUSE_DB"
            ],
            "Database": ["DATABASE_URL"],
            "Redis": ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"],
            "Langfuse": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
            "Security": ["JWT_SECRET_KEY", "FERNET_KEY"],
            "Environment": ["ENVIRONMENT"]
        }


class ServiceDiscovery:
    """
    Service discovery for development environment.
    
    This class manages service information for inter-service communication
    during development.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize service discovery.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = project_root or Path.cwd()
        self.discovery_dir = self.project_root / ".service_discovery"
        self.discovery_dir.mkdir(exist_ok=True)
    
    def write_backend_info(self, port: int):
        """Write backend service information."""
        info = {
            "port": port,
            "api_url": f"http://localhost:{port}",
            "ws_url": f"ws://localhost:{port}/ws",
            "timestamp": datetime.now().isoformat()
        }
        
        info_file = self.discovery_dir / "backend.json"
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        logger.debug(f"Wrote backend service discovery to {info_file}")
    
    def write_frontend_info(self, port: int):
        """Write frontend service information."""
        info = {
            "port": port,
            "url": f"http://localhost:{port}",
            "timestamp": datetime.now().isoformat()
        }
        
        info_file = self.discovery_dir / "frontend.json"
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        logger.debug(f"Wrote frontend service discovery to {info_file}")
    
    def read_backend_info(self) -> Optional[Dict[str, any]]:
        """Read backend service information."""
        info_file = self.discovery_dir / "backend.json"
        
        if info_file.exists():
            with open(info_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def read_frontend_info(self) -> Optional[Dict[str, any]]:
        """Read frontend service information."""
        info_file = self.discovery_dir / "frontend.json"
        
        if info_file.exists():
            with open(info_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def clear_all(self):
        """Clear all service discovery information."""
        for file in self.discovery_dir.glob("*.json"):
            file.unlink()
        
        logger.debug("Cleared all service discovery information")