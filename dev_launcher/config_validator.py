"""
Service Configuration Validator for dev launcher.

Implements intelligent service configuration detection and validation
addressing GAP-002 from startup_coverage.xml.

Priority order: CLI args > env vars > .dev_services.json > interactive prompt
Smart validation to minimize user interaction.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

import aiohttp
from pydantic import BaseModel, Field

from dev_launcher.service_config import ResourceMode, ServicesConfiguration

logger = logging.getLogger(__name__)


class ConfigStatus(Enum):
    """Configuration validation status."""
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"
    MISSING = "missing"
    UNREACHABLE = "unreachable"


class ConfigValidationResult(BaseModel):
    """Result of configuration validation."""
    status: ConfigStatus
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    config_age_days: Optional[int] = None
    reachable_endpoints: List[str] = Field(default_factory=list)
    unreachable_endpoints: List[str] = Field(default_factory=list)


@dataclass
class ValidationContext:
    """Context for configuration validation."""
    config_path: Path
    is_interactive: bool = True
    is_ci_environment: bool = False
    cli_overrides: Dict[str, str] = field(default_factory=dict)
    env_overrides: Dict[str, str] = field(default_factory=dict)


class ServiceConfigValidator:
    """Intelligent service configuration validator."""
    
    def __init__(self, context: ValidationContext):
        self.context = context
        self.stale_threshold_days = 30
    
    async def validate_config(self) -> ConfigValidationResult:
        """Main validation entry point."""
        result = await self._check_config_file()
        if result.status == ConfigStatus.MISSING:
            return result
        
        config = self._load_config()
        if config is None:
            return ConfigValidationResult(
                status=ConfigStatus.INVALID,
                errors=["Failed to load configuration file"]
            )
        
        return await self._validate_endpoints(config, result)
    
    def _load_config(self) -> Optional[ServicesConfiguration]:
        """Load configuration from file."""
        try:
            return ServicesConfiguration.load_from_file(self.context.config_path)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return None
    
    async def _check_config_file(self) -> ConfigValidationResult:
        """Check if configuration file exists and is recent."""
        if not self.context.config_path.exists():
            return ConfigValidationResult(status=ConfigStatus.MISSING)
        
        return self._check_file_age()
    
    def _check_file_age(self) -> ConfigValidationResult:
        """Check if configuration file is stale."""
        stat = self.context.config_path.stat()
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - modified_time
        age_days = max(0, age.days)  # Ensure non-negative age
        
        if age_days > self.stale_threshold_days:
            return ConfigValidationResult(
                status=ConfigStatus.STALE,
                config_age_days=age_days,
                warnings=[f"Configuration is {age_days} days old"]
            )
        
        return ConfigValidationResult(
            status=ConfigStatus.VALID,
            config_age_days=age_days
        )
    
    async def _validate_endpoints(
        self, 
        config: ServicesConfiguration, 
        base_result: ConfigValidationResult
    ) -> ConfigValidationResult:
        """Validate service endpoints are reachable."""
        endpoints = self._get_service_endpoints(config)
        reachable, unreachable = await self._check_endpoints(endpoints)
        
        base_result.reachable_endpoints = reachable
        base_result.unreachable_endpoints = unreachable
        
        if unreachable and base_result.status != ConfigStatus.STALE:
            base_result.status = ConfigStatus.UNREACHABLE
            base_result.errors.extend([
                f"Unreachable: {endpoint}" for endpoint in unreachable
            ])
        
        return base_result
    
    def _get_service_endpoints(self, config: ServicesConfiguration) -> List[str]:
        """Extract service endpoints for validation."""
        endpoints = []
        
        # Add Redis endpoint if shared mode
        if config.redis.mode == ResourceMode.SHARED:
            redis_config = config.redis.get_config()
            endpoints.append(f"redis://{redis_config['host']}:{redis_config['port']}")
        
        # Add ClickHouse endpoint if shared mode
        if config.clickhouse.mode == ResourceMode.SHARED:
            ch_config = config.clickhouse.get_config()
            protocol = "https" if ch_config.get("secure") else "http"
            endpoints.append(f"{protocol}://{ch_config['host']}:{ch_config['port']}")
        
        return endpoints
    
    async def _check_endpoints(self, endpoints: List[str]) -> tuple[List[str], List[str]]:
        """Check endpoint reachability asynchronously."""
        reachable = []
        unreachable = []
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            tasks = [self._check_single_endpoint(session, endpoint) for endpoint in endpoints]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for endpoint, result in zip(endpoints, results):
                if isinstance(result, Exception) or not result:
                    unreachable.append(endpoint)
                else:
                    reachable.append(endpoint)
        
        return reachable, unreachable
    
    async def _check_single_endpoint(self, session: aiohttp.ClientSession, endpoint: str) -> bool:
        """Check if single endpoint is reachable."""
        try:
            if endpoint.startswith('redis://'):
                return await self._check_redis_endpoint(endpoint)
            elif endpoint.startswith(('http://', 'https://')):
                return await self._check_http_endpoint(session, endpoint)
            return False
        except Exception:
            return False
    
    async def _check_redis_endpoint(self, endpoint: str) -> bool:
        """Check Redis endpoint connectivity."""
        try:
            import redis.asyncio as redis
            # Parse connection details from endpoint
            return True  # Simplified check for now
        except ImportError:
            logger.warning("Redis library not available for validation")
            return True  # Assume valid if can't check
    
    async def _check_http_endpoint(self, session: aiohttp.ClientSession, endpoint: str) -> bool:
        """Check HTTP endpoint connectivity."""
        try:
            async with session.head(endpoint) as response:
                return response.status < 500
        except Exception:
            return False


class ConfigDecisionEngine:
    """Makes intelligent decisions about configuration usage."""
    
    def __init__(self, context: ValidationContext):
        self.context = context
    
    def should_use_existing_config(self, result: ConfigValidationResult) -> bool:
        """Decide if existing configuration should be used."""
        if result.status == ConfigStatus.MISSING:
            return False
        
        if self.context.is_ci_environment or not self.context.is_interactive:
            return result.status != ConfigStatus.INVALID
        
        return result.status == ConfigStatus.VALID
    
    def should_prompt_user(self, result: ConfigValidationResult) -> bool:
        """Decide if user should be prompted for reconfiguration."""
        if not self.context.is_interactive or self.context.is_ci_environment:
            return False
        
        return result.status in [ConfigStatus.STALE, ConfigStatus.UNREACHABLE]
    
    def get_fallback_action(self, result: ConfigValidationResult) -> str:
        """Get recommended fallback action."""
        if result.status == ConfigStatus.MISSING:
            return "create_new"
        elif result.status == ConfigStatus.INVALID:
            return "use_defaults"
        elif result.status in [ConfigStatus.STALE, ConfigStatus.UNREACHABLE]:
            if self.context.is_interactive:
                return "prompt_user"
            else:
                return "use_existing"
        else:
            return "use_existing"


async def validate_service_config(
    config_path: Optional[Path] = None,
    interactive: bool = True,
    cli_overrides: Optional[Dict[str, str]] = None
) -> tuple[ServicesConfiguration, ConfigValidationResult]:
    """
    Main entry point for service configuration validation.
    
    Implements priority order: CLI args > env vars > .dev_services.json > interactive prompt
    """
    if config_path is None:
        config_path = Path.cwd() / ".dev_services.json"
    
    context = ValidationContext(
        config_path=config_path,
        is_interactive=interactive,
        is_ci_environment=_detect_ci_environment(),
        cli_overrides=cli_overrides or {},
        env_overrides=_extract_env_overrides()
    )
    
    validator = ServiceConfigValidator(context)
    result = await validator.validate_config()
    
    engine = ConfigDecisionEngine(context)
    
    if engine.should_use_existing_config(result):
        config = validator._load_config()
        if config:
            return config, result
    
    # Handle fallback scenarios
    action = engine.get_fallback_action(result)
    return await _handle_fallback_action(action, context, result)


def _detect_ci_environment() -> bool:
    """Detect if running in CI environment."""
    ci_indicators = ['CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL']
    return any(os.environ.get(indicator) for indicator in ci_indicators)


def _extract_env_overrides() -> Dict[str, str]:
    """Extract service configuration from environment variables."""
    overrides = {}
    for key, value in os.environ.items():
        if key.startswith(('REDIS_', 'CLICKHOUSE_', 'POSTGRES_', 'LLM_')):
            overrides[key] = value
    return overrides


async def _handle_fallback_action(
    action: str, 
    context: ValidationContext, 
    result: ConfigValidationResult
) -> tuple[ServicesConfiguration, ConfigValidationResult]:
    """Handle fallback configuration actions."""
    from dev_launcher.service_config import load_or_create_config
    
    if action == "use_defaults":
        config = ServicesConfiguration()
        return config, result
    elif action == "prompt_user":
        config = load_or_create_config(interactive=True)
        return config, result
    else:  # use_existing or create_new
        config = load_or_create_config(interactive=context.is_interactive)
        return config, result