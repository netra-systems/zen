"""
Service configuration management for the dev launcher.

DEFAULT CONFIGURATION:
- Redis:       DOCKER (localhost:6379 via container)
- ClickHouse:  DOCKER (localhost:9000 via container)
- PostgreSQL:  DOCKER (localhost:5433 via container)
- LLM:         SHARED (API providers - Anthropic, OpenAI, Gemini)
- Auth:        LOCAL (localhost:8081)

TO OVERRIDE DEFAULTS:
1. Environment variables: Set REDIS_MODE=shared, CLICKHOUSE_MODE=shared, etc.
2. Configuration file: Create .dev_services.json with custom settings
3. Interactive wizard: Run the launcher and choose custom configuration

Provides clear options for using local vs shared resources with user-friendly prompts.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.isolated_environment import get_env

from dev_launcher.unicode_utils import get_emoji, safe_print, setup_unicode_console

logger = logging.getLogger(__name__)


class ResourceMode(Enum):
    """Resource mode for services."""
    LOCAL = "local"          # Run service locally (requires installation)
    SHARED = "shared"        # Use shared cloud resource
    DOCKER = "docker"       # Use Docker containers for local services
    DISABLED = "disabled"   # Service is disabled (NOT RECOMMENDED)
    # NOTE: MOCK mode removed - mock services are ONLY for specific test cases, not development


@dataclass
class ServiceResource:
    """Configuration for a service resource."""
    name: str
    mode: ResourceMode = ResourceMode.SHARED
    local_config: Dict[str, Any] = field(default_factory=dict)
    shared_config: Dict[str, Any] = field(default_factory=dict)
    # mock_config removed - mock services are only for testing, not development
    docker_config: Dict[str, Any] = field(default_factory=dict)
    
    def get_config(self) -> Dict[str, Any]:
        """Get the configuration based on the current mode."""
        if self.mode == ResourceMode.LOCAL:
            # Check if this is actually Docker-based local
            config = self.local_config.copy()
            if config.get('docker', False):
                # Merge with Docker config
                config.update(self.docker_config)
            return config
        elif self.mode == ResourceMode.SHARED:
            return self.shared_config
        elif self.mode == ResourceMode.DOCKER:
            return self.docker_config
        else:
            return {}
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for this service."""
        config = self.get_config()
        env_vars = {}
        
        # Add mode indicator
        env_key = f"{self.name.upper()}_MODE"
        env_vars[env_key] = self.mode.value
        
        # Add configuration values
        for key, value in config.items():
            env_key = f"{self.name.upper()}_{key.upper()}"
            env_vars[env_key] = str(value)
        
        return env_vars


def _get_redis_defaults():
    """Get Redis configuration with environment variable support."""
    env = get_env()
    redis_mode = env.get("REDIS_MODE")
    return ServiceResource(
        name="redis",
        mode=ResourceMode(redis_mode.lower()) if redis_mode else ResourceMode.DOCKER,
        local_config={
            "host": env.get("REDIS_HOST", "localhost"),
            "port": int(env.get("REDIS_PORT", "6379")),
            "db": 0
        },
        shared_config={
            "host": "redis-17593.c305.ap-south-1-1.ec2.redns.redis-cloud.com",
            "port": 17593,
            "password": "cpmdn7pVpsJSK2mb7lUTj2VaQhSC1L3S",
            "db": 0
        },
        docker_config={
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "docker": True,
            "container_name": "netra-dev-redis"
        }
    )


def _get_clickhouse_defaults():
    """Get ClickHouse configuration with environment variable support."""
    env = get_env()
    clickhouse_mode = env.get("CLICKHOUSE_MODE")
    return ServiceResource(
        name="clickhouse",
        mode=ResourceMode(clickhouse_mode.lower()) if clickhouse_mode else ResourceMode.DOCKER,
        local_config={
            "host": env.get("CLICKHOUSE_HOST", "localhost"),
            "port": int(env.get("CLICKHOUSE_NATIVE_PORT", "9000")),
            "http_port": int(env.get("CLICKHOUSE_HTTP_PORT", "8123")),
            "user": env.get("CLICKHOUSE_USER", "default"),
            "password": env.get("CLICKHOUSE_PASSWORD", "netra_dev_password"),
            "database": env.get("CLICKHOUSE_DB", "netra_dev"),
        },
        shared_config={
            "host": env.get("CLICKHOUSE_SHARED_HOST", "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"),
            "port": 9440,
            "http_port": 8443,
            "secure": True,
            "user": "default",
            "password": "AGpI.gJfV2.0_",
            "database": "netra_shared",
        },
        docker_config={
            "host": "localhost",
            "port": 9000,
            "http_port": 8123,
            "user": "default",
            "password": "netra_dev_password",
            "database": "netra_dev",
            "docker": True,
            "container_name": "netra-dev-clickhouse"
        }
    )


def _get_postgres_defaults():
    """Get PostgreSQL configuration with environment variable support.""" 
    env = get_env()
    postgres_mode = env.get("POSTGRES_MODE")
    return ServiceResource(
        name="postgres",
        mode=ResourceMode(postgres_mode.lower()) if postgres_mode else ResourceMode.DOCKER,
        local_config={
            "host": "127.0.0.1",
            "port": 5433,
            "database": "netra_dev",
            "user": "netra_dev",
            "password": "netra_dev_password"
        },
        shared_config={
            "host": "34.93.246.241",
            "port": 5432,
            "database": "netra_dev",
            "user": "netra_dev",
            "password": "bGBaG2g4Cfa&Q@cNxGZ3"
        },
        docker_config={
            "host": "127.0.0.1",
            "port": 5433,
            "database": "netra_dev",
            "user": "netra_dev", 
            "password": "netra_dev_password",
            "docker": True,
            "container_name": "netra-dev-postgres"
        }
    )


def _get_llm_defaults():
    """Get LLM configuration with environment variable support."""
    env = get_env()
    llm_mode = env.get("LLM_MODE")
    return ServiceResource(
        name="llm",
        mode=ResourceMode(llm_mode.lower()) if llm_mode else ResourceMode.SHARED,
        shared_config={
            "providers": ["anthropic", "openai", "gemini"],
            "anthropic_api_key": "ANTHROPIC_API_KEY",
            "openai_api_key": "OPENAI_API_KEY",
            "gemini_api_key": "GEMINI_API_KEY"
        }
    )


def _get_auth_defaults():
    """Get Auth service configuration with environment variable support."""
    env = get_env()
    auth_mode = env.get("AUTH_MODE")
    return ServiceResource(
        name="auth",
        mode=ResourceMode(auth_mode.lower()) if auth_mode else ResourceMode.LOCAL,
        local_config={
            "host": "localhost",
            "port": 8081
        }
    )


@dataclass
class ServicesConfiguration:
    """Complete services configuration."""
    
    # Core services with their configurations
    redis: ServiceResource = field(default_factory=_get_redis_defaults)
    
    clickhouse: ServiceResource = field(default_factory=_get_clickhouse_defaults)
    
    postgres: ServiceResource = field(default_factory=_get_postgres_defaults)
    
    llm: ServiceResource = field(default_factory=_get_llm_defaults)
    
    auth_service: ServiceResource = field(default_factory=_get_auth_defaults)
    
    def get_all_env_vars(self) -> Dict[str, str]:
        """Get all environment variables for all services."""
        env_vars = self._get_service_env_vars()
        self._add_redis_url(env_vars)
        self._add_clickhouse_url(env_vars)
        self._add_postgres_url(env_vars)
        self._add_auth_service_url(env_vars)
        self._add_service_flags(env_vars)
        return env_vars
    
    def _get_service_env_vars(self) -> Dict[str, str]:
        """Get service-specific environment variables."""
        env_vars = {}
        for service in [self.redis, self.clickhouse, self.postgres, self.llm, self.auth_service]:
            env_vars.update(service.get_env_vars())
        return env_vars
    
    def _add_redis_url(self, env_vars: Dict[str, str]):
        """Add Redis URL to environment variables."""
        if self.redis.mode == ResourceMode.DISABLED:
            return
        redis_config = self.redis.get_config()
        if self.redis.mode == ResourceMode.SHARED and redis_config.get("password"):
            env_vars["REDIS_URL"] = f"redis://:{redis_config['password']}@{redis_config['host']}:{redis_config['port']}/{redis_config.get('db', 0)}"
        elif self.redis.mode == ResourceMode.LOCAL:
            env_vars["REDIS_URL"] = f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config.get('db', 0)}"
    
    def _add_clickhouse_url(self, env_vars: Dict[str, str]):
        """Add ClickHouse URL and individual environment variables."""
        if self.clickhouse.mode == ResourceMode.DISABLED:
            return
        ch_config = self.clickhouse.get_config()
        
        # Set individual environment variables that the backend expects
        env_vars["CLICKHOUSE_HOST"] = ch_config['host']
        env_vars["CLICKHOUSE_PORT"] = str(ch_config['port'])
        env_vars["CLICKHOUSE_USER"] = ch_config['user']
        if ch_config.get('password'):
            env_vars["CLICKHOUSE_PASSWORD"] = ch_config['password']
        env_vars["CLICKHOUSE_DB"] = ch_config['database']
        
        # Set HTTP port for backend HTTP client
        if 'http_port' in ch_config:
            env_vars["CLICKHOUSE_HTTP_PORT"] = str(ch_config['http_port'])
        
        # Set URL for compatibility
        if self.clickhouse.mode == ResourceMode.SHARED:
            protocol = "clickhouse+https" if ch_config.get("secure") else "clickhouse"
            env_vars["CLICKHOUSE_URL"] = f"{protocol}://{ch_config['user']}:{ch_config['password']}@{ch_config['host']}:{ch_config['port']}/{ch_config['database']}"
        elif self.clickhouse.mode == ResourceMode.LOCAL:
            password_part = f":{ch_config['password']}" if ch_config.get('password') else ""
            env_vars["CLICKHOUSE_URL"] = f"clickhouse://{ch_config['user']}{password_part}@{ch_config['host']}:{ch_config['port']}/{ch_config['database']}"
    
    def _add_postgres_url(self, env_vars: Dict[str, str]):
        """Add PostgreSQL URL to environment variables."""
        if self.postgres.mode == ResourceMode.DISABLED:
            return
        env = get_env()
        existing_db_url = env.get("DATABASE_URL")
        if existing_db_url:
            env_vars["DATABASE_URL"] = existing_db_url
        # Mock mode not supported in development - removed mock database URL
        elif self.postgres.mode == ResourceMode.LOCAL:
            self._add_local_postgres_url(env_vars)
        elif self.postgres.mode == ResourceMode.SHARED:
            self._handle_shared_postgres_warning()
    
    def _add_local_postgres_url(self, env_vars: Dict[str, str]):
        """Add local PostgreSQL URL."""
        pg_config = self.postgres.get_config()
        
        # Use DatabaseURLBuilder for proper URL construction
        from shared.database_url_builder import DatabaseURLBuilder
        
        # Create env vars for builder
        builder_env = {
            'POSTGRES_HOST': pg_config['host'],
            'POSTGRES_PORT': str(pg_config['port']),
            'POSTGRES_DB': pg_config['database'],
            'POSTGRES_USER': pg_config['user'],
            'POSTGRES_PASSWORD': pg_config['password'],
            'ENVIRONMENT': 'development'
        }
        
        builder = DatabaseURLBuilder(builder_env)
        # Use TCP sync URL for dev launcher (non-async)
        env_vars["DATABASE_URL"] = builder.tcp.sync_url or builder.development.default_sync_url
    
    def _handle_shared_postgres_warning(self):
        """Handle shared PostgreSQL mode warnings."""
        logger.warning("PostgreSQL is in SHARED mode but #removed-legacynot found in environment")
        logger.warning("Please set #removed-legacyenvironment variable for shared PostgreSQL")
    
    def _add_auth_service_url(self, env_vars: Dict[str, str]):
        """Add Auth Service URL to environment variables."""
        if self.auth_service.mode == ResourceMode.DISABLED:
            env_vars["AUTH_SERVICE_ENABLED"] = "false"
            return
        
        auth_config = self.auth_service.get_config()
        if auth_config.get("enabled", True):
            env_vars["AUTH_SERVICE_ENABLED"] = "true"
            # Use 127.0.0.1 for Windows compatibility instead of localhost
            host = auth_config.get("host", "127.0.0.1")
            port = auth_config.get("port", 8081)
            
            if self.auth_service.mode == ResourceMode.SHARED:
                env_vars["AUTH_SERVICE_URL"] = f"https://{host}"
            else:
                env_vars["AUTH_SERVICE_URL"] = f"http://{host}:{port}"
        else:
            env_vars["AUTH_SERVICE_ENABLED"] = "false"
    
    def _add_service_flags(self, env_vars: Dict[str, str]):
        """Add service configuration flags."""
        env_vars["ENABLE_ALL_SERVICES"] = "true"
    
    def validate(self) -> List[str]:
        """Validate the configuration and return any warnings."""
        warnings = []
        
        # Check for disabled services
        for service in [self.redis, self.clickhouse, self.postgres, self.llm]:
            if service.mode == ResourceMode.DISABLED:
                warnings.append(f" WARNING: [U+FE0F]  {service.name.upper()} is disabled - some features may not work")
        
        # Check for local services that require installation (skip Docker-based)
        if self.redis.mode == ResourceMode.LOCAL and not self.redis.get_config().get('docker', False):
            if not self._check_redis_installed():
                warnings.append(" WARNING: [U+FE0F]  Redis is set to LOCAL but doesn't appear to be installed")
        
        if self.clickhouse.mode == ResourceMode.LOCAL and not self.clickhouse.get_config().get('docker', False):
            if not self._check_clickhouse_installed():
                warnings.append(" WARNING: [U+FE0F]  ClickHouse is set to LOCAL but doesn't appear to be installed")
        
        if self.postgres.mode == ResourceMode.LOCAL and not self.postgres.get_config().get('docker', False):
            if not self._check_postgres_installed():
                warnings.append(" WARNING: [U+FE0F]  PostgreSQL is set to LOCAL but doesn't appear to be installed")
        
        # Check Docker availability for Docker mode services
        docker_services = []
        if self.redis.get_config().get('docker', False):
            docker_services.append('Redis')
        if self.clickhouse.get_config().get('docker', False):
            docker_services.append('ClickHouse')
        if self.postgres.get_config().get('docker', False):
            docker_services.append('PostgreSQL')
        
        if docker_services:
            from dev_launcher.docker_services import check_docker_availability
            if not check_docker_availability():
                services_str = ', '.join(docker_services)
                warnings.append(f" WARNING: [U+FE0F]  Docker not available but required for: {services_str}")
        
        return warnings
    
    def _check_redis_installed(self) -> bool:
        """Check if Redis is installed and running locally."""
        try:
            from dev_launcher.service_availability_checker import ServiceAvailabilityChecker
            checker = ServiceAvailabilityChecker()
            return checker._check_redis_availability()
        except ImportError:
            # Fallback to basic version check
            try:
                import subprocess
                result = subprocess.run(["redis-cli", "--version"], capture_output=True, text=True, timeout=5)
                return result.returncode == 0
            except:
                return False
    
    def _check_clickhouse_installed(self) -> bool:
        """Check if ClickHouse is installed and running locally."""
        try:
            from dev_launcher.service_availability_checker import ServiceAvailabilityChecker
            checker = ServiceAvailabilityChecker()
            return checker._check_clickhouse_availability()
        except ImportError:
            # Fallback to basic version check
            try:
                import subprocess
                result = subprocess.run(["clickhouse-client", "--version"], capture_output=True, text=True, timeout=5)
                return result.returncode == 0
            except:
                return False
    
    def _check_postgres_installed(self) -> bool:
        """Check if PostgreSQL is installed and running locally."""
        try:
            from dev_launcher.service_availability_checker import ServiceAvailabilityChecker
            checker = ServiceAvailabilityChecker()
            return checker._check_postgres_availability()
        except ImportError:
            # Fallback to basic version check
            try:
                import subprocess
                result = subprocess.run(["psql", "--version"], capture_output=True, text=True, timeout=5)
                return result.returncode == 0
            except:
                return False
    
    def save_to_file(self, path: Path):
        """Save configuration to a JSON file."""
        config_dict = {
            "redis": {"mode": self.redis.mode.value, "config": self.redis.get_config()},
            "clickhouse": {"mode": self.clickhouse.mode.value, "config": self.clickhouse.get_config()},
            "postgres": {"mode": self.postgres.mode.value, "config": self.postgres.get_config()},
            "llm": {"mode": self.llm.mode.value, "config": self.llm.get_config()}
        }
        
        with open(path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration saved to {path}")
    
    @classmethod
    def load_from_file(cls, path: Path) -> "ServicesConfiguration":
        """Load configuration from a JSON file."""
        if not path.exists():
            logger.warning(f"Configuration file not found: {path}")
            return cls()
        
        with open(path, 'r') as f:
            config_dict = json.load(f)
        
        config = cls()
        
        # Load each service configuration
        for service_name in ["redis", "clickhouse", "postgres", "llm"]:
            if service_name in config_dict:
                service_config = config_dict[service_name]
                service = getattr(config, service_name)
                
                # Set mode
                mode_str = service_config.get("mode", "shared")
                service.mode = ResourceMode(mode_str)
                
                # Update the appropriate config based on mode
                if service.mode == ResourceMode.LOCAL:
                    service.local_config.update(service_config.get("config", {}))
                elif service.mode == ResourceMode.SHARED:
                    service.shared_config.update(service_config.get("config", {}))
                # Mock mode removed - only for testing
        
        logger.info(f"Configuration loaded from {path}")
        return config


class ServiceConfigWizard:
    """Interactive wizard for configuring services."""
    
    def __init__(self):
        self.config = ServicesConfiguration()
    
    def run(self) -> ServicesConfiguration:
        """Run the configuration wizard."""
        setup_unicode_console()
        print("\n" + "="*60)
        safe_print(f"{get_emoji('rocket')} Netra Development Environment Configuration Wizard")
        print("="*60)
        print("\nThis wizard will help you configure services for development.")
        print("You can choose between:")
        print("  [U+2022] SHARED: Use cloud-hosted development resources (recommended)")
        print("  [U+2022] LOCAL:  Use locally installed services")
        # Mock mode not shown - only for testing, not development
        print()
        
        # Quick setup option
        use_defaults = self._ask_yes_no(
            "Use recommended configuration? (Local for all services except LLM)",
            default=True
        )
        
        if use_defaults:
            safe_print(f"\n{get_emoji('check')} Using recommended configuration:")
            print("  [U+2022] Redis:      LOCAL  (Local Redis)")
            print("  [U+2022] ClickHouse: LOCAL  (Local ClickHouse)")
            print("  [U+2022] PostgreSQL: LOCAL  (Local PostgreSQL)")
            print("  [U+2022] LLM:        SHARED (API providers)")
            print("  [U+2022] Auth:       LOCAL  (Local auth service)")
            return self.config
        
        # Custom configuration
        print("\nLet's configure each service:")
        
        # Configure Redis
        self._configure_service(
            self.config.redis,
            "Redis (caching & real-time features)",
            recommended_mode=ResourceMode.LOCAL
        )
        
        # Configure ClickHouse
        self._configure_service(
            self.config.clickhouse,
            "ClickHouse (analytics & metrics)",
            recommended_mode=ResourceMode.LOCAL
        )
        
        # Configure PostgreSQL
        self._configure_service(
            self.config.postgres,
            "PostgreSQL (main database)",
            recommended_mode=ResourceMode.LOCAL
        )
        
        # Configure LLM
        self._configure_service(
            self.config.llm,
            "LLM Services (AI features)",
            recommended_mode=ResourceMode.SHARED
        )
        
        # Configure Auth Service
        self._configure_service(
            self.config.auth_service,
            "Auth Service (authentication & authorization)",
            recommended_mode=ResourceMode.LOCAL
        )
        
        # Validate configuration
        warnings = self.config.validate()
        if warnings:
            print("\n WARNING: [U+FE0F]  Configuration warnings:")
            for warning in warnings:
                print(f"  {warning}")
        
        # Save configuration
        save_config = self._ask_yes_no("\nSave this configuration for future use?", default=True)
        if save_config:
            config_path = Path.cwd() / ".dev_services.json"
            self.config.save_to_file(config_path)
            print(f" PASS:  Configuration saved to {config_path}")
        
        return self.config
    
    def _configure_service(self, service: ServiceResource, description: str, recommended_mode: ResourceMode):
        """Configure a single service."""
        print(f"\n[U+1F4E6] {service.name.upper()}: {description}")
        print(f"   Recommended: {recommended_mode.value.upper()}")
        
        # Show options
        print("   Options:")
        print("     1. SHARED - Use cloud-hosted service")
        print("     2. LOCAL  - Use locally installed service")
        print("     3. SKIP   - Disable this service (not recommended)")
        
        try:
            choice = input("   Choice [1-3, default=1]: ").strip() or "1"
        except EOFError:
            logger.info("Non-interactive mode: using default choice=1")
            choice = "1"
        
        mode_map = {
            "1": ResourceMode.SHARED,
            "2": ResourceMode.LOCAL,
            "3": ResourceMode.DISABLED
            # Mock mode removed - only for testing
        }
        
        service.mode = mode_map.get(choice, ResourceMode.SHARED)
        
        # Additional configuration for local mode
        if service.mode == ResourceMode.LOCAL:
            customize = self._ask_yes_no(f"   Customize local {service.name} settings?", default=False)
            if customize:
                self._customize_local_config(service)
    
    def _customize_local_config(self, service: ServiceResource):
        """Customize local configuration for a service."""
        print(f"\n   Configuring local {service.name}:")
        
        for key, value in service.local_config.items():
            if key == "password":
                continue  # Skip password fields in interactive mode
            
            try:
                new_value = input(f"     {key} [{value}]: ").strip()
            except EOFError:
                logger.info(f"Non-interactive mode: keeping default {key}={value}")
                new_value = ""
            if new_value:
                # Convert to appropriate type
                if isinstance(value, int):
                    try:
                        service.local_config[key] = int(new_value)
                    except ValueError:
                        print(f"       Invalid value, keeping {value}")
                elif isinstance(value, bool):
                    service.local_config[key] = new_value.lower() in ["true", "yes", "1"]
                else:
                    service.local_config[key] = new_value
    
    def _ask_yes_no(self, question: str, default: bool = True) -> bool:
        """Ask a yes/no question."""
        default_str = "Y/n" if default else "y/N"
        try:
            response = input(f"{question} [{default_str}]: ").strip().lower()
        except EOFError:
            logger.info(f"Non-interactive mode: using default={default} for '{question}'")
            return default
        
        if not response:
            return default
        
        return response in ["y", "yes", "true", "1"]


def load_or_create_config(interactive: bool = False) -> ServicesConfiguration:
    """Load existing configuration or create a new one with smart service detection.
    
    This function now includes intelligent service availability checking:
    - Automatically detects if local services are installed and available
    - Falls back to shared services when local ones aren't available
    - Validates API keys and provides guidance
    - Ensures smooth cold start experience
    
    Default configuration with smart detection:
    - Redis: LOCAL (if available)  ->  SHARED (if not)
    - ClickHouse: LOCAL (if available)  ->  SHARED (if not)  
    - PostgreSQL: LOCAL (if available)  ->  SHARED (if not)
    - LLM: SHARED (API providers - requires valid API keys)
    - Auth Service: LOCAL
    
    To override defaults:
    1. Set environment variables (e.g., REDIS_MODE=shared)
    2. Create .dev_services.json file with custom configuration
    3. Use interactive wizard when prompted
    """
    config_path = Path.cwd() / ".dev_services.json"
    
    # Try to load existing configuration
    if config_path.exists():
        try:
            config = ServicesConfiguration.load_from_file(config_path)
            logger.info("Loaded existing service configuration")
            
            # Check service availability and auto-adjust if needed
            config, availability_warnings = _check_and_adjust_services(config, interactive)
            
            # Validate the configuration
            warnings = config.validate()
            warnings.extend(availability_warnings)
            
            if warnings and interactive:
                # Log warnings but don't prompt user in non-verbose mode
                for warning in warnings:
                    logger.debug(f"Configuration notice: {warning}")
            
            return config
        except Exception as e:
            logger.warning(f"Failed to load configuration: {e}")
    
    # Create new configuration with smart detection
    config = ServicesConfiguration()
    
    if interactive:
        try:
            # Check if user wants to run wizard or use smart defaults
            setup_unicode_console()
            use_smart_defaults = _ask_use_smart_defaults()
            
            if use_smart_defaults:
                config, warnings = _check_and_adjust_services(config, interactive)
                
                if warnings:
                    print()
                    safe_print(f"{get_emoji('info')} Configuration adjustments made:")
                    for warning in warnings:
                        print(f"  [U+2022] {warning}")
                
                # Save the smart configuration
                config.save_to_file(config_path)
                safe_print(f"{get_emoji('check')} Smart configuration saved to {config_path}")
                
                return config
            else:
                # Run interactive wizard
                wizard = ServiceConfigWizard()
                return wizard.run()
                
        except EOFError:
            logger.info("Non-interactive mode detected, using smart default configuration")
            config, _ = _check_and_adjust_services(config, False)
            return config
    else:
        # Non-interactive mode: use smart defaults
        config, warnings = _check_and_adjust_services(config, False)
        logger.info("Using smart default service configuration with availability detection")
        
        if warnings:
            for warning in warnings:
                logger.info(f"Service adjustment: {warning}")
        
        return config


def _ask_use_smart_defaults() -> bool:
    """Ask user if they want to use smart defaults or run wizard."""
    print("\n" + "="*60)
    safe_print(f"{get_emoji('rocket')} Netra Development Environment Setup")
    print("="*60)
    print("\nChoose setup method:")
    print("  1. Smart Setup (Recommended) - Automatically detect and configure services")
    print("  2. Custom Setup - Interactive wizard for manual configuration")
    print()
    
    try:
        choice = input("Choose setup method [1-2, default=1]: ").strip() or "1"
        return choice == "1"
    except EOFError:
        logger.info("Non-interactive mode: using smart defaults")
        return True


def _check_and_adjust_services(config: ServicesConfiguration, 
                              interactive: bool) -> tuple[ServicesConfiguration, list[str]]:
    """Check service availability and adjust configuration accordingly."""
    try:
        from dev_launcher.service_availability_checker import check_and_configure_services
        return check_and_configure_services(config, interactive=interactive)
    except ImportError:
        logger.warning("Service availability checker not available, using basic validation")
        warnings = config.validate()
        return config, warnings