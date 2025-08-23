#!/usr/bin/env python3
"""
End-to-End AI Processing Flow Test

This script validates the complete AI processing pipeline:
1. Thread creation
2. Message processing through agent system
3. LLM API integration
4. Response delivery

Critical validation for user AI interactions.
"""

import asyncio
import json
import sys
import time
from typing import Any, Dict, Optional

import aiohttp
import requests
from pydantic import BaseModel


class E2ETestResult(BaseModel):
    """End-to-end test result."""
    test_name: str
    success: bool
    duration_ms: float
    details: Dict[str, Any]
    error: Optional[str] = None


class NetraAPITester:
    """Tester for Netra AI processing flow."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> E2ETestResult:
        """Check if the backend is running."""
        start_time = time.time()
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    duration = (time.time() - start_time) * 1000
                    return E2ETestResult(
                        test_name="health_check",
                        success=True,
                        duration_ms=duration,
                        details={"status": data.get("status", "unknown")}
                    )
                else:
                    duration = (time.time() - start_time) * 1000
                    return E2ETestResult(
                        test_name="health_check",
                        success=False,
                        duration_ms=duration,
                        details={"status_code": response.status},
                        error=f"Health check failed with status {response.status}"
                    )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return E2ETestResult(
                test_name="health_check",
                success=False,
                duration_ms=duration,
                details={},
                error=f"Health check error: {str(e)}"
            )
    
    async def create_thread(self) -> E2ETestResult:
        """Create a new thread."""
        start_time = time.time()
        try:
            payload = {"title": "E2E Test Thread", "metadata": {"test": True}}
            async with self.session.post(
                f"{self.base_url}/api/threads/", 
                json=payload,
                headers={"Authorization": "Bearer dev-test-token"}
            ) as response:
                duration = (time.time() - start_time) * 1000
                if response.status == 201:
                    data = await response.json()
                    return E2ETestResult(
                        test_name="create_thread",
                        success=True,
                        duration_ms=duration,
                        details={"thread_id": data.get("id"), "title": data.get("title")}
                    )
                else:
                    error_text = await response.text()
                    return E2ETestResult(
                        test_name="create_thread",
                        success=False,
                        duration_ms=duration,
                        details={"status_code": response.status},
                        error=f"Thread creation failed: {error_text}"
                    )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return E2ETestResult(
                test_name="create_thread",
                success=False,
                duration_ms=duration,
                details={},
                error=f"Thread creation error: {str(e)}"
            )
    
    async def send_message_to_agent(self, thread_id: str, message: str) -> E2ETestResult:
        """Send a message to the agent system."""
        start_time = time.time()
        try:
            payload = {"message": message, "thread_id": thread_id}
            async with self.session.post(
                f"{self.base_url}/agent/message",
                json=payload,
                headers={"Authorization": "Bearer dev-test-token"}
            ) as response:
                duration = (time.time() - start_time) * 1000
                if response.status == 200:
                    data = await response.json()
                    return E2ETestResult(
                        test_name="send_message",
                        success=True,
                        duration_ms=duration,
                        details={
                            "response_type": type(data).__name__,
                            "has_response": bool(data.get("response")),
                            "agent_used": data.get("agent", "unknown")
                        }
                    )
                else:
                    error_text = await response.text()
                    return E2ETestResult(
                        test_name="send_message",
                        success=False,
                        duration_ms=duration,
                        details={"status_code": response.status},
                        error=f"Message sending failed: {error_text}"
                    )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return E2ETestResult(
                test_name="send_message",
                success=False,
                duration_ms=duration,
                details={},
                error=f"Message sending error: {str(e)}"
            )
    
    async def test_llm_directly(self) -> E2ETestResult:
        """Test LLM API directly through internal endpoint."""
        start_time = time.time()
        try:
            # Try to access LLM health check or configuration endpoint
            async with self.session.get(f"{self.base_url}/api/llm/health") as response:
                duration = (time.time() - start_time) * 1000
                if response.status == 200:
                    data = await response.json()
                    return E2ETestResult(
                        test_name="llm_health",
                        success=True,
                        duration_ms=duration,
                        details={"llm_status": data}
                    )
                else:
                    return E2ETestResult(
                        test_name="llm_health",
                        success=False,
                        duration_ms=duration,
                        details={"status_code": response.status},
                        error=f"LLM health check failed with status {response.status}"
                    )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return E2ETestResult(
                test_name="llm_health",
                success=False,
                duration_ms=duration,
                details={},
                error=f"LLM health check error: {str(e)}"
            )


async def run_e2e_tests():
    """Run the complete end-to-end test suite."""
    print("Starting End-to-End AI Processing Flow Tests")
    print("=" * 60)
    
    results = []
    
    async with NetraAPITester() as tester:
        # Test 1: Health Check
        print("1. Testing backend health...")
        health_result = await tester.health_check()
        results.append(health_result)
        
        if health_result.success:
            print(f"   PASS Backend is running ({health_result.duration_ms:.1f}ms)")
        else:
            print(f"   FAIL Backend health check failed: {health_result.error}")
            print("   STOP Cannot proceed with further tests")
            return results
        
        # Test 2: LLM Health
        print("2. Testing LLM integration...")
        llm_result = await tester.test_llm_directly()
        results.append(llm_result)
        
        if llm_result.success:
            print(f"   PASS LLM system is accessible ({llm_result.duration_ms:.1f}ms)")
        else:
            print(f"   WARN LLM health check failed: {llm_result.error}")
            print("   NOTE LLM might still work through agent system")
        
        # Test 3: Thread Creation
        print("3. Creating test thread...")
        thread_result = await tester.create_thread()
        results.append(thread_result)
        
        if thread_result.success:
            thread_id = thread_result.details.get("thread_id")
            print(f"   PASS Thread created: {thread_id} ({thread_result.duration_ms:.1f}ms)")
        else:
            print(f"   FAIL Thread creation failed: {thread_result.error}")
            print("   STOP Cannot test message processing without thread")
            return results
        
        # Test 4: Message Processing
        print("4. Testing AI message processing...")
        test_message = "Hello! Can you help me test the AI system? Please respond with a simple greeting."
        message_result = await tester.send_message_to_agent(thread_id, test_message)
        results.append(message_result)
        
        if message_result.success:
            print(f"   PASS Message processed successfully ({message_result.duration_ms:.1f}ms)")
            print(f"   INFO Agent: {message_result.details.get('agent_used', 'unknown')}")
            print(f"   INFO Has response: {message_result.details.get('has_response', False)}")
        else:
            print(f"   FAIL Message processing failed: {message_result.error}")
    
    return results


def print_summary(results: list[E2ETestResult]):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("END-TO-END TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.success)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\nDetailed Results:")
    for result in results:
        status = "PASS" if result.success else "FAIL"
        print(f"  {status} {result.test_name:15} ({result.duration_ms:6.1f}ms)")
        if result.error:
            print(f"       Error: {result.error}")
    
    # Critical flow analysis
    print("\nCRITICAL FLOW ANALYSIS:")
    
    # Check if core AI pipeline is working
    health_ok = any(r.test_name == "health_check" and r.success for r in results)
    thread_ok = any(r.test_name == "create_thread" and r.success for r in results)
    message_ok = any(r.test_name == "send_message" and r.success for r in results)
    
    if health_ok and thread_ok and message_ok:
        print("PASS CORE AI PIPELINE: FUNCTIONAL")
        print("   Users can create threads and send messages to AI agents")
    else:
        print("FAIL CORE AI PIPELINE: BROKEN")
        if not health_ok:
            print("   ERROR Backend is not running")
        if not thread_ok:
            print("   ERROR Cannot create threads")
        if not message_ok:
            print("   ERROR Cannot process AI messages")
    
    return passed_tests == total_tests


def main():
    """Main function."""
    try:
        all_passed = asyncio.run(main_async())
        sys.exit(0 if all_passed else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        sys.exit(1)


async def main_async():
    """Async main function."""
    results = await run_e2e_tests()
    return print_summary(results)


if __name__ == "__main__":
    main()