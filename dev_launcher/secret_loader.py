"""
Simplified secret loader with single source and remote fallback.
"""

import os
import socket
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Set
import logging

from dev_launcher.env_file_loader import EnvFileLoader

logger = logging.getLogger(__name__)


class SecretLoader:
    """
    Simplified secret loader with single source (.env) and remote fallback.
    
    Primary source: .env file (user-controlled)
    Fallback: Google Cloud Secret Manager (for missing secrets only)
    """
    
    def __init__(self, 
                 project_id: Optional[str] = None, 
                 verbose: bool = False,
                 project_root: Optional[Path] = None,
                 use_remote_fallback: bool = True):
        """Initialize the secret loader."""
        self.project_id = self._determine_project_id(project_id)
        self.verbose = verbose
        self.project_root = project_root or Path.cwd()
        self.use_remote_fallback = use_remote_fallback
        self.loaded_secrets: Dict[str, str] = {}
        self.failed_secrets: List[Tuple[str, str]] = []
        self.env_file_loader = EnvFileLoader(self.project_root, verbose)
    
    def _determine_project_id(self, project_id: Optional[str]) -> str:
        """Determine project ID based on environment."""
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        default_project_id = "701982941522" if environment == "staging" else "304612253870"
        return project_id or os.environ.get('GOOGLE_CLOUD_PROJECT', default_project_id)
    
    def load_all_secrets(self) -> bool:
        """
        Load secrets with simplified strategy:
        1. Load from .env file (primary source)
        2. Check for missing required secrets
        3. Fallback to Google Secret Manager for missing ones only
        """
        logger.info("=" * 70)
        logger.info("[SECRET LOADER] Simplified Environment Loading")
        logger.info("=" * 70)
        
        # Step 1: Capture existing OS environment
        existing_env = self._capture_existing_env()
        
        # Step 2: Load from .env file (single source)
        env_secrets = self.env_file_loader.load_env_file()
        
        # Step 3: Get required secrets list
        required_secrets = self._get_required_secrets()
        
        # Step 4: Check what's missing
        missing = self._check_missing_secrets(env_secrets, existing_env, required_secrets)
        
        # Step 5: Fallback to Google Secret Manager if needed
        google_secrets = {}
        if missing and self.use_remote_fallback:
            google_secrets = self._load_missing_from_google(missing)
        
        # Step 6: Merge and set environment
        self._merge_and_set_environment(existing_env, env_secrets, google_secrets)
        
        return True
    
    def _capture_existing_env(self) -> Dict[str, Tuple[str, str]]:
        """Capture existing OS environment variables."""
        required_keys = self._get_required_secrets()
        return self.env_file_loader.capture_existing_env(required_keys)
    
    def _get_required_secrets(self) -> Set[str]:
        """Get list of required secret keys."""
        return {
            "GEMINI_API_KEY",
            "GOOGLE_CLIENT_ID", 
            "GOOGLE_CLIENT_SECRET",
            "LANGFUSE_SECRET_KEY",
            "LANGFUSE_PUBLIC_KEY",
            "CLICKHOUSE_DEFAULT_PASSWORD",
            "CLICKHOUSE_DEVELOPMENT_PASSWORD",
            "JWT_SECRET_KEY",
            "FERNET_KEY",
            "REDIS_PASSWORD",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            # Static configs that can be overridden
            "ENVIRONMENT",
            "REDIS_HOST",
            "REDIS_PORT",
            "CLICKHOUSE_HOST",
            "CLICKHOUSE_PORT",
            "CLICKHOUSE_USER",
            "CLICKHOUSE_DB",
        }
    
    def _check_missing_secrets(self, env_secrets: Dict, existing_env: Dict, 
                               required: Set[str]) -> Set[str]:
        """Check which required secrets are missing."""
        loaded_keys = set(env_secrets.keys()) | set(existing_env.keys())
        missing = required - loaded_keys
        
        if missing:
            logger.info(f"\n[MISSING] {len(missing)} required secrets not in .env or OS:")
            for key in sorted(missing):
                logger.info(f"  - {key}")
        else:
            logger.info("\n[OK] All required secrets found in .env or OS")
        
        return missing
    
    def _load_missing_from_google(self, missing_keys: Set[str]) -> Dict[str, Tuple[str, str]]:
        """Load only missing secrets from Google Secret Manager."""
        logger.info(f"\n[FALLBACK] Loading {len(missing_keys)} missing secrets from Google...")
        logger.info(f"  Project ID: {self.project_id}")
        
        client = self._create_secret_manager_client()
        if not client:
            logger.warning("  [WARN] Cannot connect to Google Secret Manager")
            return {}
        
        return self._fetch_missing_secrets(client, missing_keys)
    
    def _create_secret_manager_client(self):
        """Create Google Secret Manager client."""
        try:
            from google.cloud import secretmanager
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(10)
            try:
                client = secretmanager.SecretManagerServiceClient()
                logger.info("  [OK] Connected to Secret Manager")
                return client
            finally:
                socket.setdefaulttimeout(original_timeout)
        except ImportError:
            logger.error("  [ERROR] Google Cloud SDK not installed")
            return None
        except Exception as e:
            logger.error(f"  [ERROR] Failed to connect: {e}")
            return None
    
    def _fetch_missing_secrets(self, client, missing_keys: Set[str]) -> Dict[str, Tuple[str, str]]:
        """Fetch only missing secrets from Google."""
        secret_mappings = self._get_secret_mappings()
        loaded = {}
        
        for env_var in missing_keys:
            # Find the secret name for this env var
            secret_name = None
            for sname, evar in secret_mappings.items():
                if evar == env_var:
                    secret_name = sname
                    break
            
            if secret_name:
                self._fetch_single_secret(client, secret_name, env_var, loaded)
            else:
                logger.debug(f"  No Google secret mapping for {env_var}")
        
        logger.info(f"  [OK] Loaded {len(loaded)} secrets from Google")
        return loaded
    
    def _fetch_single_secret(self, client, secret_name: str, env_var: str, loaded: Dict):
        """Fetch single secret from Google Secret Manager."""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(name=name)
            value = response.payload.data.decode("UTF-8")
            loaded[env_var] = (value, "google_secret")
            if self.verbose:
                masked = self._mask_value(value)
                logger.debug(f"    Loaded {env_var}: {masked}")
        except Exception as e:
            self.failed_secrets.append((env_var, str(e)))
            if self.verbose:
                logger.debug(f"    Failed {env_var}: {str(e)[:50]}")
    
    def _get_secret_mappings(self) -> Dict[str, str]:
        """Get the mapping of Google secret names to environment variables."""
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
    
    def _get_static_defaults(self) -> Dict[str, Tuple[str, str]]:
        """Get static default values for non-sensitive configs."""
        return {
            "ENVIRONMENT": ("development", "default"),
            "REDIS_HOST": ("localhost", "default"),
            "REDIS_PORT": ("6379", "default"),
            "CLICKHOUSE_HOST": ("localhost", "default"),
            "CLICKHOUSE_PORT": ("9000", "default"),
            "CLICKHOUSE_USER": ("default", "default"),
            "CLICKHOUSE_DB": ("default", "default"),
        }
    
    def _merge_and_set_environment(self, existing_env: Dict, env_secrets: Dict, 
                                   google_secrets: Dict):
        """Merge all sources and set environment variables."""
        logger.info("\n[MERGE] Setting environment variables...")
        logger.info("Priority: OS Environment > .env file > Google Secrets > Defaults")
        
        # Start with defaults
        all_secrets = self._get_static_defaults()
        
        # Override with Google secrets (fallback)
        for key, value_tuple in google_secrets.items():
            all_secrets[key] = value_tuple
        
        # Override with .env file (primary source)
        for key, value_tuple in env_secrets.items():
            all_secrets[key] = value_tuple
        
        # Override with OS environment (highest priority)
        for key, value_tuple in existing_env.items():
            all_secrets[key] = value_tuple
        
        # Set environment variables
        self._set_environment_variables(all_secrets)
        self._print_summary()
    
    def _set_environment_variables(self, all_secrets: Dict):
        """Set environment variables and track them."""
        logger.info("\n[FINAL] Environment variables set:")
        logger.info("-" * 60)
        
        categories = self._get_secret_categories()
        
        # Set by category for better organization
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
                        logger.info(f"  {key}: {masked} [from: {source}]")
        
        # Set any uncategorized
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
                logger.info(f"  {key}: {masked} [from: {source}]")
    
    def _print_summary(self):
        """Print summary of loaded environment variables."""
        logger.info("\n" + "=" * 70)
        logger.info("[SUMMARY] Environment Loading Complete")
        logger.info("=" * 70)
        
        # Count by source
        sources = {}
        for source in self.loaded_secrets.values():
            readable = {
                "os_environment": "OS Environment",
                "env_file": ".env file",
                "google_secret": "Google Secret Manager",
                "default": "Default values"
            }.get(source, source)
            sources[readable] = sources.get(readable, 0) + 1
        
        total = len(self.loaded_secrets)
        logger.info(f"\nTotal variables set: {total}")
        logger.info("\nBy source:")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            logger.info(f"  {source:25} {count:3} ({percentage:.1f}%)")
        
        # Show failures if any
        if self.failed_secrets:
            logger.warning(f"\nFailed to load {len(self.failed_secrets)} secrets:")
            for secret, error in self.failed_secrets[:5]:
                logger.warning(f"  - {secret}: {error[:50]}")
        
        # Tips
        logger.info("\n[TIP] Create a .env file for local development")
        logger.info("[TIP] Use 'cp .env.example .env' to start from example")
        logger.info("=" * 70)
    
    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value for display."""
        if len(value) > 8:
            return value[:3] + "***" + value[-3:]
        elif len(value) > 3:
            return value[:3] + "***"
        else:
            return "***"
    
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
            "Redis": ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"],
            "Langfuse": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
            "Security": ["JWT_SECRET_KEY", "FERNET_KEY"],
            "Environment": ["ENVIRONMENT"]
        }