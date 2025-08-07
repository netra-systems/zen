from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.config import settings
from app.dependencies import get_db_session, get_security_service
from app.services.security_service import SecurityService
from app.db.models_postgres import User
from app.db.postgres import AsyncSession
from app.logging_config import central_logger

router = APIRouter()
oauth = OAuth()

logger = central_logger.get_logger(__name__)

oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=settings.google_cloud.client_id,
    client_secret=settings.google_cloud.client_secret,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth')
async def auth(request: Request, db_session: AsyncSession = Depends(get_db_session), security_service: SecurityService = Depends(get_security_service)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error(f"Error authorizing access token: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed: could not verify token")

    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="Authentication failed: no user info")

    email = user_info.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="Authentication failed: no email in user info")

    user = await security_service.get_user(db_session, email)
    if not user:
        user = User(email=email, full_name=user_info.get('name'), picture=user_info.get('picture'))
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    request.session['user'] = dict(user_info)
    return RedirectResponse(url=settings.frontend_url)

@router.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url=settings.frontend_url)
