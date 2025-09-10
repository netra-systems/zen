"""
SSOT Environment Loading Module

Centralizes environment file loading logic across all Netra services to eliminate 
duplication between backend and auth service while preserving all existing behavior.

Classes:
- StartupEnvironmentManager: Central coordinator for environment loading
- EnvironmentDetector: Unified environment detection (staging/prod vs dev)
- EnvFileLoader: Standardized .env file loading with fallback chains
- DevLauncherDetector: Unified dev launcher detection patterns
- ConfigurationValidator: Environment validation utilities

CRITICAL: This module preserves ALL existing behavior while eliminating duplication.
NO breaking changes to existing deployments or configurations.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union, Tuple
import os


class EnvironmentType(Enum):
    """Standard environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"
    TEST = "test"
    LOCAL = "local"


@dataclass
class ServiceConfig:
    """Service-specific configuration for environment loading."""
    service_name: str
    critical_vars: List[str]
    dev_launcher_indicators: List[str]
    env_file_paths: List[Union[str, Path]]
    skip_missing_dotenv: bool = True
    
    
@dataclass
class LoadingResult:
    """Result of environment loading operation."""
    loaded: bool
    reason: str
    files_loaded: List[Path]
    environment_detected: EnvironmentType
    dev_launcher_detected: bool


class EnvironmentDetector:
    """Unified environment detection across services."""
    
    PRODUCTION_ENVIRONMENTS = {'staging', 'production', 'prod'}
    
    @classmethod
    def detect_environment(cls, env_manager) -> EnvironmentType:
        """Detect current environment type."""
        environment = env_manager.get('ENVIRONMENT', '').lower()
        
        if environment in cls.PRODUCTION_ENVIRONMENTS:
            if environment == 'staging':
                return EnvironmentType.STAGING
            else:
                return EnvironmentType.PRODUCTION
        elif environment == 'test':
            return EnvironmentType.TEST
        else:
            return EnvironmentType.DEVELOPMENT
    
    @classmethod
    def is_production_like(cls, env_manager) -> bool:
        """Check if running in production-like environment."""
        environment = env_manager.get('ENVIRONMENT', '').lower()
        return environment in cls.PRODUCTION_ENVIRONMENTS


class DevLauncherDetector:
    """Unified dev launcher detection patterns."""
    
    DEFAULT_INDICATORS = [
        'DEV_LAUNCHER_ACTIVE',  # Explicit flag from dev launcher
        'CROSS_SERVICE_AUTH_TOKEN',  # Token set by dev launcher
    ]
    
    @classmethod
    def is_dev_launcher_active(cls, env_manager, additional_indicators: List[str] = None) -> Tuple[bool, str]:
        """
        Check if dev launcher is active.
        Returns (is_active, reason).
        """
        indicators = cls.DEFAULT_INDICATORS.copy()
        if additional_indicators:
            indicators.extend(additional_indicators)
            
        for indicator in indicators:
            if env_manager.get(indicator):
                return True, f"Dev launcher detected via {indicator}"
                
        return False, "No dev launcher indicators found"
    
    @classmethod
    def check_critical_vars_preloaded(cls, env_manager, critical_vars: List[str]) -> Tuple[bool, str]:
        """
        Check if critical environment variables are already set.
        This handles cases where env vars are set directly without dev launcher.
        """
        vars_already_set = sum(1 for var in critical_vars if env_manager.get(var))
        threshold = len(critical_vars) // 2
        
        if vars_already_set >= threshold:
            return True, f"Critical vars already set ({vars_already_set}/{len(critical_vars)})"
        else:
            return False, f"Insufficient critical vars set ({vars_already_set}/{len(critical_vars)})"


class EnvFileLoader:
    """Standardized .env file loading with fallback chains."""
    
    @classmethod
    def load_env_file(cls, file_path: Path, override: bool = False) -> bool:
        """Load a single .env file if it exists."""
        if not file_path.exists():
            return False
            
        try:
            from dotenv import load_dotenv
            load_dotenv(file_path, override=override)
            return True
        except ImportError:
            # python-dotenv not available
            return False
    
    @classmethod
    def load_env_file_chain(cls, file_paths: List[Path], override_sequence: List[bool] = None) -> List[Path]:
        """
        Load a chain of .env files in order.
        Returns list of successfully loaded files.
        """
        if override_sequence is None:
            override_sequence = [False] + [True] * (len(file_paths) - 1)
            
        loaded_files = []
        for i, file_path in enumerate(file_paths):
            override = override_sequence[i] if i < len(override_sequence) else True
            if cls.load_env_file(file_path, override=override):
                loaded_files.append(file_path)
                
        return loaded_files
    
    @classmethod
    def get_standard_env_files(cls, root_path: Path) -> List[Path]:
        """Get standard .env file sequence for backend service."""
        return [
            root_path / '.env',
            root_path / '.env.development', 
            root_path / '.env.development.local'
        ]
    
    @classmethod
    def get_auth_service_env_files(cls, auth_service_path: Path) -> List[Path]:
        """Get .env file sequence for auth service."""
        parent_env = auth_service_path.parent / ".env"
        current_env = auth_service_path / ".env"
        return [parent_env, current_env]


class ConfigurationValidator:
    """Environment validation utilities."""
    
    @classmethod
    def validate_critical_vars(cls, env_manager, critical_vars: List[str]) -> Tuple[bool, List[str]]:
        """Validate that critical variables are present."""
        missing_vars = []
        for var in critical_vars:
            if not env_manager.get(var):
                missing_vars.append(var)
                
        return len(missing_vars) == 0, missing_vars
    
    @classmethod
    def log_env_loading_status(cls, result: LoadingResult, service_name: str) -> None:
        """Log environment loading status consistently."""
        if result.loaded:
            files_str = ", ".join(str(f) for f in result.files_loaded)
            print(f"{service_name}: Loaded environment files: {files_str}")
        else:
            print(f"{service_name}: {result.reason}")


class StartupEnvironmentManager:
    """Central coordinator for environment loading across all services."""
    
    def __init__(self, env_manager):
        """Initialize with environment manager (IsolatedEnvironment)."""
        self.env_manager = env_manager
        
    def should_load_env_files(self, config: ServiceConfig) -> Tuple[bool, str]:
        """
        Determine if .env files should be loaded based on environment and dev launcher detection.
        Returns (should_load, reason).
        """
        # CRITICAL: Never load .env files in staging or production
        if EnvironmentDetector.is_production_like(self.env_manager):
            env_type = EnvironmentDetector.detect_environment(self.env_manager)
            return False, f"Running in {env_type.value} - skipping .env file loading (using GSM)"
        
        # Check if dev launcher already loaded environment variables
        dev_launcher_active, dev_reason = DevLauncherDetector.is_dev_launcher_active(
            self.env_manager, config.dev_launcher_indicators
        )
        if dev_launcher_active:
            return False, f"Dev launcher detected - skipping .env loading: {dev_reason}"
        
        # Check if critical environment variables are already set
        vars_preloaded, vars_reason = DevLauncherDetector.check_critical_vars_preloaded(
            self.env_manager, config.critical_vars
        )
        if vars_preloaded:
            return False, f"Critical environment variables already set - skipping .env loading: {vars_reason}"
        
        return True, "Environment loading required for direct application run"
    
    def load_environment_files(self, config: ServiceConfig) -> LoadingResult:
        """
        Load environment files according to service configuration.
        Preserves all existing behavior while centralizing logic.
        """
        environment_detected = EnvironmentDetector.detect_environment(self.env_manager)
        dev_launcher_detected, _ = DevLauncherDetector.is_dev_launcher_active(
            self.env_manager, config.dev_launcher_indicators
        )
        
        should_load, reason = self.should_load_env_files(config)
        
        if not should_load:
            return LoadingResult(
                loaded=False,
                reason=reason,
                files_loaded=[],
                environment_detected=environment_detected,
                dev_launcher_detected=dev_launcher_detected
            )
        
        # Load environment files
        env_file_paths = [Path(p) for p in config.env_file_paths]
        
        try:
            loaded_files = EnvFileLoader.load_env_file_chain(env_file_paths)
            
            if loaded_files:
                return LoadingResult(
                    loaded=True,
                    reason=f"Loaded {len(loaded_files)} environment files",
                    files_loaded=loaded_files,
                    environment_detected=environment_detected,
                    dev_launcher_detected=dev_launcher_detected
                )
            else:
                return LoadingResult(
                    loaded=False,
                    reason="No environment files found or loaded",
                    files_loaded=[],
                    environment_detected=environment_detected,
                    dev_launcher_detected=dev_launcher_detected
                )
                
        except ImportError:
            if config.skip_missing_dotenv:
                return LoadingResult(
                    loaded=False,
                    reason="python-dotenv not available - skipping .env loading",
                    files_loaded=[],
                    environment_detected=environment_detected,
                    dev_launcher_detected=dev_launcher_detected
                )
            else:
                raise
    
    def setup_service_environment(self, config: ServiceConfig) -> LoadingResult:
        """
        Complete service environment setup.
        This is the main entry point for services.
        """
        result = self.load_environment_files(config)
        
        # Log the result consistently
        ConfigurationValidator.log_env_loading_status(result, config.service_name)
        
        return result


# Pre-configured service configurations for easy migration
def get_project_root() -> Path:
    """Get project root path (shared utility)."""
    current = Path(__file__).parent
    while current.parent != current:
        if (current / 'pyproject.toml').exists() or (current / '.git').exists():
            return current
        current = current.parent
    return Path.cwd()


# Backend Service Configuration
BACKEND_CONFIG = ServiceConfig(
    service_name="Backend Service",
    critical_vars=['LLM_MODE', 'POSTGRES_HOST', 'GEMINI_API_KEY'],
    dev_launcher_indicators=[
        'DEV_LAUNCHER_ACTIVE',
        'CROSS_SERVICE_AUTH_TOKEN',
    ],
    env_file_paths=EnvFileLoader.get_standard_env_files(get_project_root()),
    skip_missing_dotenv=True
)

# Auth Service Configuration  
AUTH_CONFIG = ServiceConfig(
    service_name="Auth Service",
    critical_vars=['SERVICE_SECRET'],
    dev_launcher_indicators=[
        'DEV_LAUNCHER_ACTIVE',
        'CROSS_SERVICE_AUTH_TOKEN',
    ],
    env_file_paths=EnvFileLoader.get_auth_service_env_files(Path(__file__).parent.parent / "auth_service"),
    skip_missing_dotenv=True
)