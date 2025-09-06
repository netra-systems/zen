"""Simple SSOT validation tests that verify the fixes are in place."""

import os
import subprocess
import pytest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment


class TestSSOTFixesApplied:
    """Verify that all SSOT fixes have been properly applied."""
    
    def test_json_handler_usage_in_observability(self):
        """Check that observability files use backend_json_handler instead of json.dumps."""
        # Files that were fixed
        files_to_check = [
            "netra_backend/app/agents/supervisor/observability_flow.py",
            "netra_backend/app/agents/supervisor/flow_logger.py",
            "netra_backend/app/agents/supervisor/comprehensive_observability.py"
        ]
        
        base_path = Path(__file__).parent.parent.parent  # Go up to project root
        
        for file_path in files_to_check:
            full_path = base_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for backend_json_handler usage
                assert "backend_json_handler" in content, f"{file_path} should use backend_json_handler"
                
                # Check that json.dumps is not used (except in comments)
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'json.dumps' in line and not line.strip().startswith('#'):
                        pytest.fail(f"{file_path}:{i} still uses json.dumps: {line.strip()}")
    
    def test_error_handling_in_actions_agent(self):
        """Check that ActionsToMeetGoalsSubAgent uses ErrorContext."""
        file_path = "netra_backend/app/agents/actions_to_meet_goals_sub_agent.py"
        base_path = Path(__file__).parent.parent.parent
        full_path = base_path / file_path
        
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for SSOT imports
            assert "from netra_backend.app.core.serialization.unified_json_handler import backend_json_handler" in content
            assert "from netra_backend.app.schemas.shared_types import ErrorContext" in content
            
            # Check that ErrorContext is used
            assert "ErrorContext(" in content, "Should use ErrorContext for error handling"
    
    def test_goals_triage_uses_llm_response_parser(self):
        """Check that GoalsTriageSubAgent uses LLMResponseParser."""
        file_path = "netra_backend/app/agents/goals_triage_sub_agent.py"
        base_path = Path(__file__).parent.parent.parent
        full_path = base_path / file_path
        
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for proper JSON handling
            assert "LLMResponseParser" in content, "Should use LLMResponseParser"
            assert "JSONErrorFixer" in content, "Should use JSONErrorFixer"
            
            # Check no direct json.dumps usage (except imports for type checking)
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'json.dumps(' in line and not line.strip().startswith('#') and 'TYPE_CHECKING' not in content[:content.find(line)]:
                    pytest.fail(f"Line {i} still uses json.dumps: {line.strip()}")
    
    def test_supervisor_uses_user_execution_context(self):
        """Check that SupervisorAgent uses UserExecutionContext pattern."""
        file_path = "netra_backend/app/agents/supervisor_consolidated.py"
        base_path = Path(__file__).parent.parent.parent
        full_path = base_path / file_path
        
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for UserExecutionContext imports and usage
            assert "from netra_backend.app.agents.supervisor.user_execution_context import" in content
            assert "UserExecutionContext" in content
            assert "DatabaseSessionManager" in content
            assert "managed_session" in content
            
            # Check that execute method accepts context
            assert "async def execute(self, context: UserExecutionContext" in content
            
            # Verify no session storage
            assert "self.db_session" not in content or "# NO user-specific data" in content
            assert "self.session =" not in content or "# NO user-specific data" in content
    
    def test_no_os_environ_usage(self):
        """Check that agents don't use os.environ directly."""
        files_to_check = [
            "netra_backend/app/agents/supervisor_consolidated.py",
            "netra_backend/app/agents/goals_triage_sub_agent.py",
            "netra_backend/app/agents/actions_to_meet_goals_sub_agent.py"
        ]
        
        base_path = Path(__file__).parent.parent.parent
        
        for file_path in files_to_check:
            full_path = base_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for os.environ usage
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'os.environ' in line and not line.strip().startswith('#'):
                        # Allow if it's in TYPE_CHECKING block or test code
                        if 'TYPE_CHECKING' not in content[:content.find(line)] and 'test' not in file_path.lower():
                            pytest.fail(f"{file_path}:{i} uses os.environ directly: {line.strip()}")
    
    def test_compilation_of_fixed_files(self):
        """Test that all fixed files compile without syntax errors."""
        files_to_compile = [
            "netra_backend/app/agents/supervisor_consolidated.py",
            "netra_backend/app/agents/supervisor/observability_flow.py", 
            "netra_backend/app/agents/supervisor/flow_logger.py",
            "netra_backend/app/agents/supervisor/comprehensive_observability.py",
            "netra_backend/app/agents/goals_triage_sub_agent.py",
            "netra_backend/app/agents/actions_to_meet_goals_sub_agent.py"
        ]
        
        base_path = Path(__file__).parent.parent.parent
        
        for file_path in files_to_compile:
            full_path = base_path / file_path
            if full_path.exists():
                # Try to compile the file
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    compile(code, file_path, 'exec')
                except SyntaxError as e:
                    pytest.fail(f"Syntax error in {file_path}: {e}")


class TestWebSocketIntegration:
    """Test WebSocket event integration."""
    
    def test_supervisor_websocket_events(self):
        """Verify supervisor properly emits WebSocket events."""
        file_path = "netra_backend/app/agents/supervisor_consolidated.py"
        base_path = Path(__file__).parent.parent.parent
        full_path = base_path / file_path
        
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for WebSocket emission methods
            assert "_emit_thinking" in content, "Should have _emit_thinking method"
            assert "websocket_bridge" in content, "Should use websocket_bridge"
            assert "emit_agent_event" in content
            
            # Check that context is used for user isolation
            assert "context.websocket_connection_id" in content or "context.user_id" in content
    
    def test_agents_use_websocket_adapter(self):
        """Check that agents use proper WebSocket adapters."""
        files_to_check = [
            ("netra_backend/app/agents/goals_triage_sub_agent.py", ["emit_agent_started", "emit_thinking", "emit_progress"]),
            ("netra_backend/app/agents/actions_to_meet_goals_sub_agent.py", ["emit_agent_started", "emit_thinking"])
        ]
        
        base_path = Path(__file__).parent.parent.parent
        
        for file_path, required_events in files_to_check:
            full_path = base_path / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for event in required_events:
                    assert event in content, f"{file_path} should emit {event} for chat value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])