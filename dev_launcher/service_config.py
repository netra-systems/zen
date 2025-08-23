"""
Service configuration management for the dev launcher.

DEFAULT CONFIGURATION:
- Redis:       LOCAL (localhost:6379)
- ClickHouse:  LOCAL (localhost:9000)
- PostgreSQL:  LOCAL (localhost:5433)
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
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from dev_launcher.unicode_utils import get_emoji, safe_print, setup_unicode_console

logger = logging.getLogger(__name__)


class ResourceMode(Enum):
    """Resource mode for services."""
    LOCAL = "local"          # Run service locally (requires installation)
    SHARED = "shared"        # Use shared cloud resource
    MOCK = "mock"           # Use mock/stub implementation
    DISABLED = "disabled"   # Service is disabled (NOT RECOMMENDED)


@dataclass
class ServiceResource:
    """Configuration for a service resource."""
    name: str
    mode: ResourceMode = ResourceMode.SHARED
    local_config: Dict[str, Any] = field(default_factory=dict)
    shared_config: Dict[str, Any] = field(default_factory=dict)
    mock_config: Dict[str, Any] = field(default_factory=dict)
    
    def get_config(self) -> Dict[str, Any]:
        """Get the configuration based on the current mode."""
        if self.mode == ResourceMode.LOCAL:
            return self.local_config
        elif self.mode == ResourceMode.SHARED:
            return self.shared_config
        elif self.mode == ResourceMode.MOCK:
            return self.mock_config
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


@dataclass
class ServicesConfiguration:
    """Complete services configuration."""
    
    # Core services with their configurations
    redis: ServiceResource = field(default_factory=lambda: ServiceResource(
        name="redis",
        mode=ResourceMode(os.environ.get("REDIS_MODE", "local").lower()) if os.environ.get("REDIS_MODE") else ResourceMode.LOCAL,
        local_config={
            "host": os.environ.get("REDIS_HOST", "localhost"),
            "port": int(os.environ.get("REDIS_PORT", "6379")),
            "db": 0
        },
        shared_config={
            "host": "redis-17593.c305.ap-south-1-1.ec2.redns.redis-cloud.com",
            "port": 17593,
            "password": "cpmdn7pVpsJSK2mb7lUTj2VaQhSC1L3S",
            "db": 0
        },
        mock_config={"mock": True}
    ))
    
    clickhouse: ServiceResource = field(default_factory=lambda: ServiceResource(
        name="clickhouse",
        mode=ResourceMode(os.environ.get("CLICKHOUSE_MODE", "local").lower()) if os.environ.get("CLICKHOUSE_MODE") else ResourceMode.LOCAL,
        local_config={
            "host": os.environ.get("CLICKHOUSE_HOST", "localhost"),
            "port": int(os.environ.get("CLICKHOUSE_NATIVE_PORT", "9000")),
            "http_port": int(os.environ.get("CLICKHOUSE_HTTP_PORT", "8123")),
            "user": os.environ.get("CLICKHOUSE_USER", "default"),
            "password": os.environ.get("CLICKHOUSE_PASSWORD", "netra_dev_password"),
            "database": os.environ.get("CLICKHOUSE_DB", "netra_dev"),
            "secure": False
        },
        shared_config={
            "host": os.environ.get("CLICKHOUSE_SHARED_HOST", "clickhouse_host_url_placeholder"),
            "port": 8443,
            "user": "default",
            "password": "46YQC0J~6SfZ.",
            "database": "default",
            "secure": True
        },
        mock_config={"mock": True}
    ))
    
    postgres: ServiceResource = field(default_factory=lambda: ServiceResource(
        name="postgres",
        mode=ResourceMode(os.environ.get("POSTGRES_MODE", "local").lower()) if os.environ.get("POSTGRES_MODE") else ResourceMode.LOCAL,
        local_config={
            "host": "localhost",
            "port": 5433,
            "user": "postgres",
            "password": "",
            "database": "netra_dev"
        },
        shared_config={
            # Can be configured for shared dev database if needed
            "host": "dev-postgres.example.com",
            "port": 5432,
            "user": "dev_user",
            "password": "",  # Will be loaded from secrets
            "database": "netra_dev"
        },
        mock_config={"mock": True}
    ))
    
    llm: ServiceResource = field(default_factory=lambda: ServiceResource(
        name="llm",
        mode=ResourceMode(os.environ.get("LLM_MODE", "shared").lower()) if os.environ.get("LLM_MODE") else ResourceMode.SHARED,
        local_config={
            # Local LLM options (e.g., Ollama)
            "provider": "ollama",
            "base_url": "http://localhost:11434"
        },
        shared_config={
            # Cloud LLM providers
            "providers": ["anthropic", "openai", "gemini"],
            "default_provider": "gemini"
        },
        mock_config={"mock": True, "response": "Mock LLM response"}
    ))
    
    auth_service: ServiceResource = field(default_factory=lambda: ServiceResource(
        name="auth_service",
        mode=ResourceMode(os.environ.get("AUTH_MODE", "local").lower()) if os.environ.get("AUTH_MODE") else ResourceMode.LOCAL,
        local_config={
            "host": "localhost",
            "port": 8081,
            "health_endpoint": "/health",
            "enabled": True
        },
        shared_config={
            # For production/staging
            "host": "auth.netrasystems.ai",
            "port": 443,
            "health_endpoint": "/health",
            "enabled": True
        },
        mock_config={"mock": True, "enabled": False}
    ))
    
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
        """Add ClickHouse URL to environment variables."""
        if self.clickhouse.mode == ResourceMode.DISABLED:
            return
        ch_config = self.clickhouse.get_config()
        if self.clickhouse.mode == ResourceMode.SHARED:
            protocol = "clickhouse+https" if ch_config.get("secure") else "clickhouse"
            env_vars["CLICKHOUSE_URL"] = f"{protocol}://{ch_config['user']}:{ch_config['password']}@{ch_config['host']}:{ch_config['port']}/{ch_config['database']}"
        elif self.clickhouse.mode == ResourceMode.LOCAL:
            password_part = f":{ch_config['password']}" if ch_config.get('password') else ""
            env_vars["CLICKHOUSE_URL"] = f"clickhouse://{ch_config['user']}{password_part}@{ch_config['host']}:{ch_config['port']}/{ch_config['database']}"
            # Also set HTTP port for local mode
            if 'http_port' in ch_config:
                env_vars["CLICKHOUSE_HTTP_PORT"] = str(ch_config['http_port'])
    
    def _add_postgres_url(self, env_vars: Dict[str, str]):
        """Add PostgreSQL URL to environment variables."""
        if self.postgres.mode == ResourceMode.DISABLED:
            return
        existing_db_url = os.environ.get("DATABASE_URL")
        if existing_db_url:
            env_vars["DATABASE_URL"] = existing_db_url
        elif self.postgres.mode == ResourceMode.MOCK:
            env_vars["DATABASE_URL"] = "postgresql://mock:mock@localhost:5432/mock"
        elif self.postgres.mode == ResourceMode.LOCAL:
            self._add_local_postgres_url(env_vars)
        elif self.postgres.mode == ResourceMode.SHARED:
            self._handle_shared_postgres_warning()
    
    def _add_local_postgres_url(self, env_vars: Dict[str, str]):
        """Add local PostgreSQL URL."""
        pg_config = self.postgres.get_config()
        env_vars["DATABASE_URL"] = f"postgresql://{pg_config['user']}:{pg_config['password']}@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"
    
    def _handle_shared_postgres_warning(self):
        """Handle shared PostgreSQL mode warnings."""
        logger.warning("PostgreSQL is in SHARED mode but DATABASE_URL not found in environment")
        logger.warning("Please set DATABASE_URL environment variable for shared PostgreSQL")
    
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
                warnings.append(f"⚠️  {service.name.upper()} is disabled - some features may not work")
        
        # Check for local services that require installation
        if self.redis.mode == ResourceMode.LOCAL:
            if not self._check_redis_installed():
                warnings.append("⚠️  Redis is set to LOCAL but doesn't appear to be installed")
        
        if self.clickhouse.mode == ResourceMode.LOCAL:
            if not self._check_clickhouse_installed():
                warnings.append("⚠️  ClickHouse is set to LOCAL but doesn't appear to be installed")
        
        if self.postgres.mode == ResourceMode.LOCAL:
            if not self._check_postgres_installed():
                warnings.append("⚠️  PostgreSQL is set to LOCAL but doesn't appear to be installed")
        
        return warnings
    
    def _check_redis_installed(self) -> bool:
        """Check if Redis is installed locally."""
        try:
            import subprocess
            result = subprocess.run(["redis-cli", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _check_clickhouse_installed(self) -> bool:
        """Check if ClickHouse is installed locally."""
        try:
            import subprocess
            result = subprocess.run(["clickhouse-client", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _check_postgres_installed(self) -> bool:
        """Check if PostgreSQL is installed locally."""
        try:
            import subprocess
            result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
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
                elif service.mode == ResourceMode.MOCK:
                    service.mock_config.update(service_config.get("config", {}))
        
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
        print("  • SHARED: Use cloud-hosted development resources (recommended)")
        print("  • LOCAL:  Use locally installed services")
        print("  • MOCK:   Use mock implementations (limited functionality)")
        print()
        
        # Quick setup option
        use_defaults = self._ask_yes_no(
            "Use recommended configuration? (Local for all services except LLM)",
            default=True
        )
        
        if use_defaults:
            safe_print(f"\n{get_emoji('check')} Using recommended configuration:")
            print("  • Redis:      LOCAL  (Local Redis)")
            print("  • ClickHouse: LOCAL  (Local ClickHouse)")
            print("  • PostgreSQL: LOCAL  (Local PostgreSQL)")
            print("  • LLM:        SHARED (API providers)")
            print("  • Auth:       LOCAL  (Local auth service)")
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
            print("\n⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"  {warning}")
        
        # Save configuration
        save_config = self._ask_yes_no("\nSave this configuration for future use?", default=True)
        if save_config:
            config_path = Path.cwd() / ".dev_services.json"
            self.config.save_to_file(config_path)
            print(f"✅ Configuration saved to {config_path}")
        
        return self.config
    
    def _configure_service(self, service: ServiceResource, description: str, recommended_mode: ResourceMode):
        """Configure a single service."""
        print(f"\n📦 {service.name.upper()}: {description}")
        print(f"   Recommended: {recommended_mode.value.upper()}")
        
        # Show options
        print("   Options:")
        print("     1. SHARED - Use cloud-hosted service")
        print("     2. LOCAL  - Use locally installed service")
        print("     3. MOCK   - Use mock implementation")
        print("     4. SKIP   - Disable this service (not recommended)")
        
        try:
            choice = input("   Choice [1-4, default=1]: ").strip() or "1"
        except EOFError:
            logger.info("Non-interactive mode: using default choice=1")
            choice = "1"
        
        mode_map = {
            "1": ResourceMode.SHARED,
            "2": ResourceMode.LOCAL,
            "3": ResourceMode.MOCK,
            "4": ResourceMode.DISABLED
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


def load_or_create_config(interactive: bool = True) -> ServicesConfiguration:
    """Load existing configuration or create a new one.
    
    Default configuration:
    - Redis: LOCAL
    - ClickHouse: LOCAL
    - PostgreSQL: LOCAL
    - LLM: SHARED (API providers)
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
            
            # Validate the loaded configuration
            warnings = config.validate()
            if warnings and interactive:
                # Log warnings but don't prompt user
                for warning in warnings:
                    logger.debug(f"Configuration notice: {warning}")
            
            return config
        except Exception as e:
            logger.warning(f"Failed to load configuration: {e}")
    
    # Create new configuration
    if interactive:
        try:
            wizard = ServiceConfigWizard()
            return wizard.run()
        except EOFError:
            logger.info("Non-interactive mode detected, using default configuration")
            config = ServicesConfiguration()
            return config
    else:
        # Use defaults in non-interactive mode
        config = ServicesConfiguration()
        logger.info("Using default service configuration (LOCAL for all except LLM)")
        return config