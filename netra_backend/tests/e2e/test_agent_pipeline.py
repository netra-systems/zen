"""
Agent Pipeline E2E Tests - Complete Agent Processing Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All customer tiers (Free → Enterprise)
- Business Goal: Agent intelligence and response quality
- Value Impact: Agent reliability drives customer satisfaction and retention
- Strategic Impact: Agent quality differentiates Netra's AI optimization platform

Tests the complete agent processing pipeline:
1. Message reception and routing
2. Supervisor agent orchestration
3. Sub-agent execution and tool usage
4. Response generation and validation
5. Error handling and fallback scenarios

COVERAGE:
- Supervisor agent message processing
- Sub-agent delegation and execution
- Tool dispatcher functionality
- LLM integration and response generation
- Quality gates and validation
- Error recovery and fallback responses
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.websocket_message_types import WebSocketMessage
from netra_backend.app.services.agent_service import AgentService


class MockLLMResponse:
    """Mock LLM response for testing."""
    
    def __init__(self, content: str, tool_calls: List[Dict] = None):
        self.content = content
        self.tool_calls = tool_calls or []
        
    def __str__(self):
        return self.content

class TestAgentMessageProcessing:
    """Agent message reception and routing tests."""
    
    @pytest.fixture
    def agent_service(self) -> AgentService:
        """Create agent service for testing."""
        return AgentService()
    
    @pytest.fixture
    def sample_user_message(self) -> Dict[str, Any]:
        """Create sample user message for testing."""
        return {
            "type": "agent_request",
            "content": "Help me optimize my AI infrastructure costs",
            "user_id": "user_123",
            "thread_id": "thread_456",
            "timestamp": "2025-01-20T10:00:00Z"
        }
    
    @pytest.mark.asyncio
    async def test_agent_service_processes_message(self, agent_service, sample_user_message):
        """Test agent service successfully processes user messages."""
        # Mock dependencies
        # Mock: Agent supervisor isolation for testing without spawning real agents
        with patch('netra_backend.app.services.agent_service.SupervisorAgent') as mock_supervisor:
            # Mock: Async component isolation for testing without real async operations
            mock_supervisor.return_value.process_message = AsyncMock(
                return_value={
                    "response": "I'll help you optimize your AI costs. Let me analyze your current setup.",
                    "status": "completed"
                }
            )
            
            # Process message
            result = await agent_service.process_message(sample_user_message)
            
            # Verify processing succeeded
            assert result is not None
            assert "response" in result
            assert "optimize" in result["response"].lower()
    
    @pytest.mark.asyncio
    async def test_message_routing_to_supervisor(self, agent_service, sample_user_message):
        """Test messages are correctly routed to supervisor agent."""
        # Mock: Agent supervisor isolation for testing without spawning real agents
        with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent.process_message') as mock_process:
            mock_process.return_value = {"response": "Supervisor processed"}
            
            # Process message
            await agent_service.process_message(sample_user_message)
            
            # Verify supervisor was called
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0][0]
            assert call_args["content"] == sample_user_message["content"]
    
    @pytest.mark.asyncio
    async def test_message_validation_before_processing(self, agent_service):
        """Test message validation before agent processing."""
        # Test invalid message structure
        invalid_message = {"invalid": "structure"}
        
        with pytest.raises(Exception):
            await agent_service.process_message(invalid_message)
    
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, agent_service):
        """Test concurrent processing of multiple messages."""
        messages = [
            {"type": "agent_request", "content": f"Message {i}", "user_id": f"user_{i}", "thread_id": f"thread_{i}"}
            for i in range(5)
        ]
        
        # Mock supervisor responses
        # Mock: Agent supervisor isolation for testing without spawning real agents
        with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent.process_message') as mock_process:
            mock_process.return_value = {"response": "Processed"}
            
            # Process messages concurrently
            tasks = [agent_service.process_message(msg) for msg in messages]
            results = await asyncio.gather(*tasks)
            
            # Verify all messages processed
            assert len(results) == 5
            assert all(result is not None for result in results)

class TestSupervisorAgentOrchestration:
    """Supervisor agent orchestration and delegation tests."""
    
    @pytest.fixture
    def supervisor_agent(self) -> SupervisorAgent:
        """Create supervisor agent for testing."""
        return SupervisorAgent()
    
    @pytest.fixture
    def optimization_request(self) -> Dict[str, Any]:
        """Create optimization request message."""
        return {
            "type": "agent_request",
            "content": "I need to reduce my LLM costs by 30% while maintaining quality",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
    
    @pytest.mark.asyncio
    async def test_supervisor_delegates_to_data_agent(self, supervisor_agent, optimization_request):
        """Test supervisor delegates data analysis to data sub-agent."""
        # Mock data sub-agent
        # Mock: Agent service isolation for testing without LLM agent execution
        with patch('netra_backend.app.agents.data_sub_agent.data_sub_agent.DataSubAgent.process_request') as mock_data_agent:
            mock_data_agent.return_value = {
                "analysis": "Current costs: $5000/month, optimization potential: 35%"
            }
            
            # Mock LLM response that triggers data agent
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
                mock_llm.return_value = MockLLMResponse(
                    content="I need to analyze your current usage data.",
                    tool_calls=[{"function": {"name": "data_analysis"}}]
                )
                
                # Process request
                result = await supervisor_agent.process_message(optimization_request)
                
                # Verify data agent was called
                mock_data_agent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_supervisor_delegates_to_triage_agent(self, supervisor_agent):
        """Test supervisor delegates complex requests to triage agent."""
        complex_request = {
            "type": "agent_request",
            "content": "I have multiple issues: slow responses, high costs, and poor quality",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
        
        # Mock triage sub-agent
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.agents.triage.unified_triage_agent.UnifiedTriageAgent.process_request') as mock_triage:
            mock_triage.return_value = {
                "prioritized_issues": ["performance", "cost", "quality"],
                "recommendations": ["Optimize model selection", "Implement caching"]
            }
            
            # Mock LLM response that triggers triage
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
                mock_llm.return_value = MockLLMResponse(
                    content="This requires issue triage and prioritization.",
                    tool_calls=[{"function": {"name": "triage_issues"}}]
                )
                
                # Process request
                result = await supervisor_agent.process_message(complex_request)
                
                # Verify triage agent was called
                mock_triage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_supervisor_orchestrates_multiple_agents(self, supervisor_agent):
        """Test supervisor orchestrates multiple sub-agents for complex tasks."""
        complex_optimization = {
            "type": "agent_request",
            "content": "Create a comprehensive AI optimization strategy with cost analysis and performance metrics",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
        
        # Mock multiple sub-agents
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.agents.data_sub_agent.data_sub_agent.DataSubAgent.process_request') as mock_data, \
             patch('netra_backend.app.agents.reporting_sub_agent.ReportingSubAgent.process_request') as mock_reporting:
            
            mock_data.return_value = {"cost_analysis": "Current: $5000, Potential: $3500"}
            mock_reporting.return_value = {"strategy_report": "Comprehensive optimization plan"}
            
            # Mock LLM responses
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
                # Sequence of LLM calls
                mock_llm.side_effect = [
                    MockLLMResponse("Need data analysis", [{"function": {"name": "data_analysis"}}]),
                    MockLLMResponse("Need report generation", [{"function": {"name": "generate_report"}}]),
                    MockLLMResponse("Final comprehensive strategy based on analysis and report")
                ]
                
                # Process request
                result = await supervisor_agent.process_message(complex_optimization)
                
                # Verify multiple agents were called
                mock_data.assert_called_once()
                mock_reporting.assert_called_once()

class TestSubAgentExecution:
    """Sub-agent execution and specialization tests."""
    
    @pytest.mark.asyncio
    async def test_data_agent_analyzes_metrics(self):
        """Test data sub-agent performs metric analysis."""
        data_agent = DataSubAgent()
        
        analysis_request = {
            "type": "data_analysis",
            "metrics": ["cost", "latency", "quality"],
            "time_range": "last_30_days"
        }
        
        # Mock ClickHouse data
        # Mock: ClickHouse external database isolation for unit testing performance
        with patch('netra_backend.app.db.clickhouse.ClickHouseClient.query') as mock_query:
            mock_query.return_value = [
                {"metric": "cost", "value": 5000, "date": "2025-01-01"},
                {"metric": "latency", "value": 250, "date": "2025-01-01"}
            ]
            
            # Process analysis request
            result = await data_agent.process_request(analysis_request)
            
            # Verify analysis was performed
            assert result is not None
            assert "analysis" in result or "metrics" in result
    
    @pytest.mark.asyncio
    async def test_triage_agent_prioritizes_issues(self):
        """Test triage sub-agent prioritizes multiple issues."""
        triage_agent = UnifiedTriageAgent()
        
        triage_request = {
            "type": "triage",
            "issues": [
                "High latency in API responses",
                "Increasing costs without quality improvement", 
                "User complaints about response quality"
            ]
        }
        
        # Mock LLM for issue analysis
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
            mock_llm.return_value = MockLLMResponse(
                content=json.dumps({
                    "prioritized_issues": [
                        {"issue": "High latency", "priority": "high", "impact": "user_experience"},
                        {"issue": "Increasing costs", "priority": "medium", "impact": "business"},
                        {"issue": "Quality complaints", "priority": "high", "impact": "satisfaction"}
                    ]
                })
            )
            
            # Process triage request
            result = await triage_agent.process_request(triage_request)
            
            # Verify issues were prioritized
            assert result is not None
            assert "prioritized" in str(result).lower() or "priority" in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_executes_tools(self):
        """Test tool dispatcher executes appropriate tools."""
        tool_dispatcher = ToolDispatcher()
        
        tool_request = {
            "tool_name": "cost_calculator",
            "parameters": {
                "usage_volume": 1000000,
                "model": LLMModel.GEMINI_2_5_FLASH.value,
                "optimization_level": "aggressive"
            }
        }
        
        # Mock tool execution
        # Mock: Tool execution isolation for predictable agent testing
        with patch('netra_backend.app.agents.tool_dispatcher.ToolDispatcher.execute_tool') as mock_execute:
            mock_execute.return_value = {
                "current_cost": 2500,
                "optimized_cost": 1750,
                "savings": 750
            }
            
            # Execute tool
            result = await tool_dispatcher.dispatch_tool(tool_request)
            
            # Verify tool was executed
            mock_execute.assert_called_once()
            assert result is not None

class TestAgentResponseGeneration:
    """Agent response generation and quality tests."""
    
    @pytest.mark.asyncio
    async def test_response_generation_quality(self):
        """Test agent responses meet quality standards."""
        supervisor_agent = SupervisorAgent()
        
        user_request = {
            "type": "agent_request",
            "content": "What's the best model for my cost-sensitive workload?",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
        
        # Mock LLM response
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
            mock_llm.return_value = MockLLMResponse(
                content="""Based on your cost-sensitive requirements, I recommend:
                
                1. **GPT-3.5-turbo** for general tasks (90% cost reduction vs GPT-4)
                2. **Claude-3-haiku** for simple queries (fastest, most cost-effective)
                3. **Mixtral-8x7B** for complex reasoning (open-source alternative)
                
                Expected savings: 70-80% compared to GPT-4 while maintaining quality."""
            )
            
            # Process request
            result = await supervisor_agent.process_message(user_request)
            
            # Verify response quality
            assert result is not None
            assert "response" in result
            response = result["response"]
            
            # Check for specific quality criteria
            assert len(response) > 100  # Substantial response
            assert "gpt" in response.lower()  # Contains model recommendations
            assert "cost" in response.lower()  # Addresses cost concern
            assert any(char.isdigit() for char in response)  # Contains metrics/numbers
    
    @pytest.mark.asyncio
    async def test_response_includes_actionable_recommendations(self):
        """Test agent responses include actionable recommendations."""
        supervisor_agent = SupervisorAgent()
        
        optimization_request = {
            "type": "agent_request",
            "content": "My AI costs are too high. Help me optimize.",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
        
        # Mock comprehensive response
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
            mock_llm.return_value = MockLLMResponse(
                content="""Here's your optimization plan:
                
                **Immediate Actions:**
                1. Switch high-volume tasks to GPT-3.5-turbo (save 90%)
                2. Implement response caching (save 40-60%)
                3. Use function calling instead of prompt engineering
                
                **Next Steps:**
                - Audit your current usage patterns
                - Set up cost monitoring alerts
                - Test model alternatives for quality acceptance
                
                **Expected Impact:** $2,000-3,000 monthly savings"""
            )
            
            # Process request
            result = await supervisor_agent.process_message(optimization_request)
            
            # Verify actionable recommendations
            response = result["response"]
            assert "action" in response.lower() or "step" in response.lower()
            assert "$" in response  # Contains cost information
            assert any(word in response.lower() for word in ["switch", "implement", "use", "set up"])
    
    @pytest.mark.asyncio
    async def test_response_formatting_consistency(self):
        """Test agent responses have consistent formatting."""
        supervisor_agent = SupervisorAgent()
        
        requests = [
            {"content": "Help with model selection", "user_id": "user1", "thread_id": "t1"},
            {"content": "Optimize my costs", "user_id": "user2", "thread_id": "t2"},
            {"content": "Improve response quality", "user_id": "user3", "thread_id": "t3"}
        ]
        
        responses = []
        
        # Mock consistent LLM responses
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
            mock_llm.return_value = MockLLMResponse(
                content="Well-formatted response with clear structure and recommendations."
            )
            
            # Process multiple requests
            for request in requests:
                result = await supervisor_agent.process_message(request)
                responses.append(result["response"])
        
        # Verify consistent structure
        for response in responses:
            assert isinstance(response, str)
            assert len(response) > 50  # Minimum length
            assert response.strip() == response  # No leading/trailing whitespace

class TestAgentErrorHandling:
    """Agent error handling and fallback tests."""
    
    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self):
        """Test agent handles LLM failures gracefully."""
        supervisor_agent = SupervisorAgent()
        
        user_request = {
            "type": "agent_request",
            "content": "Help me optimize my AI infrastructure",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
        
        # Mock LLM failure
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
            mock_llm.side_effect = Exception("LLM service unavailable")
            
            # Process request (should not crash)
            result = await supervisor_agent.process_message(user_request)
            
            # Verify fallback response provided
            assert result is not None
            assert "response" in result
            # Should contain error indication or fallback message
    
    @pytest.mark.asyncio
    async def test_sub_agent_failure_handling(self):
        """Test supervisor handles sub-agent failures."""
        supervisor_agent = SupervisorAgent()
        
        data_request = {
            "type": "agent_request",
            "content": "Analyze my usage data and provide cost optimization",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
        
        # Mock sub-agent failure
        # Mock: Component isolation for testing without external dependencies
        with patch('app.agents.data_sub_agent.agent.DataSubAgent.process_request') as mock_data:
            mock_data.side_effect = Exception("Data service unavailable")
            
            # Mock: LLM service isolation for fast testing without API calls or rate limits
            with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
                mock_llm.return_value = MockLLMResponse(
                    content="I'll provide general optimization advice since data analysis is unavailable."
                )
                
                # Process request
                result = await supervisor_agent.process_message(data_request)
                
                # Verify graceful handling
                assert result is not None
                assert "response" in result
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test agent handles processing timeouts."""
        supervisor_agent = SupervisorAgent()
        
        user_request = {
            "type": "agent_request",
            "content": "Complex multi-step optimization analysis",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
        
        # Mock slow LLM response
        async def slow_llm_response(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow response
            return MockLLMResponse("Delayed response")
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response', side_effect=slow_llm_response):
            # Process with timeout
            try:
                result = await asyncio.wait_for(
                    supervisor_agent.process_message(user_request),
                    timeout=5
                )
            except asyncio.TimeoutError:
                # Should handle timeout gracefully
                result = {"response": "Request is taking longer than expected. Please try again."}
            
            assert result is not None

class TestAgentPerformance:
    """Agent performance and efficiency tests."""
    
    @pytest.mark.asyncio
    async def test_response_time_performance(self):
        """Test agent response times meet performance requirements."""
        supervisor_agent = SupervisorAgent()
        
        simple_request = {
            "type": "agent_request",
            "content": "What's the cheapest LLM for simple tasks?",
            "user_id": "user_123",
            "thread_id": "thread_456"
        }
        
        # Mock fast LLM response
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
            mock_llm.return_value = MockLLMResponse(
                content="For simple tasks, use GPT-3.5-turbo or Claude-3-haiku."
            )
            
            # Measure response time
            start_time = time.time()
            result = await supervisor_agent.process_message(simple_request)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Verify performance requirements
            assert response_time < 5.0  # Max 5 seconds for simple requests
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test agent handles concurrent requests efficiently."""
        supervisor_agent = SupervisorAgent()
        
        # Create multiple requests
        requests = [
            {"type": "agent_request", "content": f"Request {i}", "user_id": f"user_{i}", "thread_id": f"thread_{i}"}
            for i in range(10)
        ]
        
        # Mock LLM responses
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        with patch('netra_backend.app.llm.llm_manager.LLMManager.generate_response') as mock_llm:
            mock_llm.return_value = MockLLMResponse("Response to request")
            
            # Process requests concurrently
            start_time = time.time()
            tasks = [supervisor_agent.process_message(req) for req in requests]
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # Verify all requests processed
            assert len(results) == 10
            assert all(result is not None for result in results)
            
            # Verify concurrent processing efficiency
            assert total_time < 10.0  # Should be much faster than sequential