from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db_session, get_security_service
from app.services.security_service import SecurityService
from app.db.models_postgres import User
from app.logging_config import central_logger
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

logger = central_logger.get_logger(__name__)

async def get_current_user(
    token: str,
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
) -> Optional[User]:
    if not token:
        logger.error("Token not found")
        return None
    try:
        payload = security_service.decode_access_token(token)
        if payload is None:
            logger.error("Token payload is invalid")
            return None
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("User ID not found in token payload")
            return None
        user = await security_service.get_user_by_id(db_session, user_id)
        if user is None:
            logger.error(f"User with ID {user_id} not found")
            return None
        return user
    except Exception as e:
        logger.error(f"Error decoding token or fetching user: {e}")
        return None

async def get_current_user_ws(
    token: Annotated[str, Query()],
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
) -> Optional[User]:
    return await get_current_user(token, db_session, security_service)

async def get_current_active_user(
    token: str = Depends(oauth2_scheme),
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
) -> Optional[User]:
    user = await get_current_user(token, db_session, security_service)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

ActiveUserDep = Depends(get_current_active_user)
ActiveUserWsDep = Depends(get_current_user_ws)