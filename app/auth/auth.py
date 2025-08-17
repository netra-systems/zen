from typing import Any, Optional
from authlib.integrations.starlette_client import OAuth
from app.auth.environment_config import auth_env_config

class OAuthClient:
    """OAuth client wrapper to properly expose the Google OAuth client"""
    def __init__(self) -> None:
        self.oauth = None
        self.google = None
    
    def init_app(self, app: Any) -> OAuth:
        """Initialize OAuth with the FastAPI app"""
        # Create OAuth instance
        self.oauth = OAuth()
        
        # Get environment-specific OAuth configuration
        oauth_config = auth_env_config.get_oauth_config()
        
        # Register Google OAuth client with environment-specific credentials
        self.google = self.oauth.register(
            name='google',
            client_id=oauth_config.client_id,
            client_secret=oauth_config.client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        
        return self.oauth

# Create a single instance to be used throughout the app
oauth_client = OAuthClient()

# Expose the google client for easy access
google = lambda: oauth_client.google