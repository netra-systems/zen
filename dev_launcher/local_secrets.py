"""
Local secret management with advanced .env parsing and variable resolution.

Provides local-first secret loading with interpolation, validation, and fallback chains.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecretValidationResult:
    """Result of secret validation."""
    is_valid: bool
    missing_keys: Set[str]
    invalid_keys: Set[str]
    warnings: list[str]


class LocalSecretManager:
    """
    Advanced local secret manager with interpolation and validation.
    
    Supports .env file parsing with ${VAR} interpolation, fallback chains,
    and comprehensive validation without external API calls.
    """
    
    def __init__(self, project_root: Path, verbose: bool = False):
        """Initialize local secret manager."""
        self.project_root = project_root
        self.verbose = verbose
        self.loaded_secrets: Dict[str, str] = {}
        self.interpolation_cache: Dict[str, str] = {}
    
    def load_secrets_with_fallback(
        self, required_keys: Set[str]
    ) -> Tuple[Dict[str, str], SecretValidationResult]:
        """Load secrets using fallback chain: OS -> .env.local -> .env."""
        logger.info("\n[LOCAL SECRETS] Loading with fallback chain...")
        
        # Step 1: Build fallback chain
        secrets = self._build_fallback_chain()
        
        # Step 2: Resolve interpolations
        resolved_secrets = self._resolve_interpolations(secrets)
        
        # Step 3: Validate required keys
        validation = self._validate_secrets(resolved_secrets, required_keys)
        
        # Step 4: Log results
        self._log_loading_results(resolved_secrets, validation)
        
        return resolved_secrets, validation
    
    def _build_fallback_chain(self) -> Dict[str, Tuple[str, str]]:
        """Build secret fallback chain with source tracking."""
        secrets = {}
        
        # Layer 1: .env file (lowest priority)
        env_file = self.project_root / ".env"
        if env_file.exists():
            env_secrets = self._parse_env_file(env_file, "env_file")
            secrets.update(env_secrets)
            logger.info(f"  [ENV] Loaded {len(env_secrets)} from .env")
        
        # Layer 2: .env.local (higher priority)
        env_local = self.project_root / ".env.local"
        if env_local.exists():
            local_secrets = self._parse_env_file(env_local, "env_local")
            secrets.update(local_secrets)
            logger.info(f"  [LOCAL] Loaded {len(local_secrets)} from .env.local")
        
        # Layer 3: OS environment (highest priority)
        os_secrets = self._capture_os_environment()
        secrets.update(os_secrets)
        logger.info(f"  [OS] Found {len(os_secrets)} in OS environment")
        
        return secrets
    
    def _parse_env_file(self, file_path: Path, source: str) -> Dict[str, Tuple[str, str]]:
        """Parse .env file with advanced features."""
        secrets = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = self._parse_env_line(line, line_num, source)
                    if parsed:
                        key, value = parsed
                        secrets[key] = (value, source)
        except Exception as e:
            logger.error(f"  [ERROR] Failed to parse {file_path}: {e}")
        
        return secrets
    
    def _parse_env_line(self, line: str, line_num: int, source: str) -> Optional[Tuple[str, str]]:
        """Parse single environment line with validation."""
        original_line = line
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            return None
        
        # Must contain equals sign
        if '=' not in line:
            if self.verbose:
                logger.debug(f"    {source}:{line_num} - No '=' found: {original_line[:50]}")
            return None
        
        # Split on first equals only
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # Validate key format
        if not self._is_valid_env_key(key):
            if self.verbose:
                logger.debug(f"    {source}:{line_num} - Invalid key format: {key}")
            return None
        
        # Process value (handle quotes, escaping)
        processed_value = self._process_env_value(value)
        
        if self.verbose:
            masked_value = self._mask_secret_value(processed_value)
            logger.debug(f"    {source}:{line_num} - {key}={masked_value}")
        
        return key, processed_value
    
    def _is_valid_env_key(self, key: str) -> bool:
        """Validate environment variable key format."""
        # Must be valid identifier: letters, numbers, underscores
        # Cannot start with number
        return re.match(r'^[A-Z_][A-Z0-9_]*$', key) is not None
    
    def _process_env_value(self, value: str) -> str:
        """Process environment value - handle quotes and escaping."""
        # Handle quoted values
        if ((value.startswith('"') and value.endswith('"')) or
            (value.startswith("'") and value.endswith("'"))):
            value = value[1:-1]
        
        # Handle basic escape sequences
        value = value.replace('\\n', '\n')
        value = value.replace('\\t', '\t')
        value = value.replace('\\"', '"')
        value = value.replace("\\'", "'")
        
        return value
    
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
                resolved_value = self._interpolate_value(value, secrets)
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
    
    def _interpolate_value(self, value: str, secrets: Dict[str, Tuple[str, str]]) -> str:
        """Interpolate ${VAR} references in a value."""
        if '${' not in value:
            return value
        
        # Find all ${VAR} patterns
        pattern = re.compile(r'\$\{([^}]+)\}')
        
        def replace_var(match):
            var_name = match.group(1)
            
            # Check if variable exists in our secrets
            if var_name in secrets:
                replacement_value, _ = secrets[var_name]
                # Recursively resolve if needed
                return self._interpolate_value(replacement_value, secrets)
            
            # Check OS environment as fallback
            if var_name in os.environ:
                return os.environ[var_name]
            
            # Variable not found - return original or empty
            logger.warning(f"      [WARN] Variable {var_name} not found for interpolation")
            return match.group(0)  # Return original ${VAR} if not found
        
        return pattern.sub(replace_var, value)
    
    def _validate_secrets(
        self, secrets: Dict[str, str], required_keys: Set[str]
    ) -> SecretValidationResult:
        """Validate loaded secrets without external API calls."""
        missing_keys = required_keys - set(secrets.keys())
        invalid_keys = set()
        warnings = []
        
        # Check for empty or placeholder values
        for key in required_keys:
            if key in secrets:
                value = secrets[key]
                if self._is_invalid_secret_value(value):
                    invalid_keys.add(key)
                    warnings.append(f"Secret {key} has invalid/placeholder value")
        
        # Check for potential issues
        for key, value in secrets.items():
            if self._has_potential_issues(key, value):
                warnings.append(f"Potential issue with {key}: {self._get_issue_description(key, value)}")
        
        is_valid = len(missing_keys) == 0 and len(invalid_keys) == 0
        
        return SecretValidationResult(
            is_valid=is_valid,
            missing_keys=missing_keys,
            invalid_keys=invalid_keys,
            warnings=warnings
        )
    
    def _is_invalid_secret_value(self, value: str) -> bool:
        """Check if secret value is invalid or placeholder."""
        if not value or value.isspace():
            return True
        
        # Common placeholder patterns
        placeholder_patterns = [
            'your_', 'YOUR_', 'placeholder', 'PLACEHOLDER',
            'change_me', 'CHANGE_ME', 'todo', 'TODO',
            'xxx', 'XXX', '***'
        ]
        
        value_lower = value.lower()
        return any(pattern.lower() in value_lower for pattern in placeholder_patterns)
    
    def _has_potential_issues(self, key: str, value: str) -> bool:
        """Check for potential issues in secret values."""
        # Check for suspiciously short API keys
        if 'API_KEY' in key and len(value) < 10:
            return True
        
        # Check for localhost in production-like settings
        if key.endswith('_HOST') and 'localhost' in value.lower():
            env = os.environ.get('ENVIRONMENT', 'development').lower()
            if env in ['staging', 'production']:
                return True
        
        return False
    
    def _get_issue_description(self, key: str, value: str) -> str:
        """Get description of potential issue."""
        if 'API_KEY' in key and len(value) < 10:
            return "API key seems too short"
        
        if key.endswith('_HOST') and 'localhost' in value.lower():
            return "localhost in non-development environment"
        
        return "unknown issue"
    
    def _log_loading_results(
        self, secrets: Dict[str, str], validation: SecretValidationResult
    ):
        """Log the results of secret loading."""
        logger.info(f"\n[RESULTS] Loaded {len(secrets)} secrets total")
        
        if validation.is_valid:
            logger.info("  [OK] All required secrets loaded successfully")
        else:
            if validation.missing_keys:
                logger.warning(f"  [MISSING] {len(validation.missing_keys)} required secrets:")
                for key in sorted(validation.missing_keys):
                    logger.warning(f"    - {key}")
            
            if validation.invalid_keys:
                logger.warning(f"  [INVALID] {len(validation.invalid_keys)} invalid secrets:")
                for key in sorted(validation.invalid_keys):
                    logger.warning(f"    - {key}")
        
        if validation.warnings:
            logger.info(f"  [WARNINGS] {len(validation.warnings)} potential issues:")
            for warning in validation.warnings[:3]:  # Show first 3
                logger.info(f"    - {warning}")
    
    def _mask_secret_value(self, value: str) -> str:
        """Mask secret value for safe display."""
        if len(value) <= 3:
            return "***"
        elif len(value) <= 8:
            return f"{value[:2]}***"
        else:
            return f"{value[:3]}***{value[-3:]}"
    
    def get_interpolation_dependencies(self, secrets: Dict[str, str]) -> Dict[str, Set[str]]:
        """Get dependency graph of variable interpolations."""
        dependencies = {}
        
        for key, value in secrets.items():
            deps = set()
            pattern = re.compile(r'\$\{([^}]+)\}')
            
            for match in pattern.finditer(value):
                var_name = match.group(1)
                deps.add(var_name)
            
            if deps:
                dependencies[key] = deps
        
        return dependencies
    
    def validate_interpolation_cycles(self, secrets: Dict[str, str]) -> bool:
        """Check for circular dependencies in interpolations."""
        dependencies = self.get_interpolation_dependencies(secrets)
        
        def has_cycle(var, visited, rec_stack):
            visited.add(var)
            rec_stack.add(var)
            
            if var in dependencies:
                for dep in dependencies[var]:
                    if dep not in visited:
                        if has_cycle(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(var)
            return False
        
        visited = set()
        for var in dependencies:
            if var not in visited:
                if has_cycle(var, visited, set()):
                    logger.error(f"[ERROR] Circular dependency detected involving {var}")
                    return False
        
        return True