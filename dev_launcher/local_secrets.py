"""
Local secret management with advanced .env parsing and variable resolution.

Main orchestrator for local-first secret loading with fallback chains.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Set, Tuple

from dev_launcher.env_parser import EnvParser
from dev_launcher.secret_validator import SecretValidator, SecretValidationResult

logger = logging.getLogger(__name__)


class LocalSecretManager:
    """
    Local secret manager with fallback chain and interpolation.
    
    Orchestrates secret loading from multiple sources with intelligent
    fallback chain: OS env → .env.local → .env → defaults
    """
    
    def __init__(self, project_root: Path, verbose: bool = False):
        """Initialize local secret manager."""
        self.project_root = project_root
        self.verbose = verbose
        self.env_parser = EnvParser(verbose)
        self.validator = SecretValidator()
    
    def load_secrets_with_fallback(
        self, required_keys: Set[str]
    ) -> Tuple[Dict[str, str], SecretValidationResult]:
        """Load secrets using fallback chain: OS -> .env.local -> .env."""
        logger.info("\n[LOCAL SECRETS] Loading with fallback chain...")
        
        # Step 1: Build fallback chain
        secrets_with_sources = self._build_fallback_chain()
        
        # Step 2: Resolve interpolations
        resolved_secrets = self._resolve_interpolations(secrets_with_sources)
        
        # Step 3: Validate required keys
        validation = self.validator.validate_secrets(resolved_secrets, required_keys)
        
        # Step 4: Log results
        self.validator.log_validation_results(resolved_secrets, validation)
        
        return resolved_secrets, validation
    
    def _build_fallback_chain(self) -> Dict[str, Tuple[str, str]]:
        """Build secret fallback chain with source tracking."""
        secrets = {}
        
        # Layer 1: .env file (lowest priority)
        env_file = self.project_root / ".env"
        if env_file.exists():
            env_secrets = self.env_parser.parse_env_file(env_file, "env_file")
            secrets.update(env_secrets)
            logger.info(f"  [ENV] Loaded {len(env_secrets)} from .env")
        
        # Layer 2: .env.local (higher priority)
        env_local = self.project_root / ".env.local"
        if env_local.exists():
            local_secrets = self.env_parser.parse_env_file(env_local, "env_local")
            secrets.update(local_secrets)
            logger.info(f"  [LOCAL] Loaded {len(local_secrets)} from .env.local")
        
        # Layer 3: OS environment (highest priority)
        os_secrets = self._capture_os_environment()
        secrets.update(os_secrets)
        logger.info(f"  [OS] Found {len(os_secrets)} in OS environment")
        
        return secrets
    
    def _capture_os_environment(self) -> Dict[str, Tuple[str, str]]:
        """Capture relevant OS environment variables."""
        secrets = {}
        
        # Get all env vars that look like configuration
        for key, value in os.environ.items():
            if self._is_relevant_env_var(key):
                secrets[key] = (value, "os_environment")
        
        return secrets
    
    def _is_relevant_env_var(self, key: str) -> bool:
        """Check if environment variable is relevant for our application."""
        relevant_patterns = [
            'GEMINI_', 'GOOGLE_', 'LANGFUSE_', 'CLICKHOUSE_',
            'REDIS_', 'JWT_', 'FERNET_', 'ANTHROPIC_', 'OPENAI_',
            'ENVIRONMENT', 'PORT'
        ]
        
        return any(key.startswith(pattern) for pattern in relevant_patterns)
    
    def _resolve_interpolations(self, secrets: Dict[str, Tuple[str, str]]) -> Dict[str, str]:
        """Resolve ${VAR} style interpolations in secret values."""
        logger.info("\n[INTERPOLATION] Resolving variable references...")
        
        resolved = {}
        interpolation_count = 0
        
        for key, (value, source) in secrets.items():
            try:
                resolved_value = self.env_parser.interpolate_value(value, secrets)
                resolved[key] = resolved_value
                
                if value != resolved_value:
                    interpolation_count += 1
                    if self.verbose:
                        logger.debug(f"    {key}: Interpolated from {source}")
            except Exception as e:
                logger.warning(f"    [WARN] Failed to interpolate {key}: {e}")
                resolved[key] = value  # Use original value on error
        
        if interpolation_count > 0:
            logger.info(f"  [OK] Resolved {interpolation_count} variable references")
        
        return resolved