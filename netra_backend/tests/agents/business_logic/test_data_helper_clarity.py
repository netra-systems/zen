from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test suite for DataHelperAgent business logic validation.
# REMOVED_SYNTAX_ERROR: Ensures data requests are clear, actionable, and lead to successful optimization.
""

import pytest
import asyncio
from typing import Dict, Any, List
import json
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.data_helper_agent import DataHelperAgent
# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.models import ( )
DataRequest,
DataRequirement,
DataCategory,
DataPriority,
UserExperience



# REMOVED_SYNTAX_ERROR: class TestDataHelperClarity:
    # REMOVED_SYNTAX_ERROR: """Validate DataHelper produces clear, actionable data requests."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def data_helper_agent(self, mock_llm_manager):
    # REMOVED_SYNTAX_ERROR: """Create a DataHelperAgent with mocked dependencies."""
    # REMOVED_SYNTAX_ERROR: agent = DataHelperAgent(llm_manager=mock_llm_manager)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return agent

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def data_request_scenarios(self) -> Dict[str, Dict[str, Any]]:
    # REMOVED_SYNTAX_ERROR: """Define scenarios for data request generation."""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "missing_cost_data": { )
    # REMOVED_SYNTAX_ERROR: "context": { )
    # REMOVED_SYNTAX_ERROR: "user_request": "Help optimize our AI",
    # REMOVED_SYNTAX_ERROR: "available_data": {},
    # REMOVED_SYNTAX_ERROR: "optimization_goal": "cost_reduction"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "expected_requests": [ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "category": DataCategory.FINANCIAL,
    # REMOVED_SYNTAX_ERROR: "priority": DataPriority.CRITICAL,
    # REMOVED_SYNTAX_ERROR: "questions": [ )
    # REMOVED_SYNTAX_ERROR: "What is your current monthly spend on AI/LLM services?",
    # REMOVED_SYNTAX_ERROR: "Which AI providers are you using (OpenAI, Anthropic, etc.)?",
    # REMOVED_SYNTAX_ERROR: "What is your average daily request volume?"
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: "format": "structured",
    # REMOVED_SYNTAX_ERROR: "examples": ["Monthly spend: $5000", "Providers: OpenAI (80%), Claude (20%)"]
    
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: "clarity_score": 0.9
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "missing_performance_data": { )
    # REMOVED_SYNTAX_ERROR: "context": { )
    # REMOVED_SYNTAX_ERROR: "user_request": "System is slow",
    # REMOVED_SYNTAX_ERROR: "available_data": {"provider": "OpenAI"},
    # REMOVED_SYNTAX_ERROR: "optimization_goal": "latency_reduction"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "expected_requests": [ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "category": DataCategory.PERFORMANCE,
    # REMOVED_SYNTAX_ERROR: "priority": DataPriority.CRITICAL,
    # REMOVED_SYNTAX_ERROR: "questions": [ )
    # REMOVED_SYNTAX_ERROR: "What are your current response time metrics (P50, P95, P99)?",
    # REMOVED_SYNTAX_ERROR: "What is the average token count per request?",
    # REMOVED_SYNTAX_ERROR: "What are your peak usage hours?"
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: "format": "metrics",
    # REMOVED_SYNTAX_ERROR: "examples": ["P95: 3.5 seconds", "Avg tokens: 1500"]
    
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: "clarity_score": 0.85
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "complex_multi_category": { )
    # REMOVED_SYNTAX_ERROR: "context": { )
    # REMOVED_SYNTAX_ERROR: "user_request": "Complete AI optimization needed",
    # REMOVED_SYNTAX_ERROR: "available_data": {"monthly_spend": 10000},
    # REMOVED_SYNTAX_ERROR: "optimization_goal": "comprehensive"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "expected_requests": [ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "category": DataCategory.USAGE,
    # REMOVED_SYNTAX_ERROR: "priority": DataPriority.HIGH,
    # REMOVED_SYNTAX_ERROR: "questions": ["Request patterns", "User segments", "Time distribution"]
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "category": DataCategory.TECHNICAL,
    # REMOVED_SYNTAX_ERROR: "priority": DataPriority.MEDIUM,
    # REMOVED_SYNTAX_ERROR: "questions": ["Current architecture", "Integration points", "Constraints"]
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "category": DataCategory.BUSINESS,
    # REMOVED_SYNTAX_ERROR: "priority": DataPriority.HIGH,
    # REMOVED_SYNTAX_ERROR: "questions": ["SLA requirements", "Quality thresholds", "Growth projections"]
    
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: "clarity_score": 0.8
    
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_critical_data_identification(self, data_helper_agent, data_request_scenarios):
        # REMOVED_SYNTAX_ERROR: """Test identification of critical missing data."""
        # REMOVED_SYNTAX_ERROR: scenario = data_request_scenarios["missing_cost_data"]

        # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent, 'identify_missing_data') as mock_identify:
            # REMOVED_SYNTAX_ERROR: mock_identify.return_value = [ )
            # REMOVED_SYNTAX_ERROR: DataRequirement( )
            # REMOVED_SYNTAX_ERROR: category=DataCategory.FINANCIAL,
            # REMOVED_SYNTAX_ERROR: field="monthly_spend",
            # REMOVED_SYNTAX_ERROR: priority=DataPriority.CRITICAL,
            # REMOVED_SYNTAX_ERROR: reason="Required for cost optimization calculations"
            # REMOVED_SYNTAX_ERROR: ),
            # REMOVED_SYNTAX_ERROR: DataRequirement( )
            # REMOVED_SYNTAX_ERROR: category=DataCategory.FINANCIAL,
            # REMOVED_SYNTAX_ERROR: field="provider_distribution",
            # REMOVED_SYNTAX_ERROR: priority=DataPriority.CRITICAL,
            # REMOVED_SYNTAX_ERROR: reason="Needed to identify optimization opportunities"
            
            

            # REMOVED_SYNTAX_ERROR: missing_data = await data_helper_agent.identify_missing_data(scenario["context"])

            # Validate critical data is identified
            # REMOVED_SYNTAX_ERROR: assert len(missing_data) > 0
            # REMOVED_SYNTAX_ERROR: assert all(req.priority == DataPriority.CRITICAL for req in missing_data )
            # REMOVED_SYNTAX_ERROR: if req.category == DataCategory.FINANCIAL)
            # REMOVED_SYNTAX_ERROR: assert all(req.reason is not None and len(req.reason) > 20 )
            # REMOVED_SYNTAX_ERROR: for req in missing_data)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_question_clarity_and_specificity(self, data_helper_agent, data_request_scenarios):
                # REMOVED_SYNTAX_ERROR: """Test that generated questions are clear and specific."""
                # REMOVED_SYNTAX_ERROR: scenario = data_request_scenarios["missing_performance_data"]

                # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent, 'generate_questions') as mock_generate:
                    # REMOVED_SYNTAX_ERROR: mock_generate.return_value = [ )
                    # REMOVED_SYNTAX_ERROR: DataRequest( )
                    # REMOVED_SYNTAX_ERROR: category=DataCategory.PERFORMANCE,
                    # REMOVED_SYNTAX_ERROR: priority=DataPriority.CRITICAL,
                    # REMOVED_SYNTAX_ERROR: questions=scenario["expected_requests"][0]["questions"],
                    # REMOVED_SYNTAX_ERROR: format="metrics",
                    # REMOVED_SYNTAX_ERROR: examples=scenario["expected_requests"][0]["examples"],
                    # REMOVED_SYNTAX_ERROR: instructions="Please provide metrics in the format shown in examples"
                    
                    

                    # REMOVED_SYNTAX_ERROR: requests = await data_helper_agent.generate_data_requests(scenario["context"])
                    # REMOVED_SYNTAX_ERROR: request = requests[0]

                    # Validate question clarity
                    # REMOVED_SYNTAX_ERROR: for question in request.questions:
                        # Questions should be specific
                        # REMOVED_SYNTAX_ERROR: assert "?" in question  # Should be a question
                        # REMOVED_SYNTAX_ERROR: assert len(question) > 20  # Not too short
                        # REMOVED_SYNTAX_ERROR: assert len(question) < 200  # Not too long

                        # Should contain specific terms
                        # REMOVED_SYNTAX_ERROR: specific_terms = ["metric", "time", "token", "request", "response",
                        # REMOVED_SYNTAX_ERROR: "latency", "throughput", "error", "cost", "usage"]
                        # REMOVED_SYNTAX_ERROR: assert any(term in question.lower() for term in specific_terms)

                        # Validate examples are provided
                        # REMOVED_SYNTAX_ERROR: assert len(request.examples) > 0
                        # REMOVED_SYNTAX_ERROR: assert all(":" in example for example in request.examples)  # Format: "Label: Value"

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_user_friendly_formatting(self, data_helper_agent):
                            # REMOVED_SYNTAX_ERROR: """Test that data requests are formatted for user understanding."""
                            # REMOVED_SYNTAX_ERROR: test_context = { )
                            # REMOVED_SYNTAX_ERROR: "user_request": "Help me optimize",
                            # REMOVED_SYNTAX_ERROR: "technical_level": "non-technical"
                            

                            # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent, 'format_for_user') as mock_format:
                                # REMOVED_SYNTAX_ERROR: mock_format.return_value = { )
                                # REMOVED_SYNTAX_ERROR: "title": "Information Needed for Optimization",
                                # REMOVED_SYNTAX_ERROR: "sections": [ )
                                # REMOVED_SYNTAX_ERROR: { )
                                # REMOVED_SYNTAX_ERROR: "heading": "Current Costs",
                                # REMOVED_SYNTAX_ERROR: "questions": [ )
                                # REMOVED_SYNTAX_ERROR: "How much do you spend monthly on AI services?",
                                # REMOVED_SYNTAX_ERROR: "Which AI services do you use most?"
                                # REMOVED_SYNTAX_ERROR: ],
                                # REMOVED_SYNTAX_ERROR: "why_needed": "This helps us identify cost-saving opportunities",
                                # REMOVED_SYNTAX_ERROR: "example_response": "We spend $5000/month, mostly on GPT-4"
                                # REMOVED_SYNTAX_ERROR: },
                                # REMOVED_SYNTAX_ERROR: { )
                                # REMOVED_SYNTAX_ERROR: "heading": "Usage Patterns",
                                # REMOVED_SYNTAX_ERROR: "questions": [ )
                                # REMOVED_SYNTAX_ERROR: "How many AI requests do you make daily?",
                                # REMOVED_SYNTAX_ERROR: "What are your peak usage hours?"
                                # REMOVED_SYNTAX_ERROR: ],
                                # REMOVED_SYNTAX_ERROR: "why_needed": "Understanding patterns helps optimize resource allocation",
                                # REMOVED_SYNTAX_ERROR: "example_response": "10,000 requests/day, peak 9am-12pm EST"
                                
                                # REMOVED_SYNTAX_ERROR: ],
                                # REMOVED_SYNTAX_ERROR: "submission_format": "You can provide answers in any format comfortable for you"
                                

                                # REMOVED_SYNTAX_ERROR: formatted_request = await data_helper_agent.format_for_user(test_context)

                                # Validate user-friendly structure
                                # REMOVED_SYNTAX_ERROR: assert "title" in formatted_request
                                # REMOVED_SYNTAX_ERROR: assert "sections" in formatted_request

                                # REMOVED_SYNTAX_ERROR: for section in formatted_request["sections"]:
                                    # REMOVED_SYNTAX_ERROR: assert "heading" in section
                                    # REMOVED_SYNTAX_ERROR: assert "questions" in section
                                    # REMOVED_SYNTAX_ERROR: assert "why_needed" in section  # Explains value
                                    # REMOVED_SYNTAX_ERROR: assert "example_response" in section  # Provides guidance

                                    # Language should be accessible
                                    # REMOVED_SYNTAX_ERROR: assert not any(term in section["why_needed"].lower() )
                                    # REMOVED_SYNTAX_ERROR: for term in ["api", "llm", "token", "embedding"])  # Avoid jargon

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_progressive_data_collection(self, data_helper_agent):
                                        # REMOVED_SYNTAX_ERROR: """Test that data collection is progressive (critical first)."""
                                        # REMOVED_SYNTAX_ERROR: context = { )
                                        # REMOVED_SYNTAX_ERROR: "optimization_goal": "comprehensive",
                                        # REMOVED_SYNTAX_ERROR: "available_data": {}
                                        

                                        # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent, 'prioritize_requests') as mock_prioritize:
                                            # REMOVED_SYNTAX_ERROR: mock_prioritize.return_value = [ )
                                            # REMOVED_SYNTAX_ERROR: DataRequest( )
                                            # REMOVED_SYNTAX_ERROR: category=DataCategory.FINANCIAL,
                                            # REMOVED_SYNTAX_ERROR: priority=DataPriority.CRITICAL,
                                            # REMOVED_SYNTAX_ERROR: questions=["What"s your monthly AI spend?"],
                                            # REMOVED_SYNTAX_ERROR: phase=1
                                            # REMOVED_SYNTAX_ERROR: ),
                                            # REMOVED_SYNTAX_ERROR: DataRequest( )
                                            # REMOVED_SYNTAX_ERROR: category=DataCategory.PERFORMANCE,
                                            # REMOVED_SYNTAX_ERROR: priority=DataPriority.HIGH,
                                            # REMOVED_SYNTAX_ERROR: questions=["What are your latency requirements?"],
                                            # REMOVED_SYNTAX_ERROR: phase=2
                                            # REMOVED_SYNTAX_ERROR: ),
                                            # REMOVED_SYNTAX_ERROR: DataRequest( )
                                            # REMOVED_SYNTAX_ERROR: category=DataCategory.TECHNICAL,
                                            # REMOVED_SYNTAX_ERROR: priority=DataPriority.MEDIUM,
                                            # REMOVED_SYNTAX_ERROR: questions=["What"s your tech stack?"],
                                            # REMOVED_SYNTAX_ERROR: phase=3
                                            
                                            

                                            # REMOVED_SYNTAX_ERROR: prioritized = await data_helper_agent.prioritize_requests(context)

                                            # Validate progressive collection
                                            # REMOVED_SYNTAX_ERROR: assert prioritized[0].priority == DataPriority.CRITICAL
                                            # REMOVED_SYNTAX_ERROR: assert prioritized[0].phase == 1

                                            # Later phases should have lower priority
                                            # REMOVED_SYNTAX_ERROR: for i in range(len(prioritized) - 1):
                                                # REMOVED_SYNTAX_ERROR: assert prioritized[i].phase <= prioritized[i + 1].phase
                                                # REMOVED_SYNTAX_ERROR: assert prioritized[i].priority.value >= prioritized[i + 1].priority.value

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_data_validation_guidance(self, data_helper_agent):
                                                    # REMOVED_SYNTAX_ERROR: """Test that requests include validation criteria."""
                                                    # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent, 'add_validation_criteria') as mock_validate:
                                                        # REMOVED_SYNTAX_ERROR: mock_validate.return_value = DataRequest( )
                                                        # REMOVED_SYNTAX_ERROR: category=DataCategory.FINANCIAL,
                                                        # REMOVED_SYNTAX_ERROR: priority=DataPriority.CRITICAL,
                                                        # REMOVED_SYNTAX_ERROR: questions=["Monthly AI spend?"],
                                                        # REMOVED_SYNTAX_ERROR: validation_criteria={ )
                                                        # REMOVED_SYNTAX_ERROR: "format": "currency",
                                                        # REMOVED_SYNTAX_ERROR: "range": {"min": 0, "max": 1000000},
                                                        # REMOVED_SYNTAX_ERROR: "required": True
                                                        # REMOVED_SYNTAX_ERROR: },
                                                        # REMOVED_SYNTAX_ERROR: error_guidance={ )
                                                        # REMOVED_SYNTAX_ERROR: "invalid_format": "Please provide amount in USD (e.g., $5000 or 5000)",
                                                        # REMOVED_SYNTAX_ERROR: "out_of_range": "Value seems unusual, please verify",
                                                        # REMOVED_SYNTAX_ERROR: "missing": "This information is required for optimization"
                                                        
                                                        

                                                        # REMOVED_SYNTAX_ERROR: request = await data_helper_agent.add_validation_criteria({})

                                                        # Validate validation criteria
                                                        # REMOVED_SYNTAX_ERROR: assert "validation_criteria" in request.__dict__
                                                        # REMOVED_SYNTAX_ERROR: assert request.validation_criteria["required"] == True
                                                        # REMOVED_SYNTAX_ERROR: assert "format" in request.validation_criteria

                                                        # Validate error guidance
                                                        # REMOVED_SYNTAX_ERROR: assert "error_guidance" in request.__dict__
                                                        # REMOVED_SYNTAX_ERROR: assert len(request.error_guidance) > 0
                                                        # REMOVED_SYNTAX_ERROR: assert all(len(msg) > 10 for msg in request.error_guidance.values())

                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_context_aware_requests(self, data_helper_agent, data_request_scenarios):
                                                            # REMOVED_SYNTAX_ERROR: """Test that requests adapt to user context."""
                                                            # REMOVED_SYNTAX_ERROR: contexts = [ )
                                                            # REMOVED_SYNTAX_ERROR: { )
                                                            # REMOVED_SYNTAX_ERROR: "user_type": "startup",
                                                            # REMOVED_SYNTAX_ERROR: "expected_focus": ["cost", "efficiency", "quick_wins"],
                                                            # REMOVED_SYNTAX_ERROR: "avoid_terms": ["enterprise", "compliance", "governance"]
                                                            # REMOVED_SYNTAX_ERROR: },
                                                            # REMOVED_SYNTAX_ERROR: { )
                                                            # REMOVED_SYNTAX_ERROR: "user_type": "enterprise",
                                                            # REMOVED_SYNTAX_ERROR: "expected_focus": ["scale", "reliability", "compliance"],
                                                            # REMOVED_SYNTAX_ERROR: "avoid_terms": ["quick", "cheap", "simple"]
                                                            # REMOVED_SYNTAX_ERROR: },
                                                            # REMOVED_SYNTAX_ERROR: { )
                                                            # REMOVED_SYNTAX_ERROR: "user_type": "technical",
                                                            # REMOVED_SYNTAX_ERROR: "expected_focus": ["metrics", "architecture", "performance"],
                                                            # REMOVED_SYNTAX_ERROR: "avoid_terms": ["roughly", "approximately", "basic"]
                                                            
                                                            

                                                            # REMOVED_SYNTAX_ERROR: for context in contexts:
                                                                # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent, 'adapt_to_context') as mock_adapt:
                                                                    # REMOVED_SYNTAX_ERROR: mock_adapt.return_value = DataRequest( )
                                                                    # REMOVED_SYNTAX_ERROR: category=DataCategory.BUSINESS,
                                                                    # REMOVED_SYNTAX_ERROR: priority=DataPriority.HIGH,
                                                                    # REMOVED_SYNTAX_ERROR: questions=["formatted_string"data_pending": [ )
                                                                        # REMOVED_SYNTAX_ERROR: "usage_patterns",
                                                                        # REMOVED_SYNTAX_ERROR: "performance_metrics"
                                                                        
                                                                        

                                                                        # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent, 'get_next_requirements') as mock_next:
                                                                            # REMOVED_SYNTAX_ERROR: mock_next.return_value = [ )
                                                                            # REMOVED_SYNTAX_ERROR: DataRequest( )
                                                                            # REMOVED_SYNTAX_ERROR: category=DataCategory.USAGE,
                                                                            # REMOVED_SYNTAX_ERROR: priority=DataPriority.HIGH,
                                                                            # REMOVED_SYNTAX_ERROR: questions=["Daily request volume?", "Peak hours?"],
                                                                            # REMOVED_SYNTAX_ERROR: acknowledges_previous=["Thank you for the cost information"],
                                                                            # REMOVED_SYNTAX_ERROR: remaining_items=1
                                                                            
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: next_requests = await data_helper_agent.get_next_requirements(session_state)
                                                                            # REMOVED_SYNTAX_ERROR: request = next_requests[0]

                                                                            # Validate incremental gathering
                                                                            # REMOVED_SYNTAX_ERROR: assert len(request.acknowledges_previous) > 0
                                                                            # REMOVED_SYNTAX_ERROR: assert "thank" in request.acknowledges_previous[0].lower()
                                                                            # REMOVED_SYNTAX_ERROR: assert request.remaining_items >= 0
                                                                            # REMOVED_SYNTAX_ERROR: assert request.category == DataCategory.USAGE  # Next in sequence

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_fallback_for_missing_data(self, data_helper_agent):
                                                                                # REMOVED_SYNTAX_ERROR: """Test graceful handling when user cannot provide data."""
                                                                                # REMOVED_SYNTAX_ERROR: context = { )
                                                                                # REMOVED_SYNTAX_ERROR: "user_response": "I don"t have access to those metrics",
                                                                                # REMOVED_SYNTAX_ERROR: "requested_data": ["performance_metrics"]
                                                                                

                                                                                # REMOVED_SYNTAX_ERROR: with patch.object(data_helper_agent, 'provide_alternatives') as mock_alternatives:
                                                                                    # REMOVED_SYNTAX_ERROR: mock_alternatives.return_value = { )
                                                                                    # REMOVED_SYNTAX_ERROR: "alternative_approaches": [ )
                                                                                    # REMOVED_SYNTAX_ERROR: { )
                                                                                    # REMOVED_SYNTAX_ERROR: "approach": "Estimation based on typical patterns",
                                                                                    # REMOVED_SYNTAX_ERROR: "questions": ["Approximate response time?", "Feels fast/medium/slow?"],
                                                                                    # REMOVED_SYNTAX_ERROR: "confidence_impact": "Recommendations will be less precise but still valuable"
                                                                                    # REMOVED_SYNTAX_ERROR: },
                                                                                    # REMOVED_SYNTAX_ERROR: { )
                                                                                    # REMOVED_SYNTAX_ERROR: "approach": "Start with monitoring",
                                                                                    # REMOVED_SYNTAX_ERROR: "action": "We can help you set up basic monitoring first",
                                                                                    # REMOVED_SYNTAX_ERROR: "timeline": "Gather data for 1 week, then optimize"
                                                                                    
                                                                                    # REMOVED_SYNTAX_ERROR: ],
                                                                                    # REMOVED_SYNTAX_ERROR: "can_proceed": True,
                                                                                    # REMOVED_SYNTAX_ERROR: "limitations": ["Savings estimates will have wider ranges"]
                                                                                    

                                                                                    # REMOVED_SYNTAX_ERROR: alternatives = await data_helper_agent.provide_alternatives(context)

                                                                                    # Validate fallback options
                                                                                    # REMOVED_SYNTAX_ERROR: assert len(alternatives["alternative_approaches"]) > 0
                                                                                    # REMOVED_SYNTAX_ERROR: assert alternatives["can_proceed"] == True
                                                                                    # REMOVED_SYNTAX_ERROR: assert "limitations" in alternatives

                                                                                    # Each alternative should be actionable
                                                                                    # REMOVED_SYNTAX_ERROR: for approach in alternatives["alternative_approaches"]:
                                                                                        # REMOVED_SYNTAX_ERROR: assert "approach" in approach
                                                                                        # REMOVED_SYNTAX_ERROR: assert len(approach["approach"]) > 10

                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                        # Removed problematic line: async def test_data_sufficiency_feedback(self, data_helper_agent):
                                                                                            # REMOVED_SYNTAX_ERROR: """Test clear feedback on data sufficiency levels."""
                                                                                            # REMOVED_SYNTAX_ERROR: data_provided = { )
                                                                                            # REMOVED_SYNTAX_ERROR: "monthly_spend": 5000,
                                                                                            # REMOVED_SYNTAX_ERROR: "provider": "OpenAI",
                                                                                            # REMOVED_SYNTAX_ERROR: "request_volume": 10000
                                                                                            

                                                                                            # Mock the execute response for data sufficiency assessment
                                                                                            # REMOVED_SYNTAX_ERROR: data_helper_agent.llm_manager.generate_response = AsyncMock( )
                                                                                            # REMOVED_SYNTAX_ERROR: return_value={ )
                                                                                            # REMOVED_SYNTAX_ERROR: "content": json.dumps({ ))
                                                                                            # REMOVED_SYNTAX_ERROR: "sufficiency_level": "PARTIAL",
                                                                                            # REMOVED_SYNTAX_ERROR: "percentage_complete": 65,
                                                                                            # REMOVED_SYNTAX_ERROR: "can_proceed": True,
                                                                                            # REMOVED_SYNTAX_ERROR: "optimization_quality": { )
                                                                                            # REMOVED_SYNTAX_ERROR: "with_current_data": "Good recommendations (60-70% confidence)",
                                                                                            # REMOVED_SYNTAX_ERROR: "with_complete_data": "Excellent recommendations (90%+ confidence)"
                                                                                            # REMOVED_SYNTAX_ERROR: },
                                                                                            # REMOVED_SYNTAX_ERROR: "missing_for_full_analysis": [ )
                                                                                            # REMOVED_SYNTAX_ERROR: "Performance metrics for latency optimization",
                                                                                            # REMOVED_SYNTAX_ERROR: "Usage patterns for load balancing"
                                                                                            # REMOVED_SYNTAX_ERROR: ],
                                                                                            # REMOVED_SYNTAX_ERROR: "value_of_additional_data": "$500-1000 additional monthly savings"
                                                                                            # REMOVED_SYNTAX_ERROR: }),
                                                                                            # REMOVED_SYNTAX_ERROR: "metadata": {"model": "test"}
                                                                                            
                                                                                            

                                                                                            # Get mocked response
                                                                                            # REMOVED_SYNTAX_ERROR: response = await data_helper_agent.llm_manager.generate_response(data_provided)
                                                                                            # REMOVED_SYNTAX_ERROR: assessment = json.loads(response["content"])

                                                                                            # Validate sufficiency feedback
                                                                                            # REMOVED_SYNTAX_ERROR: assert assessment["sufficiency_level"] in ["INSUFFICIENT", "PARTIAL", "SUFFICIENT"]
                                                                                            # REMOVED_SYNTAX_ERROR: assert 0 <= assessment["percentage_complete"] <= 100
                                                                                            # REMOVED_SYNTAX_ERROR: assert "optimization_quality" in assessment
                                                                                            # REMOVED_SYNTAX_ERROR: assert "value_of_additional_data" in assessment

                                                                                            # Should quantify the value of providing more data
                                                                                            # REMOVED_SYNTAX_ERROR: assert "$" in assessment["value_of_additional_data"]

                                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                                            # Removed problematic line: async def test_data_request_success_metrics(self, data_helper_agent):
                                                                                                # REMOVED_SYNTAX_ERROR: """Test that data requests lead to successful optimization."""
                                                                                                # Track success rate of data collection
                                                                                                # REMOVED_SYNTAX_ERROR: test_sessions = [ )
                                                                                                # REMOVED_SYNTAX_ERROR: { )
                                                                                                # REMOVED_SYNTAX_ERROR: "initial_request": "vague optimization need",
                                                                                                # REMOVED_SYNTAX_ERROR: "data_requested": ["costs", "usage", "goals"],
                                                                                                # REMOVED_SYNTAX_ERROR: "data_received": ["costs", "usage", "goals"],
                                                                                                # REMOVED_SYNTAX_ERROR: "optimization_success": True,
                                                                                                # REMOVED_SYNTAX_ERROR: "value_delivered": "$3000/month"
                                                                                                # REMOVED_SYNTAX_ERROR: },
                                                                                                # REMOVED_SYNTAX_ERROR: { )
                                                                                                # REMOVED_SYNTAX_ERROR: "initial_request": "reduce latency",
                                                                                                # REMOVED_SYNTAX_ERROR: "data_requested": ["current_metrics", "architecture"],
                                                                                                # REMOVED_SYNTAX_ERROR: "data_received": ["current_metrics"],
                                                                                                # REMOVED_SYNTAX_ERROR: "optimization_success": True,
                                                                                                # REMOVED_SYNTAX_ERROR: "value_delivered": "40% latency reduction"
                                                                                                # REMOVED_SYNTAX_ERROR: },
                                                                                                # REMOVED_SYNTAX_ERROR: { )
                                                                                                # REMOVED_SYNTAX_ERROR: "initial_request": "make AI better",
                                                                                                # REMOVED_SYNTAX_ERROR: "data_requested": ["everything"],
                                                                                                # REMOVED_SYNTAX_ERROR: "data_received": [],
                                                                                                # REMOVED_SYNTAX_ERROR: "optimization_success": False,
                                                                                                # REMOVED_SYNTAX_ERROR: "value_delivered": None
                                                                                                
                                                                                                

                                                                                                # REMOVED_SYNTAX_ERROR: success_rate = sum(1 for s in test_sessions if s["optimization_success"]) / len(test_sessions)
                                                                                                # REMOVED_SYNTAX_ERROR: completion_rate = sum( )
                                                                                                # REMOVED_SYNTAX_ERROR: len(s["data_received"]) / len(s["data_requested"])
                                                                                                # REMOVED_SYNTAX_ERROR: for s in test_sessions if s["data_requested"]
                                                                                                # REMOVED_SYNTAX_ERROR: ) / len(test_sessions)

                                                                                                # Validate success metrics
                                                                                                # REMOVED_SYNTAX_ERROR: assert success_rate >= 0.66  # At least 2/3 successful
                                                                                                # REMOVED_SYNTAX_ERROR: assert completion_rate >= 0.5  # At least half of requested data provided

# REMOVED_SYNTAX_ERROR: def test_user_experience_quality(self):
    # REMOVED_SYNTAX_ERROR: """Meta-test for user experience quality."""
    # REMOVED_SYNTAX_ERROR: ux_requirements = { )
    # REMOVED_SYNTAX_ERROR: "clarity": { )
    # REMOVED_SYNTAX_ERROR: "max_questions_per_request": 5,
    # REMOVED_SYNTAX_ERROR: "max_words_per_question": 30,
    # REMOVED_SYNTAX_ERROR: "requires_examples": True
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "guidance": { )
    # REMOVED_SYNTAX_ERROR: "provides_context": True,
    # REMOVED_SYNTAX_ERROR: "explains_value": True,
    # REMOVED_SYNTAX_ERROR: "offers_alternatives": True
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: "efficiency": { )
    # REMOVED_SYNTAX_ERROR: "progressive_collection": True,
    # REMOVED_SYNTAX_ERROR: "acknowledges_input": True,
    # REMOVED_SYNTAX_ERROR: "minimizes_friction": True
    
    

    # Validate UX requirements are defined
    # REMOVED_SYNTAX_ERROR: assert all(category for category in ux_requirements.keys())
    # REMOVED_SYNTAX_ERROR: assert ux_requirements["clarity"]["max_questions_per_request"] <= 5
    # REMOVED_SYNTAX_ERROR: assert ux_requirements["guidance"]["explains_value"] == True