"""
Concurrent User Load Test Helpers
Shared utilities for concurrent user load testing.
Maximum 300 lines, functions  <= 8 lines.
"""

import asyncio
import json
import random
import statistics
import string
import time
from datetime import datetime
from typing import Any, Dict, List

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
    
    def _get_random_industry(self) -> str:
        """Get random industry for testing."""
        industries = ['Financial Services', 'Healthcare', 'Technology', 'E-commerce']
        return random.choice(industries)
    
    def _create_base_session_fields(self, user_id: str) -> Dict[str, Any]:
        """Create base session fields."""
        return {
            'user_id': user_id,
            'auth_token': f"token_{user_id}",
            'industry': self._get_random_industry(),
            'start_time': datetime.now()
        }
    
    def _create_tracking_fields(self) -> Dict[str, Any]:
        """Create session tracking fields."""
        return {
            'messages_sent': 0,
            'errors': [],
            'response_times': []
        }
    
    def _create_session_data(self, user_id: str) -> Dict[str, Any]:
        """Create session data structure."""
        base_fields = self._create_base_session_fields(user_id)
        tracking_fields = self._create_tracking_fields()
        return {**base_fields, **tracking_fields}
    
    async def create_user_session(self, user_id: str) -> Dict[str, Any]:
        """Create a new user session"""
        session = self._create_session_data(user_id)
        self.user_sessions[user_id] = session
        return session
    
    async def load_demo_page(self, session, results):
        """Load demo page step."""
        start_time = time.time()
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{self.BASE_URL}/demo") as response:
                if response.status == 200:
                    results['completed_steps'].append('demo_page_loaded')
                results['response_times'].append(time.time() - start_time)
    
    def _create_industry_payload(self, session) -> tuple:
        """Create industry selection payload."""
        return (
            {'industry': session['industry']},
            {'Authorization': f"Bearer {session['auth_token']}"}
        )
    
    async def _post_industry_selection(self, json_data, headers, results, start_time):
        """Post industry selection request."""
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(f"{self.BASE_URL}/api/demo/select-industry", json=json_data, headers=headers) as response:
                if response.status == 200:
                    results['completed_steps'].append('industry_selected')
                results['response_times'].append(time.time() - start_time)
    
    async def select_industry(self, session, results):
        """Select industry step."""
        start_time = time.time()
        json_data, headers = self._create_industry_payload(session)
        await self._post_industry_selection(json_data, headers, results, start_time)
    
    async def _connect_websocket(self, session, results, ws_start_time):
        """Handle WebSocket connection."""
        ws_url = f"{self.WS_URL}/{session['user_id']}"
        headers = {'Authorization': f"Bearer {session['auth_token']}"}
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            results['response_times'].append(time.time() - ws_start_time)
            results['completed_steps'].append('websocket_connected')
            await self.send_chat_messages(websocket, session, results)
    
    def _handle_websocket_errors(self, e, results):
        """Handle WebSocket connection errors."""
        if isinstance(e, websockets.exceptions.WebSocketException):
            results['errors'].append(f"WebSocket error: {str(e)}")
        elif isinstance(e, asyncio.TimeoutError):
            results['errors'].append("WebSocket response timeout")
    
    async def handle_websocket_interaction(self, session, results):
        """Handle WebSocket connection and chat interaction."""
        ws_start_time = time.time()
        try:
            await self._connect_websocket(session, results, ws_start_time)
        except (websockets.exceptions.WebSocketException, asyncio.TimeoutError) as e:
            self._handle_websocket_errors(e, results)
    
    def _get_chat_messages(self) -> List[str]:
        """Get predefined chat messages for testing."""
        return [
            "Analyze my current AI workload",
            "What optimization opportunities exist?",
            "Calculate potential cost savings"
        ]
    
    def _create_chat_message(self, content: str, user_id: str) -> str:
        """Create formatted chat message."""
        return json.dumps({
            'type': 'message',
            'content': content,
            'user_id': user_id
        })
    
    async def _send_single_message(self, websocket, message: str, session, results):
        """Send single message and record response time."""
        msg_start_time = time.time()
        formatted_msg = self._create_chat_message(message, session['user_id'])
        await websocket.send(formatted_msg)
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        results['response_times'].append(time.time() - msg_start_time)
        session['messages_sent'] += 1
    
    async def send_chat_messages(self, websocket, session, results):
        """Send chat messages through WebSocket."""
        messages = self._get_chat_messages()
        for message in messages:
            await self._send_single_message(websocket, message, session, results)
        results['completed_steps'].append('chat_interaction_complete')
    
    def _get_roi_data(self, session) -> Dict[str, Any]:
        """Get ROI calculation data."""
        return {
            'monthly_spend': 100000,
            'request_volume': 10000000,
            'industry': session['industry']
        }
    
    def _create_roi_payload(self, session) -> tuple:
        """Create ROI calculation payload."""
        json_data = self._get_roi_data(session)
        headers = {'Authorization': f"Bearer {session['auth_token']}"}
        return json_data, headers
    
    async def _post_roi_calculation(self, json_data, headers, results, start_time):
        """Post ROI calculation request."""
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(f"{self.BASE_URL}/api/demo/calculate-roi", json=json_data, headers=headers) as response:
                if response.status == 200:
                    results['completed_steps'].append('roi_calculated')
                results['response_times'].append(time.time() - start_time)
    
    async def calculate_roi(self, session, results):
        """Request ROI calculation step."""
        roi_start_time = time.time()
        json_data, headers = self._create_roi_payload(session)
        await self._post_roi_calculation(json_data, headers, results, roi_start_time)
    
    def _create_report_payload(self, session) -> tuple:
        """Create report generation payload."""
        json_data = {'user_id': session['user_id']}
        headers = {'Authorization': f"Bearer {session['auth_token']}"}
        return json_data, headers
    
    async def _post_report_generation(self, session, results, start_time):
        """Post report generation request."""
        json_data, headers = self._create_report_payload(session)
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(f"{self.BASE_URL}/api/demo/generate-report", json=json_data, headers=headers) as response:
                if response.status == 200:
                    results['completed_steps'].append('report_generated')
                results['response_times'].append(time.time() - start_time)
    
    async def generate_report(self, session, results):
        """Generate report step."""
        report_start_time = time.time()
        await self._post_report_generation(session, results, report_start_time)
    
    def _get_default_result_values(self) -> Dict[str, Any]:
        """Get default values for user results."""
        return {
            'success': False,
            'response_times': [],
            'errors': [],
            'completed_steps': []
        }
    
    def _create_user_results(self, user_id: str) -> Dict[str, Any]:
        """Create initial user results structure."""
        defaults = self._get_default_result_values()
        return {'user_id': user_id, **defaults}
    
    async def _execute_demo_journey(self, session, results):
        """Execute complete demo journey steps."""
        await self.load_demo_page(session, results)
        await self.select_industry(session, results)
        await self.handle_websocket_interaction(session, results)
        await self.calculate_roi(session, results)
        await self.generate_report(session, results)
    
    def _evaluate_journey_success(self, results):
        """Evaluate if demo journey was successful."""
        if len(results['completed_steps']) >= 5:
            results['success'] = True
            self.success_count += 1
    
    def _handle_journey_error(self, e: Exception, results):
        """Handle demo journey errors."""
        results['errors'].append(f"Unexpected error: {str(e)}")
        self.error_count += 1
    
    def _process_journey_results(self, results):
        """Process journey results and update metrics."""
        self.response_times.extend(results['response_times'])
    
    async def _run_demo_journey(self, session, results):
        """Run demo journey with error handling."""
        try:
            await self._execute_demo_journey(session, results)
            self._evaluate_journey_success(results)
        except Exception as e:
            self._handle_journey_error(e, results)
    
    async def simulate_demo_user(self, user_id: str) -> Dict[str, Any]:
        """Simulate a complete demo user journey"""
        session = await self.create_user_session(user_id)
        results = self._create_user_results(user_id)
        await self._run_demo_journey(session, results)
        self._process_journey_results(results)
        return results
    
    async def _create_single_user_task(self) -> asyncio.Task:
        """Create single user simulation task."""
        user_id = self.generate_user_id()
        await asyncio.sleep(random.uniform(0, 0.5))
        return asyncio.create_task(self.simulate_demo_user(user_id))
    
    async def _create_user_tasks(self, num_users: int) -> List:
        """Create user simulation tasks."""
        tasks = []
        for i in range(num_users):
            task = await self._create_single_user_task()
            tasks.append(task)
        return tasks
    
    async def run_concurrent_users(self, num_users: int) -> Dict[str, Any]:
        """Run multiple concurrent users"""
        start_time = time.time()
        tasks = await self._create_user_tasks(num_users)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self.calculate_load_statistics(results, num_users, start_time)
    
    def _categorize_results(self, results) -> tuple:
        """Categorize test results."""
        successful = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed = [r for r in results if isinstance(r, dict) and not r.get('success')]
        exceptions = [r for r in results if isinstance(r, Exception)]
        return successful, failed, exceptions
    
    def _calculate_response_metrics(self) -> Dict[str, float]:
        """Calculate response time metrics."""
        return {
            'avg_response_time': statistics.mean(self.response_times) if self.response_times else 0,
            'p95_response_time': self.calculate_percentile(95),
            'p99_response_time': self.calculate_percentile(99)
        }
    
    def _get_user_counts(self, successful, failed, exceptions):
        """Get user count statistics."""
        return {
            'successful_users': len(successful),
            'failed_users': len(failed),
            'exceptions': len(exceptions)
        }
    
    def _get_basic_fields(self, num_users, successful, total_time):
        """Get basic statistic fields."""
        return {
            'total_users': num_users,
            'total_time': total_time,
            'success_rate': len(successful) / num_users * 100
        }
    
    def _create_basic_stats(self, num_users, successful, failed, exceptions, total_time):
        """Create basic statistics."""
        counts = self._get_user_counts(successful, failed, exceptions)
        basic = self._get_basic_fields(num_users, successful, total_time)
        return {**basic, **counts}
    
    def _create_statistics_dict(self, num_users, successful, failed, exceptions, total_time, metrics):
        """Create statistics dictionary."""
        basic_stats = self._create_basic_stats(num_users, successful, failed, exceptions, total_time)
        return {**basic_stats, **metrics}
    
    def calculate_load_statistics(self, results, num_users, start_time):
        """Calculate load test statistics."""
        total_time = time.time() - start_time
        successful, failed, exceptions = self._categorize_results(results)
        metrics = self._calculate_response_metrics()
        return self._create_statistics_dict(num_users, successful, failed, exceptions, total_time, metrics)
    
    def calculate_percentile(self, percentile: int) -> float:
        """Calculate response time percentile."""
        if not self.response_times:
            return 0
        
        if len(self.response_times) > percentile:
            return statistics.quantiles(self.response_times, n=100)[percentile-1]
        else:
            return max(self.response_times)

def _create_priority_headers(user_id: str, priority: str) -> Dict[str, str]:
    """Create priority request headers."""
    return {
        'Authorization': f"Bearer token_{user_id}",
        'X-Priority': priority
    }

def create_priority_user_request(priority: str, user_id: str):
    """Create priority user request for fair queuing test."""
    return {
        'user_id': user_id,
        'priority': priority,
        'headers': _create_priority_headers(user_id, priority),
        'json_data': {'user_id': user_id, 'priority': priority}
    }

def _extract_priority_times(results_list: List[Dict]) -> tuple:
    """Extract wait times by priority level."""
    high_priority_times = [r['wait_time'] for r in results_list if r['priority'] == 'high']
    normal_times = [r['wait_time'] for r in results_list if r['priority'] == 'normal']
    return high_priority_times, normal_times

def _create_validation_structure() -> Dict[str, bool]:
    """Create initial validation structure."""
    return {
        'priority_respected': False,
        'starvation_prevented': False,
        'fair_queuing': False
    }

def _check_priority_respected(high_times: List[float], normal_times: List[float]) -> bool:
    """Check if priority ordering is respected."""
    if not (high_times and normal_times):
        return False
    avg_high = statistics.mean(high_times)
    avg_normal = statistics.mean(normal_times)
    return avg_high < avg_normal

def _check_starvation_prevented(results_list: List[Dict]) -> bool:
    """Check if starvation was prevented."""
    return all(r['status'] in [200, 201] for r in results_list)

def _check_fair_queuing(results_list: List[Dict]) -> bool:
    """Check fair queuing implementation."""
    max_wait = max(r['wait_time'] for r in results_list)
    return max_wait < 30

def validate_fair_queuing_results(results_list: List[Dict]) -> Dict[str, bool]:
    """Validate fair queuing mechanism results."""
    high_times, normal_times = _extract_priority_times(results_list)
    validation = _create_validation_structure()
    validation['priority_respected'] = _check_priority_respected(high_times, normal_times)
    validation['starvation_prevented'] = _check_starvation_prevented(results_list)
    validation['fair_queuing'] = _check_fair_queuing(results_list)
    return validation

def _analyze_connection_metrics(connections: List[int]) -> tuple:
    """Analyze connection status metrics."""
    connection_errors = sum(1 for c in connections if c == 503)
    successful = [c for c in connections if c == 200]
    return connection_errors, successful

def _create_analysis_structure() -> Dict[str, bool]:
    """Create initial analysis structure."""
    return {
        'pool_exhaustion_handled': False,
        'queue_mechanism_works': False,
        'graceful_degradation': False
    }

def _check_pool_exhaustion_handled(connection_errors: int, total_connections: int) -> bool:
    """Check if pool exhaustion was handled properly."""
    return 0 < connection_errors < total_connections

def _check_queue_mechanism(successful_count: int, total_connections: int) -> bool:
    """Check if queue mechanism is working."""
    return successful_count > total_connections // 2

def _check_graceful_degradation(connections: List[int]) -> bool:
    """Check if graceful degradation occurred."""
    return 200 in connections and 503 in connections

def analyze_pool_exhaustion_results(connections: List[int]) -> Dict[str, bool]:
    """Analyze resource pool exhaustion test results."""
    connection_errors, successful = _analyze_connection_metrics(connections)
    results = _create_analysis_structure()
    results['pool_exhaustion_handled'] = _check_pool_exhaustion_handled(connection_errors, len(connections))
    results['queue_mechanism_works'] = _check_queue_mechanism(len(successful), len(connections))
    results['graceful_degradation'] = _check_graceful_degradation(connections)
    return results