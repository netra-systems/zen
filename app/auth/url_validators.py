"""URL validation utilities for auth service.

Validates return URLs and builds auth service URLs.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Secure URL validation and redirect handling
3. Value Impact: Prevents open redirect vulnerabilities
4. Revenue Impact: Critical for platform security
"""

import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

def validate_and_get_return_url(return_url: Optional[str]) -> str:
    """Validate and get safe return URL."""
    if not return_url:
        return get_default_return_url()
    
    if not is_valid_return_url(return_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid return URL"
        )
    
    return return_url

def is_valid_return_url(url: str) -> bool:
    """Check if return URL is valid and safe."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
            
        # Check against allowed domains
        allowed_domains = get_allowed_domains()
        return any(
            parsed.netloc == domain or parsed.netloc.endswith(f".{domain}")
            for domain in allowed_domains
        )
    except Exception:
        return False

def get_allowed_domains() -> list:
    """Get list of allowed domains for return URLs."""
    domains_str = os.getenv("ALLOWED_RETURN_DOMAINS", "localhost,netrasystems.ai")
    domains = [domain.strip() for domain in domains_str.split(",")]
    
    # Add staging and dev domains
    dev_domains = ["localhost", "127.0.0.1"]
    staging_domains = ["staging.netrasystems.ai", "dev.netrasystems.ai"]
    
    return domains + dev_domains + staging_domains

def get_default_return_url() -> str:
    """Get default return URL."""
    default_url = os.getenv("DEFAULT_RETURN_URL", "http://localhost:3000")
    return default_url

def get_auth_service_url() -> str:
    """Get auth service URL for configuration."""
    # Check for explicit auth service URL
    auth_url = os.getenv("AUTH_SERVICE_URL")
    if auth_url:
        return auth_url
        
    # Check for PR environment
    pr_number = os.getenv("PR_NUMBER")
    if pr_number:
        return f"https://auth-pr-{pr_number}.netrasystems.ai"
        
    # Default to localhost for development
    return "http://localhost:8001"

def build_oauth_redirect_uri(base_url: Optional[str] = None) -> str:
    """Build OAuth redirect URI."""
    if not base_url:
        base_url = get_auth_service_url()
        
    return f"{base_url}/auth/callback"

def validate_return_url_security(url: str) -> Dict[str, Any]:
    """Validate return URL security and return validation result."""
    try:
        parsed = urlparse(url)
        is_valid = is_valid_return_url(url)
        
        return {
            "valid": is_valid,
            "scheme": parsed.scheme,
            "domain": parsed.netloc,
            "path": parsed.path,
            "security_level": "safe" if is_valid else "unsafe"
        }
    except Exception as e:
        logger.warning(f"URL validation error: {e}")
        return {
            "valid": False,
            "error": str(e),
            "security_level": "unsafe"
        }