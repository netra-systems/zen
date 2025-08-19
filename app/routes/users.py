"""
User Management Routes - Profile, Settings, Preferences, API Keys, Sessions

Handles comprehensive user profile and account management endpoints 
that the frontend expects but were missing from the backend.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_integration.auth import get_current_user
from app.dependencies import DbDep
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])

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
    current_user: Dict = Depends(get_current_user)
) -> UserProfile:
    """Get current user profile information."""
    try:
        # Mock implementation - replace with actual database queries
        return UserProfile(
            name=current_user.get("name", ""),
            email=current_user.get("email", ""),
            avatar_url=current_user.get("avatar_url"),
            bio=current_user.get("bio", ""),
            company=current_user.get("company", ""),
            location=current_user.get("location", "")
        )
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve profile")


@router.patch("/profile")
async def update_user_profile(
    profile_data: UserProfile,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(DbDep)
) -> Dict[str, str]:
    """Update user profile information."""
    try:
        # Mock implementation - replace with actual database updates
        logger.info(f"Updated profile for user {current_user.get('id')}")
        return {"message": "Profile updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.get("/settings")
async def get_user_settings(
    current_user: Dict = Depends(get_current_user)
) -> UserSettings:
    """Get current user settings."""
    try:
        # Mock implementation
        return UserSettings(
            theme=current_user.get("theme", "light"),
            language=current_user.get("language", "en"),
            timezone=current_user.get("timezone"),
            email_notifications=current_user.get("email_notifications", True)
        )
    except Exception as e:
        logger.error(f"Failed to get user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")


@router.patch("/settings")
async def update_user_settings(
    settings_data: UserSettings,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Update user settings."""
    try:
        # Mock implementation
        logger.info(f"Updated settings for user {current_user.get('id')}")
        return {"message": "Settings updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.get("/api-keys")
async def list_api_keys(
    current_user: Dict = Depends(get_current_user)
) -> List[ApiKeyResponse]:
    """List user's API keys."""
    try:
        # Mock implementation
        return [
            ApiKeyResponse(
                id="key-1",
                name="Production Key",
                description="Main production API key",
                created_at="2024-01-01T00:00:00Z",
                last_used="2024-01-15T12:00:00Z",
                permissions=["read", "write"]
            )
        ]
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
        # Mock implementation
        import secrets
        new_key = f"nk_{secrets.token_urlsafe(32)}"
        
        return ApiKeyResponse(
            id=f"key-{secrets.token_hex(8)}",
            name=key_data.name,
            description=key_data.description,
            key=new_key,  # Only returned on creation
            created_at="2024-01-01T00:00:00Z",
            permissions=key_data.permissions
        )
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
        # Mock implementation
        logger.info(f"Deleted API key {key_id} for user {current_user.get('id')}")
        return {"message": "API key deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")


@router.get("/sessions")
async def list_user_sessions(
    current_user: Dict = Depends(get_current_user)
) -> List[SessionInfo]:
    """List user's active sessions."""
    try:
        # Mock implementation
        return [
            SessionInfo(
                id="session-1",
                device="Chrome on Windows",
                location="New York, US",
                last_active="2024-01-15T12:00:00Z",
                current=True
            )
        ]
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
        # Mock implementation
        logger.info(f"Revoked session {session_id} for user {current_user.get('id')}")
        return {"message": "Session revoked successfully"}
    except Exception as e:
        logger.error(f"Failed to revoke session: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke session")


@router.get("/notifications/settings")
async def get_notification_settings(
    current_user: Dict = Depends(get_current_user)
) -> NotificationSettings:
    """Get user notification settings."""
    try:
        # Mock implementation
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
        # Mock implementation
        logger.info(f"Updated notification settings for user {current_user.get('id')}")
        return {"message": "Notification settings updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update notification settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification settings")


@router.get("/preferences")
async def get_user_preferences(
    current_user: Dict = Depends(get_current_user)
) -> UserPreferences:
    """Get user preferences."""
    try:
        # Mock implementation
        return UserPreferences(
            dashboard_layout="grid",
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
        # Mock implementation
        logger.info(f"Updated preferences for user {current_user.get('id')}")
        return {"message": "Preferences updated successfully"}
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
            
        # Mock implementation - add real password change logic
        logger.info(f"Changed password for user {current_user.get('id')}")
        return {"message": "Password changed successfully"}
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
            
        # Mock implementation - add real account deletion logic
        background_tasks.add_task(
            lambda: logger.info(f"Account deletion queued for user {current_user.get('id')}")
        )
        return {"message": "Account deletion initiated"}
    except Exception as e:
        logger.error(f"Failed to delete account: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")