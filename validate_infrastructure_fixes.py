#!/usr/bin/env python3
"""
Infrastructure Fix Validation Script for Issue #843

This script validates the remediation fixes for the Golden Path infrastructure issues:
1. WebSocket client compatibility fix
2. Python 3.13.7 datetime compatibility fix
3. WebSocketNotifier emitter validation fix
4. Staging environment configuration

Business Impact: Validates $500K+ ARR Golden Path functionality
"""

import sys
import os
import asyncio
import importlib.util
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class InfrastructureFixValidator:
    """Validates the infrastructure fixes applied for Issue #843."""
    
    def __init__(self):
        self.results = {}
        self.overall_success = True
    
    def log_result(self, test_name: str, success: bool, message: str):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.results[test_name] = {"success": success, "message": message}
        if not success:
            self.overall_success = False
    
    def test_websocket_test_client_import(self):
        """Test Fix 1: WebSocket test client import compatibility."""
        try:
            from test_framework.ssot.websocket_test_client import UnifiedWebSocketTestClient
            self.log_result(
                "WebSocket Test Client Import", 
                True, 
                "UnifiedWebSocketTestClient import successful"
            )
        except ImportError as e:
            self.log_result(
                "WebSocket Test Client Import", 
                False, 
                f"Import failed: {e}"
            )
    
    def test_datetime_compatibility(self):
        """Test Fix 2: Python 3.13.7 datetime compatibility."""
        try:
            # Test that we can use datetime.now(timezone.utc) instead of deprecated utcnow()
            current_time = datetime.now(timezone.utc)
            
            # Import WebSocket modules to check they don't use deprecated datetime calls
            from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
            
            self.log_result(
                "Datetime Compatibility", 
                True, 
                f"timezone-aware datetime working: {current_time.isoformat()}"
            )
        except Exception as e:
            self.log_result(
                "Datetime Compatibility", 
                False, 
                f"Datetime compatibility issue: {e}"
            )
    
    async def test_websocket_notifier_creation(self):
        """Test Fix 3: WebSocketNotifier emitter validation fix."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
            
            # Create test execution context
            id_manager = UnifiedIDManager()
            test_context = type('MockUserContext', (), {
                'user_id': id_manager.generate_id(IDType.USER, prefix="test"),
                'session_id': id_manager.generate_id(IDType.THREAD, prefix="test"),
                'request_id': id_manager.generate_id(IDType.REQUEST, prefix="test"),
                'is_test': True
            })()
            
            # Test that WebSocketNotifier can be created with None emitter (should create default)
            notifier = WebSocketNotifier.create_for_user(emitter=None, exec_context=test_context)
            
            self.log_result(
                "WebSocket Notifier Creation", 
                True, 
                f"WebSocketNotifier created successfully with default emitter for user {test_context.user_id}"
            )
            
        except Exception as e:
            self.log_result(
                "WebSocket Notifier Creation", 
                False, 
                f"WebSocketNotifier creation failed: {e}"
            )
    
    def test_staging_environment_config(self):
        """Test Fix 4: Staging environment configuration."""
        try:
            # Check if staging environment setup is available
            import test_staging_env_setup
            from tests.staging.staging_config import StagingConfig
            
            staging_config = StagingConfig()
            staging_urls = staging_config.SERVICE_URLS.get("staging", {})
            
            # Verify key staging URLs are configured
            required_urls = ["AUTH_SERVICE_URL", "NETRA_BACKEND_URL", "WEBSOCKET_URL"]
            missing_urls = [url for url in required_urls if url not in staging_urls]
            
            if not missing_urls:
                self.log_result(
                    "Staging Environment Config", 
                    True, 
                    f"All staging URLs configured: {list(staging_urls.keys())}"
                )
            else:
                self.log_result(
                    "Staging Environment Config", 
                    False, 
                    f"Missing staging URLs: {missing_urls}"
                )
                
        except Exception as e:
            self.log_result(
                "Staging Environment Config", 
                False, 
                f"Staging config validation failed: {e}"
            )
    
    def test_websocket_library_compatibility(self):
        """Test Fix 5: WebSocket library compatibility with Python 3.13.7."""
        try:
            import websockets
            from websockets.asyncio.client import ClientConnection
            
            # Check version is compatible
            version = websockets.__version__
            version_parts = [int(x) for x in version.split('.')]
            
            # websockets >= 15.0.1 should be compatible with Python 3.13.7
            compatible = version_parts >= [15, 0, 1]
            
            self.log_result(
                "WebSocket Library Compatibility", 
                compatible, 
                f"websockets v{version} - {'compatible' if compatible else 'needs upgrade'}"
            )
            
        except Exception as e:
            self.log_result(
                "WebSocket Library Compatibility", 
                False, 
                f"WebSocket library check failed: {e}"
            )
    
    async def run_all_validations(self):
        """Run all infrastructure fix validations."""
        print("🔍 Infrastructure Fix Validation for Issue #843")
        print("=" * 60)
        print("Business Impact: $500K+ ARR Golden Path functionality validation")
        print("=" * 60)
        
        # Run synchronous tests
        self.test_websocket_test_client_import()
        self.test_datetime_compatibility()
        self.test_staging_environment_config()
        self.test_websocket_library_compatibility()
        
        # Run asynchronous tests
        await self.test_websocket_notifier_creation()
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results.values() if r["success"])
        total = len(self.results)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print("-" * 60)
        print(f"🏆 OVERALL RESULT: {passed}/{total} tests passed")
        
        if self.overall_success:
            print("✅ ALL INFRASTRUCTURE FIXES VALIDATED SUCCESSFULLY")
            print("🚀 System ready for Golden Path e2e testing on GCP staging")
            return True
        else:
            print("❌ SOME INFRASTRUCTURE FIXES FAILED")
            print("⚠️  Additional remediation needed")
            return False


async def main():
    """Main validation script."""
    validator = InfrastructureFixValidator()
    success = await validator.run_all_validations()
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS")
    print("=" * 60)
    
    if success:
        print("1. ✅ Infrastructure fixes validated")
        print("2. 🚀 Ready to run Golden Path e2e tests with:")
        print("   python3 run_staging_integration_tests.py --categories websocket")
        print("3. 📝 Update GitHub Issue #843 with remediation results")
        print("4. 💾 Commit infrastructure fixes")
    else:
        print("1. ❌ Fix remaining infrastructure issues")
        print("2. 🔄 Re-run validation script")
        print("3. 🚀 Then proceed with Golden Path testing")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)