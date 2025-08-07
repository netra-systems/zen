from fastapi import Depends, HTTPException, status, Request
from app.db import models_postgres
from app.config import settings
from app.services.security_service import SecurityService
from app import schemas
import uuid
from datetime import datetime

class ActiveUser:
    def __init__(
        self,
        db_session_factory: callable,
        security_service: SecurityService,
    ):
        self.db_session_factory = db_session_factory
        self.security_service = security_service

    async def __call__(self, request: Request) -> schemas.User:
        if settings.environment == "development":
            return schemas.User(
                id=str(uuid.uuid4()), 
                email=settings.dev_user_email, 
                created_at=datetime.utcnow()
            )

        user_info = request.session.get('user')
        if not user_info:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        email = user_info.get('email')
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        async with self.db_session_factory() as session:
            user = await self.security_service.get_user(session, email)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
            return schemas.User.model_validate(user)

def get_active_user_dependency(
    db_session_factory: callable = Depends(lambda: lambda: None),
    security_service: SecurityService = Depends(lambda: None),
) -> ActiveUser:
    return ActiveUser(db_session_factory, security_service)
