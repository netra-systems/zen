#!/usr/bin/env python3
"""
Test script for the adaptive workflow with data helper.
Tests different data sufficiency scenarios locally.
"""

import asyncio
import json
from typing import Dict, Any
import aiohttp
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment


class AdaptiveWorkflowTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.token = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self):
        """Check if the API is healthy."""
        async with self.session.get(f"{self.base_url}/health") as response:
            data = await response.json()
            print(f"[U+2713] Health check: {data}")
            return response.status == 200
    
    async def test_workflow(self, scenario: str, user_request: str, expected_sufficiency: str):
        """Test a specific workflow scenario."""
        print(f"\n{'='*60}")
        print(f"Testing Scenario: {scenario}")
        print(f"Expected Data Sufficiency: {expected_sufficiency}")
        print(f"User Request: {user_request}")
        print(f"{'='*60}")
        
        # Create a thread for the test
        thread_payload = {
            "user_prompt": user_request,
            "metadata": {
                "test_scenario": scenario,
                "expected_sufficiency": expected_sufficiency,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Test with the threads endpoint
        try:
            async with self.session.post(
                f"{self.base_url}/api/threads",
                json=thread_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"[U+2713] Thread created: {json.dumps(result, indent=2)}")
                    return result
                else:
                    error_text = await response.text()
                    print(f"[U+2717] Failed to create thread: {response.status}")
                    print(f"  Error: {error_text}")
                    return None
        except Exception as e:
            print(f"[U+2717] Error testing workflow: {e}")
            return None
    
    async def run_all_tests(self):
        """Run all test scenarios."""
        print("\n" + "="*70)
        print("ADAPTIVE WORKFLOW TEST SUITE")
        print("="*70)
        
        # First check health
        if not await self.health_check():
            print("[U+2717] API is not healthy. Exiting.")
            return
        
        # Test scenarios
        scenarios = [
            {
                "name": "Sufficient Data",
                "request": "I have a chatbot using GPT-4 serving 10,000 requests daily. "
                           "Average latency is 800ms, cost per request is $0.05. "
                           "Peak hours are 9-11 AM and 2-4 PM. "
                           "Quality score is 4.2/5. "
                           "How can I optimize this?",
                "expected": "sufficient"
            },
            {
                "name": "Partial Data",
                "request": "We're using LLMs for customer service with about 5000 daily requests. "
                           "Response times feel slow. "
                           "Need to reduce costs but maintain quality. "
                           "What optimizations do you recommend?",
                "expected": "partial"
            },
            {
                "name": "Insufficient Data",
                "request": "Help me optimize my AI workload",
                "expected": "insufficient"
            }
        ]
        
        results = []
        for scenario in scenarios:
            result = await self.test_workflow(
                scenario["name"],
                scenario["request"],
                scenario["expected"]
            )
            results.append({
                "scenario": scenario["name"],
                "expected": scenario["expected"],
                "result": result
            })
            
            # Wait a bit between tests
            await asyncio.sleep(2)
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        for r in results:
            status = "[U+2713]" if r["result"] else "[U+2717]"
            print(f"{status} {r['scenario']}: Expected {r['expected']}")
            if r["result"] and "thread_id" in r["result"]:
                print(f"  Thread ID: {r['result']['thread_id']}")
        
        return results


async def main():
    """Main test function."""
    async with AdaptiveWorkflowTester() as tester:
        results = await tester.run_all_tests()
        
        # Print final status
        success_count = sum(1 for r in results if r["result"])
        total_count = len(results)
        
        print(f"\n{'='*70}")
        print(f"FINAL RESULT: {success_count}/{total_count} tests completed")
        print(f"{'='*70}")


if __name__ == "__main__":
    print("Starting Adaptive Workflow Tests...")
    asyncio.run(main())