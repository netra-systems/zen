"""
Service configuration management for the dev launcher.

Provides clear options for using local vs shared resources with user-friendly prompts.
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from enum import Enum
import logging
from .unicode_utils import safe_print, get_emoji, setup_unicode_console

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
        mode=ResourceMode.SHARED,
        local_config={
            "host": "localhost",
            "port": 6379,
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
        mode=ResourceMode.SHARED,
        local_config={
            "host": "localhost",
            "port": 9000,
            "user": "default",
            "password": "",
            "database": "default"
        },
        shared_config={
            "host": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
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
        mode=ResourceMode.LOCAL,  # Usually local for development
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
        mode=ResourceMode.SHARED,  # Always use real LLM APIs
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
    
    def get_all_env_vars(self) -> Dict[str, str]:
        """Get all environment variables for all services."""
        env_vars = {}
        
        # Add service-specific environment variables
        for service in [self.redis, self.clickhouse, self.postgres, self.llm]:
            env_vars.update(service.get_env_vars())
        
        # Build connection URLs based on modes
        if self.redis.mode != ResourceMode.DISABLED:
            redis_config = self.redis.get_config()
            if self.redis.mode == ResourceMode.SHARED and redis_config.get("password"):
                env_vars["REDIS_URL"] = f"redis://:{redis_config['password']}@{redis_config['host']}:{redis_config['port']}/{redis_config.get('db', 0)}"
            elif self.redis.mode == ResourceMode.LOCAL:
                env_vars["REDIS_URL"] = f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config.get('db', 0)}"
        
        if self.clickhouse.mode != ResourceMode.DISABLED:
            ch_config = self.clickhouse.get_config()
            if self.clickhouse.mode == ResourceMode.SHARED:
                protocol = "clickhouse+https" if ch_config.get("secure") else "clickhouse"
                env_vars["CLICKHOUSE_URL"] = f"{protocol}://{ch_config['user']}:{ch_config['password']}@{ch_config['host']}:{ch_config['port']}/{ch_config['database']}"
            elif self.clickhouse.mode == ResourceMode.LOCAL:
                env_vars["CLICKHOUSE_URL"] = f"clickhouse://{ch_config['user']}@{ch_config['host']}:{ch_config['port']}/{ch_config['database']}"
        
        if self.postgres.mode != ResourceMode.DISABLED:
            # Check if DATABASE_URL is already set in environment
            existing_db_url = os.environ.get("DATABASE_URL")
            if existing_db_url:
                # Use existing DATABASE_URL from environment
                env_vars["DATABASE_URL"] = existing_db_url
                logger.info(f"Using existing DATABASE_URL from environment")
            elif self.postgres.mode == ResourceMode.MOCK:
                env_vars["DATABASE_URL"] = "postgresql://mock:mock@localhost:5432/mock"
            elif self.postgres.mode == ResourceMode.LOCAL:
                pg_config = self.postgres.get_config()
                env_vars["DATABASE_URL"] = f"postgresql://{pg_config['user']}:{pg_config['password']}@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"
            elif self.postgres.mode == ResourceMode.SHARED:
                # For shared mode, require DATABASE_URL to be set in environment
                logger.warning("PostgreSQL is in SHARED mode but DATABASE_URL not found in environment")
                logger.warning("Please set DATABASE_URL environment variable for shared PostgreSQL")
                # Don't set a default with example.com - this will cause connection errors
        
        # IMPORTANT: Remove all DEV_MODE_DISABLE flags - all services are enabled by default
        # Users should explicitly choose mock or disabled mode if needed
        env_vars["ENABLE_ALL_SERVICES"] = "true"
        
        return env_vars
    
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
            "Use recommended configuration? (Shared Redis & ClickHouse, Local PostgreSQL)",
            default=True
        )
        
        if use_defaults:
            safe_print(f"\n{get_emoji('check')} Using recommended configuration:")
            print("  • Redis:      SHARED (Cloud Redis)")
            print("  • ClickHouse: SHARED (Cloud ClickHouse)")
            print("  • PostgreSQL: LOCAL  (Local database)")
            print("  • LLM:        SHARED (API access)")
            return self.config
        
        # Custom configuration
        print("\nLet's configure each service:")
        
        # Configure Redis
        self._configure_service(
            self.config.redis,
            "Redis (caching & real-time features)",
            recommended_mode=ResourceMode.SHARED
        )
        
        # Configure ClickHouse
        self._configure_service(
            self.config.clickhouse,
            "ClickHouse (analytics & metrics)",
            recommended_mode=ResourceMode.SHARED
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
    """Load existing configuration or create a new one."""
    config_path = Path.cwd() / ".dev_services.json"
    
    # Try to load existing configuration
    if config_path.exists():
        try:
            config = ServicesConfiguration.load_from_file(config_path)
            logger.info("Loaded existing service configuration")
            
            # Validate the loaded configuration
            warnings = config.validate()
            if warnings and interactive:
                print("\n⚠️  Configuration warnings:")
                for warning in warnings:
                    print(f"  {warning}")
                
                # Ask if user wants to reconfigure
                try:
                    reconfigure = input("\nReconfigure services? [y/N]: ").strip().lower()
                    if reconfigure in ["y", "yes"]:
                        wizard = ServiceConfigWizard()
                        config = wizard.run()
                except EOFError:
                    logger.info("Non-interactive mode detected, using existing configuration")
            
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
        logger.info("Using default service configuration (all services in SHARED mode)")
        return config