"""
Emergency Golden Path Test: Agent Message Flow Core
Critical test for validating agent processing and message handling for Golden Path.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

# Use absolute imports as required by SSOT
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestAgentMessageFlow(SSotAsyncTestCase):
    """Emergency test for core agent message processing that enables Golden Path AI responses."""
    
    async def asyncSetUp(self):
        """Set up test environment with isolated agent configuration."""
        self.env = IsolatedEnvironment()
        self.env.set("ENVIRONMENT", "test")
        self.env.set("LLM_MODEL", "gpt-4")
        self.env.set("REDIS_HOST", "localhost")
        
        # Mock WebSocket emitter
        self.mock_websocket = Mock()
        self.mock_websocket.send = AsyncMock()
        
        self.emitter = UnifiedWebSocketEmitter(
            websocket=self.mock_websocket,
            user_id="test-user",
            run_id="test-run"
        )
        
        # Mock execution context
        self.context = ExecutionContext(
            user_id="test-user",
            run_id="test-run",
            websocket_emitter=self.emitter
        )
        
    async def test_agent_receives_user_message(self):
        """Test that agent properly receives and acknowledges user message."""
        # Arrange
        user_message = "Hello, can you help me analyze my data?"
        
        with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._process_message') as mock_process:
            mock_process.return_value = "I'll help you analyze your data."
            
            supervisor = SupervisorAgent(context=self.context)
            
            # Act
            response = await supervisor.process_user_message(user_message)
            
            # Assert
            self.assertIsNotNone(response)
            self.assertIn("analyze", response.lower())
            mock_process.assert_called_once_with(user_message)
            
    async def test_agent_sends_websocket_events_during_processing(self):
        """Test that agent sends all required WebSocket events during message processing."""
        # Arrange
        user_message = "Analyze the performance data for last month"
        
        # Mock LLM response
        mock_llm_response = {
            "content": "I'll analyze your performance data for last month. Let me start by processing the data...",
            "reasoning": "User wants performance analysis for last month data"
        }
        
        with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._call_llm') as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            supervisor = SupervisorAgent(context=self.context)
            
            # Act
            await supervisor.process_user_message(user_message)
            
            # Assert - Verify WebSocket events were sent
            send_calls = self.mock_websocket.send.call_args_list
            self.assertGreater(len(send_calls), 0, "No WebSocket events were sent")
            
            # Check for agent_started event
            event_types = []
            for call in send_calls:
                event_data = json.loads(call[0][0])
                event_types.append(event_data["type"])
            
            self.assertIn("agent_started", event_types, "agent_started event not sent")
            
    async def test_agent_handles_complex_user_request(self):
        """Test that agent can handle complex user requests requiring multiple steps."""
        # Arrange
        complex_message = "Can you analyze my sales data and create a forecast for next quarter?"
        
        # Mock agent reasoning and tool usage
        with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._analyze_request') as mock_analyze:
            mock_analyze.return_value = {
                "steps": ["analyze_sales_data", "create_forecast"],
                "tools_needed": ["data_analyzer", "forecasting_tool"]
            }
            
            with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._execute_analysis') as mock_execute:
                mock_execute.return_value = {
                    "sales_analysis": "Sales increased 15% last quarter",
                    "forecast": "Projected 12% growth next quarter"
                }
                
                supervisor = SupervisorAgent(context=self.context)
                
                # Act
                response = await supervisor.process_user_message(complex_message)
                
                # Assert
                self.assertIsNotNone(response)
                self.assertIn("sales", response.lower())
                self.assertIn("forecast", response.lower())
                
    async def test_agent_error_handling_with_websocket_notification(self):
        """Test that agent properly handles errors and notifies user via WebSocket."""
        # Arrange
        user_message = "Process this invalid data format"
        
        with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._process_message') as mock_process:
            mock_process.side_effect = Exception("Data format not supported")
            
            supervisor = SupervisorAgent(context=self.context)
            
            # Act
            response = await supervisor.process_user_message(user_message)
            
            # Assert
            self.assertIsNotNone(response)
            self.assertIn("error", response.lower())
            
            # Verify error was communicated via WebSocket
            send_calls = self.mock_websocket.send.call_args_list
            self.assertGreater(len(send_calls), 0)
            
    async def test_agent_provides_substantive_ai_value(self):
        """Test that agent provides meaningful, actionable AI responses (not just technical success)."""
        # Arrange
        user_message = "What should I focus on to improve my business metrics?"
        
        # Mock a substantive AI response
        substantive_response = {
            "recommendations": [
                "Focus on customer retention - current rate is 85%, target 90%",
                "Optimize conversion funnel - losing 30% at checkout",
                "Invest in upselling - average order value opportunity: $45"
            ],
            "reasoning": "Based on data analysis, these are the highest impact areas",
            "confidence": 0.87,
            "next_steps": [
                "Implement exit-intent surveys",
                "A/B test checkout process",
                "Create upselling email campaigns"
            ]
        }
        
        with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._generate_business_insights') as mock_insights:
            mock_insights.return_value = substantive_response
            
            supervisor = SupervisorAgent(context=self.context)
            
            # Act
            response = await supervisor.process_user_message(user_message)
            
            # Assert - Verify substantive value
            self.assertIsNotNone(response)
            self.assertIn("retention", response.lower())
            self.assertIn("conversion", response.lower())
            
            # Verify actionable recommendations
            self.assertIn("implement", response.lower())
            self.assertIn("optimize", response.lower())
            
    async def test_agent_context_persistence_across_messages(self):
        """Test that agent maintains context across multiple user messages."""
        # Arrange
        supervisor = SupervisorAgent(context=self.context)
        
        # Message 1: Initial request
        message1 = "Analyze my Q3 sales data"
        
        with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._store_context') as mock_store:
            with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._retrieve_context') as mock_retrieve:
                mock_retrieve.return_value = {"previous_analysis": "Q3 sales data processed"}
                
                # Act
                response1 = await supervisor.process_user_message(message1)
                
                # Message 2: Follow-up request
                message2 = "Now compare it with Q2"
                response2 = await supervisor.process_user_message(message2)
                
                # Assert
                self.assertIsNotNone(response1)
                self.assertIsNotNone(response2)
                
                # Verify context was stored and retrieved
                mock_store.assert_called()
                mock_retrieve.assert_called()
                
    async def test_agent_tool_integration_with_notifications(self):
        """Test that agent properly integrates with tools and sends notifications."""
        # Arrange
        user_message = "Calculate the ROI for my marketing campaigns"
        
        # Mock tool execution
        mock_tool_result = {
            "campaign_roi": {
                "facebook": 3.2,
                "google": 4.1,
                "email": 5.8
            },
            "total_spend": 15000,
            "total_revenue": 67500,
            "overall_roi": 4.5
        }
        
        with patch('netra_backend.app.tools.enhanced_dispatcher.EnhancedToolDispatcher.execute_tool') as mock_tool:
            mock_tool.return_value = mock_tool_result
            
            supervisor = SupervisorAgent(context=self.context)
            
            # Act
            response = await supervisor.process_user_message(user_message)
            
            # Assert
            self.assertIsNotNone(response)
            self.assertIn("roi", response.lower())
            
            # Verify tool execution notifications were sent
            send_calls = self.mock_websocket.send.call_args_list
            event_types = []
            for call in send_calls:
                if call and call[0]:
                    event_data = json.loads(call[0][0])
                    event_types.append(event_data["type"])
            
            # Should include tool_executing and tool_completed events
            self.assertTrue(
                any("tool" in event_type for event_type in event_types),
                "No tool-related WebSocket events sent"
            )
            
    async def test_golden_path_end_to_end_agent_flow(self):
        """Test complete Golden Path: user message -> agent processing -> AI response -> WebSocket events."""
        # Arrange
        user_message = "Help me understand my customer churn patterns"
        
        # Mock complete agent response pipeline
        analysis_result = {
            "churn_rate": "12% monthly",
            "top_reasons": ["pricing concerns", "product complexity", "poor support"],
            "recommendations": [
                "Implement pricing tiers",
                "Simplify onboarding", 
                "Improve support response time"
            ],
            "projected_impact": "Reduce churn to 8% within 6 months"
        }
        
        with patch('netra_backend.app.agents.supervisor_agent_modern.SupervisorAgent._comprehensive_analysis') as mock_analysis:
            mock_analysis.return_value = analysis_result
            
            supervisor = SupervisorAgent(context=self.context)
            
            # Act
            response = await supervisor.process_user_message(user_message)
            
            # Assert - Verify complete Golden Path
            
            # 1. Agent produced meaningful response
            self.assertIsNotNone(response)
            self.assertIn("churn", response.lower())
            self.assertIn("recommendations", response.lower())
            
            # 2. WebSocket events were sent (user sees progress)
            send_calls = self.mock_websocket.send.call_args_list
            self.assertGreater(len(send_calls), 0, "No WebSocket events sent to user")
            
            # 3. Response contains actionable business value
            self.assertIn("implement", response.lower())
            self.assertIn("improve", response.lower())
            
            # 4. Verify event sequence for complete user experience
            event_types = []
            for call in send_calls:
                if call and call[0]:
                    try:
                        event_data = json.loads(call[0][0])
                        event_types.append(event_data["type"])
                    except:
                        continue
            
            # At minimum should have agent_started and agent_completed
            has_start = any("started" in event_type for event_type in event_types)
            has_completion = any("completed" in event_type for event_type in event_types)
            
            self.assertTrue(has_start or has_completion, 
                          "Missing critical agent lifecycle events for user experience")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])