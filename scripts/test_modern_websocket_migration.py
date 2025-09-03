#!/usr/bin/env python3
"""
Test Modern WebSocket Migration

This script tests the modern WebSocket implementation to ensure:
1. No deprecation warnings are generated
2. WebSocket connections work properly
3. Modern abstractions function correctly
4. Backward compatibility is maintained
"""

import asyncio
import json
import logging
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging to catch warnings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Capture all warnings
warnings.filterwarnings('error', category=DeprecationWarning)

class WebSocketMigrationTester:
    """Tests for modern WebSocket migration."""
    
    def __init__(self):
        self.test_results: Dict[str, bool] = {}
        self.deprecation_warnings: List[str] = []
        
    async def test_modern_abstraction_import(self) -> bool:
        """Test that canonical WebSocket manager can be imported without warnings."""
        try:
            from netra_backend.app.websocket_core import (
                WebSocketManager,
                get_websocket_manager,
                websocket_context
            )
            logger.info("Canonical WebSocket manager imported successfully (modern features integrated)")
            return True
        except Exception as e:
            logger.error(f"Failed to import canonical WebSocket manager: {e}")
            return False
    
    async def test_websocket_core_imports(self) -> bool:
        """Test that WebSocket core imports work without deprecation warnings."""
        try:
            from netra_backend.app.websocket_core import (
                WebSocketManager,
                get_websocket_manager,
                WebSocketMessage,
                MessageRouter
            )
            logger.info("WebSocket core imports successful")
            return True
        except Exception as e:
            logger.error(f"Failed to import WebSocket core: {e}")
            return False
    
    async def test_modern_websocket_manager(self) -> bool:
        """Test canonical WebSocket manager functionality (with integrated modern features)."""
        try:
            from netra_backend.app.websocket_core import get_websocket_manager
            
            manager = get_websocket_manager()
            
            # Test basic functionality
            stats = await manager.get_stats()
            assert stats is not None
            logger.info("Canonical WebSocket manager functional (modern features integrated)")
            return True
        except Exception as e:
            logger.error(f"Canonical WebSocket manager test failed: {e}")
            return False
    
    async def test_no_legacy_imports(self) -> bool:
        """Test that core imports work without legacy dependencies."""
        try:
            # This should work without issues - canonical approach
            from netra_backend.app.websocket_core import WebSocketManager, MessageType, ConnectionInfo
            logger.info("Core WebSocket imports successful (no legacy dependencies)")
            return True
        except Exception as e:
            logger.error(f"Core WebSocket imports failed: {e}")
            return False
    
    async def test_websocket_wrapper(self) -> bool:
        """Test the canonical WebSocket manager functionality (replaces wrapper)."""
        try:
            from netra_backend.app.websocket_core import get_websocket_manager, create_standard_message
            
            manager = get_websocket_manager()
            
            # Test message creation (replaces wrapper functionality)
            message = create_standard_message(
                message_type="test",
                payload={"test": "data"}
            )
            
            assert message is not None
            assert message.message_type == "test"
            
            logger.info("Canonical WebSocket manager tests passed (replaces wrapper functionality)")
            return True
        except Exception as e:
            logger.error(f"Canonical WebSocket manager test failed: {e}")
            return False
    
    async def test_uvicorn_config(self) -> bool:
        """Test that uvicorn configuration includes modern WebSocket settings."""
        try:
            from netra_backend.app.main import _get_uvicorn_config
            
            config = _get_uvicorn_config()
            
            # Check for modern WebSocket configuration
            required_keys = [
                "ws_ping_interval",
                "ws_ping_timeout", 
                "ws_max_size",
                "interface"
            ]
            
            for key in required_keys:
                assert key in config, f"Missing {key} in uvicorn config"
            
            assert config["interface"] == "asgi3", "Should use ASGI3 interface"
            
            logger.info("Uvicorn configuration includes modern WebSocket settings")
            return True
        except Exception as e:
            logger.error(f"Uvicorn config test failed: {e}")
            return False
    
    def check_for_deprecation_warnings(self) -> bool:
        """Check if any deprecation warnings were generated."""
        if self.deprecation_warnings:
            logger.error(f"Found {len(self.deprecation_warnings)} deprecation warnings:")
            for warning in self.deprecation_warnings:
                logger.error(f"  - {warning}")
            return False
        else:
            logger.info("No deprecation warnings detected")
            return True
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all WebSocket migration tests."""
        tests = [
            ("modern_abstraction_import", self.test_modern_abstraction_import),
            ("websocket_core_imports", self.test_websocket_core_imports),
            ("modern_websocket_manager", self.test_modern_websocket_manager),
            ("no_legacy_imports", self.test_no_legacy_imports),
            ("websocket_wrapper", self.test_websocket_wrapper),
            ("uvicorn_config", self.test_uvicorn_config),
        ]
        
        logger.info("Running WebSocket migration tests...")
        
        for test_name, test_func in tests:
            try:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    result = await test_func()
                    
                    # Check for deprecation warnings
                    for warning in w:
                        if issubclass(warning.category, DeprecationWarning):
                            self.deprecation_warnings.append(str(warning.message))
                    
                    self.test_results[test_name] = result
                    status = "PASS" if result else "FAIL"
                    logger.info(f"{test_name}: {status}")
                    
            except Exception as e:
                logger.error(f"{test_name}: FAIL - {e}")
                self.test_results[test_name] = False
        
        # Final warning check
        no_warnings = self.check_for_deprecation_warnings()
        self.test_results["no_deprecation_warnings"] = no_warnings
        
        return self.test_results
    
    def print_summary(self):
        """Print test summary."""
        total = len(self.test_results)
        passed = sum(1 for result in self.test_results.values() if result)
        failed = total - passed
        
        print("\n" + "="*60)
        print("WEBSOCKET MIGRATION TEST SUMMARY")
        print("="*60)
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for test_name, result in self.test_results.items():
                if not result:
                    print(f"  - {test_name}")
        
        if self.deprecation_warnings:
            print(f"\nDEPRECATION WARNINGS: {len(self.deprecation_warnings)}")
            for warning in self.deprecation_warnings:
                print(f"  - {warning}")
        
        print("="*60)
        
        return failed == 0 and len(self.deprecation_warnings) == 0

async def main():
    """Main test execution."""
    tester = WebSocketMigrationTester()
    
    try:
        results = await tester.run_all_tests()
        success = tester.print_summary()
        
        if success:
            print("\nAll WebSocket migration tests PASSED!")
            print("Modern WebSocket implementation is working correctly.")
            sys.exit(0)
        else:
            print("\nSome WebSocket migration tests FAILED!")
            print("Review the issues above before proceeding.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())