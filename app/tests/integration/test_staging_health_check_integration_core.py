"""Core Tests - Split from test_staging_health_check_integration.py

    BVJ: Protects 100% of $7K MRR by ensuring services are operational.
    Priority: P0 - Blocks all deployments if failing.
"""

import asyncio
import pytest
import time
import httpx
import os
from typing import Dict, Any, Tuple, List
from datetime import datetime
import json

    def __init__(self):
        """Initialize staging health validator with GCP service names."""
        # Service names MUST match GCP Cloud Run deployment names exactly
        # Per SPEC/learnings/deployment_staging.xml
        self.staging_base_url = os.getenv("STAGING_BASE_URL", "https://netra-backend-staging-xyz.run.app")
        self.local_base_url = "http://localhost:8000"
        
        self.services = {
            "backend": {
                "staging_name": "netra-backend-staging",  # CRITICAL: Must use -staging suffix
                "local_url": "http://localhost:8000",
                "staging_url": self.staging_base_url,
                "health_endpoint": "/health",
                "critical": True,
                "timeout": 2.0  # Health must respond within 2 seconds
            },
            "auth": {
                "staging_name": "netra-auth-service",  # No -staging suffix per spec
                "local_url": "http://localhost:8080",  # Auth service on 8080, not 8001
                "staging_url": os.getenv("AUTH_SERVICE_URL", "https://netra-auth-service-xyz.run.app"),
                "health_endpoint": "/health/ready",  # Auth uses /health/ready endpoint
                "critical": True,
                "timeout": 2.0
            },
            "frontend": {
                "staging_name": "netra-frontend-staging",  # CRITICAL: Must use -staging suffix
                "local_url": "http://localhost:3000",
                "staging_url": os.getenv("FRONTEND_URL", "https://netra-frontend-staging-xyz.run.app"),
                "health_endpoint": "/",  # Frontend may not have dedicated health endpoint
                "critical": True,
                "timeout": 3.0  # Frontend may take longer
            }
        }
        
        self.is_staging = os.getenv("ENVIRONMENT", "local") == "staging"
