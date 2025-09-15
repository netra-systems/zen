"""
NetraOptimizer Cloud Configuration
Integrates with Netra's CloudSQL and Secret Manager infrastructure.

This module uses the existing shared database configuration patterns
to connect NetraOptimizer to the same CloudSQL instance used by the main application.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import quote

# Add project root to path to access shared modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import shared database configuration utilities
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class CloudSQLConfig:
    """
    Cloud SQL configuration for NetraOptimizer.
    Uses the same database configuration patterns as the main Netra application.
    """

    def __init__(self, env_manager: Optional[IsolatedEnvironment] = None):
        """
        Initialize CloudSQL configuration.

        Args:
            env_manager: Optional isolated environment manager
        """
        self.env_manager = env_manager or IsolatedEnvironment()
        self.environment = self.env_manager.get("ENVIRONMENT", "development").lower()
        self._db_url_builder = None

    @property
    def db_url_builder(self) -> DatabaseURLBuilder:
        """Get or create the database URL builder."""
        if self._db_url_builder is None:
            # Get all environment variables for the builder
            env_vars = self.env_manager.get_all()
            self._db_url_builder = DatabaseURLBuilder(env_vars)
        return self._db_url_builder

    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration for NetraOptimizer.

        Returns:
            Dictionary with database configuration
        """
        # Try to load from Secret Manager in staging/production
        if self.environment in ["staging", "production"]:
            secrets = self._load_staging_secrets()
            if secrets:
                config = secrets
            else:
                # Fallback to environment variables
                config = {
                    "host": self.env_manager.get("POSTGRES_HOST"),
                    "port": self.env_manager.get("POSTGRES_PORT", "5432"),
                    "user": self.env_manager.get("POSTGRES_USER"),
                    "password": self.env_manager.get("POSTGRES_PASSWORD"),
                    "database": "netra_optimizer",  # NetraOptimizer specific database
                    "environment": self.environment,
                }
        else:
            # Development/local configuration
            config = {
                "host": self.env_manager.get("POSTGRES_HOST") or self.env_manager.get("NETRA_DB_HOST", "localhost"),
                "port": self.env_manager.get("POSTGRES_PORT") or self.env_manager.get("NETRA_DB_PORT", "5432"),
                "user": self.env_manager.get("POSTGRES_USER") or self.env_manager.get("NETRA_DB_USER", "postgres"),
                "password": self.env_manager.get("POSTGRES_PASSWORD") or self.env_manager.get("NETRA_DB_PASSWORD", ""),
                "database": "netra_optimizer",  # NetraOptimizer specific database
                "environment": self.environment,
            }

        # Check if this is a CloudSQL configuration
        if config["host"] and "/cloudsql/" in config["host"]:
            config["is_cloud_sql"] = True
            config["socket_path"] = config["host"]
            logger.info(f"CloudSQL configuration detected: {config['socket_path']}")
        else:
            config["is_cloud_sql"] = False

        return config

    def get_database_url(self, sync: bool = False) -> str:
        """
        Get the database URL for NetraOptimizer.

        Args:
            sync: If True, return synchronous URL (for setup/migrations)

        Returns:
            Database URL string formatted for the appropriate driver
        """
        # Get base configuration
        config = self.get_database_config()

        # Build URL based on environment and connection type
        if config["is_cloud_sql"]:
            # CloudSQL Unix socket connection
            user = quote(config["user"], safe='') if config["user"] else ""
            password_part = f":{quote(config['password'], safe='')}" if config["password"] else ""

            if sync:
                # Synchronous URL for migrations/setup
                url = (
                    f"postgresql://"
                    f"{user}{password_part}"
                    f"@/{config['database']}"
                    f"?host={config['socket_path']}"
                )
            else:
                # Async URL for asyncpg (without SQLAlchemy prefix)
                url = (
                    f"postgresql://"
                    f"{user}{password_part}"
                    f"@/{config['database']}"
                    f"?host={config['socket_path']}"
                )
        else:
            # TCP connection (development/local)
            user = quote(config["user"] or "postgres", safe='')
            password_part = f":{quote(config['password'], safe='')}" if config["password"] else ""
            host = config["host"] or "localhost"
            port = config["port"]

            if sync:
                # Synchronous URL
                url = (
                    f"postgresql://"
                    f"{user}{password_part}"
                    f"@{host}:{port}"
                    f"/{config['database']}"
                )
            else:
                # Async URL for asyncpg (without SQLAlchemy prefix)
                url = (
                    f"postgresql://"
                    f"{user}{password_part}"
                    f"@{host}:{port}"
                    f"/{config['database']}"
                )

            # Add SSL for staging/production TCP connections
            if self.environment in ["staging", "production"] and not config["is_cloud_sql"]:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}sslmode=require"

        # Mask URL for logging
        masked_url = DatabaseURLBuilder.mask_url_for_logging(url)
        logger.info(f"Database URL configured for {self.environment}: {masked_url}")

        return url

    def get_secret_manager_config(self) -> Optional[Dict[str, Any]]:
        """
        Get Google Secret Manager configuration if available.

        Returns:
            Dictionary with Secret Manager configuration or None
        """
        project_id = self.env_manager.get("GCP_PROJECT_ID")
        if not project_id:
            logger.debug("GCP_PROJECT_ID not set, Secret Manager not available")
            return None

        return {
            "project_id": project_id,
            "enabled": self.environment in ["staging", "production"],
        }

    def load_secret(self, secret_name: str) -> Optional[str]:
        """
        Load a secret from Google Secret Manager.

        Args:
            secret_name: Name of the secret to load

        Returns:
            Secret value or None if not available
        """
        config = self.get_secret_manager_config()
        if not config or not config["enabled"]:
            return None

        try:
            from google.cloud import secretmanager

            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{config['project_id']}/secrets/{secret_name}/versions/latest"

            response = client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")

            logger.info(f"Successfully loaded secret: {secret_name}")
            return secret_value

        except ImportError:
            logger.debug("Google Cloud Secret Manager library not installed")
            return None
        except Exception as e:
            logger.error(f"Error loading secret {secret_name}: {e}")
            return None

    def _load_staging_secrets(self) -> Optional[Dict[str, Any]]:
        """
        Load database configuration from Google Secret Manager for staging/production.

        Returns:
            Dictionary with database configuration or None
        """
        try:
            # Map of config keys to secret names
            secret_mappings = {
                "host": "postgres-host-staging",
                "port": "postgres-port-staging",
                "user": "postgres-user-staging",
                "password": "postgres-password-staging",
                "database": "postgres-db-staging",
            }

            config = {}
            for key, secret_name in secret_mappings.items():
                value = self.load_secret(secret_name)
                if value:
                    config[key] = value
                else:
                    logger.warning(f"Could not load secret {secret_name}")
                    return None  # All secrets required for staging

            # Override database name for NetraOptimizer
            config["database"] = "netra_optimizer"
            config["environment"] = self.environment

            logger.info("Successfully loaded database configuration from Secret Manager")
            return config

        except Exception as e:
            logger.error(f"Error loading staging secrets: {e}")
            return None

    def validate_configuration(self) -> tuple[bool, str]:
        """
        Validate the database configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        config = self.get_database_config()

        # Check required fields
        if not config["user"]:
            return False, "POSTGRES_USER not configured"

        if not config["host"]:
            return False, "POSTGRES_HOST not configured"

        # Validate CloudSQL format if applicable
        if config["is_cloud_sql"]:
            if not config["socket_path"].startswith("/cloudsql/"):
                return False, f"Invalid CloudSQL socket path: {config['socket_path']}"

            # Should be format: /cloudsql/PROJECT:REGION:INSTANCE
            parts = config["socket_path"].replace("/cloudsql/", "").split(":")
            if len(parts) != 3:
                return False, "Invalid CloudSQL format. Expected /cloudsql/PROJECT:REGION:INSTANCE"

        # Check for password in production environments
        if self.environment in ["staging", "production"] and not config["password"]:
            return False, f"POSTGRES_PASSWORD required for {self.environment} environment"

        return True, ""

    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get debug information about the configuration.

        Returns:
            Dictionary with debug information
        """
        config = self.get_database_config()
        secret_config = self.get_secret_manager_config()

        return {
            "environment": self.environment,
            "is_cloud_sql": config["is_cloud_sql"],
            "has_password": bool(config["password"]),
            "database": config["database"],
            "host_type": "CloudSQL" if config["is_cloud_sql"] else "TCP",
            "secret_manager_enabled": secret_config["enabled"] if secret_config else False,
            "gcp_project": secret_config["project_id"] if secret_config else None,
        }


# Module-level instance for convenience
cloud_config = CloudSQLConfig()