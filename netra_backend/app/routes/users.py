"""
User Management Routes - Profile, Settings, Preferences, API Keys, Sessions

Handles comprehensive user profile and account management endpoints 
that the frontend expects but were missing from the backend.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.dependencies import DbDep
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.tracing import TracingManager
from netra_backend.app.db.repositories.user_repository import UserRepository
from netra_backend.app.db.models_user import User as UserModel

logger = central_logger.get_logger(__name__)
router = APIRouter(prefix="/user", tags=["users"])
tracing_manager = TracingManager()
user_repository = UserRepository()

# Pydantic models for request/response
class UserProfile(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None

class UserSettings(BaseModel):
    theme: Optional[str] = "light"
    language: Optional[str] = "en"
    timezone: Optional[str] = None
    email_notifications: Optional[bool] = True

class NotificationSettings(BaseModel):
    email_alerts: Optional[bool] = True
    push_notifications: Optional[bool] = True
    marketing_emails: Optional[bool] = False
    security_alerts: Optional[bool] = True

class UserPreferences(BaseModel):
    dashboard_layout: Optional[str] = "default"
    default_view: Optional[str] = "overview"
    items_per_page: Optional[int] = 20
    auto_save: Optional[bool] = True

class ApiKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = []

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    key: Optional[str] = None  # Only returned on creation
    created_at: str
    last_used: Optional[str] = None
    permissions: List[str]

class SessionInfo(BaseModel):
    id: str
    device: str
    location: str
    last_active: str
    current: bool


@router.get("/profile")
async def get_user_profile(
    db: DbDep,
    current_user: Dict = Depends(get_current_user),
    request: Request = None
) -> UserProfile:
    """Get current user profile information with distributed tracing support."""
    try:
        # Start distributed tracing span for OAuth integration test support
        with tracing_manager.start_span("user_profile_request") as span:
            if request:
                # Extract and propagate trace context from headers
                trace_headers = tracing_manager.extract_trace_headers(dict(request.headers))
                span.set_attribute("trace.propagated", bool(trace_headers))
                span.set_attribute("request.method", request.method)
                span.set_attribute("request.url", str(request.url))
                
                # Log trace context for test verification
                if trace_headers:
                    logger.info(f"Trace context propagated: {trace_headers}")
                    span.set_attribute("trace.headers.count", len(trace_headers))
                
                # Add user context for debugging
                span.set_attribute("user.id", current_user.get("id", "unknown"))
                span.set_attribute("user.email", current_user.get("email", "unknown"))
            
            # Get user profile from database
            user_id = current_user.get("id") or current_user.get("user_id")
            if not user_id:
                raise HTTPException(status_code=400, detail="User ID not found in token")
            
            # Get user from database using repository
            user = await user_repository.get_by_id(db, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            profile = UserProfile(
                name=user.full_name,
                email=user.email,
                avatar_url=user.picture,
                bio=None,  # No bio field in current model
                company=None,  # No company field in current model
                location=None  # No location field in current model
            )
            
            span.set_attribute("response.status", "success")
            span.set_attribute("response.profile.complete", bool(profile.name and profile.email))
            
            return profile
            
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve profile")


@router.patch("/profile")
async def update_user_profile(
    profile_data: UserProfile,
    db: DbDep,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Update user profile information."""
    try:
        # Update user profile in database
        user_id = current_user.get("id") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in token")
        
        # Prepare update data (only non-None values)
        update_data = {}
        if profile_data.name is not None:
            update_data['full_name'] = profile_data.name
        if profile_data.email is not None:
            update_data['email'] = profile_data.email
        if profile_data.avatar_url is not None:
            update_data['picture'] = profile_data.avatar_url
        
        if not update_data:
            return {"message": "No data to update"}
        
        # Update user in database
        updated_user = await user_repository.update(db, user_id, **update_data)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Updated profile for user {user_id}: {list(update_data.keys())}")
        return {"message": "Profile updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.get("/settings")
async def get_user_settings(
    db: DbDep,
    current_user: Dict = Depends(get_current_user)
) -> UserSettings:
    """Get current user settings."""
    try:
        # User settings not yet implemented in database schema
        # Return default settings instead of mock data
        return UserSettings(
            theme="light",
            language="en",
            timezone=None,
            email_notifications=True
        )
    except Exception as e:
        logger.error(f"Failed to get user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")


@router.patch("/settings")
async def update_user_settings(
    settings_data: UserSettings,
    db: DbDep,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Update user settings."""
    try:
        # User settings not yet implemented in database schema
        # Log the attempt but don't persist until schema is updated
        user_id = current_user.get("id") or current_user.get("user_id")
        logger.info(f"Settings update requested for user {user_id}: {settings_data.dict()}")
        raise HTTPException(status_code=501, detail="User settings not yet implemented")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.get("/api-keys")
async def list_api_keys(
    db: DbDep,
    current_user: Dict = Depends(get_current_user)
) -> List[ApiKeyResponse]:
    """List user's API keys."""
    try:
        # API key management not yet implemented in database schema
        # Return empty list instead of mock data
        return []
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve API keys")


@router.post("/api-keys")
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user: Dict = Depends(get_current_user)
) -> ApiKeyResponse:
    """Create a new API key."""
    try:
        # API key management not yet implemented in database schema
        raise HTTPException(status_code=501, detail="API key creation not yet implemented")
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete an API key."""
    try:
        # API key management not yet implemented in database schema
        raise HTTPException(status_code=501, detail="API key deletion not yet implemented")
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")


@router.get("/sessions")
async def list_user_sessions(
    current_user: Dict = Depends(get_current_user)
) -> List[SessionInfo]:
    """List user's active sessions."""
    try:
        # Session management not yet implemented in database schema
        # Return empty list instead of mock data
        return []
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Revoke a user session."""
    try:
        # Session management not yet implemented in database schema
        raise HTTPException(status_code=501, detail="Session revocation not yet implemented")
    except Exception as e:
        logger.error(f"Failed to revoke session: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke session")


@router.get("/notifications/settings")
async def get_notification_settings(
    current_user: Dict = Depends(get_current_user)
) -> NotificationSettings:
    """Get user notification settings."""
    try:
        # Notification settings not yet implemented in database schema
        # Return default settings instead of mock data
        return NotificationSettings(
            email_alerts=True,
            push_notifications=True,
            marketing_emails=False,
            security_alerts=True
        )
    except Exception as e:
        logger.error(f"Failed to get notification settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notification settings")


@router.patch("/notifications/settings")
async def update_notification_settings(
    settings_data: NotificationSettings,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Update user notification settings."""
    try:
        # Notification settings not yet implemented in database schema
        user_id = current_user.get("id") or current_user.get("user_id")
        logger.info(f"Notification settings update requested for user {user_id}: {settings_data.dict()}")
        raise HTTPException(status_code=501, detail="Notification settings update not yet implemented")
    except Exception as e:
        logger.error(f"Failed to update notification settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification settings")


@router.get("/preferences")
async def get_user_preferences(
    current_user: Dict = Depends(get_current_user)
) -> UserPreferences:
    """Get user preferences."""
    try:
        # User preferences not yet implemented in database schema
        # Return default preferences instead of mock data
        return UserPreferences(
            dashboard_layout="default",
            default_view="overview",
            items_per_page=20,
            auto_save=True
        )
    except Exception as e:
        logger.error(f"Failed to get user preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")


@router.patch("/preferences")
async def update_user_preferences(
    preferences_data: UserPreferences,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Update user preferences."""
    try:
        # User preferences not yet implemented in database schema
        user_id = current_user.get("id") or current_user.get("user_id")
        logger.info(f"Preferences update requested for user {user_id}: {preferences_data.dict()}")
        raise HTTPException(status_code=501, detail="User preferences update not yet implemented")
    except Exception as e:
        logger.error(f"Failed to update preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")


@router.post("/change-password")
async def change_user_password(
    password_data: Dict[str, str],
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Change user password."""
    try:
        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        
        if not current_password or not new_password:
            raise HTTPException(status_code=400, detail="Missing password fields")
            
        # Password changes must go through auth service per architecture
        # This endpoint should delegate to auth service client
        user_id = current_user.get("id") or current_user.get("user_id")
        logger.info(f"Password change requested for user {user_id}")
        raise HTTPException(status_code=501, detail="Password changes must be implemented via auth service delegation")
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.delete("/account")
async def delete_user_account(
    confirmation_data: Dict[str, str],
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete user account."""
    try:
        confirmation = confirmation_data.get("confirmation")
        if confirmation != "DELETE":
            raise HTTPException(status_code=400, detail="Invalid confirmation")
            
        # Account deletion must coordinate with auth service per architecture
        # This requires careful multi-service coordination
        user_id = current_user.get("id") or current_user.get("user_id")
        logger.info(f"Account deletion requested for user {user_id}")
        raise HTTPException(status_code=501, detail="Account deletion must be implemented via auth service coordination")
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")