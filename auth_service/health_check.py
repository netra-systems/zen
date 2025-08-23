#!/usr/bin/env python3
"""
Health check script for Auth Service
Used by orchestrators and load balancers to determine service health
"""
import sys
import urllib.request
import urllib.error
import json
import os


def check_health(port=None):
    """Check if the auth service is healthy"""
    if port is None:
        port = os.getenv('PORT', '8080')
    
    health_url = f"http://localhost:{port}/health"
    
    try:
        with urllib.request.urlopen(health_url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read())
                if data.get('status') == 'healthy':
                    return True
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        pass
    
    return False


def check_readiness(port=None):
    """Check if the auth service is ready to serve requests"""
    if port is None:
        port = os.getenv('PORT', '8080')
    
    ready_url = f"http://localhost:{port}/health/ready"
    
    try:
        with urllib.request.urlopen(ready_url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read())
                if data.get('status') == 'ready':
                    return True
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        pass
    
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