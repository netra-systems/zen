"""
Configuration management for development launcher.
"""

import logging
import os
from pathlib import Path

from dev_launcher.config import LauncherConfig
from dev_launcher.service_config import ServicesConfiguration, load_or_create_config
from dev_launcher.utils import print_with_emoji

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages launcher configuration and service configuration.
    
    Handles loading, validation, and display of configuration
    for the development environment launcher.
    """
    
    def __init__(self, config: LauncherConfig, use_emoji: bool = True):
        """Initialize configuration manager."""
        self.config = config
        self.use_emoji = use_emoji
        self.services_config = self._load_service_config()
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def _load_service_config(self) -> ServicesConfiguration:
        """Load service configuration."""
        import sys
        interactive = sys.stdin.isatty() and not self.config.non_interactive
        return load_or_create_config(interactive=interactive)
    
    def log_verbose_config(self):
        """Log verbose configuration information."""
        if not self.config.verbose:
            return
        logger.info(f"Project root: {self.config.project_root}")
        logger.info(f"Log directory: {self.config.log_dir}")
        self._log_service_config()
    
    def _log_service_config(self):
        """Log service configuration details."""
        logger.info("Service configuration loaded:")
        self._log_redis_config()
        self._log_clickhouse_config()
        self._log_postgres_config()
        self._log_llm_config()
    
    def _log_redis_config(self):
        """Log Redis configuration."""
        logger.info(f"  Redis: {self.services_config.redis.mode.value}")
    
    def _log_clickhouse_config(self):
        """Log ClickHouse configuration."""
        logger.info(f"  ClickHouse: {self.services_config.clickhouse.mode.value}")
    
    def _log_postgres_config(self):
        """Log PostgreSQL configuration."""
        logger.info(f"  PostgreSQL: {self.services_config.postgres.mode.value}")
    
    def _log_llm_config(self):
        """Log LLM configuration."""
        logger.info(f"  LLM: {self.services_config.llm.mode.value}")
    
    def show_configuration(self):
        """Show configuration summary."""
        self._print("📝", "CONFIG", "Configuration:")
        self._print_config_options()
    
    def _print_config_options(self):
        """Print configuration options."""
        self._print_port_and_reload_configs()
        self._print_feature_configs()
        print()
    
    def _print_port_and_reload_configs(self):
        """Print port and reload configuration options."""
        self._print_dynamic_ports_config()
        self._print_backend_reload_config()
        self._print_frontend_reload_config()
        self._print_logging_config()
    
    def _print_dynamic_ports_config(self):
        """Print dynamic ports configuration."""
        print(f"  • Dynamic ports: {'YES' if self.config.dynamic_ports else 'NO'}")
    
    def _print_backend_reload_config(self):
        """Print backend reload configuration."""
        reload_text = 'YES (uvicorn native)' if self.config.backend_reload else 'NO'
        print(f"  • Backend hot reload: {reload_text}")
    
    def _print_frontend_reload_config(self):
        """Print frontend reload configuration."""
        print(f"  • Frontend hot reload: YES (Next.js native)")
    
    def _print_logging_config(self):
        """Print logging configuration."""
        print(f"  • Real-time logging: YES")
    
    def _print_feature_configs(self):
        """Print feature configuration options."""
        self._print_turbopack_config()
        self._print_secrets_config()
        self._print_verbose_config()
    
    def _print_turbopack_config(self):
        """Print Turbopack configuration."""
        print(f"  • Turbopack: {'YES' if self.config.use_turbopack else 'NO'}")
    
    def _print_secrets_config(self):
        """Print secrets configuration."""
        print(f"  • Secret loading: {'YES' if self.config.load_secrets else 'NO'}")
    
    def _print_verbose_config(self):
        """Print verbose configuration."""
        print(f"  • Verbose output: {'YES' if self.config.verbose else 'NO'}")
    
    def show_env_var_debug_info(self):
        """Show debug information about environment variables."""
        print("\n" + "=" * 60)
        print("🔍 ENVIRONMENT VARIABLE DEBUG INFO")
        print("=" * 60)
        self._show_env_files_status()
        self._show_key_env_vars()
        print("=" * 60)
    
    def _show_env_files_status(self):
        """Show environment files status."""
        env_files = self._get_env_files_list()
        print("\n📁 Environment Files Status:")
        for filename, description in env_files:
            self._show_env_file_status(filename, description)
    
    def _get_env_files_list(self) -> list:
        """Get list of environment files."""
        return [
            (".env", "Base configuration"),
            (".env.development", "Development overrides"),
            (".env.development.local", "Terraform-generated"),
        ]
    
    def _show_env_file_status(self, filename: str, description: str):
        """Show individual environment file status."""
        filepath = self.config.project_root / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✅ {filename:25} - {description} ({size} bytes)")
        else:
            print(f"  ❌ {filename:25} - {description} (not found)")
    
    def _show_key_env_vars(self):
        """Show key environment variables."""
        print("\n🔑 Key Environment Variables (current state):")
        important_vars = self._get_important_env_vars()
        for var in important_vars:
            self._show_env_var_status(var)
    
    def _get_important_env_vars(self) -> list:
        """Get list of important environment variables."""
        return [
            "GOOGLE_CLIENT_ID", "GEMINI_API_KEY", "CLICKHOUSE_HOST",
            "DATABASE_URL", "REDIS_HOST", "JWT_SECRET_KEY", "ENVIRONMENT"
        ]
    
    def _show_env_var_status(self, var: str):
        """Show individual environment variable status."""
        value = os.environ.get(var)
        if value:
            masked = self._mask_env_var_value(value)
            print(f"  {var:30} = {masked}")
        else:
            print(f"  {var:30} = <not set>")
    
    def _mask_env_var_value(self, value: str) -> str:
        """Mask environment variable value."""
        if len(value) > 10:
            return value[:3] + "***" + value[-3:]
        return "***"