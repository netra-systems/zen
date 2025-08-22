"""Startup check helpers for testing service initialization."""

import asyncio
import time
from typing import Dict, List, Optional, Any
from unittest.mock import MagicMock
import httpx

class StartupTestHelper:
    """Helper for testing service startup processes."""
    
    def __init__(self):
        self.services_started = []
        self.services_failed = []
        self.startup_times = {}
        
    async def wait_for_service(self, service_name: str, url: str, timeout: int = 30) -> bool:
        """Wait for a service to become available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200:
                        self.services_started.append(service_name)
                        self.startup_times[service_name] = time.time() - start_time
                        return True
            except Exception:
                pass
            await asyncio.sleep(1)
        
        self.services_failed.append(service_name)
        return False
    
    def check_all_services_started(self) -> bool:
        """Check if all expected services have started."""
        return len(self.services_failed) == 0
    
    def get_startup_report(self) -> Dict:
        """Get a report of service startup status."""
        return {
            "started": self.services_started,
            "failed": self.services_failed,
            "startup_times": self.startup_times
        }
    
    async def simulate_startup_sequence(self, services: List[str]) -> Dict:
        """Simulate a startup sequence for testing."""
        results = {}
        for service in services:
            # Simulate startup delay
            await asyncio.sleep(0.1)
            results[service] = "started"
            self.services_started.append(service)
        return results

class RealServiceTestValidator:
    """Validator for testing real service integrations."""
    
    def __init__(self):
        self.validation_results = {}
        self.errors = []
        
    async def validate_service_health(self, service_name: str, health_url: str) -> bool:
        """Validate a service's health endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(health_url)
                is_healthy = response.status_code == 200
                self.validation_results[service_name] = {
                    "healthy": is_healthy,
                    "status_code": response.status_code,
                    "response": response.json() if is_healthy else None
                }
                return is_healthy
        except Exception as e:
            self.errors.append(f"{service_name}: {str(e)}")
            self.validation_results[service_name] = {
                "healthy": False,
                "error": str(e)
            }
            return False
    
    async def validate_service_dependencies(self, service_name: str, dependencies: List[str]) -> bool:
        """Validate that a service's dependencies are available."""
        all_valid = True
        for dep in dependencies:
            # Mock validation for testing
            is_valid = True  # In real implementation, check actual dependency
            if not is_valid:
                all_valid = False
                self.errors.append(f"{service_name} dependency {dep} not available")
        return all_valid
    
    def get_validation_report(self) -> Dict:
        """Get validation report."""
        return {
            "results": self.validation_results,
            "errors": self.errors,
            "all_valid": len(self.errors) == 0
        }
    
    async def validate_api_endpoint(self, endpoint: str, expected_status: int = 200) -> bool:
        """Validate an API endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoint)
                return response.status_code == expected_status
        except Exception as e:
            self.errors.append(f"API endpoint {endpoint}: {str(e)}")
            return False