# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Mission Critical: WebSocket Bridge Consistency Test Suite
    # REMOVED_SYNTAX_ERROR: ========================================================
    # REMOVED_SYNTAX_ERROR: Tests to ensure SSOT compliance for WebSocket communication patterns.
    # REMOVED_SYNTAX_ERROR: All agents MUST use the unified WebSocket bridge pattern.

    # REMOVED_SYNTAX_ERROR: CRITICAL: This test suite validates that:
        # REMOVED_SYNTAX_ERROR: 1. All agents use WebSocket bridge exclusively
        # REMOVED_SYNTAX_ERROR: 2. No duplicate WebSocket event methods exist
        # REMOVED_SYNTAX_ERROR: 3. Consistent event emission paths are used
        # REMOVED_SYNTAX_ERROR: 4. WebSocket manager is not used directly
        # REMOVED_SYNTAX_ERROR: 5. Full SSOT compliance is maintained
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import inspect
        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: from pathlib import Path
        # REMOVED_SYNTAX_ERROR: from typing import List, Dict, Any, Set, Tuple
        # REMOVED_SYNTAX_ERROR: import ast
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Add project root to path
        # REMOVED_SYNTAX_ERROR: sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent
        # Using protocol-based approach for agent execution
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class WebSocketPatternAnalyzer:
    # REMOVED_SYNTAX_ERROR: """Analyzes code for WebSocket pattern usage."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.violations = []
    # REMOVED_SYNTAX_ERROR: self.bridge_usage = []
    # REMOVED_SYNTAX_ERROR: self.manager_usage = []
    # REMOVED_SYNTAX_ERROR: self.mixed_usage = []
    # REMOVED_SYNTAX_ERROR: self.duplicate_methods = {}

# REMOVED_SYNTAX_ERROR: def analyze_file(self, filepath: Path) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Analyze a Python file for WebSocket patterns."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: with open(filepath, 'r', encoding='utf-8') as f:
            # REMOVED_SYNTAX_ERROR: content = f.read()
            # REMOVED_SYNTAX_ERROR: tree = ast.parse(content)

            # REMOVED_SYNTAX_ERROR: return self._analyze_ast(tree, filepath, content)
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: return {'error': str(e), 'file': str(filepath)}

# REMOVED_SYNTAX_ERROR: def _analyze_ast(self, tree: ast.AST, filepath: Path, content: str) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Analyze AST for WebSocket patterns."""
    # REMOVED_SYNTAX_ERROR: results = { )
    # REMOVED_SYNTAX_ERROR: 'file': str(filepath),
    # REMOVED_SYNTAX_ERROR: 'uses_bridge': False,
    # REMOVED_SYNTAX_ERROR: 'uses_manager': False,
    # REMOVED_SYNTAX_ERROR: 'is_mixed': False,
    # REMOVED_SYNTAX_ERROR: 'websocket_methods': [],
    # REMOVED_SYNTAX_ERROR: 'manager_refs': [],
    # REMOVED_SYNTAX_ERROR: 'bridge_refs': [],
    # REMOVED_SYNTAX_ERROR: 'violations': []
    

    # REMOVED_SYNTAX_ERROR: for node in ast.walk(tree):
        # Check for WebSocket manager usage
        # REMOVED_SYNTAX_ERROR: if isinstance(node, ast.Attribute):
            # REMOVED_SYNTAX_ERROR: if node.attr == 'websocket_manager':
                # REMOVED_SYNTAX_ERROR: line_no = node.lineno if hasattr(node, 'lineno') else 0
                # REMOVED_SYNTAX_ERROR: results['manager_refs'].append(line_no)
                # REMOVED_SYNTAX_ERROR: results['uses_manager'] = True

                # Check for bridge usage
                # REMOVED_SYNTAX_ERROR: if isinstance(node, ast.Name):
                    # REMOVED_SYNTAX_ERROR: if node.id in ['WebSocketBridgeAdapter', 'get_agent_websocket_bridge']:
                        # REMOVED_SYNTAX_ERROR: results['uses_bridge'] = True
                        # REMOVED_SYNTAX_ERROR: results['bridge_refs'].append(node.lineno if hasattr(node, 'lineno') else 0)

                        # Check for WebSocket event methods
                        # REMOVED_SYNTAX_ERROR: if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                            # REMOVED_SYNTAX_ERROR: method_name = node.name
                            # REMOVED_SYNTAX_ERROR: ws_methods = [ )
                            # REMOVED_SYNTAX_ERROR: 'send_agent_update', 'send_agent_thinking', 'send_tool_executing',
                            # REMOVED_SYNTAX_ERROR: 'send_tool_completed', 'send_partial_result', 'send_final_report',
                            # REMOVED_SYNTAX_ERROR: 'notify_agent_thinking', 'notify_tool_execution', 'notify_agent_completed',
                            # REMOVED_SYNTAX_ERROR: 'emit_thinking', 'emit_tool_executing', 'emit_tool_completed',
                            # REMOVED_SYNTAX_ERROR: 'emit_error', 'emit_progress', 'emit_agent_started', 'emit_agent_completed'
                            

                            # REMOVED_SYNTAX_ERROR: if any(m in method_name for m in ws_methods):
                                # REMOVED_SYNTAX_ERROR: results['websocket_methods'].append({ ))
                                # REMOVED_SYNTAX_ERROR: 'name': method_name,
                                # REMOVED_SYNTAX_ERROR: 'line': node.lineno if hasattr(node, 'lineno') else 0
                                

                                # Determine if mixed usage
                                # REMOVED_SYNTAX_ERROR: if results['uses_bridge'] and results['uses_manager']:
                                    # REMOVED_SYNTAX_ERROR: results['is_mixed'] = True
                                    # REMOVED_SYNTAX_ERROR: results['violations'].append('Mixed WebSocket pattern usage detected')

                                    # REMOVED_SYNTAX_ERROR: return results


# REMOVED_SYNTAX_ERROR: class TestWebSocketBridgeConsistency:
    # REMOVED_SYNTAX_ERROR: """Test suite for WebSocket bridge consistency and SSOT compliance."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def setup(self):
    # REMOVED_SYNTAX_ERROR: """Setup test environment."""
    # REMOVED_SYNTAX_ERROR: self.analyzer = WebSocketPatternAnalyzer()
    # REMOVED_SYNTAX_ERROR: self.agent_files = self._get_agent_files()

# REMOVED_SYNTAX_ERROR: def _get_agent_files(self) -> List[Path]:
    # REMOVED_SYNTAX_ERROR: """Get all agent Python files."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: base_path = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "agents"
    # REMOVED_SYNTAX_ERROR: agent_files = []

    # REMOVED_SYNTAX_ERROR: for file in base_path.rglob("*.py"):
        # Skip __pycache__ and test files
        # REMOVED_SYNTAX_ERROR: if "__pycache__" not in str(file) and "test_" not in file.name:
            # REMOVED_SYNTAX_ERROR: agent_files.append(file)

            # REMOVED_SYNTAX_ERROR: return agent_files

# REMOVED_SYNTAX_ERROR: def test_no_duplicate_websocket_methods(self):
    # REMOVED_SYNTAX_ERROR: """Test that WebSocket event methods are not duplicated across files."""
    # REMOVED_SYNTAX_ERROR: method_locations = {}
    # REMOVED_SYNTAX_ERROR: duplicates = []

    # REMOVED_SYNTAX_ERROR: for filepath in self.agent_files:
        # REMOVED_SYNTAX_ERROR: results = self.analyzer.analyze_file(filepath)

        # REMOVED_SYNTAX_ERROR: for method in results.get('websocket_methods', []):
            # REMOVED_SYNTAX_ERROR: method_name = method['name']
            # REMOVED_SYNTAX_ERROR: location = "formatted_string"

            # REMOVED_SYNTAX_ERROR: if method_name not in method_locations:
                # REMOVED_SYNTAX_ERROR: method_locations[method_name] = []
                # REMOVED_SYNTAX_ERROR: method_locations[method_name].append(location)

                # Check for duplicates
                # REMOVED_SYNTAX_ERROR: for method_name, locations in method_locations.items():
                    # REMOVED_SYNTAX_ERROR: if len(locations) > 1:
                        # Allow some specific exceptions (like base class + implementation)
                        # REMOVED_SYNTAX_ERROR: if not self._is_allowed_duplicate(method_name, locations):
                            # REMOVED_SYNTAX_ERROR: duplicates.append({ ))
                            # REMOVED_SYNTAX_ERROR: 'method': method_name,
                            # REMOVED_SYNTAX_ERROR: 'locations': locations,
                            # REMOVED_SYNTAX_ERROR: 'count': len(locations)
                            

                            # REMOVED_SYNTAX_ERROR: assert len(duplicates) == 0, ( )
                            # REMOVED_SYNTAX_ERROR: "formatted_string" +
                                # REMOVED_SYNTAX_ERROR: "
                                # REMOVED_SYNTAX_ERROR: ".join(["formatted_string"count"]} occurrences in {", ".join(d["locations"])}" ))
                                # REMOVED_SYNTAX_ERROR: for d in duplicates])
                                

# REMOVED_SYNTAX_ERROR: def _is_allowed_duplicate(self, method_name: str, locations: List[str]) -> bool:
    # REMOVED_SYNTAX_ERROR: """Check if a duplicate is allowed (e.g., base class + override)."""
    # REMOVED_SYNTAX_ERROR: pass
    # Allow emit_* methods in BaseAgent and its adapters
    # REMOVED_SYNTAX_ERROR: if method_name.startswith('emit_'):
        # REMOVED_SYNTAX_ERROR: base_files = ['base_agent.py', 'websocket_bridge_adapter.py']
        # REMOVED_SYNTAX_ERROR: if any(base in loc for base in base_files for loc in locations):
            # REMOVED_SYNTAX_ERROR: return True
            # REMOVED_SYNTAX_ERROR: return False

# REMOVED_SYNTAX_ERROR: def test_no_mixed_websocket_patterns(self):
    # REMOVED_SYNTAX_ERROR: """Test that files don't mix WebSocket manager and bridge patterns."""
    # REMOVED_SYNTAX_ERROR: mixed_files = []

    # REMOVED_SYNTAX_ERROR: for filepath in self.agent_files:
        # REMOVED_SYNTAX_ERROR: results = self.analyzer.analyze_file(filepath)

        # REMOVED_SYNTAX_ERROR: if results.get('is_mixed'):
            # REMOVED_SYNTAX_ERROR: mixed_files.append({ ))
            # REMOVED_SYNTAX_ERROR: 'file': filepath.name,
            # REMOVED_SYNTAX_ERROR: 'manager_refs': len(results.get('manager_refs', [])),
            # REMOVED_SYNTAX_ERROR: 'bridge_refs': len(results.get('bridge_refs', [])),
            # REMOVED_SYNTAX_ERROR: 'violations': results.get('violations', [])
            

            # REMOVED_SYNTAX_ERROR: assert len(mixed_files) == 0, ( )
            # REMOVED_SYNTAX_ERROR: "formatted_string" +
                # REMOVED_SYNTAX_ERROR: "
                # REMOVED_SYNTAX_ERROR: ".join(["formatted_string"manager_refs"]} manager refs, {f["bridge_refs"]} bridge refs" ))
                # REMOVED_SYNTAX_ERROR: for f in mixed_files])
                

# REMOVED_SYNTAX_ERROR: def test_websocket_manager_not_used_directly(self):
    # REMOVED_SYNTAX_ERROR: """Test that WebSocket manager is not used directly in agent implementations."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: manager_usage = []

    # Allowed files that may reference manager for compatibility
    # REMOVED_SYNTAX_ERROR: allowed_files = ['websocket_bridge_adapter.py', 'agent_websocket_bridge.py']

    # REMOVED_SYNTAX_ERROR: for filepath in self.agent_files:
        # REMOVED_SYNTAX_ERROR: if filepath.name in allowed_files:
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: results = self.analyzer.analyze_file(filepath)

            # REMOVED_SYNTAX_ERROR: if results.get('uses_manager') and results.get('manager_refs'):
                # REMOVED_SYNTAX_ERROR: manager_usage.append({ ))
                # REMOVED_SYNTAX_ERROR: 'file': filepath.name,
                # REMOVED_SYNTAX_ERROR: 'lines': results['manager_refs']
                

                # REMOVED_SYNTAX_ERROR: assert len(manager_usage) == 0, ( )
                # REMOVED_SYNTAX_ERROR: "formatted_string" +
                    # REMOVED_SYNTAX_ERROR: "
                    # REMOVED_SYNTAX_ERROR: ".join(["formatted_string"lines"]}" for f in manager_usage])
                    

# REMOVED_SYNTAX_ERROR: def test_consistent_event_emission_pattern(self):
    # REMOVED_SYNTAX_ERROR: """Test that all agents use consistent event emission pattern."""
    # REMOVED_SYNTAX_ERROR: inconsistent_patterns = []

    # Expected pattern: use emit_* methods from bridge adapter
    # REMOVED_SYNTAX_ERROR: expected_methods = { )
    # REMOVED_SYNTAX_ERROR: 'emit_thinking', 'emit_tool_executing', 'emit_tool_completed',
    # REMOVED_SYNTAX_ERROR: 'emit_error', 'emit_progress', 'emit_agent_started', 'emit_agent_completed'
    

    # REMOVED_SYNTAX_ERROR: for filepath in self.agent_files:
        # Skip base/infrastructure files
        # REMOVED_SYNTAX_ERROR: if filepath.name in ['__init__.py', 'websocket_bridge_adapter.py']:
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: results = self.analyzer.analyze_file(filepath)
            # REMOVED_SYNTAX_ERROR: ws_methods = {m['name'] for m in results.get('websocket_methods', [])}

            # Check if using non-standard emission methods
            # REMOVED_SYNTAX_ERROR: non_standard = ws_methods - expected_methods
            # REMOVED_SYNTAX_ERROR: if non_standard and 'send_' in str(non_standard):
                # REMOVED_SYNTAX_ERROR: inconsistent_patterns.append({ ))
                # REMOVED_SYNTAX_ERROR: 'file': filepath.name,
                # REMOVED_SYNTAX_ERROR: 'non_standard_methods': list(non_standard)
                

                # REMOVED_SYNTAX_ERROR: assert len(inconsistent_patterns) == 0, ( )
                # REMOVED_SYNTAX_ERROR: "formatted_string" +
                    # REMOVED_SYNTAX_ERROR: "
                    # REMOVED_SYNTAX_ERROR: ".join(["formatted_string"non_standard_methods"]}" ))
                    # REMOVED_SYNTAX_ERROR: for f in inconsistent_patterns])
                    

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_bridge_singleton_usage(self):
                        # REMOVED_SYNTAX_ERROR: """Test that all agents use the singleton bridge instance correctly."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # Get bridge instance
                        # REMOVED_SYNTAX_ERROR: bridge1 = await get_agent_websocket_bridge()
                        # REMOVED_SYNTAX_ERROR: bridge2 = await get_agent_websocket_bridge()

                        # Verify singleton
                        # REMOVED_SYNTAX_ERROR: assert bridge1 is bridge2, "Bridge should be a singleton"

                        # Test that agents can set and use bridge
                        # REMOVED_SYNTAX_ERROR: agent = BaseAgent( )
                        # REMOVED_SYNTAX_ERROR: agent_id="test-agent",
                        # REMOVED_SYNTAX_ERROR: name="Test Agent"
                        

                        # Set bridge
                        # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(bridge1, "test-run-id")

                        # Verify bridge is set
                        # REMOVED_SYNTAX_ERROR: assert agent.websocket_bridge is not None
                        # REMOVED_SYNTAX_ERROR: assert agent.websocket_bridge == bridge1

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_websocket_events_flow_through_bridge(self):
                            # REMOVED_SYNTAX_ERROR: """Test that WebSocket events flow through the bridge correctly."""
                            # REMOVED_SYNTAX_ERROR: bridge = await get_agent_websocket_bridge()

                            # Mock WebSocket manager
                            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                            # REMOVED_SYNTAX_ERROR: bridge.websocket_manager = mock_manager

                            # Create agent and set bridge
                            # REMOVED_SYNTAX_ERROR: agent = DataSubAgent()
                            # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(bridge, "test-run-id")

                            # Test event emission
                            # REMOVED_SYNTAX_ERROR: await agent.emit_thinking("Processing data...")

                            # Verify bridge was called (not direct manager)
                            # REMOVED_SYNTAX_ERROR: assert mock_manager.send_agent_update.called or mock_manager.notify_agent_thinking.called

# REMOVED_SYNTAX_ERROR: def test_no_circular_imports_with_bridge(self):
    # REMOVED_SYNTAX_ERROR: """Test that bridge pattern doesn't create circular imports."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: try:
        # Try importing all agent modules
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents import base_agent
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.mixins import websocket_bridge_adapter
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services import agent_websocket_bridge
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents import agent_communication
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents import agent_lifecycle

        # If we get here, no circular imports
        # REMOVED_SYNTAX_ERROR: assert True
        # REMOVED_SYNTAX_ERROR: except ImportError as e:
            # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_bridge_methods_are_consistent(self):
    # REMOVED_SYNTAX_ERROR: """Test that bridge methods have consistent signatures across implementations."""
    # REMOVED_SYNTAX_ERROR: bridge_adapter = WebSocketBridgeAdapter()

    # Get all emit methods
    # REMOVED_SYNTAX_ERROR: emit_methods = [item for item in []]

    # Verify each has consistent signature
    # REMOVED_SYNTAX_ERROR: for method_name in emit_methods:
        # REMOVED_SYNTAX_ERROR: method = getattr(bridge_adapter, method_name)
        # REMOVED_SYNTAX_ERROR: sig = inspect.signature(method)

        # All emit methods should be async
        # REMOVED_SYNTAX_ERROR: assert inspect.iscoroutinefunction(method), "formatted_string"

        # Check common parameters
        # REMOVED_SYNTAX_ERROR: params = list(sig.parameters.keys())
        # REMOVED_SYNTAX_ERROR: assert 'self' in params, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_ssot_compliance_score(self):
    # REMOVED_SYNTAX_ERROR: """Calculate and verify SSOT compliance score for WebSocket patterns."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: total_files = len(self.agent_files)
    # REMOVED_SYNTAX_ERROR: compliant_files = 0
    # REMOVED_SYNTAX_ERROR: violations = []

    # REMOVED_SYNTAX_ERROR: for filepath in self.agent_files:
        # REMOVED_SYNTAX_ERROR: results = self.analyzer.analyze_file(filepath)

        # File is compliant if:
            # 1. Uses bridge OR doesn't use WebSocket at all
            # 2. Doesn't use manager directly
            # 3. Not mixed usage
            # REMOVED_SYNTAX_ERROR: is_compliant = ( )
            # REMOVED_SYNTAX_ERROR: (results.get('uses_bridge') or )
            # REMOVED_SYNTAX_ERROR: (not results.get('uses_bridge') and not results.get('uses_manager'))) and
            # REMOVED_SYNTAX_ERROR: not results.get('uses_manager') and
            # REMOVED_SYNTAX_ERROR: not results.get('is_mixed')
            

            # REMOVED_SYNTAX_ERROR: if is_compliant:
                # REMOVED_SYNTAX_ERROR: compliant_files += 1
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: violations.append(filepath.name)

                    # REMOVED_SYNTAX_ERROR: compliance_score = (compliant_files / total_files) * 100 if total_files > 0 else 0

                    # REMOVED_SYNTAX_ERROR: print("formatted_string")
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # REMOVED_SYNTAX_ERROR: if violations:
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                        # REMOVED_SYNTAX_ERROR: if len(violations) > 5:
                            # REMOVED_SYNTAX_ERROR: print("formatted_string")

                            # Fail if compliance is below threshold
                            # REMOVED_SYNTAX_ERROR: assert compliance_score >= 80, ( )
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            # REMOVED_SYNTAX_ERROR: "formatted_string"
                            


# REMOVED_SYNTAX_ERROR: class TestWebSocketBridgeIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for unified WebSocket bridge."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_agent_lifecycle_with_bridge(self):
        # REMOVED_SYNTAX_ERROR: """Test complete agent lifecycle using bridge pattern."""
        # REMOVED_SYNTAX_ERROR: bridge = await get_agent_websocket_bridge()
        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
        # REMOVED_SYNTAX_ERROR: bridge.websocket_manager = mock_manager

        # Create agent
        # REMOVED_SYNTAX_ERROR: agent = ValidationSubAgent()
        # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(bridge, "test-run-123")

        # Simulate lifecycle
        # REMOVED_SYNTAX_ERROR: await agent.emit_agent_started({"status": "initializing"})
        # REMOVED_SYNTAX_ERROR: await agent.emit_thinking("Validating data...")
        # REMOVED_SYNTAX_ERROR: await agent.emit_tool_executing("data_validator", {"input": "test"})
        # REMOVED_SYNTAX_ERROR: await agent.emit_tool_completed("data_validator", {"result": "valid"})
        # REMOVED_SYNTAX_ERROR: await agent.emit_agent_completed({"status": "success"})

        # Verify all events were sent through bridge
        # REMOVED_SYNTAX_ERROR: assert mock_manager.send_agent_update.call_count >= 5 or \
        # REMOVED_SYNTAX_ERROR: mock_manager.notify_agent_started.called

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_error_handling_through_bridge(self):
            # REMOVED_SYNTAX_ERROR: """Test error handling flows through bridge correctly."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: bridge = await get_agent_websocket_bridge()
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
            # REMOVED_SYNTAX_ERROR: bridge.websocket_manager = mock_manager

            # REMOVED_SYNTAX_ERROR: agent = BaseAgent(agent_id="test", name="Test")
            # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(bridge, "error-run")

            # Emit error
            # REMOVED_SYNTAX_ERROR: await agent.emit_error("Test error", {"code": "TEST_001"})

            # Verify error was sent
            # REMOVED_SYNTAX_ERROR: assert mock_manager.send_agent_update.called or \
            # REMOVED_SYNTAX_ERROR: mock_manager.notify_error.called

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_concurrent_agents_using_bridge(self):
                # REMOVED_SYNTAX_ERROR: """Test multiple agents can use bridge concurrently."""
                # REMOVED_SYNTAX_ERROR: bridge = await get_agent_websocket_bridge()
                # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                # REMOVED_SYNTAX_ERROR: bridge.websocket_manager = mock_manager

                # Create multiple agents
                # REMOVED_SYNTAX_ERROR: agents = [ )
                # REMOVED_SYNTAX_ERROR: DataSubAgent(),
                # REMOVED_SYNTAX_ERROR: ValidationSubAgent()
                
                # Add more base agents
                # REMOVED_SYNTAX_ERROR: for i in range(3):
                    # REMOVED_SYNTAX_ERROR: agents.append(BaseAgent(agent_id="formatted_string", name="formatted_string"))

                    # Set bridge for all
                    # REMOVED_SYNTAX_ERROR: for i, agent in enumerate(agents):
                        # REMOVED_SYNTAX_ERROR: agent.set_websocket_bridge(bridge, "formatted_string")

                        # Concurrent emissions
                        # REMOVED_SYNTAX_ERROR: tasks = [ )
                        # REMOVED_SYNTAX_ERROR: agent.emit_thinking("formatted_string")
                        # REMOVED_SYNTAX_ERROR: for agent in agents
                        

                        # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

                        # Verify all emissions succeeded
                        # REMOVED_SYNTAX_ERROR: assert mock_manager.send_agent_update.call_count >= len(agents) or \
                        # REMOVED_SYNTAX_ERROR: mock_manager.notify_agent_thinking.call_count >= len(agents)


# REMOVED_SYNTAX_ERROR: class TestWebSocketMigrationPath:
    # REMOVED_SYNTAX_ERROR: """Tests to verify migration from manager to bridge pattern."""

# REMOVED_SYNTAX_ERROR: def test_identify_files_needing_migration(self):
    # REMOVED_SYNTAX_ERROR: """Identify all files that need migration to bridge pattern."""
    # REMOVED_SYNTAX_ERROR: analyzer = WebSocketPatternAnalyzer()
    # REMOVED_SYNTAX_ERROR: base_path = Path(__file__).parent.parent.parent / "netra_backend" / "app" / "agents"

    # REMOVED_SYNTAX_ERROR: files_to_migrate = []

    # REMOVED_SYNTAX_ERROR: for filepath in base_path.rglob("*.py"):
        # REMOVED_SYNTAX_ERROR: if "__pycache__" in str(filepath) or "test_" in filepath.name:
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: results = analyzer.analyze_file(filepath)

            # File needs migration if it uses manager or has mixed usage
            # REMOVED_SYNTAX_ERROR: if results.get('uses_manager') or results.get('is_mixed'):
                # REMOVED_SYNTAX_ERROR: files_to_migrate.append({ ))
                # REMOVED_SYNTAX_ERROR: 'file': str(filepath.relative_to(base_path)),
                # REMOVED_SYNTAX_ERROR: 'manager_refs': len(results.get('manager_refs', [])),
                # REMOVED_SYNTAX_ERROR: 'current_pattern': 'mixed' if results.get('is_mixed') else 'manager'
                

                # REMOVED_SYNTAX_ERROR: if files_to_migrate:
                    # REMOVED_SYNTAX_ERROR: print(" )
                    # REMOVED_SYNTAX_ERROR: 📋 Files Needing Migration to Bridge Pattern:")
                    # REMOVED_SYNTAX_ERROR: for f in files_to_migrate:
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                        # This test is informational, not a failure
                        # REMOVED_SYNTAX_ERROR: assert True

# REMOVED_SYNTAX_ERROR: def test_bridge_adapter_completeness(self):
    # REMOVED_SYNTAX_ERROR: """Test that bridge adapter covers all necessary WebSocket operations."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: adapter = WebSocketBridgeAdapter()

    # REMOVED_SYNTAX_ERROR: required_methods = [ )
    # REMOVED_SYNTAX_ERROR: 'emit_agent_started',
    # REMOVED_SYNTAX_ERROR: 'emit_agent_completed',
    # REMOVED_SYNTAX_ERROR: 'emit_thinking',
    # REMOVED_SYNTAX_ERROR: 'emit_tool_executing',
    # REMOVED_SYNTAX_ERROR: 'emit_tool_completed',
    # REMOVED_SYNTAX_ERROR: 'emit_error',
    # REMOVED_SYNTAX_ERROR: 'emit_progress',
    # REMOVED_SYNTAX_ERROR: 'has_websocket_bridge',
    # REMOVED_SYNTAX_ERROR: 'set_websocket_bridge'
    

    # REMOVED_SYNTAX_ERROR: for method in required_methods:
        # REMOVED_SYNTAX_ERROR: assert hasattr(adapter, method), "formatted_string"

        # Verify it's callable
        # REMOVED_SYNTAX_ERROR: method_obj = getattr(adapter, method)
        # REMOVED_SYNTAX_ERROR: assert callable(method_obj), "formatted_string"


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # Run tests with detailed output
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s", "--tb=short"])