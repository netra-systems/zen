"""
Google Secret Manager integration for fallback secret loading.

Handles Google Cloud Secret Manager operations with timeout and error handling.
"""

import logging
import socket
from typing import Dict, Optional, Set, Tuple

# Import shared secret mappings
from shared.secret_mappings import get_secret_mappings

logger = logging.getLogger(__name__)


class GoogleSecretManager:
    """
    Google Secret Manager client with timeout and error handling.
    
    Provides fallback secret loading from Google Cloud Secret Manager
    with proper timeout management and error recovery.
    """
    
    def __init__(self, project_id: str, verbose: bool = False, environment: str = "staging"):
        """Initialize Google Secret Manager client."""
        self.project_id = project_id
        self.verbose = verbose
        self.environment = environment
        self.client = None
    
    def load_missing_secrets(self, missing_keys: Set[str]) -> Dict[str, Tuple[str, str]]:
        """Load missing secrets from Google Secret Manager."""
        logger.info(f"\n[GSM] Loading {len(missing_keys)} missing secrets...")
        logger.info(f"  Project ID: {self.project_id}")
        
        client = self._create_client()
        if not client:
            logger.warning("  [WARN] Cannot connect to Google Secret Manager")
            return {}
        
        return self._fetch_secrets(client, missing_keys)
    
    def _create_client(self):
        """Create Google Secret Manager client with timeout."""
        try:
            from google.cloud import secretmanager
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(10)
            try:
                client = secretmanager.SecretManagerServiceClient()
                logger.info("  [OK] Connected to Secret Manager")
                return client
            finally:
                socket.setdefaulttimeout(original_timeout)
        except ImportError:
            logger.error("  [ERROR] Google Cloud SDK not installed")
            return None
        except Exception as e:
            logger.error(f"  [ERROR] Failed to connect: {e}")
            return None
    
    def _fetch_secrets(self, client, missing_keys: Set[str]) -> Dict[str, Tuple[str, str]]:
        """Fetch secrets from Google Secret Manager using environment-specific mappings."""
        secret_mappings = self._get_secret_mappings()
        loaded = {}
        
        # Log which environment mappings we're using
        logger.info(f"  Using {self.environment} environment secret mappings ({len(secret_mappings)} total)")
        
        for env_var in missing_keys:
            secret_name = self._find_secret_name(secret_mappings, env_var)
            if secret_name:
                self._fetch_single_secret(client, secret_name, env_var, loaded)
            else:
                logger.debug(f"  No Google secret mapping for {env_var} in {self.environment} environment")
        
        logger.info(f"  [OK] Loaded {len(loaded)} secrets from Google Secret Manager")
        return loaded
    
    def _find_secret_name(self, secret_mappings: Dict[str, str], env_var: str) -> Optional[str]:
        """Find Google secret name for environment variable."""
        for secret_name, mapped_env_var in secret_mappings.items():
            if mapped_env_var == env_var:
                return secret_name
        return None
    
    def _fetch_single_secret(self, client, secret_name: str, env_var: str, loaded: Dict):
        """Fetch single secret from Google Secret Manager."""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(name=name)
            value = response.payload.data.decode("UTF-8")
            loaded[env_var] = (value, "google_secret")
            if self.verbose:
                masked = self._mask_value(value)
                logger.debug(f"    Loaded {env_var}: {masked}")
        except Exception as e:
            if self.verbose:
                logger.debug(f"    Failed {env_var}: {str(e)[:50]}")
    
    def _get_secret_mappings(self) -> Dict[str, str]:
        """Get mapping of Google secret names to environment variables using shared mappings.
        
        Note: These mappings are for Google Secret Manager (GCP) which uses
        dash-separated names. Local .env files use underscore-separated names.
        """
        # Use shared secret mappings for consistency across services
        # Default to staging since dev_launcher is typically used for staging-like environments
        return get_secret_mappings("staging")
    
    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value for display."""
        if len(value) > 8:
            return value[:3] + "***" + value[-3:]
        elif len(value) > 3:
            return value[:3] + "***"
        else:
            return "***"