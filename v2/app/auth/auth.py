
from authlib.integrations.starlette_client import OAuth
from app.config import settings

oauth = OAuth()

google = oauth.register(
    name='google',
    client_id=settings.oauth_config.client_id,
    client_secret=settings.oauth_config.client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)
