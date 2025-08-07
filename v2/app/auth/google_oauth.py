
from authlib.integrations.starlette_client import OAuth
from fastapi import Request, Depends
from app.config import settings
from app.db.postgres import get_async_db
from app.services.security_service import SecurityService
from app.db.models_postgres import User
from app import schemas

oauth = OAuth()

oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=settings.google_cloud.client_id,
    client_secret=settings.google_cloud.client_secret,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

async def auth(request: Request, security_service: SecurityService = Depends()):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    
    if user_info:
        email = user_info.get('email')
        async with get_async_db() as session:
            user = await security_service.get_user(session, email)
            if not user:
                user = User(email=email, name=user_info.get('name'))
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            access_token = security_service.create_access_token(user.email)
            response = RedirectResponse(url="/")
            response.set_cookie(key="access_token", value=access_token, httponly=True)
            return response

    raise HTTPException(status_code=400, detail="Authentication failed")

async def logout(request: Request):
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response
