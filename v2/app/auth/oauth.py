from authlib.integrations.starlette_client import OAuth
from app.config import settings

oauth = OAuth()

google_redirect_uri = settings.api_base_url + '/api/v3/auth/callback'

oauth.register(
    name='google',
    client_id=settings.google_cloud.client_id,
    client_secret=settings.google_cloud.client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'redirect_url': google_redirect_uri
    }
)
