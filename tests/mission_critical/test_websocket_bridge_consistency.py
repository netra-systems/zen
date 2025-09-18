class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks."
    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
    async def send_json(self, message: dict):
        ""Send JSON message.""

        if self._closed:
            raise RuntimeError(WebSocket is closed)"""

        self.messages_sent.append(message)
    async def close(self, code: int = 1000, reason: str = Normal closure"):"
        Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False
    async def get_messages(self) -> list:
        Get all sent messages."
        Get all sent messages.""

        await asyncio.sleep(0)
        return self.messages_sent.copy()
        '''
        '''
        Mission Critical: WebSocket Bridge Consistency Test Suite
        ========================================================
        Tests to ensure SSOT compliance for WebSocket communication patterns.
        All agents MUST use the unified WebSocket bridge pattern.
        CRITICAL: This test suite validates that:
        1. All agents use WebSocket bridge exclusively
        2. No duplicate WebSocket event methods exist
        3. Consistent event emission paths are used
        4. WebSocket manager is not used directly
        5. Full SSOT compliance is maintained
        '''
        '''
        import asyncio
        import inspect
        import sys
        import os
        from pathlib import Path
        from typing import List, Dict, Any, Set, Tuple
        import ast
        import pytest
        from shared.isolated_environment import IsolatedEnvironment
        # Add project root to path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from netra_backend.app.agents.base_agent import BaseAgent
        # Using protocol-based approach for agent execution
        from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
        from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
        from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
        from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
class WebSocketPatternAnalyzer:
        "Analyzes code for WebSocket pattern usage."
    def __init__(self):
        pass
        self.violations = []
        self.bridge_usage = []
        self.manager_usage = []
        self.mixed_usage = []
        self.duplicate_methods = {}
    def analyze_file(self, filepath: Path) -> Dict[str, Any]:
        ""Analyze a Python file for WebSocket patterns.""

        try:
        with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        tree = ast.parse(content)
        return self._analyze_ast(tree, filepath, content)
        except Exception as e:
        return {'error': str(e), 'file': str(filepath)}
    def _analyze_ast(self, tree: ast.AST, filepath: Path, content: str) -> Dict[str, Any]:
        Analyze AST for WebSocket patterns.""
        results = {
        'file': str(filepath),
        'uses_bridge': False,
        'uses_manager': False,
        'is_mixed': False,
        'websocket_methods': [],
        'manager_refs': [],
        'bridge_refs': [],
        'violations': []
    
        for node in ast.walk(tree):
        # Check for WebSocket manager usage
        if isinstance(node, ast.Attribute):
        if node.attr == 'websocket_manager':
        line_no = node.lineno if hasattr(node, 'lineno') else 0
        results['manager_refs'].append(line_no)
        results['uses_manager'] = True
                # Check for bridge usage
        if isinstance(node, ast.Name):
        if node.id in ['WebSocketBridgeAdapter', 'get_agent_websocket_bridge']:
        results['uses_bridge'] = True
        results['bridge_refs'].append(node.lineno if hasattr(node, 'lineno') else 0)
                        # Check for WebSocket event methods
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
        method_name = node.name
        ws_methods = [
        'send_agent_update', 'send_agent_thinking', 'send_tool_executing',
        'send_tool_completed', 'send_partial_result', 'send_final_report',
        'notify_agent_thinking', 'notify_tool_execution', 'notify_agent_completed',
        'emit_thinking', 'emit_tool_executing', 'emit_tool_completed',
        'emit_error', 'emit_progress', 'emit_agent_started', 'emit_agent_completed'
                            
        if any(m in method_name for m in ws_methods):
        results['websocket_methods'].append()
        'name': method_name,
        'line': node.lineno if hasattr(node, 'lineno') else 0
                                
                                # Determine if mixed usage
        if results['uses_bridge'] and results['uses_manager']:
        results['is_mixed'] = True
        results['violations'].append('Mixed WebSocket pattern usage detected')
        return results
class TestWebSocketBridgeConsistency:
        Test suite for WebSocket bridge consistency and SSOT compliance.""
        @pytest.fixture
    def setup(self):
        Setup test environment."
        Setup test environment.""

        self.analyzer = WebSocketPatternAnalyzer()
        self.agent_files = self._get_agent_files()
    def _get_agent_files(self) -> List[Path]:
        "Get all agent Python files."
        pass
        base_path = Path(__file__).parent.parent.parent / "netra_backend / app / agents"
        agent_files = []
        for file in base_path.rglob(*.py):"
        for file in base_path.rglob(*.py):"
        # Skip __pycache__ and test files
        if "__pycache__ not in str(file) and test_ not in file.name:"
        agent_files.append(file)
        return agent_files
    def test_no_duplicate_websocket_methods(self):
        Test that WebSocket event methods are not duplicated across files.""
        method_locations = {}
        duplicates = []
        for filepath in self.agent_files:
        results = self.analyzer.analyze_file(filepath)
        for method in results.get('websocket_methods', [):
        method_name = method['name']
        location = formatted_string
        if method_name not in method_locations:
        method_locations[method_name] = []
        method_locations[method_name].append(location)
                # Check for duplicates
        for method_name, locations in method_locations.items():
        if len(locations) > 1:
                        # Allow some specific exceptions (like base class + implementation)
        if not self._is_allowed_duplicate(method_name, locations):
        duplicates.append()
        'method': method_name,
        'locations': locations,
        'count': len(locations)
                            
        assert len(duplicates) == 0, "( )"
        formatted_string +"
        formatted_string +""

        
        ".join([formatted_stringcount]} occurrences in {, .join(d[locations]}" ))"
        ".join([formatted_stringcount]} occurrences in {, .join(d[locations]}" ))""

        for d in duplicates]
                                
    def _is_allowed_duplicate(self, method_name: str, locations: List[str) -> bool:
        Check if a duplicate is allowed (e.g., base class + override)."
        Check if a duplicate is allowed (e.g., base class + override).""

        pass
    # Allow emit_* methods in BaseAgent and its adapters
        if method_name.startswith('emit_'):
        base_files = ['base_agent.py', 'websocket_bridge_adapter.py']
        if any(base in loc for base in base_files for loc in locations):
        return True
        return False
    def test_no_mixed_websocket_patterns(self):
        "Test that files don't mix WebSocket manager and bridge patterns."
        mixed_files = []
        for filepath in self.agent_files:
        results = self.analyzer.analyze_file(filepath)
        if results.get('is_mixed'):
        mixed_files.append()
        'file': filepath.name,
        'manager_refs': len(results.get('manager_refs', []),
        'bridge_refs': len(results.get('bridge_refs', []),
        'violations': results.get('violations', [)
            
        assert len(mixed_files) == 0, "( )"
        "formatted_string +"
        
        .join([formatted_stringmanager_refs]} manager refs, {f[bridge_refs"]} bridge refs ))"
        for f in mixed_files]
                
    def test_websocket_manager_not_used_directly(self):
        "Test that WebSocket manager is not used directly in agent implementations."
        pass
        manager_usage = []
    # Allowed files that may reference manager for compatibility
        allowed_files = ['websocket_bridge_adapter.py', 'agent_websocket_bridge.py']
        for filepath in self.agent_files:
        if filepath.name in allowed_files:
        continue
        results = self.analyzer.analyze_file(filepath)
        if results.get('uses_manager') and results.get('manager_refs'):
        manager_usage.append()
        'file': filepath.name,
        'lines': results['manager_refs']
                
        assert len(manager_usage) == 0, "( )"
        "formatted_string +"
        
        .join([formatted_stringlines]) for f in manager_usage]"
        .join([formatted_stringlines]) for f in manager_usage]""

                    
    def test_consistent_event_emission_pattern(self):
        "Test that all agents use consistent event emission pattern."
        inconsistent_patterns = []
    Expected pattern: use emit_* methods from bridge adapter
        expected_methods = {
        'emit_thinking', 'emit_tool_executing', 'emit_tool_completed',
        'emit_error', 'emit_progress', 'emit_agent_started', 'emit_agent_completed'
    
        for filepath in self.agent_files:
        # Skip base/infrastructure files
        if filepath.name in ['__init__.py', 'websocket_bridge_adapter.py']:
        continue
        results = self.analyzer.analyze_file(filepath)
        ws_methods = {m['name'] for m in results.get('websocket_methods', [])
            # Check if using non-standard emission methods
        non_standard = ws_methods - expected_methods
        if non_standard and 'send_' in str(non_standard):
        inconsistent_patterns.append()
        'file': filepath.name,
        'non_standard_methods': list(non_standard)
                
        assert len(inconsistent_patterns) == 0, "( )"
        formatted_string" +"

        .join([formatted_string"non_standard_methods]} ))"
        for f in inconsistent_patterns]
                    
@pytest.mark.asyncio
    async def test_bridge_singleton_usage(self):
    Test that all agents use the singleton bridge instance correctly."
    Test that all agents use the singleton bridge instance correctly.""

pass
                        # Get bridge instance
bridge1 = await get_agent_websocket_bridge()
bridge2 = await get_agent_websocket_bridge()
                        # Verify singleton
assert bridge1 is bridge2, "Bridge should be a singleton"
                        # Test that agents can set and use bridge
agent = BaseAgent( )
agent_id=test-agent,
name="Test Agent"
                        
                        # Set bridge
agent.set_websocket_bridge(bridge1, test-run-id)
                        # Verify bridge is set
assert agent.websocket_bridge is not None
assert agent.websocket_bridge == bridge1
@pytest.mark.asyncio
    async def test_websocket_events_flow_through_bridge(self):
    Test that WebSocket events flow through the bridge correctly.""
bridge = await get_agent_websocket_bridge()
                            # Mock WebSocket manager
websocket = TestWebSocketConnection()
bridge.websocket_manager = mock_manager
                            # Create agent and set bridge
agent = DataSubAgent()
agent.set_websocket_bridge(bridge, test-run-id)
                            # Test event emission
await agent.emit_thinking("Processing data...)"
                            # Verify bridge was called (not direct manager)
assert mock_manager.send_agent_update.called or mock_manager.notify_agent_thinking.called
def test_no_circular_imports_with_bridge(self):
    Test that bridge pattern doesn't create circular imports."
    Test that bridge pattern doesn't create circular imports.""

pass
try:
        # Try importing all agent modules
from netra_backend.app.agents import base_agent
from netra_backend.app.agents.mixins import websocket_bridge_adapter
from netra_backend.app.services import agent_websocket_bridge
from netra_backend.app.agents import agent_communication
from netra_backend.app.agents import agent_lifecycle
        # If we get here, no circular imports
assert True
except ImportError as e:
    pytest.fail("
    pytest.fail(""

def test_bridge_methods_are_consistent(self):
    "Test that bridge methods have consistent signatures across implementations."
bridge_adapter = WebSocketBridgeAdapter()
    # Get all emit methods
emit_methods = [item for item in []]
    # Verify each has consistent signature
for method_name in emit_methods:
    method = getattr(bridge_adapter, method_name)
sig = inspect.signature(method)
        # All emit methods should be async
assert inspect.iscoroutinefunction(method), "formatted_string"
        # Check common parameters
params = list(sig.parameters.keys())
assert 'self' in params, formatted_string""
def test_ssot_compliance_score(self):
    Calculate and verify SSOT compliance score for WebSocket patterns."
    Calculate and verify SSOT compliance score for WebSocket patterns.""

pass
total_files = len(self.agent_files)
compliant_files = 0
violations = []
for filepath in self.agent_files:
    results = self.analyzer.analyze_file(filepath)
        # File is compliant if:
            # 1. Uses bridge OR doesn't use WebSocket at all'
            # 2. Doesn't use manager directly'
            # 3. Not mixed usage
is_compliant = ( )
(results.get('uses_bridge') or )
(not results.get('uses_bridge') and not results.get('uses_manager'))) and
not results.get('uses_manager') and
not results.get('is_mixed')
            
if is_compliant:
    compliant_files += 1
else:
    violations.append(filepath.name)
compliance_score = (compliant_files / total_files) * 100 if total_files > 0 else 0
print(formatted_string")"
print("")
if violations:
    print(formatted_string)"
    print(formatted_string)""

if len(violations) > 5:
    print("")
                            # Fail if compliance is below threshold
assert compliance_score >= 80, "( )"
formatted_string""
formatted_string
                            
class TestWebSocketBridgeIntegration:
        "Integration tests for unified WebSocket bridge."
@pytest.mark.asyncio
    async def test_agent_lifecycle_with_bridge(self):
    Test complete agent lifecycle using bridge pattern.""
bridge = await get_agent_websocket_bridge()
websocket = TestWebSocketConnection()
bridge.websocket_manager = mock_manager
        # Create agent
agent = ValidationSubAgent()
agent.set_websocket_bridge(bridge, test-run-123)
        # Simulate lifecycle
await agent.emit_agent_started({status: initializing")"
await agent.emit_thinking("Validating data...)"
await agent.emit_tool_executing(data_validator, {input: test")"
await agent.emit_tool_completed(data_validator, {result: valid)"
await agent.emit_tool_completed(data_validator, {result: valid)"
await agent.emit_agent_completed({status": success)"
        # Verify all events were sent through bridge
assert mock_manager.send_agent_update.call_count >= 5 or \
    mock_manager.notify_agent_started.called
@pytest.mark.asyncio
    async def test_error_handling_through_bridge(self):
    Test error handling flows through bridge correctly.""
pass
bridge = await get_agent_websocket_bridge()
websocket = TestWebSocketConnection()
bridge.websocket_manager = mock_manager
agent = BaseAgent(agent_id=test, name=Test)
agent.set_websocket_bridge(bridge, error-run)""
            # Emit error
await agent.emit_error(Test error", {code: TEST_001)"
            # Verify error was sent
assert mock_manager.send_agent_update.called or \
    mock_manager.notify_error.called
@pytest.mark.asyncio
    async def test_concurrent_agents_using_bridge(self):
    "Test multiple agents can use bridge concurrently."
bridge = await get_agent_websocket_bridge()
websocket = TestWebSocketConnection()
bridge.websocket_manager = mock_manager
                # Create multiple agents
agents = [
DataSubAgent(),
ValidationSubAgent()
                
                # Add more base agents
for i in range(3):
    agents.append(BaseAgent(agent_id=formatted_string, name="")
                    # Set bridge for all
for i, agent in enumerate(agents):
    agent.set_websocket_bridge(bridge, formatted_string)
                        # Concurrent emissions
tasks = [
agent.emit_thinking(""
for agent in agents
                        
await asyncio.gather(*tasks)
                        # Verify all emissions succeeded
assert mock_manager.send_agent_update.call_count >= len(agents) or \
    mock_manager.notify_agent_thinking.call_count >= len(agents)
class TestWebSocketMigrationPath:
    Tests to verify migration from manager to bridge pattern."
    Tests to verify migration from manager to bridge pattern.""

    def test_identify_files_needing_migration(self):
        "Identify all files that need migration to bridge pattern."
        analyzer = WebSocketPatternAnalyzer()
        base_path = Path(__file__).parent.parent.parent / netra_backend" / app / agents"
        files_to_migrate = []
        for filepath in base_path.rglob(*.py):"
        for filepath in base_path.rglob(*.py):"
        if __pycache__" in str(filepath) or test_ in filepath.name:"
        continue
        results = analyzer.analyze_file(filepath)
            # File needs migration if it uses manager or has mixed usage
        if results.get('uses_manager') or results.get('is_mixed'):
        files_to_migrate.append()
        'file': str(filepath.relative_to(base_path)),
        'manager_refs': len(results.get('manager_refs', []),
        'current_pattern': 'mixed' if results.get('is_mixed') else 'manager'
                
        if files_to_migrate:
        print()"
        print()"
        [U+1F4CB] Files Needing Migration to Bridge Pattern:")"
        for f in files_to_migrate:
        print(formatted_string)
                        # This test is informational, not a failure
        assert True
    def test_bridge_adapter_completeness(self):
        Test that bridge adapter covers all necessary WebSocket operations.""
        pass
        adapter = WebSocketBridgeAdapter()
        required_methods = [
        'emit_agent_started',
        'emit_agent_completed',
        'emit_thinking',
        'emit_tool_executing',
        'emit_tool_completed',
        'emit_error',
        'emit_progress',
        'has_websocket_bridge',
        'set_websocket_bridge'
    
        for method in required_methods:
        assert hasattr(adapter, "method), formatted_string"
        # Verify it's callable'
        method_obj = getattr(adapter, method)
        assert callable(method_obj), 
        if __name__ == __main__":"
            # Run tests with detailed output
)))))))))))))))
]]]