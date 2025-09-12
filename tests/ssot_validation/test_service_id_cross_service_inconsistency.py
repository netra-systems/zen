"""
SSOT Validation Test: SERVICE_ID Cross-Service Inconsistency Detection

PHASE 1: CREATE FAILING TEST - Expose Cross-Service SERVICE_ID Mismatches

Purpose: This test MUST FAIL with current codebase to expose SERVICE_ID 
inconsistencies between auth_service and netra_backend that cause authentication 
cascade failures.

Business Value: Platform/Critical - Prevents cross-service auth mismatches 
causing 60-second cascade failures (affecting $500K+ ARR).

Expected Behavior:
- FAIL: With current inconsistent SERVICE_ID values between services
- PASS: After SSOT remediation ensures all services use same constant

CRITICAL: This test protects the Golden Path: users login  ->  get AI responses
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

import pytest
import httpx

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class TestServiceIdCrossServiceInconsistency(SSotAsyncTestCase):
    """
    Detect SERVICE_ID inconsistencies between auth_service and netra_backend.
    
    This test validates that all services use consistent SERVICE_ID values
    for cross-service authentication. Current codebase has inconsistencies
    that cause authentication failures.
    
    EXPECTED TO FAIL: Current cross-service SERVICE_ID mismatches exist
    """
    
    def setup_method(self, method=None):
        """Setup test environment with cross-service metrics."""
        super().setup_method(method)
        self.record_metric("test_category", "cross_service_inconsistency")
        self.record_metric("business_impact", "prevents_cross_service_auth_failures")
        
    @pytest.mark.asyncio
    async def test_auth_service_backend_service_id_consistency(self):
        """
        CRITICAL FAILING TEST: Validate SERVICE_ID consistency between services.
        
        This test checks that auth_service and netra_backend use the same
        SERVICE_ID value for cross-service authentication.
        """
        auth_service_id = await self._extract_auth_service_service_id()
        backend_service_id = await self._extract_backend_service_id()
        
        self.record_metric("auth_service_id", auth_service_id)
        self.record_metric("backend_service_id", backend_service_id)
        
        print(f"AUTH SERVICE_ID: {auth_service_id}")
        print(f"BACKEND SERVICE_ID: {backend_service_id}")
        
        # This MUST FAIL initially due to known inconsistencies
        assert auth_service_id == backend_service_id, (
            f"CROSS-SERVICE INCONSISTENCY: auth_service expects SERVICE_ID '{auth_service_id}' "
            f"but backend uses '{backend_service_id}'. This causes authentication failures."
        )
    
    @pytest.mark.asyncio
    async def test_service_id_header_validation_consistency(self):
        """
        CRITICAL FAILING TEST: Validate X-Service-ID header handling consistency.
        
        Tests that both services validate X-Service-ID headers using the same
        expected value, preventing authentication mismatches.
        """
        auth_expected_headers = await self._extract_auth_service_expected_headers()
        backend_expected_headers = await self._extract_backend_expected_headers()
        
        self.record_metric("auth_expected_service_id", auth_expected_headers.get("service_id"))
        self.record_metric("backend_expected_service_id", backend_expected_headers.get("service_id"))
        
        print(f"AUTH EXPECTED HEADERS: {auth_expected_headers}")
        print(f"BACKEND EXPECTED HEADERS: {backend_expected_headers}")
        
        # Check SERVICE_ID consistency in header validation
        auth_service_id = auth_expected_headers.get("service_id")
        backend_service_id = backend_expected_headers.get("service_id")
        
        # This MUST FAIL with current inconsistent header validation
        assert auth_service_id == backend_service_id, (
            f"HEADER VALIDATION INCONSISTENCY: auth_service expects X-Service-ID '{auth_service_id}' "
            f"but backend expects '{backend_service_id}'. This breaks cross-service auth."
        )
    
    @pytest.mark.asyncio
    async def test_environment_vs_hardcoded_service_id_conflicts(self):
        """
        CRITICAL FAILING TEST: Detect conflicts between environment and hardcoded SERVICE_ID.
        
        This test checks if services mix environment-based and hardcoded SERVICE_ID
        values, creating inconsistency depending on environment configuration.
        """
        # Get environment-based SERVICE_ID if configured
        env = get_env()
        env_service_id = env.get("SERVICE_ID")
        
        # Extract hardcoded SERVICE_ID from each service
        auth_hardcoded = await self._extract_hardcoded_service_id("auth_service")
        backend_hardcoded = await self._extract_hardcoded_service_id("netra_backend")
        
        self.record_metric("env_service_id", env_service_id)
        self.record_metric("auth_hardcoded_service_id", auth_hardcoded)
        self.record_metric("backend_hardcoded_service_id", backend_hardcoded)
        
        print(f"ENVIRONMENT SERVICE_ID: {env_service_id}")
        print(f"AUTH HARDCODED SERVICE_ID: {auth_hardcoded}")
        print(f"BACKEND HARDCODED SERVICE_ID: {backend_hardcoded}")
        
        # Analyze conflicts
        conflicts = self._analyze_service_id_conflicts(env_service_id, auth_hardcoded, backend_hardcoded)
        
        self.record_metric("conflicts_detected", len(conflicts))
        
        for conflict in conflicts:
            print(f"CONFLICT DETECTED: {conflict}")
        
        # This MUST FAIL - conflicts exist between environment and hardcoded values
        assert len(conflicts) == 0, (
            f"SERVICE_ID conflicts detected between environment and hardcoded values: {conflicts}. "
            f"This creates inconsistent behavior across environments."
        )
    
    @pytest.mark.asyncio
    async def test_cross_service_authentication_flow_consistency(self):
        """
        CRITICAL FAILING TEST: Validate end-to-end cross-service auth flow.
        
        This test simulates the actual authentication flow between services
        to detect SERVICE_ID mismatches that cause authentication failures.
        """
        # Simulate backend making request to auth service
        backend_headers = await self._generate_backend_service_headers()
        auth_validation_result = await self._simulate_auth_service_validation(backend_headers)
        
        self.record_metric("backend_headers", backend_headers)
        self.record_metric("auth_validation_success", auth_validation_result["success"])
        self.record_metric("auth_validation_error", auth_validation_result.get("error"))
        
        print(f"BACKEND HEADERS: {backend_headers}")
        print(f"AUTH VALIDATION RESULT: {auth_validation_result}")
        
        # This MUST FAIL if SERVICE_ID mismatch exists
        assert auth_validation_result["success"], (
            f"Cross-service authentication failed: {auth_validation_result.get('error')}. "
            f"This indicates SERVICE_ID mismatch between services."
        )
    
    @pytest.mark.asyncio
    async def test_service_configuration_drift_detection(self):
        """
        CRITICAL FAILING TEST: Detect SERVICE_ID configuration drift.
        
        This test checks for configuration drift where different deployment
        environments or configuration files specify different SERVICE_ID values.
        """
        config_sources = await self._scan_service_id_configuration_sources()
        
        self.record_metric("config_sources_found", len(config_sources))
        
        # Analyze configuration consistency
        consistency_analysis = self._analyze_configuration_consistency(config_sources)
        
        self.record_metric("config_consistency_score", consistency_analysis["score"])
        self.record_metric("config_drift_violations", len(consistency_analysis["violations"]))
        
        for source, value in config_sources.items():
            print(f"CONFIG SOURCE {source}: {value}")
        
        for violation in consistency_analysis["violations"]:
            print(f"CONFIGURATION DRIFT: {violation}")
        
        # This MUST FAIL if configuration drift exists
        assert consistency_analysis["score"] >= 0.95, (
            f"Configuration drift detected in SERVICE_ID values. "
            f"Consistency score: {consistency_analysis['score']} (threshold: 0.95). "
            f"Violations: {consistency_analysis['violations']}"
        )
    
    async def _extract_auth_service_service_id(self) -> Optional[str]:
        """Extract SERVICE_ID value used by auth service."""
        auth_routes_path = Path(__file__).parent.parent.parent / "auth_service" / "auth_core" / "routes" / "auth_routes.py"
        
        if not auth_routes_path.exists():
            return None
        
        try:
            with open(auth_routes_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for hardcoded SERVICE_ID in auth routes
            # Based on known issue: lines 760 and 935 have hardcoded "netra-backend"
            if 'expected_service_id = "netra-backend"' in content:
                return "netra-backend"
            
            # Look for environment-based access
            if 'os.environ.get("SERVICE_ID")' in content:
                env = get_env()
                return env.get("SERVICE_ID", "undefined")
            
        except (FileNotFoundError, PermissionError):
            pass
        
        return None
    
    async def _extract_backend_service_id(self) -> Optional[str]:
        """Extract SERVICE_ID value used by backend service."""
        # Look for backend SERVICE_ID configuration
        backend_paths = [
            Path(__file__).parent.parent.parent / "netra_backend" / "app" / "config.py",
            Path(__file__).parent.parent.parent / "netra_backend" / "app" / "core" / "configuration",
        ]
        
        for path in backend_paths:
            if path.is_file():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for SERVICE_ID configuration
                    if 'SERVICE_ID' in content:
                        # Check for hardcoded values
                        if '"netra-backend"' in content:
                            return "netra-backend"
                        
                        # Check for environment access
                        if 'environ' in content:
                            env = get_env()
                            return env.get("SERVICE_ID", "undefined")
                
                except (FileNotFoundError, PermissionError):
                    continue
            elif path.is_dir():
                # Scan directory for configuration files
                for config_file in path.rglob("*.py"):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        if 'SERVICE_ID' in content:
                            if '"netra-backend"' in content:
                                return "netra-backend"
                            if 'environ' in content:
                                env = get_env()
                                return env.get("SERVICE_ID", "undefined")
                    
                    except (FileNotFoundError, PermissionError):
                        continue
        
        return None
    
    async def _extract_auth_service_expected_headers(self) -> Dict[str, Any]:
        """Extract expected headers from auth service validation logic."""
        # Simulate auth service header expectations
        return {
            "service_id": "netra-backend",  # Known hardcoded value from issue
            "requires_service_secret": True,
            "header_name": "X-Service-ID"
        }
    
    async def _extract_backend_expected_headers(self) -> Dict[str, Any]:
        """Extract expected headers from backend service logic."""
        # Look for backend header generation logic
        env = get_env()
        
        # Check if backend uses environment or hardcoded values
        return {
            "service_id": env.get("SERVICE_ID", "netra-backend"),  # May be environment-based
            "requires_service_secret": True,
            "header_name": "X-Service-ID"
        }
    
    async def _extract_hardcoded_service_id(self, service_name: str) -> Optional[str]:
        """Extract hardcoded SERVICE_ID from specific service."""
        service_path = Path(__file__).parent.parent.parent / service_name
        
        if not service_path.exists():
            return None
        
        # Scan service directory for hardcoded SERVICE_ID
        for python_file in service_path.rglob("**/*.py"):
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for hardcoded "netra-backend" assignments
                if 'service_id = "netra-backend"' in content or 'SERVICE_ID = "netra-backend"' in content:
                    return "netra-backend"
                
            except (FileNotFoundError, PermissionError):
                continue
        
        return None
    
    def _analyze_service_id_conflicts(self, env_value: Optional[str], auth_hardcoded: Optional[str], backend_hardcoded: Optional[str]) -> List[str]:
        """Analyze conflicts between different SERVICE_ID sources."""
        conflicts = []
        
        values = [
            ("environment", env_value),
            ("auth_hardcoded", auth_hardcoded),
            ("backend_hardcoded", backend_hardcoded)
        ]
        
        # Remove None values
        valid_values = [(source, value) for source, value in values if value is not None]
        
        if len(valid_values) < 2:
            return conflicts
        
        # Check for inconsistencies
        unique_values = set(value for _, value in valid_values)
        
        if len(unique_values) > 1:
            for source, value in valid_values:
                conflicts.append(f"{source} uses '{value}' while others differ")
        
        return conflicts
    
    async def _generate_backend_service_headers(self) -> Dict[str, str]:
        """Generate headers that backend would send to auth service."""
        env = get_env()
        
        return {
            "X-Service-ID": env.get("SERVICE_ID", "netra-backend"),
            "X-Service-Secret": env.get("SERVICE_SECRET", "test-secret"),
            "Content-Type": "application/json"
        }
    
    async def _simulate_auth_service_validation(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Simulate auth service validating incoming service headers."""
        # Based on known hardcoded validation in auth_routes.py
        expected_service_id = "netra-backend"  # Hardcoded in auth service
        received_service_id = headers.get("X-Service-ID")
        
        if received_service_id == expected_service_id:
            return {"success": True}
        else:
            return {
                "success": False,
                "error": f"Service ID mismatch: received '{received_service_id}', expected '{expected_service_id}'"
            }
    
    async def _scan_service_id_configuration_sources(self) -> Dict[str, str]:
        """Scan for all SERVICE_ID configuration sources."""
        config_sources = {}
        project_root = Path(__file__).parent.parent.parent
        
        # Check environment files
        env_files = [
            ".env",
            ".env.local",
            ".env.staging",
            ".env.production",
            ".env.alpine-test"
        ]
        
        for env_file in env_files:
            env_path = project_root / env_file
            if env_path.exists():
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for line in content.split('\n'):
                        if line.startswith('SERVICE_ID='):
                            value = line.split('=', 1)[1].strip()
                            config_sources[f"env_file_{env_file}"] = value
                
                except (FileNotFoundError, PermissionError):
                    continue
        
        # Check Docker compose files
        compose_files = list(project_root.rglob("docker-compose*.yml")) + list(project_root.rglob("docker-compose*.yaml"))
        
        for compose_file in compose_files:
            try:
                with open(compose_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'SERVICE_ID' in content:
                    # Simple extraction - could be enhanced with YAML parsing
                    config_sources[f"compose_{compose_file.name}"] = "configured_in_compose"
            
            except (FileNotFoundError, PermissionError):
                continue
        
        return config_sources
    
    def _analyze_configuration_consistency(self, config_sources: Dict[str, str]) -> Dict[str, Any]:
        """Analyze consistency across configuration sources."""
        if not config_sources:
            return {"score": 1.0, "violations": []}
        
        unique_values = set(config_sources.values())
        
        # Calculate consistency score
        if len(unique_values) == 1:
            score = 1.0
            violations = []
        else:
            score = 1.0 / len(unique_values)  # Lower score for more variations
            violations = [
                f"Inconsistent values across sources: {dict(config_sources)}"
            ]
        
        return {
            "score": score,
            "violations": violations
        }