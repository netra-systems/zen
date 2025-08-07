from fastapi import Depends, HTTPException, status, Request
from app.config import settings
from app.services.security_service import SecurityService
from app import schemas
import uuid
from datetime import datetime
from app.db.postgres import AsyncSession
from app.dependencies import get_db_session, get_security_service
from typing import Annotated

async def get_active_user(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    security_service: Annotated[SecurityService, Depends(get_security_service)],
) -> schemas.User:
    if settings.environment == "development" and 'user' not in request.session:
        return schemas.User(
            id=str(uuid.uuid4()),
            email=settings.dev_user_email,
            created_at=datetime.utcnow(),
            full_name="Dev User",
            picture=None
        )

    user_info = request.session.get('user')
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    email = user_info.get('email')
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = await security_service.get_user(db_session, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    return schemas.User.model_validate(user)

CurrentUser = Annotated[schemas.User, Depends(get_active_user)]