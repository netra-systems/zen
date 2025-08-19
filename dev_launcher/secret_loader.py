"""
Simplified secret loader with single source and remote fallback.
"""

import os
import socket
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Set
import logging

from dev_launcher.env_file_loader import EnvFileLoader
from dev_launcher.local_secrets import LocalSecretManager
from dev_launcher.secret_cache import SecretCache
from dev_launcher.cache_manager import CacheManager

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
                 load_secrets: bool = False):
        """Initialize the secret loader."""
        self.project_id = self._determine_project_id(project_id)
        self.verbose = verbose
        self.project_root = project_root or Path.cwd()
        self.load_secrets = load_secrets
        self.loaded_secrets: Dict[str, str] = {}
        self.failed_secrets: List[Tuple[str, str]] = []
        self.env_file_loader = EnvFileLoader(self.project_root, verbose)
        self.cache_manager = CacheManager(self.project_root)
        self.local_secret_manager = LocalSecretManager(self.project_root, verbose)
        self.secret_cache = SecretCache(self.project_root, self.cache_manager)
    
    def _determine_project_id(self, project_id: Optional[str]) -> str:
        """Determine project ID based on environment."""
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        default_project_id = "701982941522" if environment == "staging" else "304612253870"
        return project_id or os.environ.get('GOOGLE_CLOUD_PROJECT', default_project_id)
    
    def load_all_secrets(self) -> bool:
        """
        Load secrets with local-first strategy and intelligent caching:
        1. Check cached secrets first (sub-100ms validation)
        2. Load from fallback chain: OS env → .env.local → .env → defaults
        3. Optional GSM fallback with --load-secrets flag
        4. Cache results for 24 hours
        """
        logger.info("=" * 70)
        logger.info("[SECRET LOADER] Local-First Environment Loading")
        logger.info("=" * 70)
        logger.info(f"GSM Fallback: {'ENABLED' if self.load_secrets else 'DISABLED (use --load-secrets to enable)'}")
        
        # Step 1: Get required secrets
        required_secrets = self._get_required_secrets()
        
        # Step 2: Try cached secrets first (fast path)
        if self._try_load_cached_secrets(required_secrets):
            return True
        
        # Step 3: Load from local files with fallback chain
        secrets, validation_result = self.local_secret_manager.load_secrets_with_fallback(required_secrets)
        
        # Step 4: Handle missing secrets
        if not validation_result.is_valid and self.load_secrets:
            secrets = self._augment_with_google_secrets(secrets, validation_result.missing_keys)
        elif not validation_result.is_valid:
            self._warn_missing_secrets(validation_result.missing_keys)
        
        # Step 5: Set environment and cache results
        self._set_environment_from_secrets(secrets)
        self._cache_secrets_if_valid(secrets, validation_result)
        
        return True
    
    def _capture_existing_env(self) -> Dict[str, Tuple[str, str]]:
        """Capture existing OS environment variables."""
        required_keys = self._get_required_secrets()
        return self.env_file_loader.capture_existing_env(required_keys)
    
    def _get_required_secrets(self) -> Set[str]:
        """Get list of critical secret keys that must be present."""
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
        }
    
    def _check_missing_secrets_legacy(self, env_secrets: Dict, existing_env: Dict, 
                               required: Set[str]) -> Set[str]:
        """Legacy method - kept for backwards compatibility."""
        loaded_keys = set(env_secrets.keys()) | set(existing_env.keys())
        missing = required - loaded_keys
        
        if missing:
            logger.info(f"\n[MISSING] {len(missing)} required secrets not in .env or OS:")
            for key in sorted(missing):
                logger.info(f"  - {key}")
        else:
            logger.info("\n[OK] All required secrets found in .env or OS")
        
        return missing
    
    def _warn_missing_secrets(self, missing_keys: Set[str]):
        """Warn about missing secrets and suggest solutions."""
        logger.warning(f"\n[WARN] {len(missing_keys)} secrets missing:")
        for key in sorted(missing_keys):
            logger.warning(f"  - {key}")
        logger.warning("\n[SOLUTION] Options to resolve:")
        logger.warning("  1. Add to .env file (recommended for dev)")
        logger.warning("  2. Set as OS environment variables")
        logger.warning("  3. Use --load-secrets flag for GSM fallback")
    
    def _try_load_cached_secrets(self, required_secrets: Set[str]) -> bool:
        """Try to load secrets from cache (fast path)."""
        logger.info("\n[CACHE] Checking for cached secrets...")
        
        # Invalidate cache if env files changed
        self.secret_cache.invalidate_on_changes()
        
        # Try fast validation
        is_valid, cached_validation = self.secret_cache.validate_cached_secrets(required_secrets)
        
        if is_valid:
            cached_secrets = self.secret_cache.get_cached_secrets(required_secrets)
            if cached_secrets:
                logger.info(f"  [HIT] Using cached secrets for {len(cached_secrets)} variables")
                self._set_environment_from_secrets(cached_secrets)
                return True
        
        logger.info("  [MISS] Cache miss, loading from files")
        return False
    
    def _augment_with_google_secrets(self, secrets: Dict[str, str], missing_keys: Set[str]) -> Dict[str, str]:
        """Augment local secrets with Google Secret Manager."""
        logger.info(f"\n[GSM] Loading {len(missing_keys)} missing secrets from Google...")
        
        google_secrets = self._load_missing_from_google(missing_keys)
        
        # Merge Google secrets (don't override local)
        augmented_secrets = secrets.copy()
        for key, (value, source) in google_secrets.items():
            if key not in augmented_secrets:
                augmented_secrets[key] = value
                logger.info(f"  [GSM] Added {key} from Google")
        
        return augmented_secrets
    
    def _set_environment_from_secrets(self, secrets: Dict[str, str]):
        """Set environment variables from secret dictionary."""
        logger.info(f"\n[ENVIRONMENT] Setting {len(secrets)} environment variables...")
        
        for key, value in secrets.items():
            os.environ[key] = value
            self.loaded_secrets[key] = value
    
    def _cache_secrets_if_valid(self, secrets: Dict[str, str], validation_result):
        """Cache secrets if validation passed."""
        if validation_result.is_valid:
            source_metadata = {key: "local" for key in secrets.keys()}
            success = self.secret_cache.cache_secrets(
                secrets, 
                {
                    'is_valid': validation_result.is_valid,
                    'missing_keys': list(validation_result.missing_keys),
                    'warnings': validation_result.warnings
                },
                source_metadata
            )
            if success:
                logger.info("  [CACHED] Secrets cached for 24 hours")
    
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
    
    def _merge_and_set_environment_legacy(self, existing_env: Dict, env_secrets: Dict, 
                                   google_secrets: Dict):
        """Legacy merge method - kept for backwards compatibility."""
        logger.info("\n[MERGE] Setting environment variables...")
        logger.info("Priority: OS Environment > .env.local > .env > Google Secrets > Defaults")
        
        # Start with defaults
        all_secrets = self._get_static_defaults()
        
        # Override with Google secrets (fallback)
        for key, value_tuple in google_secrets.items():
            all_secrets[key] = value_tuple
        
        # Override with local env files (.env then .env.local already merged)
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