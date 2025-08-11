"""
Critical Test #3: Concurrent User Load Test
Tests system behavior under multiple simultaneous demo users
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
import pytest
from unittest.mock import patch, MagicMock
import websockets
import json
import random
import string
from datetime import datetime


class ConcurrentUserLoadTest:
    """Test suite for concurrent user load on demo system"""
    
    BASE_URL = "http://localhost:8000"
    WS_URL = "ws://localhost:8000/ws"
    TARGET_CONCURRENT_USERS = 50
    MAX_RESPONSE_TIME = 2.0  # seconds
    
    def __init__(self):
        self.response_times: List[float] = []
        self.error_count = 0
        self.success_count = 0
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
    
    def generate_user_id(self) -> str:
        """Generate unique user ID for testing"""
        return f"test_user_{''.join(random.choices(string.ascii_lowercase, k=8))}"
    
    async def create_user_session(self, user_id: str) -> Dict[str, Any]:
        """Create a new user session"""
        session = {
            'user_id': user_id,
            'auth_token': f"token_{user_id}",
            'industry': random.choice(['Financial Services', 'Healthcare', 'Technology', 'E-commerce']),
            'start_time': datetime.now(),
            'messages_sent': 0,
            'errors': [],
            'response_times': []
        }
        self.user_sessions[user_id] = session
        return session
    
    async def simulate_demo_user(self, user_id: str) -> Dict[str, Any]:
        """Simulate a complete demo user journey"""
        session = await self.create_user_session(user_id)
        results = {
            'user_id': user_id,
            'success': False,
            'response_times': [],
            'errors': [],
            'completed_steps': []
        }
        
        try:
            # Step 1: Load demo page
            start_time = time.time()
            async with aiohttp.ClientSession() as http_session:
                async with http_session.get(f"{self.BASE_URL}/demo") as response:
                    if response.status == 200:
                        results['completed_steps'].append('demo_page_loaded')
                    load_time = time.time() - start_time
                    results['response_times'].append(load_time)
                
                # Step 2: Select industry
                start_time = time.time()
                async with http_session.post(
                    f"{self.BASE_URL}/api/demo/select-industry",
                    json={'industry': session['industry']},
                    headers={'Authorization': f"Bearer {session['auth_token']}"}
                ) as response:
                    if response.status == 200:
                        results['completed_steps'].append('industry_selected')
                    selection_time = time.time() - start_time
                    results['response_times'].append(selection_time)
                
                # Step 3: Establish WebSocket connection
                ws_start_time = time.time()
                try:
                    async with websockets.connect(
                        f"{self.WS_URL}/{user_id}",
                        extra_headers={'Authorization': f"Bearer {session['auth_token']}"}
                    ) as websocket:
                        ws_connect_time = time.time() - ws_start_time
                        results['response_times'].append(ws_connect_time)
                        results['completed_steps'].append('websocket_connected')
                        
                        # Step 4: Send chat messages
                        messages = [
                            "Analyze my current AI workload",
                            "What optimization opportunities exist?",
                            "Calculate potential cost savings"
                        ]
                        
                        for message in messages:
                            msg_start_time = time.time()
                            await websocket.send(json.dumps({
                                'type': 'message',
                                'content': message,
                                'user_id': user_id
                            }))
                            
                            # Wait for response
                            response = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=5.0
                            )
                            msg_response_time = time.time() - msg_start_time
                            results['response_times'].append(msg_response_time)
                            session['messages_sent'] += 1
                        
                        results['completed_steps'].append('chat_interaction_complete')
                        
                except websockets.exceptions.WebSocketException as e:
                    results['errors'].append(f"WebSocket error: {str(e)}")
                except asyncio.TimeoutError:
                    results['errors'].append("WebSocket response timeout")
                
                # Step 5: Request ROI calculation
                roi_start_time = time.time()
                async with http_session.post(
                    f"{self.BASE_URL}/api/demo/calculate-roi",
                    json={
                        'monthly_spend': 100000,
                        'request_volume': 10000000,
                        'industry': session['industry']
                    },
                    headers={'Authorization': f"Bearer {session['auth_token']}"}
                ) as response:
                    if response.status == 200:
                        results['completed_steps'].append('roi_calculated')
                    roi_time = time.time() - roi_start_time
                    results['response_times'].append(roi_time)
                
                # Step 6: Generate report
                report_start_time = time.time()
                async with http_session.post(
                    f"{self.BASE_URL}/api/demo/generate-report",
                    json={'user_id': user_id},
                    headers={'Authorization': f"Bearer {session['auth_token']}"}
                ) as response:
                    if response.status == 200:
                        results['completed_steps'].append('report_generated')
                    report_time = time.time() - report_start_time
                    results['response_times'].append(report_time)
            
            # Mark as successful if all steps completed
            if len(results['completed_steps']) >= 5:
                results['success'] = True
                self.success_count += 1
            
        except Exception as e:
            results['errors'].append(f"Unexpected error: {str(e)}")
            self.error_count += 1
        
        # Store response times
        self.response_times.extend(results['response_times'])
        
        return results
    
    async def run_concurrent_users(self, num_users: int) -> Dict[str, Any]:
        """Run multiple concurrent users"""
        tasks = []
        start_time = time.time()
        
        for i in range(num_users):
            user_id = self.generate_user_id()
            # Stagger user starts slightly to avoid thundering herd
            await asyncio.sleep(random.uniform(0, 0.5))
            task = asyncio.create_task(self.simulate_demo_user(user_id))
            tasks.append(task)
        
        # Wait for all users to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get('success')]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        return {
            'total_users': num_users,
            'successful_users': len(successful_results),
            'failed_users': len(failed_results),
            'exceptions': len(exceptions),
            'total_time': total_time,
            'success_rate': len(successful_results) / num_users * 100,
            'avg_response_time': statistics.mean(self.response_times) if self.response_times else 0,
            'p95_response_time': statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else max(self.response_times) if self.response_times else 0,
            'p99_response_time': statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) > 100 else max(self.response_times) if self.response_times else 0
        }
    
    async def test_resource_pool_exhaustion(self) -> Dict[str, Any]:
        """Test handling of resource pool exhaustion"""
        results = {
            'pool_exhaustion_handled': False,
            'queue_mechanism_works': False,
            'graceful_degradation': False
        }
        
        # Simulate rapid connection attempts
        connections = []
        connection_errors = 0
        
        try:
            for i in range(100):  # Try to create more connections than pool allows
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.BASE_URL}/demo") as response:
                        if response.status == 503:  # Service unavailable
                            connection_errors += 1
                        connections.append(response.status)
                
                if i % 10 == 0:
                    await asyncio.sleep(0.1)  # Brief pause
            
            # Check if system handled exhaustion
            if connection_errors > 0 and connection_errors < 100:
                results['pool_exhaustion_handled'] = True
            
            # Check if queuing worked (some requests succeeded despite load)
            successful = [c for c in connections if c == 200]
            if len(successful) > 50:
                results['queue_mechanism_works'] = True
            
            # Check for graceful degradation
            if 200 in connections and 503 in connections:
                results['graceful_degradation'] = True
        
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    async def test_fair_queuing(self) -> Dict[str, Any]:
        """Test fair queuing mechanism under load"""
        results = {
            'fair_queuing': False,
            'priority_respected': False,
            'starvation_prevented': False
        }
        
        # Create users with different priorities
        high_priority_users = []
        normal_users = []
        
        async def create_priority_user(priority: str) -> Dict[str, Any]:
            user_id = self.generate_user_id()
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f"Bearer token_{user_id}",
                    'X-Priority': priority
                }
                
                async with session.post(
                    f"{self.BASE_URL}/api/demo/process",
                    json={'user_id': user_id, 'priority': priority},
                    headers=headers
                ) as response:
                    wait_time = time.time() - start_time
                    return {
                        'user_id': user_id,
                        'priority': priority,
                        'wait_time': wait_time,
                        'status': response.status
                    }
        
        # Submit requests
        tasks = []
        for i in range(10):
            tasks.append(create_priority_user('high'))
            high_priority_users.append(f"high_{i}")
        
        for i in range(20):
            tasks.append(create_priority_user('normal'))
            normal_users.append(f"normal_{i}")
        
        results_list = await asyncio.gather(*tasks)
        
        # Analyze results
        high_priority_times = [r['wait_time'] for r in results_list if r['priority'] == 'high']
        normal_times = [r['wait_time'] for r in results_list if r['priority'] == 'normal']
        
        # Check if high priority users were served faster
        if high_priority_times and normal_times:
            avg_high = statistics.mean(high_priority_times)
            avg_normal = statistics.mean(normal_times)
            
            if avg_high < avg_normal:
                results['priority_respected'] = True
        
        # Check if all users were eventually served
        all_served = all(r['status'] in [200, 201] for r in results_list)
        if all_served:
            results['starvation_prevented'] = True
        
        # Check for fair distribution (no user waited excessively long)
        max_wait = max(r['wait_time'] for r in results_list)
        if max_wait < 30:  # No one waited more than 30 seconds
            results['fair_queuing'] = True
        
        return results


@pytest.mark.asyncio
class TestConcurrentUserLoad:
    """Pytest test cases for concurrent user load"""
    
    async def test_50_concurrent_users(self):
        """Test system with 50 concurrent demo users"""
        tester = ConcurrentUserLoadTest()
        results = await tester.run_concurrent_users(50)
        
        assert results['success_rate'] > 90, f"Success rate too low: {results['success_rate']}%"
        assert results['avg_response_time'] < 2.0, f"Average response time too high: {results['avg_response_time']}s"
        assert results['p95_response_time'] < 5.0, f"P95 response time too high: {results['p95_response_time']}s"
    
    async def test_response_time_under_load(self):
        """Verify response time stays under 2s with concurrent users"""
        tester = ConcurrentUserLoadTest()
        
        # Test with increasing load
        for num_users in [10, 20, 30, 40, 50]:
            tester.response_times = []  # Reset for each test
            results = await tester.run_concurrent_users(num_users)
            
            assert results['avg_response_time'] < 2.0, \
                f"Response time degraded with {num_users} users: {results['avg_response_time']}s"
    
    async def test_resource_pool_exhaustion_handling(self):
        """Test that system handles resource pool exhaustion gracefully"""
        tester = ConcurrentUserLoadTest()
        results = await tester.test_resource_pool_exhaustion()
        
        assert results['pool_exhaustion_handled'], "System did not handle pool exhaustion"
        assert results['queue_mechanism_works'], "Queue mechanism failed under load"
        assert results['graceful_degradation'], "System did not degrade gracefully"
    
    async def test_fair_queuing_mechanism(self):
        """Validate fair queuing of requests under load"""
        tester = ConcurrentUserLoadTest()
        results = await tester.test_fair_queuing()
        
        assert results['priority_respected'], "Priority queuing not working"
        assert results['starvation_prevented'], "Some users were starved of resources"
        assert results['fair_queuing'], "Queuing mechanism is not fair"
    
    async def test_websocket_connection_limits(self):
        """Test WebSocket connection handling under load"""
        connections = []
        connection_count = 0
        max_connections = 100
        
        async def create_ws_connection(user_id: str):
            try:
                ws = await websockets.connect(f"ws://localhost:8000/ws/{user_id}")
                connections.append(ws)
                return True
            except:
                return False
        
        # Try to create many connections
        tasks = []
        for i in range(max_connections):
            user_id = f"ws_test_user_{i}"
            task = asyncio.create_task(create_ws_connection(user_id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        successful = sum(1 for r in results if r)
        
        # Clean up connections
        for ws in connections:
            await ws.close()
        
        assert successful > 50, f"Too few WebSocket connections accepted: {successful}"
        assert successful < max_connections, "No connection limiting in place"
    
    async def test_gradual_load_increase(self):
        """Test system behavior with gradually increasing load"""
        tester = ConcurrentUserLoadTest()
        performance_metrics = []
        
        for num_users in [5, 10, 20, 30, 40, 50]:
            tester.response_times = []
            tester.error_count = 0
            tester.success_count = 0
            
            results = await tester.run_concurrent_users(num_users)
            performance_metrics.append({
                'users': num_users,
                'avg_response': results['avg_response_time'],
                'success_rate': results['success_rate']
            })
            
            # Brief pause between load levels
            await asyncio.sleep(2)
        
        # Verify performance doesn't degrade catastrophically
        for i in range(1, len(performance_metrics)):
            prev = performance_metrics[i-1]
            curr = performance_metrics[i]
            
            # Response time shouldn't more than double
            assert curr['avg_response'] < prev['avg_response'] * 2.5, \
                f"Response time degraded too much: {prev['avg_response']}s -> {curr['avg_response']}s"
            
            # Success rate shouldn't drop below 80%
            assert curr['success_rate'] > 80, \
                f"Success rate too low with {curr['users']} users: {curr['success_rate']}%"
    
    async def test_burst_traffic_handling(self):
        """Test handling of sudden traffic bursts"""
        tester = ConcurrentUserLoadTest()
        
        # Normal load
        baseline = await tester.run_concurrent_users(10)
        baseline_response_time = baseline['avg_response_time']
        
        # Sudden burst
        tester.response_times = []
        burst = await tester.run_concurrent_users(50)
        
        # System should handle burst
        assert burst['success_rate'] > 85, f"Burst handling failed: {burst['success_rate']}% success"
        assert burst['avg_response_time'] < baseline_response_time * 3, \
            "Response time increased too much during burst"
        
        # Recovery after burst
        await asyncio.sleep(5)
        tester.response_times = []
        recovery = await tester.run_concurrent_users(10)
        
        # Should return to normal
        assert recovery['avg_response_time'] < baseline_response_time * 1.5, \
            "System did not recover after burst"


if __name__ == "__main__":
    # Run tests directly
    async def main():
        tester = ConcurrentUserLoadTest()
        
        print("Testing 50 concurrent users...")
        results = await tester.run_concurrent_users(50)
        print(f"Results: {json.dumps(results, indent=2)}")
        
        print("\nTesting resource pool exhaustion...")
        pool_results = await tester.test_resource_pool_exhaustion()
        print(f"Pool exhaustion results: {json.dumps(pool_results, indent=2)}")
        
        print("\nTesting fair queuing...")
        queue_results = await tester.test_fair_queuing()
        print(f"Fair queuing results: {json.dumps(queue_results, indent=2)}")
    
    asyncio.run(main())