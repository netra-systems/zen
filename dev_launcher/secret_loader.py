"""
Local-first secret loader with caching and GSM fallback.

Main secret loading orchestrator with local-first approach.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Set, Optional
import time

from dev_launcher.local_secrets import LocalSecretManager
from dev_launcher.secret_cache import SecretCache
from dev_launcher.cache_manager import CacheManager
from dev_launcher.google_secret_manager import GoogleSecretManager
from dev_launcher.secret_config import SecretConfig

logger = logging.getLogger(__name__)


class SecretLoader:
    """
    Local-first secret loader with intelligent caching.
    
    Priority: OS env → .env.local → .env → GSM (optional) → defaults
    Features: 24-hour caching, sub-100ms validation, ${VAR} interpolation
    """
    
    def __init__(self, 
                 project_id: Optional[str] = None, 
                 verbose: bool = False,
                 project_root: Optional[Path] = None,
                 load_secrets: bool = False,
                 local_first: bool = True):
        """Initialize the secret loader."""
        self.project_id = SecretConfig.determine_project_id(project_id)
        self.verbose = verbose
        self.project_root = project_root or Path.cwd()
        self.load_secrets = load_secrets
        self.local_first = local_first
        self.loaded_secrets: Dict[str, str] = {}
        self._fast_mode = False
        self._setup_components()
    
    def _setup_components(self):
        """Setup internal components."""
        self.cache_manager = CacheManager(self.project_root)
        self.local_secret_manager = LocalSecretManager(self.project_root, self.verbose)
        self.secret_cache = SecretCache(self.project_root, self.cache_manager)
        if self.load_secrets:
            self.google_manager = GoogleSecretManager(self.project_id, self.verbose)
    
    def load_all_secrets(self) -> bool:
        """
        Load secrets with local-first strategy and intelligent caching.
        
        Steps:
        1. Check cached secrets first (sub-100ms validation)
        2. Load from fallback chain: OS env → .env.local → .env → defaults  
        3. Optional GSM fallback with --load-secrets flag
        4. Cache results for 24 hours
        """
        self._log_startup_banner()
        
        required_secrets = SecretConfig.get_required_secrets()
        
        # Fast path: Try cached secrets first
        if self._try_load_cached_secrets(required_secrets):
            return True
        
        # Slow path: Load from files with fallback chain
        secrets, validation_result = self.local_secret_manager.load_secrets_with_fallback(required_secrets)
        
        # Handle missing secrets
        if not validation_result.is_valid and self.load_secrets:
            secrets = self._augment_with_google_secrets(secrets, validation_result.missing_keys)
        elif not validation_result.is_valid:
            self._warn_missing_secrets(validation_result.missing_keys)
        
        # Set environment and cache results
        self._set_environment_from_secrets(secrets)
        self._cache_secrets_if_valid(secrets, validation_result)
        self._log_completion_summary()
        
        return True
    
    def _log_startup_banner(self):
        """Log startup information."""
        logger.info("=" * 70)
        logger.info("[SECRET LOADER] Local-First Environment Loading")
        logger.info("=" * 70)
        logger.info(f"GSM Fallback: {'ENABLED' if self.load_secrets else 'DISABLED (use --load-secrets to enable)'}")
    
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
        google_secrets = self.google_manager.load_missing_secrets(missing_keys)
        
        # Merge Google secrets (don't override local)
        augmented_secrets = secrets.copy()
        for key, (value, source) in google_secrets.items():
            if key not in augmented_secrets:
                augmented_secrets[key] = value
                logger.info(f"  [GSM] Added {key} from Google")
        
        return augmented_secrets
    
    def _warn_missing_secrets(self, missing_keys: Set[str]):
        """Warn about missing secrets and suggest solutions."""
        logger.warning(f"\n[WARN] {len(missing_keys)} secrets missing:")
        for key in sorted(missing_keys):
            logger.warning(f"  - {key}")
        logger.warning("\n[SOLUTION] Options to resolve:")
        logger.warning("  1. Add to .env file (recommended for dev)")
        logger.warning("  2. Set as OS environment variables")  
        logger.warning("  3. Use --load-secrets flag for GSM fallback")
    
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
    
    def _log_completion_summary(self):
        """Log completion summary."""
        logger.info("\n" + "=" * 70)
        logger.info("[SUMMARY] Local-First Secret Loading Complete")
        logger.info("=" * 70)
        logger.info(f"Total secrets loaded: {len(self.loaded_secrets)}")
        logger.info("Priority: OS Environment > .env.local > .env > Google Secrets > Defaults")
        logger.info("[TIP] Create a .env file for local development")
        logger.info("[TIP] Use 'cp .env.example .env' to start from example")
        logger.info("=" * 70)
    
    def enable_fast_mode(self) -> None:
        """Enable fast mode for sub-100ms secret loading."""
        self._fast_mode = True
        self.local_first = True
        logger.info("Fast mode enabled for secret loading")
    
    def load_secrets_fast(self, required_secrets: Set[str]) -> Dict[str, str]:
        """Fast secret loading using only local sources."""
        if not self._fast_mode:
            return self.load_all_secrets()
        
        # Try cache first
        if self._try_load_cached_secrets(required_secrets):
            return self.loaded_secrets
        
        # Fast local-only loading
        secrets, _ = self.local_secret_manager.load_secrets_with_fallback(required_secrets)
        self._set_environment_from_secrets(secrets)
        return secrets
    
    def validate_local_env_files(self) -> bool:
        """Validate that local environment files are sufficient."""
        required_secrets = SecretConfig.get_required_secrets()
        env_secrets = {}
        
        # Check .env files
        for env_file in [".env.local", ".env"]:
            env_path = self.project_root / env_file
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_secrets[key.strip()] = value.strip('"\'')
        
        # Check OS environment
        for key in required_secrets:
            if key in os.environ:
                env_secrets[key] = os.environ[key]
        
        missing = required_secrets - set(env_secrets.keys())
        if missing:
            logger.warning(f"Missing local secrets: {missing}")
            return False
        return True