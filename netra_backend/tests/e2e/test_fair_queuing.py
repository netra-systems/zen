"""
Fair Queuing Mechanism Tests
Tests fair queuing of requests under load.
Maximum 300 lines, functions ≤8 lines.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time

import aiohttp
import pytest

# Add project root to path
from tests.e2e.concurrent_load_helpers import (
    # Add project root to path
    ConcurrentUserLoadTest,
    create_priority_user_request,
    validate_fair_queuing_results,
)


class TestFairQueuing:
    """Test fair queuing mechanism"""
    
    async def test_fair_queuing_mechanism(self):
        """Validate fair queuing of requests under load"""
        tester = ConcurrentUserLoadTest()
        results = await self.test_fair_queuing(tester)
        
        assert results['priority_respected'], "Priority queuing not working"
        assert results['starvation_prevented'], "Some users were starved of resources"
        assert results['fair_queuing'], "Queuing mechanism is not fair"
    
    async def test_fair_queuing(self, tester) -> dict:
        """Test fair queuing mechanism under load"""
        tasks = []
        
        for i in range(10):
            user_id = tester.generate_user_id()
            request = create_priority_user_request('high', user_id)
            task = asyncio.create_task(self.create_priority_user(request))
            tasks.append(task)
        
        for i in range(20):
            user_id = tester.generate_user_id()
            request = create_priority_user_request('normal', user_id)
            task = asyncio.create_task(self.create_priority_user(request))
            tasks.append(task)
        
        results_list = await asyncio.gather(*tasks)
        return validate_fair_queuing_results(results_list)
    
    async def create_priority_user(self, request: dict) -> dict:
        """Create priority user request"""
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ConcurrentUserLoadTest.BASE_URL}/api/demo/process",
                json=request['json_data'],
                headers=request['headers']
            ) as response:
                wait_time = time.time() - start_time
                return {
                    'user_id': request['user_id'],
                    'priority': request['priority'],
                    'wait_time': wait_time,
                    'status': response.status
                }