#!/usr/bin/env python3
"""Run all NACIS tests and verify system integrity.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Ensures NACIS system is working correctly.
"""

import subprocess
import sys
from pathlib import Path

# Add project root to path


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print(f"❌ {description} - FAILED")
        if result.stderr:
            print("Error:", result.stderr)
        if result.stdout:
            print("Output:", result.stdout)
        return False


def main():
    """Run all NACIS tests."""
    print("🚀 NACIS Test Suite Runner")
    print("="*60)
    
    tests = [
        ("python3 tests/chat_system/test_imports.py 2>/dev/null", 
         "Import Tests"),
        
        ("python3 -m pytest tests/chat_system/unit/test_chat_orchestrator.py -q",
         "Chat Orchestrator Unit Tests"),
        
        ("python3 -m pytest tests/chat_system/unit/test_reliability_scorer.py -q",
         "Reliability Scorer Unit Tests"),
        
        ("python3 -m pytest tests/chat_system/integration/test_orchestration_flow.py -q",
         "Integration Tests"),
        
        ("python3 -m pytest tests/chat_system/e2e/test_tco_analysis.py -q",
         "E2E TCO Analysis Tests"),
        
        ("python3 -m pytest tests/chat_system/security/test_guardrails.py -q",
         "Security Guardrails Tests"),
    ]
    
    results = []
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<40} {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print("="*60)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! NACIS system is ready.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())