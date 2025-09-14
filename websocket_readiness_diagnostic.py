#!/usr/bin/env python3
"""
WebSocket Readiness Diagnostic Tool for Issue #919

PURPOSE: Reproducing and diagnosing the "unknown state" WebSocket rejection issue
BUSINESS IMPACT: WebSocket connections being rejected with 503 Service Unavailable
ERROR PATTERN: State: unknown, Failed services: [], Error: service_not_ready
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.append('/Users/anthony/Desktop/netra-apex')

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger


class WebSocketReadinessDiagnostic:
    """Diagnostic tool to reproduce Issue #919 WebSocket rejection pattern."""
    
    def __init__(self):
        self.logger = central_logger.get_logger(__name__)
        self.env_manager = get_env()
    
    async def run_diagnostic(self) -> Dict[str, Any]:
        """Run comprehensive diagnostic to reproduce the issue."""
        
        diagnostic_results = {
            "environment_check": await self._check_environment(),
            "gcp_validator_check": await self._check_gcp_validator(),
            "middleware_check": await self._check_middleware_behavior(),
            "readiness_simulation": await self._simulate_readiness_check()
        }
        
        return diagnostic_results
    
    async def _check_environment(self) -> Dict[str, Any]:
        """Check environment configuration that affects WebSocket readiness."""
        
        try:
            environment = self.env_manager.get('ENVIRONMENT', '').lower()
            bypass_staging = self.env_manager.get('BYPASS_WEBSOCKET_READINESS_STAGING', 'false').lower() == 'true'
            gcp_env = self.env_manager.get('GOOGLE_CLOUD_PROJECT', '') != ''
            
            return {
                "status": "success",
                "environment": environment,
                "bypass_staging_flag": bypass_staging,
                "gcp_environment": gcp_env,
                "google_cloud_project": self.env_manager.get('GOOGLE_CLOUD_PROJECT', 'not_set'),
                "issue_analysis": self._analyze_environment_config(environment, bypass_staging, gcp_env)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _analyze_environment_config(self, environment: str, bypass: bool, gcp_env: bool) -> str:
        """Analyze environment configuration for Issue #919 patterns."""
        
        if gcp_env and environment == 'staging' and not bypass:
            return "LIKELY CAUSE: GCP staging environment without bypass flag - readiness check will fail"
        elif gcp_env and not environment:
            return "LIKELY CAUSE: GCP environment detected but ENVIRONMENT variable not set - state remains unknown"
        elif not gcp_env:
            return "INFO: Non-GCP environment - should skip GCP validation"
        else:
            return "CONFIG OK: Environment configuration appears correct"
    
    async def _check_gcp_validator(self) -> Dict[str, Any]:
        """Check GCP validator import and initialization."""
        
        try:
            from netra_backend.app.websocket_core.gcp_initialization_validator import (
                create_gcp_websocket_validator,
                gcp_websocket_readiness_check,
                GCPReadinessState
            )
            
            # Create a mock app_state
            class MockAppState:
                def __init__(self):
                    self.startup_phase = 'unknown'
                    self.startup_complete = False
                    self.startup_failed = False
            
            mock_app_state = MockAppState()
            
            # Test validator creation
            validator = create_gcp_websocket_validator(mock_app_state)
            
            return {
                "status": "success",
                "validator_created": True,
                "initial_state": validator.current_state.value,
                "environment": validator.environment,
                "is_gcp_environment": validator.is_gcp_environment,
                "is_cloud_run": validator.is_cloud_run,
                "issue_analysis": self._analyze_validator_state(validator)
            }
            
        except ImportError as e:
            return {
                "status": "import_error",
                "error": str(e),
                "issue_analysis": "LIKELY CAUSE: GCP validator import failure would cause 'unknown' state"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _analyze_validator_state(self, validator) -> str:
        """Analyze validator configuration for Issue #919 patterns."""
        
        if validator.current_state.value == 'unknown' and not validator.is_gcp_environment:
            return "INFO: Non-GCP environment detected - validator should skip GCP checks"
        elif validator.current_state.value == 'unknown' and validator.is_gcp_environment:
            return "CRITICAL: GCP environment with unknown state - this would cause rejections"
        else:
            return "CONFIG OK: Validator state appears correct for environment"
    
    async def _check_middleware_behavior(self) -> Dict[str, Any]:
        """Check middleware rejection logic."""
        
        try:
            from netra_backend.app.middleware.gcp_websocket_readiness_middleware import (
                GCPWebSocketReadinessMiddleware
            )
            
            # Test middleware initialization
            middleware = GCPWebSocketReadinessMiddleware(None)  # No app needed for initialization
            
            return {
                "status": "success",
                "middleware_created": True,
                "environment": middleware.environment,
                "is_gcp_environment": middleware.is_gcp_environment,
                "cache_duration": middleware._cache_duration,
                "issue_analysis": self._analyze_middleware_config(middleware)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _analyze_middleware_config(self, middleware) -> str:
        """Analyze middleware configuration for Issue #919 patterns."""
        
        if middleware.is_gcp_environment and middleware.environment != 'staging':
            return "CRITICAL: GCP environment without staging bypass - would reject connections"
        elif not middleware.is_gcp_environment:
            return "INFO: Non-GCP environment - should allow connections"
        else:
            return "CONFIG: Middleware configuration depends on bypass flag"
    
    async def _simulate_readiness_check(self) -> Dict[str, Any]:
        """Simulate the readiness check that's failing in production."""
        
        try:
            from netra_backend.app.websocket_core.gcp_initialization_validator import (
                gcp_websocket_readiness_check
            )
            
            # Create a mock app_state similar to what would be in GCP
            class MockAppState:
                def __init__(self):
                    self.startup_phase = 'unknown'  # This could be the issue
                    self.startup_complete = False
                    self.startup_failed = False
            
            mock_app_state = MockAppState()
            
            # Temporarily set environment variables to simulate GCP staging/active-dev
            import os
            original_env = os.environ.get('ENVIRONMENT')
            original_gcp = os.environ.get('GOOGLE_CLOUD_PROJECT')
            
            # Simulate GCP active-dev environment (matches Issue #919 logs)
            os.environ['ENVIRONMENT'] = 'gcp-active-dev'
            os.environ['GOOGLE_CLOUD_PROJECT'] = 'netra-staging'
            
            try:
                # Run the actual readiness check
                ready, details = await gcp_websocket_readiness_check(mock_app_state)
                
                return {
                    "status": "success",
                    "ready": ready,
                    "details": details,
                    "issue_analysis": self._analyze_readiness_result(ready, details)
                }
            finally:
                # Restore original environment variables
                if original_env:
                    os.environ['ENVIRONMENT'] = original_env
                else:
                    os.environ.pop('ENVIRONMENT', None)
                if original_gcp:
                    os.environ['GOOGLE_CLOUD_PROJECT'] = original_gcp
                else:
                    os.environ.pop('GOOGLE_CLOUD_PROJECT', None)
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _analyze_readiness_result(self, ready: bool, details: Dict[str, Any]) -> str:
        """Analyze readiness check results for Issue #919 patterns."""
        
        state = details.get('state', 'unknown')
        failed_services = details.get('failed_services', [])
        
        if not ready and state == 'unknown' and not failed_services:
            return "REPRODUCED: This matches Issue #919 pattern exactly!"
        elif not ready and state == 'bypassed_for_staging':
            return "INFO: Staging bypass working correctly"
        elif ready and state == 'websocket_ready':
            return "INFO: Readiness check passed successfully"
        else:
            return f"ANALYSIS: ready={ready}, state={state}, failed_services={failed_services}"


async def main():
    """Run the diagnostic tool."""
    
    print("🔍 WebSocket Readiness Diagnostic Tool for Issue #919")
    print("=" * 60)
    
    diagnostic = WebSocketReadinessDiagnostic()
    results = await diagnostic.run_diagnostic()
    
    print("\n📊 DIAGNOSTIC RESULTS:")
    print("=" * 60)
    
    for category, result in results.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        print("-" * 40)
        
        if result.get('status') == 'success':
            print("✅ SUCCESS")
        elif result.get('status') == 'error':
            print(f"❌ ERROR: {result.get('error')}")
        elif result.get('status') == 'import_error':
            print(f"🚫 IMPORT ERROR: {result.get('error')}")
            
        # Print analysis
        if 'issue_analysis' in result:
            print(f"🔍 ANALYSIS: {result['issue_analysis']}")
        
        # Print key details
        for key, value in result.items():
            if key not in ['status', 'error', 'issue_analysis']:
                print(f"   {key}: {value}")
    
    print("\n🎯 RECOMMENDATIONS:")
    print("=" * 60)
    print("1. Check if ENVIRONMENT variable is set correctly in GCP")
    print("2. Verify BYPASS_WEBSOCKET_READINESS_STAGING flag for staging")
    print("3. Check if startup_phase is progressing past 'unknown'")
    print("4. Ensure app_state is properly initialized before WebSocket validation")


if __name__ == "__main__":
    asyncio.run(main())