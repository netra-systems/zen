from authlib.integrations.starlette_client import OAuth
from app.config import settings

oauth = OAuth()

google_redirect_uri = f'{settings.api_base_url}/api/v3/auth/callback'

oauth.register(
    name='google',
    client_id=settings.oauth_config.client_id,
    client_secret=settings.oauth_config.client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'redirect_uri': google_redirect_uri
    }
)
