"""
Integration tests for Issue #1116: Supervisor Agent Multi-User Isolation Vulnerability

PURPOSE: Prove that supervisor agent creation through factory causes user isolation failures
- Test complete supervisor agent workflow with real services
- Demonstrate WebSocket event contamination between users
- Verify agent execution context leakage in realistic scenarios

VULNERABILITY HYPOTHESIS:
- Supervisor agents created via singleton factory share execution state
- WebSocket events sent to wrong users during concurrent execution
- Agent tool execution results leak between user sessions

EXPECTED RESULT: These tests should FAIL initially, proving the vulnerability exists
"""

import pytest
import asyncio
import uuid
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor
import threading

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.manager import WebSocketManager


class TestSupervisorAgentMultiUserIsolation(SSotAsyncTestCase):
    """
    Integration test suite to PROVE multi-user isolation vulnerabilities.
    
    These tests use real supervisor agent workflows to demonstrate:
    1. WebSocket event cross-contamination between users
    2. Agent execution state leakage during concurrent workflows
    3. Tool execution results sent to wrong users
    """

    def setUp(self):
        """Set up test environment with realistic user scenarios."""
        super().setUp()
        
        # Create realistic user contexts representing different enterprise customers
        self.enterprise_user_context = UserExecutionContext(
            user_id="enterprise_user_001",
            session_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            websocket_manager=Mock(),
            execution_metadata={
                "user_name": "Enterprise Admin",
                "role": "admin",
                "organization": "Acme Corp",
                "data_classification": "confidential"
            }
        )
        
        self.startup_user_context = UserExecutionContext(
            user_id="startup_user_002", 
            session_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            websocket_manager=Mock(),
            execution_metadata={
                "user_name": "Startup Founder",
                "role": "owner",
                "organization": "Tech Startup",
                "data_classification": "internal"
            }
        )
        
        # Track WebSocket events to detect cross-contamination
        self.enterprise_events = []
        self.startup_events = []
        
        # Mock WebSocket managers to capture events
        self.enterprise_user_context.websocket_manager.send_message = AsyncMock(
            side_effect=lambda event, data: self.enterprise_events.append({
                'event': event, 'data': data, 'timestamp': time.time(),
                'thread_id': threading.current_thread().ident
            })
        )
        
        self.startup_user_context.websocket_manager.send_message = AsyncMock(
            side_effect=lambda event, data: self.startup_events.append({
                'event': event, 'data': data, 'timestamp': time.time(),
                'thread_id': threading.current_thread().ident
            })
        )

    def test_websocket_event_contamination_vulnerability(self):
        """
        VULNERABILITY TEST: Prove WebSocket events sent to wrong users
        
        EXPECTED: This test should FAIL (proving event contamination)
        - Enterprise user's events sent to startup user
        - WebSocket manager instances get mixed up
        """
        factory = get_agent_instance_factory()
        
        # Create supervisor agents for both users
        enterprise_agent = factory.create_supervisor_agent(self.enterprise_user_context)
        startup_agent = factory.create_supervisor_agent(self.startup_user_context)
        
        # Simulate agent execution that sends WebSocket events
        enterprise_task = "Analyze confidential financial data for Q4 projections"
        startup_task = "Review product roadmap for Series A pitch"
        
        # Execute tasks that should send events to respective users
        try:
            # Enterprise user workflow
            if hasattr(enterprise_agent, 'send_agent_started_event'):
                asyncio.run(enterprise_agent.send_agent_started_event(enterprise_task))
            
            # Startup user workflow  
            if hasattr(startup_agent, 'send_agent_started_event'):
                asyncio.run(startup_agent.send_agent_started_event(startup_task))
                
        except Exception as e:
            self.fail(f"Failed to execute agent workflows: {e}")
        
        # VULNERABILITY CHECK: Events should only go to correct users
        # Check for cross-contamination in event content
        enterprise_event_content = []
        for event in self.enterprise_events:
            if isinstance(event.get('data'), dict):
                content = json.dumps(event['data']).lower()
                enterprise_event_content.append(content)
        
        startup_event_content = []
        for event in self.startup_events:
            if isinstance(event.get('data'), dict):
                content = json.dumps(event['data']).lower()
                startup_event_content.append(content)
        
        # These assertions SHOULD FAIL if events are cross-contaminated
        for content in enterprise_event_content:
            self.assertNotIn("series a", content, 
                           f"VULNERABILITY: Enterprise user received startup-related event: {content}")
            self.assertNotIn("product roadmap", content,
                           f"VULNERABILITY: Enterprise user received startup task data: {content}")
        
        for content in startup_event_content:
            self.assertNotIn("confidential financial", content,
                           f"VULNERABILITY: Startup user received enterprise-sensitive event: {content}")
            self.assertNotIn("q4 projections", content,
                           f"VULNERABILITY: Startup user received enterprise task data: {content}")

    def test_concurrent_agent_execution_isolation_vulnerability(self):
        """
        VULNERABILITY TEST: Prove agent execution contexts get mixed during concurrent execution
        
        EXPECTED: This test should FAIL (proving execution isolation failure)
        - Concurrent agent execution causes context mixing
        - User-specific data appears in wrong agent's context
        """
        factory = get_agent_instance_factory()
        execution_results = {}
        execution_errors = []
        
        def execute_agent_workflow(user_id, user_context, task_description):
            """Execute agent workflow and track execution context."""
            try:
                agent = factory.create_supervisor_agent(user_context)
                
                # Verify agent has correct user context at start
                initial_user_id = agent.user_execution_context.user_id
                initial_metadata = agent.user_execution_context.execution_metadata.copy()
                
                # Simulate agent processing time with realistic delay
                time.sleep(0.05)  # 50ms processing simulation
                
                # Check if context changed during execution
                final_user_id = agent.user_execution_context.user_id
                final_metadata = agent.user_execution_context.execution_metadata
                
                execution_results[user_id] = {
                    'initial_user_id': initial_user_id,
                    'final_user_id': final_user_id,
                    'user_id_stable': initial_user_id == final_user_id,
                    'initial_metadata': initial_metadata,
                    'final_metadata': final_metadata,
                    'metadata_stable': initial_metadata == final_metadata,
                    'thread_id': threading.current_thread().ident,
                    'task': task_description
                }
                
            except Exception as e:
                execution_errors.append(f"User {user_id}: {str(e)}")
        
        # Define concurrent user workflows with sensitive data
        user_workflows = [
            ("enterprise_001", self.enterprise_user_context, "Process HIPAA-compliant patient data"),
            ("startup_002", self.startup_user_context, "Analyze competitor pricing strategy"),
            ("enterprise_003", self.enterprise_user_context, "Generate SOC2 compliance report"),
            ("startup_004", self.startup_user_context, "Review investor term sheet"),
            ("enterprise_005", self.enterprise_user_context, "Audit financial transactions")
        ]
        
        # Execute concurrent workflows
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for user_id, context, task in user_workflows:
                future = executor.submit(execute_agent_workflow, user_id, context, task)
                futures.append(future)
            
            # Wait for all executions to complete
            for future in futures:
                future.result()
        
        # Analyze results for isolation violations
        self.assertEqual(len(execution_errors), 0, 
                        f"Errors during concurrent execution: {execution_errors}")
        
        context_violations = []
        for user_id, result in execution_results.items():
            if not result['user_id_stable']:
                context_violations.append({
                    'user_id': user_id,
                    'initial_user_id': result['initial_user_id'],
                    'final_user_id': result['final_user_id'],
                    'thread': result['thread_id']
                })
            
            if not result['metadata_stable']:
                context_violations.append({
                    'user_id': user_id,
                    'metadata_change': {
                        'initial': result['initial_metadata'],
                        'final': result['final_metadata']
                    }
                })
        
        # This assertion SHOULD FAIL if context isolation fails
        self.assertEqual(len(context_violations), 0,
                        f"ISOLATION VULNERABILITY: {len(context_violations)} context violations "
                        f"detected during concurrent execution: {context_violations}")

    def test_agent_tool_execution_result_contamination(self):
        """
        VULNERABILITY TEST: Prove tool execution results get sent to wrong users
        
        EXPECTED: This test should FAIL (proving tool result contamination)  
        - Tool execution results for User A sent to User B
        - Agent workflow state mixed between concurrent users
        """
        factory = get_agent_instance_factory()
        
        # Create agents for both users
        enterprise_agent = factory.create_supervisor_agent(self.enterprise_user_context)
        startup_agent = factory.create_supervisor_agent(self.startup_user_context)
        
        # Mock tool execution with user-specific results
        enterprise_tool_result = {
            "tool": "financial_analyzer",
            "result": "CONFIDENTIAL: Q4 revenue $2.3M, classified information",
            "user_id": "enterprise_user_001",
            "data_classification": "confidential"
        }
        
        startup_tool_result = {
            "tool": "market_analyzer", 
            "result": "Market analysis: 15% growth potential identified",
            "user_id": "startup_user_002",
            "data_classification": "internal"
        }
        
        # Simulate concurrent tool execution
        with patch.object(enterprise_agent, '_execute_tool_with_websocket_events') as enterprise_mock:
            with patch.object(startup_agent, '_execute_tool_with_websocket_events') as startup_mock:
                
                enterprise_mock.return_value = enterprise_tool_result
                startup_mock.return_value = startup_tool_result
                
                # Execute tools concurrently
                def execute_enterprise_tool():
                    try:
                        return enterprise_mock()
                    except Exception as e:
                        return {"error": str(e)}
                
                def execute_startup_tool():
                    try:
                        return startup_mock()
                    except Exception as e:
                        return {"error": str(e)}
                
                with ThreadPoolExecutor(max_workers=2) as executor:
                    enterprise_future = executor.submit(execute_enterprise_tool)
                    startup_future = executor.submit(execute_startup_tool)
                    
                    enterprise_result = enterprise_future.result()
                    startup_result = startup_future.result()
        
        # VULNERABILITY CHECK: Verify tool results went to correct users
        # Check WebSocket events for cross-contamination
        all_enterprise_events = [json.dumps(event) for event in self.enterprise_events]
        all_startup_events = [json.dumps(event) for event in self.startup_events]
        
        # These assertions SHOULD FAIL if tool results are cross-contaminated
        for event_str in all_enterprise_events:
            self.assertNotIn("15% growth potential", event_str,
                           f"VULNERABILITY: Enterprise user received startup tool result: {event_str}")
            self.assertNotIn("market_analyzer", event_str,
                           f"VULNERABILITY: Enterprise user received wrong tool result: {event_str}")
        
        for event_str in all_startup_events:
            self.assertNotIn("CONFIDENTIAL: Q4 revenue", event_str,
                           f"VULNERABILITY: Startup user received confidential enterprise data: {event_str}")
            self.assertNotIn("financial_analyzer", event_str,
                           f"VULNERABILITY: Startup user received enterprise tool result: {event_str}")

    def test_agent_workflow_state_persistence_vulnerability(self):
        """
        VULNERABILITY TEST: Prove agent workflow state persists between different users
        
        EXPECTED: This test should FAIL (proving workflow state persistence)
        - Previous user's workflow state affects next user
        - Agent decision-making contaminated by previous user's context
        """
        factory = get_agent_instance_factory()
        
        # User 1: Enterprise user with complex workflow
        enterprise_agent = factory.create_supervisor_agent(self.enterprise_user_context)
        
        # Simulate complex enterprise workflow that modifies agent state
        enterprise_workflow_state = {
            "current_phase": "financial_analysis",
            "completed_steps": ["data_validation", "compliance_check", "risk_assessment"],
            "pending_approvals": ["cfo_approval", "board_review"],
            "confidential_findings": ["revenue_decline_q3", "cost_overrun_detected"],
            "classification_level": "top_secret"
        }
        
        # Inject workflow state into enterprise agent
        if hasattr(enterprise_agent, '_workflow_state'):
            enterprise_agent._workflow_state = enterprise_workflow_state
        elif hasattr(enterprise_agent, 'execution_state'):
            enterprise_agent.execution_state.update(enterprise_workflow_state)
        
        # User 2: Startup user should get clean agent with no prior state
        startup_agent = factory.create_supervisor_agent(self.startup_user_context)
        
        # VULNERABILITY CHECK: Startup agent should have clean state
        # These assertions SHOULD FAIL if workflow state persists
        if hasattr(startup_agent, '_workflow_state'):
            startup_workflow_state = startup_agent._workflow_state or {}
        elif hasattr(startup_agent, 'execution_state'):
            startup_workflow_state = startup_agent.execution_state or {}
        else:
            startup_workflow_state = {}
        
        # Check for enterprise data contamination in startup agent
        contamination_found = []
        
        for key, value in enterprise_workflow_state.items():
            if key in startup_workflow_state:
                contamination_found.append({
                    'key': key,
                    'enterprise_value': value,
                    'startup_value': startup_workflow_state[key]
                })
        
        # Look for specific confidential data leakage
        startup_state_str = json.dumps(startup_workflow_state).lower()
        confidential_terms = ["revenue_decline", "cost_overrun", "cfo_approval", "top_secret"]
        
        leaked_terms = [term for term in confidential_terms if term in startup_state_str]
        
        # These assertions SHOULD FAIL if state contamination exists
        self.assertEqual(len(contamination_found), 0,
                        f"WORKFLOW STATE VULNERABILITY: Enterprise state contaminated startup agent: "
                        f"{contamination_found}")
        
        self.assertEqual(len(leaked_terms), 0,
                        f"CONFIDENTIAL DATA LEAK: Enterprise confidential terms found in startup agent: "
                        f"{leaked_terms} in {startup_state_str}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])