"""Services Tests - Split from test_auth_service_dependency_resolution.py

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability
- Value Impact: Prevents service startup ordering failures
- Revenue Impact: Protects $12K infrastructure reliability value

Tests service startup dependency resolution, health check cascade behavior,
backend graceful waiting for auth service readiness, and error handling.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime
from app.core.health_check import HealthCheckService
from app.services.service_orchestrator import ServiceOrchestrator
from test_framework.real_service_helper import RealServiceHelper

    def __init__(self):
        self.startup_events: List[Dict[str, Any]] = []
        self.service_states: Dict[str, str] = {}
        self.dependency_graph: Dict[str, List[str]] = {
            "auth_service": [],  # No dependencies
            "backend": ["auth_service"],  # Depends on auth
            "frontend": ["backend", "auth_service"]  # Depends on both
        }

    def record_startup_event(self, service_name: str, event_type: str, timestamp: float = None):
        """Record a service startup event."""
        if timestamp is None:
            timestamp = time.time()
        
        self.startup_events.append({
            "service": service_name,
            "event": event_type,
            "timestamp": timestamp
        })
        
        if event_type == "started":
            self.service_states[service_name] = "starting"
        elif event_type == "ready":
            self.service_states[service_name] = "ready"
        elif event_type == "failed":
            self.service_states[service_name] = "failed"

    def get_startup_order(self) -> List[str]:
        """Get the actual startup order of services."""
        started_services = []
        for event in self.startup_events:
            if event["event"] == "started" and event["service"] not in started_services:
                started_services.append(event["service"])
        return started_services

    def validate_dependency_order(self) -> bool:
        """Validate that services started in correct dependency order."""
        startup_order = self.get_startup_order()
        
        for service, dependencies in self.dependency_graph.items():
            if service in startup_order:
                service_index = startup_order.index(service)
                for dep in dependencies:
                    if dep in startup_order:
                        dep_index = startup_order.index(dep)
                        if dep_index >= service_index:
                            return False  # Dependency started after dependent
        return True

    def __init__(self):
        self.orchestrator = ServiceOrchestrator()
        self.service_helper = RealServiceHelper()
        self.health_service = HealthCheckService()
        self.startup_monitor = ServiceStartupMonitor()
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3000"
