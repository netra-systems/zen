"""OAuth utilities for Google OAuth integration.

Handles OAuth URL building, token exchange, and user info retrieval.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Seamless OAuth authentication
3. Value Impact: Enables secure Google OAuth login
4. Revenue Impact: Critical for user onboarding and authentication
"""

import os
import requests
from typing import Dict, Any
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

def build_google_oauth_url(oauth_config: Dict[str, str], state: str) -> str:
    """Build Google OAuth authorization URL."""
    params = {
        "client_id": oauth_config["client_id"],
        "redirect_uri": oauth_config["redirect_uri"],
        "scope": "openid email profile",
        "response_type": "code",
        "state": state,
        "access_type": "offline"
    }
    return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

def exchange_code_for_tokens(code: str, oauth_config: Dict[str, str]) -> Dict[str, Any]:
    """Exchange authorization code for access tokens."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": oauth_config["client_id"],
        "client_secret": oauth_config["client_secret"],
        "redirect_uri": oauth_config["redirect_uri"],
        "grant_type": "authorization_code",
        "code": code
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()

def get_user_info_from_google(access_token: str) -> Dict[str, Any]:
    """Get user information from Google using access token."""
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(userinfo_url, headers=headers)
    response.raise_for_status()
    user_info = response.json()
    
    # Standardize user info format
    return {
        "id": user_info.get("id"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "verified_email": user_info.get("verified_email", False)
    }

def refresh_google_token(refresh_token: str, oauth_config: Dict[str, str]) -> Dict[str, Any]:
    """Refresh Google OAuth token."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": oauth_config["client_id"],
        "client_secret": oauth_config["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()

def revoke_google_token(token: str) -> bool:
    """Revoke Google OAuth token."""
    revoke_url = f"https://oauth2.googleapis.com/revoke?token={token}"
    
    try:
        response = requests.post(revoke_url)
        return response.status_code == 200
    except requests.RequestException:
        logger.warning("Failed to revoke Google token")
        return False