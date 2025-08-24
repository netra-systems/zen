"""
Local secret management with advanced .env parsing and variable resolution.

Main orchestrator for local-first secret loading with fallback chains.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Set, Tuple

from dev_launcher.env_parser import EnvParser
from dev_launcher.secret_validator import SecretValidationResult, SecretValidator

logger = logging.getLogger(__name__)


class LocalSecretManager:
    """
    Local secret manager with fallback chain and interpolation.
    
    Orchestrates secret loading from multiple sources with intelligent
    fallback chain: 
    - isolation_mode=False: OS env → .env.local → .env → defaults (production)
    - isolation_mode=True: .env.local → .env → defaults (development/testing)
    """
    
    def __init__(self, project_root: Path, verbose: bool = False, isolation_mode: bool = False):
        """Initialize local secret manager.
        
        Args:
            project_root: Root directory of the project
            verbose: Enable verbose logging
            isolation_mode: When True, skip OS environment loading (for development/testing)
        """
        self.project_root = project_root
        self.verbose = verbose
        self.isolation_mode = isolation_mode
        self.env_parser = EnvParser(verbose)
        self.validator = SecretValidator()
    
    def load_secrets_with_fallback(
        self, required_keys: Set[str]
    ) -> Tuple[Dict[str, str], SecretValidationResult]:
        """Load secrets using fallback chain with optional isolation mode."""
        isolation_status = "ENABLED (development/testing)" if self.isolation_mode else "DISABLED (production)"
        logger.info(f"\n[LOCAL SECRETS] Loading with fallback chain... (Isolation mode: {isolation_status})")
        
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
        """Build secret fallback chain with source tracking and optional isolation.
        
        Priority order:
        - isolation_mode=False: .secrets → .env → .env.local → OS env (production)
        - isolation_mode=True: .secrets → .env → .env.local (development/testing)
        """
        secrets = {}
        
        # Layer 1: .secrets file (lowest priority - legacy support)
        secrets_file = self.project_root / ".secrets"
        if secrets_file.exists():
            secrets_from_file = self.env_parser.parse_env_file(secrets_file, "secrets_file")
            secrets.update(secrets_from_file)
            logger.info(f"  [SECRETS] Loaded {len(secrets_from_file)} from .secrets")
        
        # Layer 2: .env file (base configuration)
        env_file = self.project_root / ".env"
        if env_file.exists():
            env_secrets = self.env_parser.parse_env_file(env_file, "env_file")
            secrets.update(env_secrets)
            logger.info(f"  [ENV] Loaded {len(env_secrets)} from .env")
        
        # Layer 3: .env.local (local overrides)
        env_local = self.project_root / ".env.local"
        if env_local.exists():
            local_secrets = self.env_parser.parse_env_file(env_local, "env_local")
            secrets.update(local_secrets)
            logger.info(f"  [LOCAL] Loaded {len(local_secrets)} from .env.local")
        
        # Layer 4: OS environment (highest priority - only in production mode)
        if not self.isolation_mode:
            os_secrets = self._capture_os_environment()
            secrets.update(os_secrets)
            logger.info(f"  [OS] Found {len(os_secrets)} in OS environment")
        else:
            logger.info("  [ISOLATION] Skipping system environment variables (isolation mode enabled)")
        
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
        """Check if environment variable is relevant for our application.
        
        Extended to capture ALL potentially relevant variables including TEST_ 
        variables for testing scenarios.
        """
        # Common configuration patterns
        relevant_patterns = [
            'GEMINI_', 'GOOGLE_', 'LANGFUSE_', 'CLICKHOUSE_',
            'REDIS_', 'JWT_', 'FERNET_', 'ANTHROPIC_', 'OPENAI_',
            'ENVIRONMENT', 'PORT', 'DATABASE_', 'API_', 'SECRET_',
            'KEY_', 'TOKEN_', 'AUTH_', 'SERVICE_', 'NETRA_',
            'TEST_'  # Include test variables for testing
        ]
        
        # Check if the key starts with any relevant pattern
        if any(key.startswith(pattern) for pattern in relevant_patterns):
            return True
        
        # Also include specific single-word configs
        single_configs = {'ENVIRONMENT', 'DEBUG', 'TESTING', 'PORT', 'HOST'}
        return key in single_configs
    
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