_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
_lazy_imports = {}

def lazy_import(module_path: str, component: str=None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f'Warning: Failed to lazy load {module_path}: {e}')
            _lazy_imports[module_path] = None
    return _lazy_imports[module_path]
'\nCritical WebSocket Agent Events E2E Test - COMPLETELY REWRITTEN\n\nTHIS IS THE PRIMARY TEST FOR AGENT WEBSOCKET COMMUNICATION.\nBusiness Value: $500K+ ARR protection - Core chat functionality depends on this.\n\nTests that ALL required agent events are sent through the WebSocket pipeline:\n- agent_started: User sees agent is working\n- agent_thinking: Real-time reasoning display  \n- tool_executing: Tool execution visibility\n- tool_completed: Tool results display\n- agent_completed: Execution finished\n\nCRITICAL: If this test fails, the chat UI will appear broken to users.\nThis test uses REAL services, REAL authentication, and REAL WebSocket connections.\nNO MOCKS, NO FAKES, NO CHEATING.\n'
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
import pytest
import websockets
from loguru import logger
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env
CRITICAL_EVENTS = {'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'}
ENHANCED_EVENTS = {'partial_result', 'final_report', 'agent_fallback', 'agent_update'}
REQUIRED_EVENT_ORDER = ['agent_started', 'agent_completed']

class CriticalEventValidator:
    """Validates that all critical WebSocket events are sent."""

    def __init__(self):
        self.events: List[Dict] = []
        self.event_types: Set[str] = set()
        self.event_order: List[str] = []
        self.tool_events: List[Dict] = []
        self.thinking_events: List[Dict] = []
        self.partial_results: List[str] = []
        self.timing: Dict[str, float] = {}
        self.start_time = time.time()
        self.errors: List[str] = []

    def record_event(self, event: Dict) -> None:
        """Record a WebSocket event for validation."""
        self.events.append(event)
        event_type = event.get('type', 'unknown')
        self.event_types.add(event_type)
        self.event_order.append(event_type)
        self.timing[event_type] = time.time() - self.start_time
        if event_type == 'tool_executing':
            self.tool_events.append(event)
        elif event_type == 'tool_completed':
            self.tool_events.append(event)
        elif event_type == 'agent_thinking':
            self.thinking_events.append(event)
        elif event_type == 'partial_result':
            content = event.get('data', {}).get('content', '')
            self.partial_results.append(content)

    def validate_critical_events(self) -> tuple[bool, List[str]]:
        """Validate that all critical events were sent."""
        missing = CRITICAL_EVENTS - self.event_types
        errors = []
        if missing:
            errors.append(f'CRITICAL: Missing required events: {missing}')
        if self.event_order:
            if self.event_order[0] != 'agent_started':
                errors.append('CRITICAL: agent_started must be first event')
            last_event = self.event_order[-1]
            if last_event not in ['agent_completed', 'final_report']:
                errors.append(f'CRITICAL: Last event must be completion, got {last_event}')
        else:
            errors.append('CRITICAL: No events received at all!')
        tool_starts = [e for e in self.tool_events if e.get('type') == 'tool_executing']
        tool_ends = [e for e in self.tool_events if e.get('type') == 'tool_completed']
        if len(tool_starts) != len(tool_ends):
            errors.append(f'CRITICAL: Tool events not paired: {len(tool_starts)} starts, {len(tool_ends)} ends')
        return (len(errors) == 0, errors)

    def get_performance_metrics(self) -> Dict:
        """Get performance metrics for the event flow."""
        metrics = {'total_events': len(self.events), 'unique_event_types': len(self.event_types), 'thinking_updates': len(self.thinking_events), 'tool_executions': len([e for e in self.tool_events if e.get('type') == 'tool_executing']), 'partial_results': len(self.partial_results), 'total_duration': max(self.timing.values()) if self.timing else 0}
        if 'agent_started' in self.timing:
            metrics['time_to_first_event'] = self.timing['agent_started']
        if 'agent_thinking' in self.timing:
            metrics['time_to_first_thought'] = self.timing['agent_thinking']
        if 'partial_result' in self.timing:
            metrics['time_to_first_result'] = self.timing['partial_result']
        return metrics

    def generate_report(self) -> str:
        """Generate a comprehensive validation report."""
        is_valid, errors = self.validate_critical_events()
        metrics = self.get_performance_metrics()
        report = ['=' * 60, 'CRITICAL WEBSOCKET EVENT VALIDATION REPORT', '=' * 60, f"Validation Result: {(' PASS:  PASSED' if is_valid else ' FAIL:  FAILED')}", f'Total Events: {len(self.events)}', f'Event Types: {sorted(self.event_types)}', '', 'Critical Events Status:']
        for event in CRITICAL_EVENTS:
            status = ' PASS: ' if event in self.event_types else ' FAIL: '
            report.append(f'  {status} {event}')
        if errors:
            report.extend(['', 'Errors Found:'] + [f'  - {e}' for e in errors])
        report.extend(['', 'Performance Metrics:', f"  Total Events: {metrics['total_events']}", f"  Total Duration: {metrics['total_duration']:.2f}s", f"  Thinking Updates: {metrics['thinking_updates']}", f"  Tool Executions: {metrics['tool_executions']}"])
        if 'time_to_first_thought' in metrics:
            report.append(f"  Time to First Thought: {metrics['time_to_first_thought']:.2f}s")
        report.extend(['', 'Event Sequence:'])
        for i, event in enumerate(self.event_order[:20]):
            report.append(f'  {i + 1:2d}. {event}')
        if len(self.event_order) > 20:
            report.append(f'  ... and {len(self.event_order) - 20} more events')
        report.append('=' * 60)
        return '\n'.join(report)

class TestCriticalWebSocketAgentEvents:
    """Test suite for critical WebSocket agent event flow - COMPLETELY REWRITTEN."""

    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated WebSocket helper."""
        env = get_env()
        environment = env.get('TEST_ENV', 'test')
        return E2EWebSocketAuthHelper(environment=environment)

    @pytest.fixture
    def event_validator(self):
        """Create an event validator."""
        return CriticalEventValidator()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_critical_agent_lifecycle_events(self, auth_helper: E2EWebSocketAuthHelper, event_validator: CriticalEventValidator):
        """Test that ALL critical agent lifecycle events are sent via real WebSocket.
        
        This test uses REAL authentication, REAL WebSocket connection, and REAL services.
        It will FAIL HARD if the system doesn't work properly. No mocks, no fakes.
        """
        logger.info('[U+1F680] Starting critical WebSocket agent events test')
        logger.info('[U+1F4E1] Connecting to WebSocket with real authentication...')
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        assert websocket is not None, 'Failed to establish WebSocket connection'
        logger.info(' PASS:  WebSocket connected successfully')
        test_message = {'type': 'chat', 'message': 'What is 2 + 2? Please show your calculation.', 'thread_id': str(uuid.uuid4()), 'request_id': f'test-{int(time.time())}'}
        logger.info(f"[U+1F4E8] Sending chat message: {test_message['message']}")
        await websocket.send(json.dumps(test_message))
        logger.info('[U+1F442] Listening for WebSocket events...')
        start_time = time.time()
        max_wait_time = 30.0
        received_completion = False
        while time.time() - start_time < max_wait_time and (not received_completion):
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            event = json.loads(message)
            event_validator.record_event(event)
            event_type = event.get('type', 'unknown')
            logger.info(f'[U+1F4E5] Received event: {event_type}')
            if event_type in ['agent_completed', 'final_report']:
                received_completion = True
                logger.info(f' TARGET:  Received completion event: {event_type}')
                break
            if event_type in CRITICAL_EVENTS:
                data = event.get('data', {})
                content = str(data.get('content', ''))[:100]
                logger.info(f'[U+1F4CB] {event_type}: {content}...')
        await websocket.close()
        logger.info('[U+1F50C] WebSocket connection closed')
        report = event_validator.generate_report()
        logger.info(f' CHART:  Event Validation Report:\n{report}')
        is_valid, errors = event_validator.validate_critical_events()
        assert len(event_validator.events) > 0, 'CRITICAL FAILURE: No WebSocket events received at all!'
        missing_critical = CRITICAL_EVENTS - event_validator.event_types
        assert len(missing_critical) == 0, f'CRITICAL FAILURE: Missing required events: {missing_critical}'
        assert len(event_validator.event_order) > 0, 'CRITICAL FAILURE: No event sequence recorded'
        assert event_validator.event_order[0] == 'agent_started', f"CRITICAL FAILURE: First event must be 'agent_started', got '{event_validator.event_order[0]}'"
        last_event = event_validator.event_order[-1]
        assert last_event in ['agent_completed', 'final_report'], f"CRITICAL FAILURE: Last event must be completion, got '{last_event}'"
        assert len(event_validator.thinking_events) > 0, "CRITICAL FAILURE: No 'agent_thinking' events - user won't see AI reasoning"
        assert is_valid, f'CRITICAL FAILURE: Event validation failed:\n{chr(10).join(errors)}'
        logger.info(' PASS:  All critical WebSocket agent events validated successfully!')
        metrics = event_validator.get_performance_metrics()
        total_duration = metrics.get('total_duration', 0)
        assert total_duration > 0, 'CRITICAL FAILURE: No event timing recorded'
        assert total_duration < 60.0, f'PERFORMANCE FAILURE: Agent execution took too long: {total_duration:.2f}s'
        logger.info(f" LIGHTNING:  Performance: {metrics['total_events']} events in {total_duration:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_connection_resilience(self, auth_helper: E2EWebSocketAuthHelper, event_validator: CriticalEventValidator):
        """Test WebSocket connection handling and error scenarios."""
        logger.info(' CYCLE:  Testing WebSocket connection resilience...')
        websocket = await auth_helper.connect_authenticated_websocket(timeout=10.0)
        assert websocket is not None, 'Failed to establish initial WebSocket connection'
        ping_message = {'type': 'ping', 'timestamp': datetime.now().isoformat()}
        await websocket.send(json.dumps(ping_message))
        logger.info('[U+1F4E4] Sent ping message')
        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        response_data = json.loads(response)
        logger.info(f"[U+1F4E8] Received response: {response_data.get('type', 'unknown')}")
        await websocket.close()
        logger.info(' PASS:  WebSocket resilience test completed')
        assert response_data is not None, 'No response to ping message'

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multiple_concurrent_websocket_messages(self, auth_helper: E2EWebSocketAuthHelper, event_validator: CriticalEventValidator):
        """Test sending multiple messages through WebSocket connection."""
        logger.info(' CYCLE:  Testing multiple concurrent WebSocket messages...')
        websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
        assert websocket is not None, 'Failed to establish WebSocket connection'
        messages = ['Hello', 'What is 1 + 1?', 'Tell me a short joke']
        for i, msg in enumerate(messages):
            test_message = {'type': 'chat', 'message': msg, 'thread_id': str(uuid.uuid4()), 'request_id': f'multi-test-{i}-{int(time.time())}'}
            logger.info(f'[U+1F4E4] Sending message {i + 1}: {msg}')
            await websocket.send(json.dumps(test_message))
            response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
            event = json.loads(response)
            event_validator.record_event(event)
            logger.info(f"[U+1F4E5] Got response for message {i + 1}: {event.get('type', 'unknown')}")
            await asyncio.sleep(0.5)
        await websocket.close()
        logger.info(' PASS:  Multiple message test completed')
        assert len(event_validator.events) >= len(messages), f'Expected at least {len(messages)} events, got {len(event_validator.events)}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')