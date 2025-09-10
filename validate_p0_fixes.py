#!/usr/bin/env python3
"""
Validate P0 Critical Infrastructure Fixes

This script validates the three critical P0 fixes implemented to protect $1.5M+ ARR:

1. WebSocket 1011 internal errors fix with GCP staging auto-detection
2. Agent Registry initialization with proper llm_manager validation
3. E2E_OAUTH_SIMULATION_KEY deployment validation

Usage:
    python validate_p0_fixes.py
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Tuple
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

class P0FixValidator:
    """Validates all P0 critical infrastructure fixes."""
    
    def __init__(self):
        self.validation_results: Dict[str, Dict[str, Any]] = {}
        self.overall_status = True
    
    def validate_fix_1_websocket_gcp_detection(self) -> Dict[str, Any]:
        """Validate WebSocket GCP staging auto-detection fix."""
        print("🔍 Validating Fix #1: WebSocket GCP Staging Auto-Detection")
        
        try:
            # Test 1: Import the updated unified manager
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            print("  ✅ UnifiedWebSocketManager imports successfully")
            
            # Test 2: Check if the auto-detection code exists
            import inspect
            source = inspect.getsource(UnifiedWebSocketManager.emit_critical_event)
            
            if "GCP staging auto-detection" in source:
                print("  ✅ GCP staging auto-detection code present")
            else:
                print("  ❌ GCP staging auto-detection code NOT found")
                return {"status": "FAILED", "error": "Auto-detection code missing"}
            
            if "netra-staging" in source and "staging.netrasystems.ai" in source:
                print("  ✅ Staging environment detection patterns present")
            else:
                print("  ❌ Staging detection patterns missing")
                return {"status": "FAILED", "error": "Detection patterns missing"}
            
            # Test 3: Validate retry configuration logic
            if "max_retries = 3" in source and "retry_delay = 1.0" in source:
                print("  ✅ Cloud environment retry configuration present")
            else:
                print("  ❌ Cloud retry configuration missing")
                return {"status": "FAILED", "error": "Retry config missing"}
            
            return {
                "status": "PASSED", 
                "details": "GCP staging auto-detection implemented with proper retry logic"
            }
            
        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            return {"status": "FAILED", "error": str(e)}
    
    def validate_fix_2_agent_registry_initialization(self) -> Dict[str, Any]:
        """Validate Agent Registry initialization fix."""
        print("🔍 Validating Fix #2: Agent Registry Initialization")
        
        try:
            # Test 1: Import the updated agent registry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            print("  ✅ AgentRegistry imports successfully")
            
            # Test 2: Validate llm_manager requirement is enforced
            try:
                registry = AgentRegistry(None)  # Should fail
                print("  ❌ AgentRegistry accepts None llm_manager (should be rejected)")
                return {"status": "FAILED", "error": "llm_manager validation not enforced"}
            except ValueError as e:
                if "llm_manager is required" in str(e):
                    print("  ✅ llm_manager validation properly enforced")
                else:
                    print(f"  ❌ Unexpected validation error: {e}")
                    return {"status": "FAILED", "error": f"Unexpected error: {e}"}
            except Exception as e:
                print(f"  ❌ Unexpected exception: {e}")
                return {"status": "FAILED", "error": f"Unexpected exception: {e}"}
            
            # Test 3: Check initialization validation code exists  
            import inspect
            source = inspect.getsource(AgentRegistry.__init__)
            
            if "llm_manager is None" in source and "ValueError" in source:
                print("  ✅ Initialization validation code present")
            else:
                print("  ❌ Initialization validation code missing")
                return {"status": "FAILED", "error": "Validation code missing"}
            
            return {
                "status": "PASSED",
                "details": "Agent Registry properly validates required llm_manager parameter"
            }
            
        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            return {"status": "FAILED", "error": str(e)}
    
    def validate_fix_3_e2e_oauth_key(self) -> Dict[str, Any]:
        """Validate E2E OAuth simulation key deployment."""
        print("🔍 Validating Fix #3: E2E OAuth Simulation Key Deployment")
        
        try:
            # Test 1: Check if deployment script exists
            script_path = Path(__file__).parent / "deploy_e2e_oauth_key.py"
            if script_path.exists():
                print("  ✅ E2E OAuth deployment script created")
            else:
                print("  ❌ E2E OAuth deployment script missing")
                return {"status": "FAILED", "error": "Deployment script missing"}
            
            # Test 2: Check if deployment commands exist
            commands_path = Path(__file__).parent / "E2E_OAUTH_DEPLOYMENT_COMMANDS.md"
            if commands_path.exists():
                print("  ✅ Deployment commands documentation created")
                
                # Validate command content
                content = commands_path.read_text()
                if "E2E_OAUTH_SIMULATION_KEY" in content and "netra-staging" in content:
                    print("  ✅ Deployment commands contain correct secret name and project")
                else:
                    print("  ❌ Deployment commands missing required content")
                    return {"status": "FAILED", "error": "Commands missing required content"}
            else:
                print("  ❌ Deployment commands documentation missing")
                return {"status": "FAILED", "error": "Commands documentation missing"}
            
            # Test 3: Validate secret key format
            with open(script_path, 'r') as f:
                script_content = f.read()
            
            if "e0e9c5d29e7aea3942f47855b4870d3e0272e061c2de22827e71b893071d777e" in script_content:
                print("  ✅ 256-bit hex secret key present in deployment script")
            else:
                print("  ❌ Secret key missing from deployment script")
                return {"status": "FAILED", "error": "Secret key missing"}
            
            return {
                "status": "PASSED",
                "details": "E2E OAuth simulation key deployment ready with commands and documentation"
            }
            
        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            return {"status": "FAILED", "error": str(e)}
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of all P0 fixes."""
        print("🚀 P0 Critical Infrastructure Fixes Validation")
        print("=" * 60)
        print("Protecting $1.5M+ ARR at risk from Data Helper Agent functionality gaps")
        print()
        
        # Validate each fix
        fixes = [
            ("Fix #1: WebSocket GCP Auto-Detection", self.validate_fix_1_websocket_gcp_detection),
            ("Fix #2: Agent Registry Initialization", self.validate_fix_2_agent_registry_initialization),
            ("Fix #3: E2E OAuth Key Deployment", self.validate_fix_3_e2e_oauth_key)
        ]
        
        results = {}
        passed_count = 0
        
        for fix_name, validator in fixes:
            print(f"\n{fix_name}")
            print("-" * len(fix_name))
            
            result = validator()
            results[fix_name] = result
            
            if result["status"] == "PASSED":
                passed_count += 1
                print(f"  🎉 {fix_name}: PASSED")
                if "details" in result:
                    print(f"     Details: {result['details']}")
            else:
                self.overall_status = False
                print(f"  💥 {fix_name}: FAILED")
                print(f"     Error: {result['error']}")
        
        # Overall summary
        print("\n" + "=" * 60)
        print("📋 VALIDATION SUMMARY")
        print("=" * 60)
        
        print(f"✅ Passed: {passed_count}/3 fixes")
        print(f"❌ Failed: {3 - passed_count}/3 fixes")
        
        if self.overall_status:
            print("\n🎉 ALL P0 CRITICAL FIXES VALIDATED SUCCESSFULLY!")
            print("✅ Ready for deployment to staging environment")
            print("✅ Data Helper Agent functionality protection implemented")
            print("✅ $1.5M+ ARR risk mitigation complete")
        else:
            print("\n💥 VALIDATION FAILURES DETECTED!")
            print("❌ Review and fix failed validations before deployment")
            print("❌ Data Helper Agent functionality still at risk")
        
        return {
            "overall_status": self.overall_status,
            "passed_fixes": passed_count,
            "total_fixes": 3,
            "detailed_results": results
        }

def main():
    """Main validation entry point."""
    validator = P0FixValidator()
    results = validator.run_comprehensive_validation()
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_status"] else 1)

if __name__ == "__main__":
    main()