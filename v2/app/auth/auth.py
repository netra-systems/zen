from authlib.integrations.starlette_client import OAuth
from app.config import settings

class OAuthClient:
    """OAuth client wrapper to properly expose the Google OAuth client"""
    def __init__(self):
        self.oauth = None
        self.google = None
    
    def init_app(self, app):
        """Initialize OAuth with the FastAPI app"""
        # Create OAuth instance
        self.oauth = OAuth()
        
        # Register Google OAuth client
        self.google = self.oauth.register(
            name='google',
            client_id=settings.oauth_config.client_id,
            client_secret=settings.oauth_config.client_secret,
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