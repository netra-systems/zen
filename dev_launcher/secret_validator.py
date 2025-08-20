"""
Secret validation utilities without external API calls.

Provides fast local validation for secret values and configurations.
"""

import os
import logging
from typing import Dict, Set
from dataclasses import dataclass
from app.core.environment_constants import (
    Environment, get_current_environment
)

logger = logging.getLogger(__name__)


@dataclass
class SecretValidationResult:
    """Result of secret validation."""
    is_valid: bool
    missing_keys: Set[str]
    invalid_keys: Set[str]
    warnings: list[str]


class SecretValidator:
    """
    Secret validation utilities without external API calls.
    
    Provides fast local validation for secret values, placeholder detection,
    and configuration issue identification.
    """
    
    def validate_secrets(
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
            env = get_current_environment()
            if env in [Environment.STAGING.value, Environment.PRODUCTION.value]:
                return True
        
        return False
    
    def _get_issue_description(self, key: str, value: str) -> str:
        """Get description of potential issue."""
        if 'API_KEY' in key and len(value) < 10:
            return "API key seems too short"
        
        if key.endswith('_HOST') and 'localhost' in value.lower():
            return "localhost in non-development environment"
        
        return "unknown issue"
    
    def log_validation_results(self, secrets: Dict[str, str], validation: SecretValidationResult):
        """Log the results of secret validation."""
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