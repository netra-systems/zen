"""PR Router for handling Pull Request specific authentication flows.

Handles PR environment routing, validation, and authentication workflows.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Enable secure PR environment authentication
3. Value Impact: Enables testing and staging environment access
4. Revenue Impact: Critical for development workflow and customer demos
"""

import os
import re
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

def extract_pr_number_from_request(request_headers: Dict[str, str]) -> Optional[str]:
    """Extract PR number from request headers or host."""
    # Check for PR number in custom header
    pr_header = request_headers.get("X-PR-Number")
    if pr_header:
        return validate_pr_number_format(pr_header)
        
    # Extract from host header for PR environments
    host = request_headers.get("host", "")
    return extract_pr_from_host(host)

def extract_pr_from_host(host: str) -> Optional[str]:
    """Extract PR number from host string."""
    # Pattern: pr-123.staging.netrasystems.ai or pr-123-api.staging.netrasystems.ai
    pr_pattern = r"pr-(\d+)(?:-api)?\.staging\.netrasystems\.ai"
    match = re.search(pr_pattern, host)
    return match.group(1) if match else None

def validate_pr_number_format(pr_number: str) -> Optional[str]:
    """Validate PR number format."""
    if not pr_number or not pr_number.isdigit():
        return None
    
    pr_int = int(pr_number)
    if pr_int < 1 or pr_int > 99999:  # Reasonable PR number range
        return None
        
    return pr_number

def build_pr_redirect_url(pr_number: str, base_path: str = "/") -> str:
    """Build PR environment redirect URL."""
    pr_domain = f"https://pr-{pr_number}.staging.netrasystems.ai"
    return f"{pr_domain}{base_path}"

def get_pr_auth_config(pr_number: str) -> Dict[str, Any]:
    """Get authentication configuration for PR environment."""
    return {
        "pr_number": pr_number,
        "environment": "pr",
        "auth_domain": f"https://auth-pr-{pr_number}.staging.netrasystems.ai",
        "frontend_domain": f"https://pr-{pr_number}.staging.netrasystems.ai",
        "api_domain": f"https://pr-{pr_number}-api.staging.netrasystems.ai"
    }

def validate_pr_environment_access(pr_number: str, user_permissions: Dict[str, Any]) -> bool:
    """Validate user access to PR environment."""
    # Check if user has PR access permissions
    if not user_permissions.get("pr_access", False):
        return False
        
    # Check if user has access to specific PR
    allowed_prs = user_permissions.get("allowed_prs", [])
    if allowed_prs and pr_number not in allowed_prs:
        return False
        
    return True

def route_pr_authentication(
    pr_number: str, 
    auth_flow: str,
    return_url: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """Route PR authentication flow and return redirect URL and config."""
    pr_config = get_pr_auth_config(pr_number)
    
    if auth_flow == "login":
        redirect_url = f"{pr_config['auth_domain']}/auth/login"
        if return_url:
            redirect_url += f"?return_url={return_url}&pr={pr_number}"
    elif auth_flow == "callback":
        redirect_url = f"{pr_config['frontend_domain']}/auth/callback"
    else:
        redirect_url = pr_config['frontend_domain']
        
    return redirect_url, pr_config

def handle_pr_routing_error(error: Exception, pr_number: str) -> HTTPException:
    """Handle PR routing errors."""
    logger.error(f"PR routing error for PR {pr_number}: {error}")
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid PR environment configuration: {pr_number}"
    )

def get_pr_environment_status(pr_number: str) -> Dict[str, Any]:
    """Get PR environment status and health."""
    pr_config = get_pr_auth_config(pr_number)
    
    return {
        "pr_number": pr_number,
        "status": "active",
        "auth_domain": pr_config["auth_domain"],
        "frontend_domain": pr_config["frontend_domain"],
        "api_domain": pr_config["api_domain"],
        "last_updated": "2025-08-17T18:00:00Z"
    }