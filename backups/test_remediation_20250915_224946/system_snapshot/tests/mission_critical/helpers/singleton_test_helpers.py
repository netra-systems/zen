class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()
        \n'''
        Singleton Test Helpers - Utilities for validating singleton removal

        BUSINESS VALUE JUSTIFICATION:
        - Segment: Platform/Internal
        - Business Goal: Testing Infrastructure & Quality Assurance
        - Value Impact: Enables comprehensive validation of concurrent user isolation
        - Strategic Impact: Foundation for enterprise-grade concurrent user support

        These utilities provide comprehensive testing infrastructure for validating
        that singleton patterns have been properly removed and replaced with factory
        patterns that support concurrent user isolation.

        KEY CAPABILITIES:
        1. Concurrent User Context Generation
        2. State Isolation Verification
        3. WebSocket Event Capture and Analysis
        4. Memory Leak Detection
        5. Race Condition Detection
        6. Performance Degradation Measurement
        7. Factory Pattern Validation
        8. Data Leakage Detection
        '''

        import asyncio
        import time
        import uuid
        import gc
        import psutil
        import os
        import threading
        import random
        from typing import Dict, List, Optional, Set, Any, Tuple, Callable
        from dataclasses import dataclass, field
        from collections import defaultdict
        from datetime import datetime, timezone
        from concurrent.futures import ThreadPoolExecutor
        import weakref
        import inspect
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


        @dataclass
class MockUserContext:
        '''
        Comprehensive mock user context for isolation testing.

        Represents a complete user session with all the state that should
        be isolated between concurrent users.
        '''
    # Core identifiers
        user_id: str
        thread_id: str
        run_id: str
        session_id: str

    # Mock WebSocket connection
        websocket: Mock

    # User session data (should be isolated)
        session_data: Dict[str, Any] = field(default_factory=dict)
        private_data: Dict[str, Any] = field(default_factory=dict)
        user_secrets: Dict[str, str] = field(default_factory=dict)

    # Event tracking
        received_events: List[Dict[str, Any]] = field(default_factory=list)
        sent_messages: List[Dict[str, Any]] = field(default_factory=list)

    # Execution context
        execution_context: Optional[Dict[str, Any]] = None
        agent_runs: List[str] = field(default_factory=list)

    # Timestamps
        created_at: datetime = field(default_factory=lambda x: None datetime.now(timezone.utc))
        last_activity: datetime = field(default_factory=lambda x: None datetime.now(timezone.utc))

    # Component references (for singleton detection)
        component_references: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize mock WebSocket with proper async methods"""
        if not hasattr(self.websocket, 'send_json'):
        self.websocket.websocket = TestWebSocketConnection()
        if not hasattr(self.websocket, 'send_text'):
        self.websocket.websocket = TestWebSocketConnection()
        if not hasattr(self.websocket, 'close'):
        self.websocket.websocket = TestWebSocketConnection()
        if not hasattr(self.websocket, 'receive_json'):
        self.websocket.websocket = TestWebSocketConnection()

    def add_event(self, event: Dict[str, Any]) -> None:
        """Add received event to tracking"""
        event['received_at'] = datetime.now(timezone.utc).isoformat()
        self.received_events.append(event)
        self.last_activity = datetime.now(timezone.utc)

    def add_sent_message(self, message: Dict[str, Any]) -> None:
        """Add sent message to tracking"""
        message['sent_at'] = datetime.now(timezone.utc).isoformat()
        self.sent_messages.append(message)
        self.last_activity = datetime.now(timezone.utc)

    def store_component_reference(self, component_name: str, component: Any) -> None:
        """Store component reference for singleton detection"""
        self.component_references[component_name] = { )
        'instance': component,
        'instance_id': id(component),
        'type': type(component).__name__,
        'stored_at': datetime.now(timezone.utc)
    


        @dataclass
class IsolationTestResult:
        """Results from user isolation testing"""

    # Test parameters
        users_tested: int
        test_duration_seconds: float
        test_type: str

    # Isolation results
        successful_isolations: int
        failed_isolations: int
        isolation_success_rate: float

    # Data leakage detection
        data_leakage_incidents: List[Dict[str, Any]]
        shared_state_violations: List[Dict[str, Any]]
        cross_user_contamination: List[Dict[str, Any]]

    # Performance metrics
        performance_metrics: Dict[str, float]
        memory_usage_mb: float
        memory_growth_mb: float
        memory_per_user_mb: float

    # Concurrency issues
        race_conditions_detected: int
        deadlocks_detected: int
        timeout_errors: int

    # Component analysis
        singleton_components_detected: Dict[str, int]  # component_name -> unique_instance_count
        factory_violations: List[str]

    # Event routing analysis
        event_routing_errors: List[Dict[str, Any]]
        misdirected_events: int
        lost_events: int

        @property
    def is_isolated(self) -> bool:
        """Check if isolation was successful"""
        return ( )
        len(self.data_leakage_incidents) == 0 and
        len(self.shared_state_violations) == 0 and
        len(self.cross_user_contamination) == 0 and
        self.race_conditions_detected == 0 and
        all(count == self.users_tested for count in self.singleton_components_detected.values())
    

    def get_failure_summary(self) -> str:
        """Get human-readable failure summary"""
        if self.is_isolated:
        return " PASS:  Perfect isolation achieved"

        issues = []
        if self.data_leakage_incidents:
        issues.append("formatted_string")
        if self.shared_state_violations:
        issues.append("formatted_string")
        if self.cross_user_contamination:
        issues.append("formatted_string")
        if self.race_conditions_detected:
        issues.append("formatted_string")

        singleton_issues = [ )
        "formatted_string"
        for component, count in self.singleton_components_detected.items()
        if count < self.users_tested
                        
        if singleton_issues:
        issues.append("formatted_string")

        return "formatted_string"


class SingletonDetector:
        """Utility class for detecting singleton patterns in code"""

        @staticmethod
        def detect_singleton_instances( )
components: Dict[str, List[Any]]
) -> Dict[str, Tuple[int, List[int]]]:
'''
Detect singleton behavior by analyzing instance IDs.

Args:
components: Dict of component_name -> list of instances

Returns:
Dict of component_name -> (unique_count, list_of_instance_ids)
'''
singleton_analysis = {}

for component_name, instances in components.items():
instance_ids = [item for item in []]
unique_ids = list(set(instance_ids))

singleton_analysis[component_name] = (len(unique_ids), instance_ids)

return singleton_analysis

@staticmethod
def analyze_shared_references( )
user_contexts: List[MockUserContext]
) -> List[Dict[str, Any]]:
'''
Analyze component references to detect shared instances.

Args:
user_contexts: List of user contexts to analyze

Returns:
List of shared reference violations
'''
violations = []

            # Group component references by type
components_by_type = defaultdict(list)

for user_context in user_contexts:
for component_name, component_info in user_context.component_references.items():
components_by_type[component_name].append({ ))
'user_id': user_context.user_id,
'instance_id': component_info['instance_id'],
'instance': component_info['instance'],
'type': component_info['type']
                    

                    # Check for shared instances
for component_name, component_instances in components_by_type.items():
instance_ids = [ci['instance_id'] for ci in component_instances]
unique_ids = set(instance_ids)

if len(unique_ids) < len(component_instances):
                            # Found shared instances
shared_instances = defaultdict(list)
for ci in component_instances:
shared_instances[ci['instance_id']].append(ci['user_id'])

for instance_id, sharing_users in shared_instances.items():
if len(sharing_users) > 1:
violations.append({ ))
'type': 'shared_component_instance',
'component_name': component_name,
'instance_id': instance_id,
'sharing_users': sharing_users,
'user_count': len(sharing_users)
                                        

return violations

@staticmethod
def validate_factory_uniqueness( )
factory_func: Callable,
iterations: int = 10,
factory_args: Optional[Tuple] = None,
factory_kwargs: Optional[Dict] = None
) -> Tuple[bool, List[str], List[Any]]:
'''
Validate that a factory function returns unique instances.

Args:
factory_func: Factory function to test
iterations: Number of times to call the factory
factory_args: Arguments to pass to factory
factory_kwargs: Keyword arguments to pass to factory

Returns:
(is_unique, issues_list, instances_list)
'''
instances = []
issues = []
factory_args = factory_args or ()
factory_kwargs = factory_kwargs or {}

for i in range(iterations):
try:
if asyncio.iscoroutinefunction(factory_func):
                        # Handle async factories
loop = None
try:
loop = asyncio.get_running_loop()
except RuntimeError:
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

instance = loop.run_until_complete( )
factory_func(*factory_args, **factory_kwargs)
                                
else:
instance = factory_func(*factory_args, **factory_kwargs)

instances.append(instance)

except Exception as e:
issues.append("formatted_string")

if not instances:
return False, issues + ["No instances created"], []

                                            # Check for unique instances
instance_ids = [id(instance) for instance in instances]
unique_ids = set(instance_ids)

if len(unique_ids) != len(instances):
duplicate_count = len(instances) - len(unique_ids)
issues.append( )
"formatted_string"
"formatted_string"
                                                

                                                # Identify which instances are duplicated
id_counts = defaultdict(int)
for instance_id in instance_ids:
id_counts[instance_id] += 1

duplicated_ids = [item for item in []]
issues.append("formatted_string")

return len(unique_ids) == len(instances), issues, instances


class ConcurrentUserSimulator:
    """Simulator for concurrent user interactions"""

    @staticmethod
    def create_mock_users( )
    count: int,
user_id_prefix: str = "test_user",
include_secrets: bool = True
) -> List[MockUserContext]:
'''
Create multiple mock user contexts for concurrent testing.

Args:
count: Number of users to create
user_id_prefix: Prefix for user IDs
include_secrets: Whether to include user-specific secrets

Returns:
List of MockUserContext instances
'''
users = []

for i in range(count):
session_id = uuid.uuid4().hex
user_id = "formatted_string"
thread_id = "formatted_string"
run_id = "formatted_string"

                # Create mock WebSocket
websocket = TestWebSocketConnection()  # Real WebSocket implementation
websocket.websocket = TestWebSocketConnection()
websocket.websocket = TestWebSocketConnection()
websocket.websocket = TestWebSocketConnection()
websocket.websocket = TestWebSocketConnection()

                # User-specific data that should never be shared
session_data = { )
'user_preferences': 'formatted_string',
'session_token': 'formatted_string',
'user_state': 'formatted_string'
                

private_data = { )
'email': 'formatted_string',
'api_keys': ['formatted_string' for _ in range(3)],
'private_documents': ['formatted_string' for j in range(5)]
                

user_secrets = {}
if include_secrets:
user_secrets = { )
'auth_secret': 'formatted_string',
'encryption_key': 'formatted_string',
'private_token': 'formatted_string'
                    

user_context = MockUserContext( )
user_id=user_id,
thread_id=thread_id,
run_id=run_id,
session_id=session_id,
websocket=websocket,
session_data=session_data,
private_data=private_data,
user_secrets=user_secrets
                    

users.append(user_context)

return users

@staticmethod
async def simulate_concurrent_workflow( )
users: List[MockUserContext],
workflow_func: Callable[[MockUserContext], Any],
max_concurrent: Optional[int] = None,
include_delays: bool = True,
timeout_seconds: float = 30.0
) -> IsolationTestResult:
'''
Simulate concurrent user workflows and analyze isolation.

Args:
users: List of user contexts to simulate
workflow_func: Async function to execute for each user
max_concurrent: Maximum concurrent executions (None = unlimited)
include_delays: Whether to include random delays to expose race conditions
timeout_seconds: Timeout for entire simulation

Returns:
IsolationTestResult with comprehensive analysis
'''
start_time = time.time()
initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            # Track execution results
successful_executions = []
failed_executions = []
race_condition_errors = []
timeout_errors = []

            # Component tracking for singleton detection
component_instances = defaultdict(list)

async def execute_user_workflow(user: MockUserContext) -> Dict[str, Any]:
"""Execute workflow for a single user with error tracking"""
try:
        # Add random delay to expose race conditions
if include_delays:
await asyncio.sleep(random.uniform(0, 0.2))

            # Execute user workflow
if asyncio.iscoroutinefunction(workflow_func):
result = await workflow_func(user)
else:
result = workflow_func(user)

                    # Track component instances for singleton detection
for component_name, component_info in user.component_references.items():
component_instances[component_name].append(component_info['instance'])

return { )
'user_id': user.user_id,
'success': True,
'result': result,
'execution_time': time.time() - start_time
                        

except asyncio.TimeoutError as e:
timeout_errors.append({ ))
'user_id': user.user_id,
'error': str(e),
'error_type': 'timeout'
                            
return {'user_id': user.user_id, 'success': False, 'error_type': 'timeout'}

except Exception as e:
                                # Categorize errors
error_type = 'race_condition' if any( )
keyword in str(e).lower()
for keyword in ['race', 'concurrent', 'lock', 'already', 'conflict']
) else 'general'

if error_type == 'race_condition':
race_condition_errors.append({ ))
'user_id': user.user_id,
'error': str(e),
'error_type': error_type
                                    
else:
failed_executions.append({ ))
'user_id': user.user_id,
'error': str(e),
'error_type': error_type
                                        

return {'user_id': user.user_id, 'success': False, 'error': str(e)}

                                        # Execute users concurrently with optional concurrency limit
if max_concurrent and max_concurrent < len(users):
                                            # Use semaphore to limit concurrency
semaphore = asyncio.Semaphore(max_concurrent)

async def bounded_execution(user: MockUserContext):
async with semaphore:
return await execute_user_workflow(user)

tasks = [bounded_execution(user) for user in users]
else:
            # Unlimited concurrency
tasks = [execute_user_workflow(user) for user in users]

            # Run all tasks with timeout
try:
results = await asyncio.wait_for( )
asyncio.gather(*tasks, return_exceptions=True),
timeout=timeout_seconds
                
except asyncio.TimeoutError:
results = [{'success': False, 'error_type': 'global_timeout'} for _ in users]
timeout_errors.extend(results)

                    # Analyze results
successful_results = [item for item in []]

end_time = time.time()
final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

                    # Detect data leakage and isolation violations
data_leakage_incidents = ConcurrentUserSimulator._detect_data_leakage(users)
shared_state_violations = SingletonDetector.analyze_shared_references(users)
cross_user_contamination = ConcurrentUserSimulator._detect_cross_user_contamination(users)

                    # Analyze singleton components
singleton_analysis = SingletonDetector.detect_singleton_instances(component_instances)
singleton_components_detected = { )
name: unique_count
for name, (unique_count, _) in singleton_analysis.items()
                    

                    # Performance metrics
test_duration = end_time - start_time
performance_metrics = { )
'total_duration_seconds': test_duration,
'avg_execution_time_seconds': test_duration / max(len(users), 1),
'successful_executions': len(successful_results),
'failed_executions': len(failed_executions),
'throughput_users_per_second': len(users) / max(test_duration, 0.001),
'success_rate': len(successful_results) / max(len(users), 1)
                    

return IsolationTestResult( )
users_tested=len(users),
test_duration_seconds=test_duration,
test_type='concurrent_workflow_simulation',
successful_isolations=len(successful_results),
failed_isolations=len(failed_executions) + len(race_condition_errors),
isolation_success_rate=len(successful_results) / max(len(users), 1),
data_leakage_incidents=data_leakage_incidents,
shared_state_violations=shared_state_violations,
cross_user_contamination=cross_user_contamination,
performance_metrics=performance_metrics,
memory_usage_mb=final_memory,
memory_growth_mb=final_memory - initial_memory,
memory_per_user_mb=(final_memory - initial_memory) / max(len(users), 1),
race_conditions_detected=len(race_condition_errors),
deadlocks_detected=0,  # Could be enhanced to detect deadlocks
timeout_errors=len(timeout_errors),
singleton_components_detected=singleton_components_detected,
factory_violations=[],  # Could be enhanced with factory analysis
event_routing_errors=[],  # Could be enhanced with event analysis
misdirected_events=0,
lost_events=0
                    

@staticmethod
def _detect_data_leakage(users: List[MockUserContext]) -> List[Dict[str, Any]]:
"""Detect data leakage between user contexts"""
leakage_incidents = []

for i, user1 in enumerate(users):
for j, user2 in enumerate(users[i+1:], i+1):
            # Check for shared data references
shared_data = ConcurrentUserSimulator._find_shared_data( )
user1.session_data, user2.session_data
            

if shared_data:
leakage_incidents.append({ ))
'type': 'shared_session_data',
'user1_id': user1.user_id,
'user2_id': user2.user_id,
'shared_keys': shared_data
                

                # Check for shared private data
shared_private = ConcurrentUserSimulator._find_shared_data( )
user1.private_data, user2.private_data
                

if shared_private:
leakage_incidents.append({ ))
'type': 'shared_private_data',
'user1_id': user1.user_id,
'user2_id': user2.user_id,
'shared_keys': shared_private
                    

                    # Check for shared secrets
shared_secrets = ConcurrentUserSimulator._find_shared_data( )
user1.user_secrets, user2.user_secrets
                    

if shared_secrets:
leakage_incidents.append({ ))
'type': 'shared_secrets',
'user1_id': user1.user_id,
'user2_id': user2.user_id,
'shared_keys': shared_secrets,
'severity': 'critical'
                        

return leakage_incidents

@staticmethod
def _find_shared_data(data1: Dict[str, Any], data2: Dict[str, Any]) -> List[str]:
"""Find shared data references between two dictionaries"""
shared_keys = []

for key in data1.keys() & data2.keys():
if data1[key] is data2[key] and data1[key] is not None:
            # Same object reference (not just equal values)
shared_keys.append(key)

return shared_keys

@staticmethod
def _detect_cross_user_contamination(users: List[MockUserContext]) -> List[Dict[str, Any]]:
"""Detect cross-user contamination in events and messages"""
contamination_incidents = []

for user in users:
        # Check received events for other users' data
for event in user.received_events:
for other_user in users:
if other_user.user_id != user.user_id:
                    # Check if event contains other user's data
if ConcurrentUserSimulator._contains_user_data(event, other_user):
contamination_incidents.append({ ))
'type': 'cross_user_event_contamination',
'receiving_user': user.user_id,
'data_owner': other_user.user_id,
'event': event,
'severity': 'high'
                        

                        # Check sent messages for other users' data leakage
for message in user.sent_messages:
for other_user in users:
if other_user.user_id != user.user_id:
if ConcurrentUserSimulator._contains_user_data(message, other_user):
contamination_incidents.append({ ))
'type': 'cross_user_message_contamination',
'sending_user': user.user_id,
'data_owner': other_user.user_id,
'message': message,
'severity': 'critical'
                                        

return contamination_incidents

@staticmethod
def _contains_user_data(data: Dict[str, Any], user: MockUserContext) -> bool:
"""Check if data contains user-specific information"""
data_str = str(data).lower()

    # Check for user identifiers
identifiers_to_check = [ )
user.user_id.lower(),
user.thread_id.lower(),
user.run_id.lower(),
user.session_id.lower()
    

    # Check for user secrets
for secret in user.user_secrets.values():
identifiers_to_check.append(secret.lower())

        # Check for user private data
for private_value in user.private_data.values():
if isinstance(private_value, str):
identifiers_to_check.append(private_value.lower())
elif isinstance(private_value, list):
identifiers_to_check.extend([str(v).lower() for v in private_value])

return any(identifier in data_str for identifier in identifiers_to_check)


class WebSocketEventCapture:
        """Utility for capturing and analyzing WebSocket events"""

        @staticmethod
    def setup_event_capture(websocket_mock: Mock) -> Dict[str, List[Dict[str, Any]]]:
        """Setup WebSocket mock to capture all events"""
        captured_events = { )
        'sent_json': [],
        'sent_text': [],
        'received_json': [],
        'received_text': []
    

        original_send_json = websocket_mock.send_json
        original_send_text = websocket_mock.send_text

    async def capture_send_json(data):
        captured_events['sent_json'].append({ ))
        'data': data,
        'timestamp': time.time(),
        'thread_id': threading.get_ident()
    
        if original_send_json:
        return await original_send_json(data)

    async def capture_send_text(data):
        captured_events['sent_text'].append({ ))
        'data': data,
        'timestamp': time.time(),
        'thread_id': threading.get_ident()
    
        if original_send_text:
        return await original_send_text(data)

        websocket_mock.send_json.side_effect = capture_send_json
        websocket_mock.send_text.side_effect = capture_send_text

        return captured_events

        @staticmethod
        def analyze_event_routing( )
        users: List[MockUserContext],
expected_events: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Dict[str, Any]:
'''
Analyze WebSocket event routing for correctness.

Args:
users: List of user contexts with captured events
expected_events: Optional dict of user_id -> expected events

Returns:
Analysis results with routing errors, misdirected events, etc.
'''
routing_analysis = { )
'total_users': len(users),
'total_events_sent': 0,
'events_per_user': {},
'routing_errors': [],
'misdirected_events': [],
'lost_events': [],
'duplicate_events': [],
'event_types_seen': set()
            

            # Analyze each user's events
for user in users:
user_events = []

                Collect all events for this user from WebSocket calls
for call in user.websocket.send_json.call_args_list:
if call.args:
event = call.args[0]
user_events.append(event)

                        # Track event types
if isinstance(event, dict) and 'type' in event:
routing_analysis['event_types_seen'].add(event['type'])

routing_analysis['events_per_user'][user.user_id] = { )
'count': len(user_events),
'events': user_events
                            

routing_analysis['total_events_sent'] += len(user_events)

                            # Check for events containing other users' data
for event in user_events:
for other_user in users:
if other_user.user_id != user.user_id:
if ConcurrentUserSimulator._contains_user_data(event, other_user):
routing_analysis['misdirected_events'].append({ ))
'receiving_user': user.user_id,
'data_owner': other_user.user_id,
'event': event
                                            

                                            # If expected events provided, check for lost events
if expected_events:
for user_id, expected in expected_events.items():
actual = routing_analysis['events_per_user'].get(user_id, {}).get('events', [])

if len(actual) < len(expected):
lost_count = len(expected) - len(actual)
routing_analysis['lost_events'].append({ ))
'user_id': user_id,
'expected_count': len(expected),
'actual_count': len(actual),
'lost_count': lost_count
                                                        

routing_analysis['event_types_seen'] = list(routing_analysis['event_types_seen'])
return routing_analysis


class MemoryLeakDetector:
    """Utility for detecting memory leaks in concurrent scenarios"""

    @staticmethod
    def start_monitoring() -> Dict[str, Any]:
        """Start memory monitoring"""
        gc.collect()

        process = psutil.Process(os.getpid())

        return { )
        'start_time': time.time(),
        'initial_memory_mb': process.memory_info().rss / 1024 / 1024,
        'initial_memory_percent': process.memory_percent(),
        'gc_stats': { )
        'collected': gc.get_stats(),
        'counts': gc.get_count()
    
    

        @staticmethod
    def end_monitoring(start_data: Dict[str, Any]) -> Dict[str, Any]:
        """End memory monitoring and analyze results"""
        gc.collect()

        process = psutil.Process(os.getpid())
        end_time = time.time()

        final_memory_mb = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory_mb - start_data['initial_memory_mb']

        return { )
        'end_time': end_time,
        'duration_seconds': end_time - start_data['start_time'],
        'final_memory_mb': final_memory_mb,
        'memory_growth_mb': memory_growth,
        'memory_growth_percent': (memory_growth / start_data['initial_memory_mb']) * 100,
        'gc_stats': { )
        'collected': gc.get_stats(),
        'counts': gc.get_count()
        },
        'is_leak_suspected': memory_growth > 100  # >100MB growth is suspicious
    

        @staticmethod
        def detect_unbounded_growth( )
        measurements: List[Dict[str, Any]],
growth_threshold_mb: float = 50.0
) -> Dict[str, Any]:
"""Detect unbounded memory growth pattern"""
if len(measurements) < 2:
return {'unbounded_growth_detected': False, 'reason': 'insufficient_data'}

        # Analyze memory growth trend
memory_values = [m['final_memory_mb'] for m in measurements]
growth_rates = []

for i in range(1, len(memory_values)):
growth_rate = memory_values[i] - memory_values[i-1]
growth_rates.append(growth_rate)

avg_growth_rate = sum(growth_rates) / len(growth_rates)
max_growth_rate = max(growth_rates)

            # Check for consistently increasing memory usage
consistently_growing = all(rate > 0 for rate in growth_rates[-3:])  # Last 3 measurements

unbounded_growth_detected = ( )
avg_growth_rate > growth_threshold_mb or
max_growth_rate > growth_threshold_mb * 2 or
(consistently_growing and len(growth_rates) >= 3)
            

return { )
'unbounded_growth_detected': unbounded_growth_detected,
'avg_growth_rate_mb': avg_growth_rate,
'max_growth_rate_mb': max_growth_rate,
'consistently_growing': consistently_growing,
'measurements_count': len(measurements),
'total_growth_mb': memory_values[-1] - memory_values[0] if memory_values else 0
            


class PerformanceProfiler:
    """Utility for profiling performance under concurrent load"""

    @staticmethod
    async def profile_concurrent_execution( )
    user_counts: List[int],
    workflow_func: Callable,
iterations_per_count: int = 3
) -> Dict[str, Any]:
'''
Profile performance across different concurrent user counts.

Args:
user_counts: List of user counts to test
workflow_func: Workflow function to execute
iterations_per_count: Number of iterations per user count

Returns:
Performance profile with scaling analysis
'''
profile_results = { )
'user_counts_tested': user_counts,
'iterations_per_count': iterations_per_count,
'measurements': {},
'scaling_analysis': {},
'performance_degradation_detected': False
            

for user_count in user_counts:
user_measurements = []

for iteration in range(iterations_per_count):
users = ConcurrentUserSimulator.create_mock_users(user_count)

result = await ConcurrentUserSimulator.simulate_concurrent_workflow( )
users=users,
workflow_func=workflow_func,
timeout_seconds=30.0
                    

user_measurements.append({ ))
'iteration': iteration,
'duration_seconds': result.test_duration_seconds,
'throughput_users_per_second': result.performance_metrics['throughput_users_per_second'],
'success_rate': result.isolation_success_rate,
'memory_growth_mb': result.memory_growth_mb,
'race_conditions': result.race_conditions_detected
                    

                    # Calculate averages
avg_duration = sum(m['duration_seconds'] for m in user_measurements) / len(user_measurements)
avg_throughput = sum(m['throughput_users_per_second'] for m in user_measurements) / len(user_measurements)
avg_success_rate = sum(m['success_rate'] for m in user_measurements) / len(user_measurements)
avg_memory_growth = sum(m['memory_growth_mb'] for m in user_measurements) / len(user_measurements)

profile_results['measurements'][user_count] = { )
'avg_duration_seconds': avg_duration,
'avg_throughput_users_per_second': avg_throughput,
'avg_success_rate': avg_success_rate,
'avg_memory_growth_mb': avg_memory_growth,
'individual_measurements': user_measurements
                    

                    # Analyze scaling behavior
if len(user_counts) >= 2:
profile_results['scaling_analysis'] = PerformanceProfiler._analyze_scaling_behavior( )
profile_results['measurements']
                        

return profile_results

@staticmethod
def _analyze_scaling_behavior(measurements: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
"""Analyze scaling behavior from performance measurements"""
user_counts = sorted(measurements.keys())

if len(user_counts) < 2:
return {'analysis_possible': False, 'reason': 'insufficient_data_points'}

        # Calculate scaling factors
baseline_count = user_counts[0]
baseline_metrics = measurements[baseline_count]

scaling_factors = {}
performance_degradation = {}

for user_count in user_counts[1:]:
current_metrics = measurements[user_count]
scale_factor = user_count / baseline_count

            # Expected linear scaling
expected_duration = baseline_metrics['avg_duration_seconds']  # Should stay constant
expected_throughput = baseline_metrics['avg_throughput_users_per_second'] * scale_factor
expected_memory = baseline_metrics['avg_memory_growth_mb'] * scale_factor

            # Actual scaling
actual_duration = current_metrics['avg_duration_seconds']
actual_throughput = current_metrics['avg_throughput_users_per_second']
actual_memory = current_metrics['avg_memory_growth_mb']

            # Calculate efficiency
duration_efficiency = expected_duration / max(actual_duration, 0.001)  # Higher is better
throughput_efficiency = actual_throughput / max(expected_throughput, 0.001)  # Higher is better
memory_efficiency = expected_memory / max(actual_memory, 0.001)  # Higher is better

scaling_factors[user_count] = { )
'scale_factor': scale_factor,
'duration_efficiency': duration_efficiency,
'throughput_efficiency': throughput_efficiency,
'memory_efficiency': memory_efficiency,
'overall_efficiency': (duration_efficiency + throughput_efficiency + memory_efficiency) / 3
            

            # Detect performance degradation
duration_degraded = actual_duration > expected_duration * 2  # 2x slower
throughput_degraded = actual_throughput < expected_throughput * 0.5  # 50% less throughput
memory_degraded = actual_memory > expected_memory * 2  # 2x more memory

performance_degradation[user_count] = { )
'duration_degraded': duration_degraded,
'throughput_degraded': throughput_degraded,
'memory_degraded': memory_degraded,
'any_degradation': duration_degraded or throughput_degraded or memory_degraded
            

            # Overall analysis
any_degradation = any( )
pd['any_degradation'] for pd in performance_degradation.values()
            

avg_efficiency = sum(sf['overall_efficiency'] for sf in scaling_factors.values()) / len(scaling_factors)

return { )
'analysis_possible': True,
'scaling_factors': scaling_factors,
'performance_degradation': performance_degradation,
'performance_degradation_detected': any_degradation,
'average_efficiency': avg_efficiency,
'efficiency_rating': ( )
'excellent' if avg_efficiency > 0.9 else
'good' if avg_efficiency > 0.7 else
'poor' if avg_efficiency > 0.5 else
'failing'
            
            


            # Export all utilities
__all__ = [ )
'MockUserContext',
'IsolationTestResult',
'SingletonDetector',
'ConcurrentUserSimulator',
'WebSocketEventCapture',
'MemoryLeakDetector',
'PerformanceProfiler'
            
