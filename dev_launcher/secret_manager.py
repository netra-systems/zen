"""
Secret management for development environment.
"""

import os
import json
import socket
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SecretLoader:
    """
    Enhanced secret loader with support for multiple sources.
    
    This class loads secrets from environment files and Google Cloud Secret Manager,
    providing detailed visibility into the loading process.
    """
    
    def __init__(self, 
                 project_id: Optional[str] = None, 
                 verbose: bool = False,
                 project_root: Optional[Path] = None):
        """
        Initialize the secret loader.
        
        Args:
            project_id: Google Cloud project ID
            verbose: Whether to show verbose output
            project_root: Project root directory
        """
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT', "304612253870")
        self.verbose = verbose
        self.project_root = project_root or Path.cwd()
        self.loaded_secrets: Dict[str, str] = {}
        self.failed_secrets: List[Tuple[str, str]] = []
        
    def load_from_env_file(self, env_file: Optional[Path] = None) -> Dict[str, Tuple[str, str]]:
        """
        Load secrets from an environment file.
        
        Args:
            env_file: Path to the .env file
        
        Returns:
            Dictionary mapping environment variable names to (value, source) tuples
        """
        if env_file is None:
            env_file = self.project_root / ".env"
        
        loaded = {}
        
        if env_file.exists():
            logger.info(f"Loading from existing .env file: {env_file}")
            
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        loaded[key] = (value.strip('"\''), "env_file")
                        
                        if self.verbose:
                            # Show masked value for sensitive data
                            masked_value = self._mask_value(value)
                            logger.debug(f"  Loaded {key}: {masked_value} (from .env file)")
        else:
            logger.debug(f"No .env file found at {env_file}")
        
        return loaded
    
    def load_from_google_secrets(self) -> Dict[str, Tuple[str, str]]:
        """
        Load secrets from Google Secret Manager.
        
        Returns:
            Dictionary mapping environment variable names to (value, source) tuples
        """
        logger.info(f"Loading secrets from Google Cloud Secret Manager")
        logger.info(f"  Project ID: {self.project_id}")
        
        try:
            from google.cloud import secretmanager
            
            # Create client with timeout
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(10)
            
            try:
                client = secretmanager.SecretManagerServiceClient()
                logger.info("  Connected to Secret Manager")
            finally:
                socket.setdefaulttimeout(original_timeout)
                
        except ImportError:
            logger.error("  Google Cloud SDK not installed")
            return {}
        except Exception as e:
            logger.error(f"  Failed to connect: {e}")
            return {}
        
        # Define the secrets to fetch
        secret_mappings = self._get_secret_mappings()
        
        loaded = {}
        logger.info(f"  Fetching {len(secret_mappings)} secrets...")
        
        for secret_name, env_var in secret_mappings.items():
            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(name=name)
                value = response.payload.data.decode("UTF-8")
                loaded[env_var] = (value, "google_secret")
                
                # Show success with masked value
                masked_value = self._mask_value(value)
                logger.info(f"  Loaded {env_var}: {masked_value} (from Google Secret: {secret_name})")
                
            except Exception as e:
                self.failed_secrets.append((env_var, str(e)))
                if self.verbose:
                    logger.warning(f"  Failed to load {env_var}: {str(e)[:50]}")
        
        return loaded
    
    def _get_secret_mappings(self) -> Dict[str, str]:
        """Get the mapping of secret names to environment variables."""
        return {
            "gemini-api-key": "GEMINI_API_KEY",
            "google-client-id": "GOOGLE_CLIENT_ID",
            "google-client-secret": "GOOGLE_CLIENT_SECRET",
            "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
            "langfuse-public-key": "LANGFUSE_PUBLIC_KEY",
            "clickhouse-default-password": "CLICKHOUSE_DEFAULT_PASSWORD",
            "clickhouse-development-password": "CLICKHOUSE_DEVELOPMENT_PASSWORD",
            "jwt-secret-key": "JWT_SECRET_KEY",
            "fernet-key": "FERNET_KEY",
            "redis-default": "REDIS_PASSWORD",
            "anthropic-api-key": "ANTHROPIC_API_KEY",
            "openai-api-key": "OPENAI_API_KEY",
        }
    
    def _get_static_config(self) -> Dict[str, Tuple[str, str]]:
        """Get static configuration values."""
        return {
            "CLICKHOUSE_HOST": ("xedvrr4c3r.us-central1.gcp.clickhouse.cloud", "static"),
            "CLICKHOUSE_PORT": ("8443", "static"),
            "CLICKHOUSE_USER": ("default", "static"),
            "CLICKHOUSE_DB": ("default", "static"),
            "ENVIRONMENT": ("development", "static"),
            "REDIS_HOST": ("localhost", "static"),
            "REDIS_PORT": ("6379", "static"),
            "DATABASE_URL": ("postgresql://localhost/netra", "static"),
        }
    
    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value for display."""
        if len(value) > 8:
            return value[:3] + "***" + value[-3:]
        elif len(value) > 3:
            return value[:3] + "***"
        else:
            return "***"
    
    def load_all_secrets(self) -> bool:
        """
        Load secrets from all sources with priority.
        
        Returns:
            True if secrets were loaded successfully
        """
        logger.info("Secret Loading Process Started")
        logger.info("=" * 60)
        
        # First, try to load from existing .env file
        env_secrets = self.load_from_env_file()
        
        # Then try Google Secret Manager
        google_secrets = {}
        if self.project_id:
            google_secrets = self.load_from_google_secrets()
        
        # Merge with Google secrets taking priority
        all_secrets = {**env_secrets, **google_secrets}
        
        # Add static configuration
        static_config = self._get_static_config()
        
        logger.info("Adding static configuration...")
        for key, (value, source) in static_config.items():
            if key not in all_secrets:
                all_secrets[key] = (value, source)
                if self.verbose:
                    logger.debug(f"  Added {key}: {value} (static config)")
        
        # Set environment variables
        logger.info("Setting environment variables...")
        for key, (value, source) in all_secrets.items():
            os.environ[key] = value
            self.loaded_secrets[key] = source
        
        # Summary
        self._print_summary()
        
        # Write updated .env file
        self._write_env_file(all_secrets)
        
        return True
    
    def _print_summary(self):
        """Print a summary of loaded secrets."""
        logger.info("=" * 60)
        logger.info("Secret Loading Summary:")
        
        sources: Dict[str, int] = {}
        for source in self.loaded_secrets.values():
            sources[source] = sources.get(source, 0) + 1
        
        total = len(self.loaded_secrets)
        logger.info(f"  Total secrets loaded: {total}")
        
        for source, count in sources.items():
            logger.info(f"  - From {source}: {count}")
        
        if self.failed_secrets and self.verbose:
            logger.warning(f"  Failed to load {len(self.failed_secrets)} secrets:")
            for secret, error in self.failed_secrets[:3]:
                logger.warning(f"    - {secret}: {error[:50]}")
        
        logger.info("=" * 60)
    
    def _write_env_file(self, secrets: Dict[str, Tuple[str, str]]):
        """
        Write secrets to .env file for persistence.
        
        Args:
            secrets: Dictionary of secrets to write
        """
        env_file = self.project_root / ".env"
        logger.info(f"Writing secrets to {env_file}")
        
        with open(env_file, 'w') as f:
            f.write("# Auto-generated .env file\n")
            f.write(f"# Generated at {datetime.now().isoformat()}\n\n")
            
            # Group by category
            categories = self._get_secret_categories()
            
            for category, keys in categories.items():
                f.write(f"\n# {category}\n")
                for key in keys:
                    if key in secrets:
                        value, _ = secrets[key]
                        f.write(f"{key}={value}\n")
            
            # Write any remaining secrets not in categories
            categorized_keys = set()
            for keys in categories.values():
                categorized_keys.update(keys)
            
            remaining = {k: v for k, v in secrets.items() if k not in categorized_keys}
            if remaining:
                f.write("\n# Other\n")
                for key, (value, _) in remaining.items():
                    f.write(f"{key}={value}\n")
    
    def _get_secret_categories(self) -> Dict[str, List[str]]:
        """Get categorized grouping of secrets."""
        return {
            "Google OAuth": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
            "API Keys": ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "ClickHouse": [
                "CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER",
                "CLICKHOUSE_DEFAULT_PASSWORD", "CLICKHOUSE_DEVELOPMENT_PASSWORD", 
                "CLICKHOUSE_DB"
            ],
            "Database": ["DATABASE_URL"],
            "Redis": ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"],
            "Langfuse": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
            "Security": ["JWT_SECRET_KEY", "FERNET_KEY"],
            "Environment": ["ENVIRONMENT"]
        }


class ServiceDiscovery:
    """
    Service discovery for development environment.
    
    This class manages service information for inter-service communication
    during development.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize service discovery.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = project_root or Path.cwd()
        self.discovery_dir = self.project_root / ".service_discovery"
        self.discovery_dir.mkdir(exist_ok=True)
    
    def write_backend_info(self, port: int):
        """Write backend service information."""
        info = {
            "port": port,
            "api_url": f"http://localhost:{port}",
            "ws_url": f"ws://localhost:{port}/ws",
            "timestamp": datetime.now().isoformat()
        }
        
        info_file = self.discovery_dir / "backend.json"
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        logger.debug(f"Wrote backend service discovery to {info_file}")
    
    def write_frontend_info(self, port: int):
        """Write frontend service information."""
        info = {
            "port": port,
            "url": f"http://localhost:{port}",
            "timestamp": datetime.now().isoformat()
        }
        
        info_file = self.discovery_dir / "frontend.json"
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        logger.debug(f"Wrote frontend service discovery to {info_file}")
    
    def read_backend_info(self) -> Optional[Dict[str, any]]:
        """Read backend service information."""
        info_file = self.discovery_dir / "backend.json"
        
        if info_file.exists():
            with open(info_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def read_frontend_info(self) -> Optional[Dict[str, any]]:
        """Read frontend service information."""
        info_file = self.discovery_dir / "frontend.json"
        
        if info_file.exists():
            with open(info_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def clear_all(self):
        """Clear all service discovery information."""
        for file in self.discovery_dir.glob("*.json"):
            file.unlink()
        
        logger.debug("Cleared all service discovery information")