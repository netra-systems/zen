"""OAuth proxy service for handling dynamic PR staging environments."""

import base64
import json
import time
from typing import Dict, Optional, Any, Tuple
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
    
    def __init__(self) -> None:
        self.redis = redis_service
        self.token_ttl = 300  # 5 minutes
        
    async def encode_state(self, pr_number: str, return_url: str, csrf_token: str) -> str:
        """Encode state parameter for OAuth flow."""
        state_data = self._build_state_data(pr_number, return_url, csrf_token)
        state_b64 = self._encode_state_data(state_data)
        await self._store_csrf_token(pr_number, csrf_token)
        return state_b64
    
    def _build_state_data(self, pr_number: str, return_url: str, csrf_token: str) -> Dict[str, Any]:
        """Build state data dictionary."""
        return {
            "pr_number": pr_number, "return_url": return_url,
            "csrf_token": csrf_token, "timestamp": int(time.time())
        }
    
    def _encode_state_data(self, state_data: Dict[str, Any]) -> str:
        """Encode state data to base64."""
        state_json = json.dumps(state_data)
        state_bytes = state_json.encode('utf-8')
        return base64.urlsafe_b64encode(state_bytes).decode('utf-8')
    
    async def _store_csrf_token(self, pr_number: str, csrf_token: str) -> None:
        """Store CSRF token in Redis for validation."""
        csrf_key = f"oauth_csrf:{pr_number}:{csrf_token}"
        await self.redis.setex(csrf_key, self.token_ttl, "valid")
    
    async def decode_state(self, state: str) -> Dict[str, Any]:
        """Decode and validate state parameter."""
        try:
            state_data = self._decode_state_data(state)
            self._validate_state_timestamp(state_data)
            await self._validate_and_consume_csrf(state_data)
            return state_data
        except Exception as e:
            logger.error(f"Failed to decode state: {e}")
            raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    def _decode_state_data(self, state: str) -> Dict[str, Any]:
        """Decode state data from base64."""
        state_bytes = base64.urlsafe_b64decode(state.encode('utf-8'))
        state_json = state_bytes.decode('utf-8')
        return json.loads(state_json)
    
    def _validate_state_timestamp(self, state_data: Dict[str, Any]) -> None:
        """Validate state timestamp is not expired."""
        current_time = int(time.time())
        if current_time - state_data.get("timestamp", 0) > self.token_ttl:
            raise ValueError("State parameter expired")
    
    async def _validate_and_consume_csrf(self, state_data: Dict[str, Any]) -> None:
        """Validate and consume CSRF token."""
        pr_number = state_data.get("pr_number")
        csrf_token = state_data.get("csrf_token")
        csrf_key = f"oauth_csrf:{pr_number}:{csrf_token}"
        csrf_valid = await self.redis.get(csrf_key)
        if not csrf_valid:
            raise ValueError("Invalid CSRF token")
        await self.redis.delete(csrf_key)
    
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
        data = self._build_token_exchange_data(code, client_id, client_secret)
        return await self._perform_token_exchange(token_url, data)
    
    def _build_token_exchange_data(self, code: str, client_id: str, client_secret: str) -> Dict[str, str]:
        """Build token exchange request data."""
        return {
            "code": code, "client_id": client_id, "client_secret": client_secret,
            "redirect_uri": "https://auth.staging.netrasystems.ai/callback",
            "grant_type": "authorization_code"
        }
    
    async def _perform_token_exchange(self, token_url: str, data: Dict[str, str]) -> Dict[str, Any]:
        """Perform the actual token exchange request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google."""
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = self._build_auth_headers(access_token)
        return await self._fetch_user_info(user_info_url, headers)
    
    def _build_auth_headers(self, access_token: str) -> Dict[str, str]:
        """Build authorization headers."""
        return {"Authorization": f"Bearer {access_token}"}
    
    async def _fetch_user_info(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Fetch user info from Google API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to get user info")
            return response.json()


# Initialize service
oauth_proxy = OAuthProxyService()


@router.get("/initiate")
async def initiate_oauth(request: Request, pr_number: str, return_url: str):
    """Initiate OAuth flow for a PR environment."""
    csrf_token = _generate_csrf_token()
    state = await oauth_proxy.encode_state(pr_number, return_url, csrf_token)
    oauth_config = auth_env_config.get_oauth_config()
    auth_url = _build_google_auth_url(oauth_config, state)
    logger.info(f"Initiating OAuth for PR #{pr_number}")
    return RedirectResponse(url=auth_url)

def _generate_csrf_token() -> str:
    """Generate secure CSRF token."""
    import secrets
    return secrets.token_urlsafe(32)

def _build_google_auth_url(oauth_config, state: str) -> str:
    """Build Google OAuth authorization URL."""
    params = _build_oauth_params(oauth_config, state)
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

def _build_oauth_params(oauth_config, state: str) -> Dict[str, str]:
    """Build OAuth authorization parameters."""
    return {
        "client_id": oauth_config.client_id,
        "redirect_uri": "https://auth.staging.netrasystems.ai/callback",
        "response_type": "code", "scope": "openid email profile",
        "state": state, "access_type": "online"
    }


@router.get("/callback")
async def oauth_callback(request: Request, code: str, state: str):
    """Handle OAuth callback from Google."""
    state_data = await oauth_proxy.decode_state(state)
    pr_number, return_url = _extract_state_info(state_data)
    logger.info(f"OAuth callback for PR #{pr_number}")
    token_data, user_info = await _exchange_and_get_user_info(code)
    transfer_key = await _store_oauth_results(pr_number, token_data, user_info)
    return _build_callback_response(return_url, transfer_key)

def _extract_state_info(state_data: Dict[str, Any]) -> Tuple[str, str]:
    """Extract PR number and return URL from state data."""
    return state_data["pr_number"], state_data["return_url"]

async def _exchange_and_get_user_info(code: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Exchange code for token and get user info."""
    oauth_config = auth_env_config.get_oauth_config()
    token_data = await oauth_proxy.exchange_code_for_token(
        code, oauth_config.client_id, oauth_config.client_secret
    )
    user_info = await oauth_proxy.get_user_info(token_data["access_token"])
    return token_data, user_info

async def _store_oauth_results(pr_number: str, token_data: Dict[str, Any], user_info: Dict[str, Any]) -> str:
    """Store OAuth results and return transfer key."""
    return await oauth_proxy.store_token(pr_number, {
        "access_token": token_data["access_token"],
        "user_info": user_info
    })

def _build_callback_response(return_url: str, transfer_key: str) -> RedirectResponse:
    """Build OAuth callback response with cookie."""
    redirect_url = f"{return_url}/auth/complete?key={transfer_key}"
    response = RedirectResponse(url=redirect_url)
    _set_transfer_cookie(response, transfer_key)
    return response

def _set_transfer_cookie(response: RedirectResponse, transfer_key: str) -> None:
    """Set secure transfer cookie."""
    response.set_cookie(
        key="oauth_transfer", value=transfer_key, max_age=300,
        secure=True, httponly=True, samesite="none",
        domain=".staging.netrasystems.ai"
    )


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