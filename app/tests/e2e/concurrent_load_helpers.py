"""
Concurrent User Load Test Helpers
Shared utilities for concurrent user load testing.
Maximum 300 lines, functions ≤8 lines.
"""

import asyncio
import time
import statistics
import random
import string
import json
from typing import List, Dict, Any
from datetime import datetime
import aiohttp
import websockets


class ConcurrentUserLoadTest:
    """Test suite for concurrent user load on demo system"""
    
    BASE_URL = "http://localhost:8000"
    WS_URL = "ws://localhost:8000/ws"
    TARGET_CONCURRENT_USERS = 50
    MAX_RESPONSE_TIME = 2.0  # seconds
    
    def __init__(self):
        """Initialize load test instance."""
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
    
    async def load_demo_page(self, session, results):
        """Load demo page step."""
        start_time = time.time()
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{self.BASE_URL}/demo") as response:
                if response.status == 200:
                    results['completed_steps'].append('demo_page_loaded')
                load_time = time.time() - start_time
                results['response_times'].append(load_time)
    
    async def select_industry(self, session, results):
        """Select industry step."""
        start_time = time.time()
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                f"{self.BASE_URL}/api/demo/select-industry",
                json={'industry': session['industry']},
                headers={'Authorization': f"Bearer {session['auth_token']}"}
            ) as response:
                if response.status == 200:
                    results['completed_steps'].append('industry_selected')
                selection_time = time.time() - start_time
                results['response_times'].append(selection_time)
    
    async def handle_websocket_interaction(self, session, results):
        """Handle WebSocket connection and chat interaction."""
        ws_start_time = time.time()
        try:
            async with websockets.connect(
                f"{self.WS_URL}/{session['user_id']}",
                extra_headers={'Authorization': f"Bearer {session['auth_token']}"}
            ) as websocket:
                ws_connect_time = time.time() - ws_start_time
                results['response_times'].append(ws_connect_time)
                results['completed_steps'].append('websocket_connected')
                
                await self.send_chat_messages(websocket, session, results)
                
        except websockets.exceptions.WebSocketException as e:
            results['errors'].append(f"WebSocket error: {str(e)}")
        except asyncio.TimeoutError:
            results['errors'].append("WebSocket response timeout")
    
    async def send_chat_messages(self, websocket, session, results):
        """Send chat messages through WebSocket."""
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
                'user_id': session['user_id']
            }))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            msg_response_time = time.time() - msg_start_time
            results['response_times'].append(msg_response_time)
            session['messages_sent'] += 1
        
        results['completed_steps'].append('chat_interaction_complete')
    
    async def calculate_roi(self, session, results):
        """Request ROI calculation step."""
        roi_start_time = time.time()
        async with aiohttp.ClientSession() as http_session:
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
    
    async def generate_report(self, session, results):
        """Generate report step."""
        report_start_time = time.time()
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                f"{self.BASE_URL}/api/demo/generate-report",
                json={'user_id': session['user_id']},
                headers={'Authorization': f"Bearer {session['auth_token']}"}
            ) as response:
                if response.status == 200:
                    results['completed_steps'].append('report_generated')
                report_time = time.time() - report_start_time
                results['response_times'].append(report_time)
    
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
            await self.load_demo_page(session, results)
            await self.select_industry(session, results)
            await self.handle_websocket_interaction(session, results)
            await self.calculate_roi(session, results)
            await self.generate_report(session, results)
            
            if len(results['completed_steps']) >= 5:
                results['success'] = True
                self.success_count += 1
            
        except Exception as e:
            results['errors'].append(f"Unexpected error: {str(e)}")
            self.error_count += 1
        
        self.response_times.extend(results['response_times'])
        return results
    
    async def run_concurrent_users(self, num_users: int) -> Dict[str, Any]:
        """Run multiple concurrent users"""
        tasks = []
        start_time = time.time()
        
        for i in range(num_users):
            user_id = self.generate_user_id()
            await asyncio.sleep(random.uniform(0, 0.5))
            task = asyncio.create_task(self.simulate_demo_user(user_id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self.calculate_load_statistics(results, num_users, start_time)
    
    def calculate_load_statistics(self, results, num_users, start_time):
        """Calculate load test statistics."""
        total_time = time.time() - start_time
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
            'p95_response_time': self.calculate_percentile(95),
            'p99_response_time': self.calculate_percentile(99)
        }
    
    def calculate_percentile(self, percentile: int) -> float:
        """Calculate response time percentile."""
        if not self.response_times:
            return 0
        
        if len(self.response_times) > percentile:
            return statistics.quantiles(self.response_times, n=100)[percentile-1]
        else:
            return max(self.response_times)


def create_priority_user_request(priority: str, user_id: str):
    """Create priority user request for fair queuing test."""
    return {
        'user_id': user_id,
        'priority': priority,
        'headers': {
            'Authorization': f"Bearer token_{user_id}",
            'X-Priority': priority
        },
        'json_data': {'user_id': user_id, 'priority': priority}
    }


def validate_fair_queuing_results(results_list: List[Dict]) -> Dict[str, bool]:
    """Validate fair queuing mechanism results."""
    high_priority_times = [r['wait_time'] for r in results_list if r['priority'] == 'high']
    normal_times = [r['wait_time'] for r in results_list if r['priority'] == 'normal']
    
    validation = {
        'priority_respected': False,
        'starvation_prevented': False,
        'fair_queuing': False
    }
    
    if high_priority_times and normal_times:
        avg_high = statistics.mean(high_priority_times)
        avg_normal = statistics.mean(normal_times)
        if avg_high < avg_normal:
            validation['priority_respected'] = True
    
    all_served = all(r['status'] in [200, 201] for r in results_list)
    if all_served:
        validation['starvation_prevented'] = True
    
    max_wait = max(r['wait_time'] for r in results_list)
    if max_wait < 30:
        validation['fair_queuing'] = True
    
    return validation


def analyze_pool_exhaustion_results(connections: List[int]) -> Dict[str, bool]:
    """Analyze resource pool exhaustion test results."""
    connection_errors = sum(1 for c in connections if c == 503)
    successful = [c for c in connections if c == 200]
    
    results = {
        'pool_exhaustion_handled': False,
        'queue_mechanism_works': False,
        'graceful_degradation': False
    }
    
    if 0 < connection_errors < len(connections):
        results['pool_exhaustion_handled'] = True
    
    if len(successful) > len(connections) // 2:
        results['queue_mechanism_works'] = True
    
    if 200 in connections and 503 in connections:
        results['graceful_degradation'] = True
    
    return results