from authlib.integrations.starlette_client import OAuth
from app.config import settings

google_oauth = OAuth()

google_oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=settings.google_cloud.client_id,
    client_secret=settings.google_cloud.client_secret,
    client_kwargs={
        'scope': 'openid email profile'
    }
)
