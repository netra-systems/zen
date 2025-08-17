from typing import Any, Optional
from authlib.integrations.starlette_client import OAuth
from app.auth.environment_config import auth_env_config
from app.logging_config import central_logger as logger

class OAuthClient:
    """OAuth client wrapper to properly expose the Google OAuth client"""
    def __init__(self) -> None:
        self.oauth = None
        self.google = None
    
    def _log_oauth_initialization(self, oauth_config) -> None:
        """Log OAuth initialization for debugging."""
        logger.info(f"Initializing OAuth for environment: {auth_env_config.environment.value}")
        logger.info(f"OAuth client ID configured: {bool(oauth_config.client_id)}")
        logger.info(f"OAuth client secret configured: {bool(oauth_config.client_secret)}")
    
    def _register_google_oauth(self, oauth_config) -> None:
        """Register Google OAuth client with environment credentials."""
        self.google = self.oauth.register(
            name='google',
            client_id=oauth_config.client_id,
            client_secret=oauth_config.client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
    
    def init_app(self, app: Any) -> OAuth:
        """Initialize OAuth with the FastAPI app"""
        self.oauth = OAuth()
        oauth_config = auth_env_config.get_oauth_config()
        
        self._log_oauth_initialization(oauth_config)
        self._register_google_oauth(oauth_config)
        
        return self.oauth

# Create a single instance to be used throughout the app
oauth_client = OAuthClient()

# Expose the google client for easy access
google = lambda: oauth_client.google