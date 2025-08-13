"""OAuth proxy service for handling dynamic PR staging environments."""

import base64
import json
import time
from typing import Dict, Optional, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
import httpx

from app.logging_config import central_logger as logger
from app.redis_manager import RedisManager

redis_service = RedisManager()
from app.auth.environment_config import auth_env_config


router = APIRouter(prefix="/auth/proxy", tags=["auth-proxy"])


class OAuthProxyService:
    """Handles OAuth flow for dynamic PR environments."""
    
    def __init__(self):
        self.redis = redis_service
        self.token_ttl = 300  # 5 minutes
        
    async def encode_state(self, pr_number: str, return_url: str, csrf_token: str) -> str:
        """Encode state parameter for OAuth flow."""
        state_data = {
            "pr_number": pr_number,
            "return_url": return_url,
            "csrf_token": csrf_token,
            "timestamp": int(time.time()),
        }
        
        state_json = json.dumps(state_data)
        state_bytes = state_json.encode('utf-8')
        state_b64 = base64.urlsafe_b64encode(state_bytes).decode('utf-8')
        
        # Store CSRF token in Redis for validation
        csrf_key = f"oauth_csrf:{pr_number}:{csrf_token}"
        await self.redis.setex(csrf_key, self.token_ttl, "valid")
        
        return state_b64
    
    async def decode_state(self, state: str) -> Dict[str, Any]:
        """Decode and validate state parameter."""
        try:
            state_bytes = base64.urlsafe_b64decode(state.encode('utf-8'))
            state_json = state_bytes.decode('utf-8')
            state_data = json.loads(state_json)
            
            # Validate timestamp
            current_time = int(time.time())
            if current_time - state_data.get("timestamp", 0) > self.token_ttl:
                raise ValueError("State parameter expired")
            
            # Validate CSRF token
            pr_number = state_data.get("pr_number")
            csrf_token = state_data.get("csrf_token")
            csrf_key = f"oauth_csrf:{pr_number}:{csrf_token}"
            
            csrf_valid = await self.redis.get(csrf_key)
            if not csrf_valid:
                raise ValueError("Invalid CSRF token")
            
            # Delete CSRF token after use
            await self.redis.delete(csrf_key)
            
            return state_data
            
        except Exception as e:
            logger.error(f"Failed to decode state: {e}")
            raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    async def store_token(self, pr_number: str, token_data: Dict[str, Any]) -> str:
        """Store OAuth token temporarily and return transfer key."""
        transfer_key = f"oauth_token:{pr_number}:{int(time.time())}"
        await self.redis.setex(transfer_key, self.token_ttl, json.dumps(token_data))
        return transfer_key
    
    async def retrieve_token(self, transfer_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve and delete OAuth token."""
        token_json = await self.redis.get(transfer_key)
        if token_json:
            await self.redis.delete(transfer_key)
            return json.loads(token_json)
        return None
    
    async def exchange_code_for_token(self, code: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": "https://auth.staging.netrasystems.ai/callback",
            "grant_type": "authorization_code",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google."""
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
            return response.json()


# Initialize service
oauth_proxy = OAuthProxyService()


@router.get("/initiate")
async def initiate_oauth(request: Request, pr_number: str, return_url: str):
    """Initiate OAuth flow for a PR environment."""
    
    # Generate CSRF token
    import secrets
    csrf_token = secrets.token_urlsafe(32)
    
    # Encode state
    state = await oauth_proxy.encode_state(pr_number, return_url, csrf_token)
    
    # Get OAuth config
    oauth_config = auth_env_config.get_oauth_config()
    
    # Build Google OAuth URL
    params = {
        "client_id": oauth_config.client_id,
        "redirect_uri": "https://auth.staging.netrasystems.ai/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    logger.info(f"Initiating OAuth for PR #{pr_number}")
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def oauth_callback(request: Request, code: str, state: str):
    """Handle OAuth callback from Google."""
    
    # Decode and validate state
    state_data = await oauth_proxy.decode_state(state)
    pr_number = state_data["pr_number"]
    return_url = state_data["return_url"]
    
    logger.info(f"OAuth callback for PR #{pr_number}")
    
    # Get OAuth config
    oauth_config = auth_env_config.get_oauth_config()
    
    # Exchange code for token
    token_data = await oauth_proxy.exchange_code_for_token(
        code,
        oauth_config.client_id,
        oauth_config.client_secret
    )
    
    # Get user info
    user_info = await oauth_proxy.get_user_info(token_data["access_token"])
    
    # Store token temporarily
    transfer_key = await oauth_proxy.store_token(pr_number, {
        "access_token": token_data["access_token"],
        "user_info": user_info,
    })
    
    # Redirect back to PR environment with transfer key
    redirect_url = f"{return_url}/auth/complete?key={transfer_key}"
    
    response = RedirectResponse(url=redirect_url)
    
    # Also set a secure cookie for the subdomain
    response.set_cookie(
        key="oauth_transfer",
        value=transfer_key,
        max_age=300,
        secure=True,
        httponly=True,
        samesite="none",
        domain=".staging.netrasystems.ai"
    )
    
    return response


@router.post("/complete")
async def complete_oauth(request: Request, transfer_key: str):
    """Complete OAuth flow by retrieving token."""
    
    # Retrieve token
    token_data = await oauth_proxy.retrieve_token(transfer_key)
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired transfer key")
    
    return {
        "success": True,
        "access_token": token_data["access_token"],
        "user_info": token_data["user_info"],
    }


@router.get("/status")
async def proxy_status():
    """Check OAuth proxy status."""
    return {
        "status": "healthy",
        "environment": auth_env_config.environment.value,
        "is_pr_environment": auth_env_config.is_pr_environment,
        "pr_number": auth_env_config.pr_number,
    }