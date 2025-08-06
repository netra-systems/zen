
from fastapi import Depends, HTTPException, status, Request
from app.db import models_postgres
from app.config import settings
from app.services.security_service import SecurityService
from sqlalchemy.ext.asyncio import AsyncSession

class ActiveUser:
    def __init__(
        self,
        db_session_factory: callable,
        security_service: SecurityService,
    ):
        self.db_session_factory = db_session_factory
        self.security_service = security_service

    async def __call__(self, request: Request) -> models_postgres.User:
        if settings.environment == "development":
            return models_postgres.User(email=settings.dev_user_email, hashed_password="dev")

        token = request.headers.get("Authorization")
        if token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        email = self.security_service.get_user_email_from_token(token)
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        async with self.db_session_factory() as session:
            user = await self.security_service.get_user(session, email)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
            return user

def get_active_user_dependency(
    db_session_factory: callable = Depends(lambda: lambda: None),
    security_service: SecurityService = Depends(lambda: None),
) -> ActiveUser:
    return ActiveUser(db_session_factory, security_service)
