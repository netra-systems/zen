#!/usr/bin/env python3
"""
Health check script for Auth Service
Used by orchestrators and load balancers to determine service health

Maintains service independence by implementing its own health check logic.
"""
import sys
import os
import urllib.request
import urllib.error
import json
import time
from typing import Tuple
from shared.isolated_environment import get_env


def check_health(port=None) -> bool:
    """Check if the auth service is healthy."""
    if port is None:
        # Environment-specific port defaults (no fallback pattern)
        port_str = get_env().get('PORT')
        if port_str:
            port = int(port_str)
        else:
            # Get environment to determine appropriate port
            environment = get_env().get('ENVIRONMENT', 'development').lower()
            if environment in ['production', 'staging']:
                port = 8080  # Cloud Run standard port
            elif environment == 'development':
                port = 8081  # Development port
            elif environment == 'test':
                port = 8082  # Test port
            else:
                port = 8080  # Default
    
    try:
        url = f"http://localhost:{port}/health"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'auth-health-checker/1.0')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read())
                return data.get('status') == 'healthy'
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"Health check failed: {e}")
        return False
    
    return False


def check_readiness(port=None) -> bool:
    """Check if the auth service is ready to serve requests."""
    if port is None:
        # Environment-specific port defaults (no fallback pattern)
        port_str = get_env().get('PORT')
        if port_str:
            port = int(port_str)
        else:
            # Get environment to determine appropriate port
            environment = get_env().get('ENVIRONMENT', 'development').lower()
            if environment in ['production', 'staging']:
                port = 8080  # Cloud Run standard port
            elif environment == 'development':
                port = 8081  # Development port
            elif environment == 'test':
                port = 8082  # Test port
            else:
                port = 8080  # Default
    
    try:
        url = f"http://localhost:{port}/readiness"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'auth-health-checker/1.0')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read())
                return data.get('ready', False)
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"Readiness check failed: {e}")
        return False
    
    return False


if __name__ == "__main__":
    # Check both health and readiness
    is_healthy = check_health()
    is_ready = check_readiness()
    
    if is_healthy and is_ready:
        print("Service is healthy and ready")
        sys.exit(0)
    elif is_healthy:
        print("Service is healthy but not ready")
        sys.exit(1)
    else:
        print("Service is not healthy")
        sys.exit(1)