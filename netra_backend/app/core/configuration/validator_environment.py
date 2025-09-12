"""Environment Configuration Validation

**CRITICAL: Enterprise-Grade Environment Validation**

Environment-specific validation helpers for configuration validation.
Business Value: Prevents environment-specific configuration errors.

Each function  <= 8 lines, file  <= 300 lines.
"""

from typing import List
from urllib.parse import urlparse

from netra_backend.app.schemas.config import AppConfig


class EnvironmentValidator:
    """Environment configuration validation helpers."""
    
    def __init__(self, validation_rules: dict, environment: str):
        """Initialize environment validator."""
        self._validation_rules = validation_rules
        self._environment = environment
    
    def validate_external_services(self, config: AppConfig) -> List[str]:
        """Validate external service configurations."""
        errors = []
        errors.extend(self._validate_urls(config))
        errors.extend(self._validate_environment_consistency(config))
        return errors
    
    def _validate_urls(self, config: AppConfig) -> List[str]:
        """Validate URL configurations."""
        errors = []
        url_fields = ["frontend_url", "api_base_url"]
        for field in url_fields:
            self._check_url_field(config, field, errors)
        return errors
    
    def _check_url_field(self, config: AppConfig, field: str, errors: List[str]) -> None:
        """Check individual URL field validation."""
        if hasattr(config, field):
            url = getattr(config, field)
            if url:
                errors.extend(self._validate_single_url(field, url))
    
    def _validate_single_url(self, field_name: str, url: str) -> List[str]:
        """Validate a single URL field."""
        errors = []
        if not self._is_valid_url(url):
            errors.append(f"Invalid URL format for {field_name}: {url}")
        return errors
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid."""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except Exception:
            return False
    
    def _validate_environment_consistency(self, config: AppConfig) -> List[str]:
        """Validate environment-specific configuration consistency."""
        errors = self._check_localhost_restrictions(config)
        errors.extend(self._check_production_requirements(config))
        return errors
    
    def _check_localhost_restrictions(self, config: AppConfig) -> List[str]:
        """Check localhost restrictions based on environment."""
        rules = self._validation_rules.get(self._environment, {})
        if not rules.get("allow_localhost", True):
            return self._check_no_localhost_urls(config)
        return []
    
    def _check_production_requirements(self, config: AppConfig) -> List[str]:
        """Check production-specific requirements."""
        if self._environment == "production":
            return self._validate_production_requirements(config)
        return []
    
    def _check_no_localhost_urls(self, config: AppConfig) -> List[str]:
        """Check that no URLs contain localhost in non-dev environments."""
        errors = []
        url_fields = ["frontend_url", "api_base_url"]
        for field in url_fields:
            errors.extend(self._check_field_for_localhost(config, field))
        return errors
    
    def _check_field_for_localhost(self, config: AppConfig, field: str) -> List[str]:
        """Check if a field contains localhost URLs."""
        if not hasattr(config, field):
            return []
        url = getattr(config, field, "")
        if "localhost" in url or "127.0.0.1" in url:
            return [f"{field} contains localhost in {self._environment} environment"]
        return []
    
    def _validate_production_requirements(self, config: AppConfig) -> List[str]:
        """Validate production-specific requirements."""
        errors = []
        secure_fields = ["frontend_url", "api_base_url"]
        for field in secure_fields:
            errors.extend(self._check_https_requirement(config, field))
        return errors
    
    def _check_https_requirement(self, config: AppConfig, field: str) -> List[str]:
        """Check HTTPS requirement for a URL field."""
        if not hasattr(config, field):
            return []
        url = getattr(config, field, "")
        if url and not url.startswith("https://"):
            return [f"Production {field} must use HTTPS"]
        return []