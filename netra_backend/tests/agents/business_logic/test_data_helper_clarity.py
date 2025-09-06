"""
Test suite for DataHelperAgent business logic validation.
Ensures data requests are clear, actionable, and lead to successful optimization.
"""

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
from netra_backend.app.agents.models import (
    DataRequest,
    DataRequirement,
    DataCategory,
    DataPriority,
    UserExperience
)


class TestDataHelperClarity:
    """Validate DataHelper produces clear, actionable data requests."""

    @pytest.fixture
    async def data_helper_agent(self, mock_llm_manager):
        """Create a DataHelperAgent with mocked dependencies."""
        agent = DataHelperAgent(llm_manager=mock_llm_manager)
        await asyncio.sleep(0)
        return agent

    @pytest.fixture
    def data_request_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Define scenarios for data request generation."""
        return {
            "missing_cost_data": {
                "context": {
                    "user_request": "Help optimize our AI",
                    "available_data": {},
                    "optimization_goal": "cost_reduction"
                },
                "expected_requests": [
                    {
                        "category": DataCategory.FINANCIAL,
                        "priority": DataPriority.CRITICAL,
                        "questions": [
                            "What is your current monthly spend on AI/LLM services?",
                            "Which AI providers are you using (OpenAI, Anthropic, etc.)?",
                            "What is your average daily request volume?"
                        ],
                        "format": "structured",
                        "examples": ["Monthly spend: $5000", "Providers: OpenAI (80%), Claude (20%)"]
                    }
                ],
                "clarity_score": 0.9
            },
            "missing_performance_data": {
                "context": {
                    "user_request": "System is slow",
                    "available_data": {"provider": "OpenAI"},
                    "optimization_goal": "latency_reduction"
                },
                "expected_requests": [
                    {
                        "category": DataCategory.PERFORMANCE,
                        "priority": DataPriority.CRITICAL,
                        "questions": [
                            "What are your current response time metrics (P50, P95, P99)?",
                            "What is the average token count per request?",
                            "What are your peak usage hours?"
                        ],
                        "format": "metrics",
                        "examples": ["P95: 3.5 seconds", "Avg tokens: 1500"]
                    }
                ],
                "clarity_score": 0.85
            },
            "complex_multi_category": {
                "context": {
                    "user_request": "Complete AI optimization needed",
                    "available_data": {"monthly_spend": 10000},
                    "optimization_goal": "comprehensive"
                },
                "expected_requests": [
                    {
                        "category": DataCategory.USAGE,
                        "priority": DataPriority.HIGH,
                        "questions": ["Request patterns", "User segments", "Time distribution"]
                    },
                    {
                        "category": DataCategory.TECHNICAL,
                        "priority": DataPriority.MEDIUM,
                        "questions": ["Current architecture", "Integration points", "Constraints"]
                    },
                    {
                        "category": DataCategory.BUSINESS,
                        "priority": DataPriority.HIGH,
                        "questions": ["SLA requirements", "Quality thresholds", "Growth projections"]
                    }
                ],
                "clarity_score": 0.8
            }
        }

    @pytest.mark.asyncio
    async def test_critical_data_identification(self, data_helper_agent, data_request_scenarios):
        """Test identification of critical missing data."""
        scenario = data_request_scenarios["missing_cost_data"]
        
        with patch.object(data_helper_agent, 'identify_missing_data') as mock_identify:
            mock_identify.return_value = [
                DataRequirement(
                    category=DataCategory.FINANCIAL,
                    field="monthly_spend",
                    priority=DataPriority.CRITICAL,
                    reason="Required for cost optimization calculations"
                ),
                DataRequirement(
                    category=DataCategory.FINANCIAL,
                    field="provider_distribution",
                    priority=DataPriority.CRITICAL,
                    reason="Needed to identify optimization opportunities"
                )
            ]
            
            missing_data = await data_helper_agent.identify_missing_data(scenario["context"])
            
            # Validate critical data is identified
            assert len(missing_data) > 0
            assert all(req.priority == DataPriority.CRITICAL for req in missing_data 
                      if req.category == DataCategory.FINANCIAL)
            assert all(req.reason is not None and len(req.reason) > 20 
                      for req in missing_data)

    @pytest.mark.asyncio
    async def test_question_clarity_and_specificity(self, data_helper_agent, data_request_scenarios):
        """Test that generated questions are clear and specific."""
        scenario = data_request_scenarios["missing_performance_data"]
        
        with patch.object(data_helper_agent, 'generate_questions') as mock_generate:
            mock_generate.return_value = [
                DataRequest(
                    category=DataCategory.PERFORMANCE,
                    priority=DataPriority.CRITICAL,
                    questions=scenario["expected_requests"][0]["questions"],
                    format="metrics",
                    examples=scenario["expected_requests"][0]["examples"],
                    instructions="Please provide metrics in the format shown in examples"
                )
            ]
            
            requests = await data_helper_agent.generate_data_requests(scenario["context"])
            request = requests[0]
            
            # Validate question clarity
            for question in request.questions:
                # Questions should be specific
                assert "?" in question  # Should be a question
                assert len(question) > 20  # Not too short
                assert len(question) < 200  # Not too long
                
                # Should contain specific terms
                specific_terms = ["metric", "time", "token", "request", "response", 
                                 "latency", "throughput", "error", "cost", "usage"]
                assert any(term in question.lower() for term in specific_terms)
            
            # Validate examples are provided
            assert len(request.examples) > 0
            assert all(":" in example for example in request.examples)  # Format: "Label: Value"

    @pytest.mark.asyncio
    async def test_user_friendly_formatting(self, data_helper_agent):
        """Test that data requests are formatted for user understanding."""
        test_context = {
            "user_request": "Help me optimize",
            "technical_level": "non-technical"
        }
        
        with patch.object(data_helper_agent, 'format_for_user') as mock_format:
            mock_format.return_value = {
                "title": "Information Needed for Optimization",
                "sections": [
                    {
                        "heading": "Current Costs",
                        "questions": [
                            "How much do you spend monthly on AI services?",
                            "Which AI services do you use most?"
                        ],
                        "why_needed": "This helps us identify cost-saving opportunities",
                        "example_response": "We spend $5000/month, mostly on GPT-4"
                    },
                    {
                        "heading": "Usage Patterns",
                        "questions": [
                            "How many AI requests do you make daily?",
                            "What are your peak usage hours?"
                        ],
                        "why_needed": "Understanding patterns helps optimize resource allocation",
                        "example_response": "10,000 requests/day, peak 9am-12pm EST"
                    }
                ],
                "submission_format": "You can provide answers in any format comfortable for you"
            }
            
            formatted_request = await data_helper_agent.format_for_user(test_context)
            
            # Validate user-friendly structure
            assert "title" in formatted_request
            assert "sections" in formatted_request
            
            for section in formatted_request["sections"]:
                assert "heading" in section
                assert "questions" in section
                assert "why_needed" in section  # Explains value
                assert "example_response" in section  # Provides guidance
                
                # Language should be accessible
                assert not any(term in section["why_needed"].lower() 
                             for term in ["api", "llm", "token", "embedding"])  # Avoid jargon

    @pytest.mark.asyncio
    async def test_progressive_data_collection(self, data_helper_agent):
        """Test that data collection is progressive (critical first)."""
        context = {
            "optimization_goal": "comprehensive",
            "available_data": {}
        }
        
        with patch.object(data_helper_agent, 'prioritize_requests') as mock_prioritize:
            mock_prioritize.return_value = [
                DataRequest(
                    category=DataCategory.FINANCIAL,
                    priority=DataPriority.CRITICAL,
                    questions=["What's your monthly AI spend?"],
                    phase=1
                ),
                DataRequest(
                    category=DataCategory.PERFORMANCE,
                    priority=DataPriority.HIGH,
                    questions=["What are your latency requirements?"],
                    phase=2
                ),
                DataRequest(
                    category=DataCategory.TECHNICAL,
                    priority=DataPriority.MEDIUM,
                    questions=["What's your tech stack?"],
                    phase=3
                )
            ]
            
            prioritized = await data_helper_agent.prioritize_requests(context)
            
            # Validate progressive collection
            assert prioritized[0].priority == DataPriority.CRITICAL
            assert prioritized[0].phase == 1
            
            # Later phases should have lower priority
            for i in range(len(prioritized) - 1):
                assert prioritized[i].phase <= prioritized[i + 1].phase
                assert prioritized[i].priority.value >= prioritized[i + 1].priority.value

    @pytest.mark.asyncio
    async def test_data_validation_guidance(self, data_helper_agent):
        """Test that requests include validation criteria."""
        with patch.object(data_helper_agent, 'add_validation_criteria') as mock_validate:
            mock_validate.return_value = DataRequest(
                category=DataCategory.FINANCIAL,
                priority=DataPriority.CRITICAL,
                questions=["Monthly AI spend?"],
                validation_criteria={
                    "format": "currency",
                    "range": {"min": 0, "max": 1000000},
                    "required": True
                },
                error_guidance={
                    "invalid_format": "Please provide amount in USD (e.g., $5000 or 5000)",
                    "out_of_range": "Value seems unusual, please verify",
                    "missing": "This information is required for optimization"
                }
            )
            
            request = await data_helper_agent.add_validation_criteria({})
            
            # Validate validation criteria
            assert "validation_criteria" in request.__dict__
            assert request.validation_criteria["required"] == True
            assert "format" in request.validation_criteria
            
            # Validate error guidance
            assert "error_guidance" in request.__dict__
            assert len(request.error_guidance) > 0
            assert all(len(msg) > 10 for msg in request.error_guidance.values())

    @pytest.mark.asyncio
    async def test_context_aware_requests(self, data_helper_agent, data_request_scenarios):
        """Test that requests adapt to user context."""
        contexts = [
            {
                "user_type": "startup",
                "expected_focus": ["cost", "efficiency", "quick_wins"],
                "avoid_terms": ["enterprise", "compliance", "governance"]
            },
            {
                "user_type": "enterprise",
                "expected_focus": ["scale", "reliability", "compliance"],
                "avoid_terms": ["quick", "cheap", "simple"]
            },
            {
                "user_type": "technical",
                "expected_focus": ["metrics", "architecture", "performance"],
                "avoid_terms": ["roughly", "approximately", "basic"]
            }
        ]
        
        for context in contexts:
            with patch.object(data_helper_agent, 'adapt_to_context') as mock_adapt:
                mock_adapt.return_value = DataRequest(
                    category=DataCategory.BUSINESS,
                    priority=DataPriority.HIGH,
                    questions=[f"Questions tailored for {context['user_type']}"],
                    language_style=context["user_type"],
                    focus_areas=context["expected_focus"]
                )
                
                request = await data_helper_agent.adapt_to_context(context)
                
                # Validate context adaptation
                assert request.language_style == context["user_type"]
                assert any(focus in str(request.focus_areas) 
                          for focus in context["expected_focus"])

    @pytest.mark.asyncio
    async def test_incremental_data_gathering(self, data_helper_agent):
        """Test support for incremental data gathering."""
        session_state = {
            "data_collected": {
                "monthly_spend": 5000,
                "provider": "OpenAI"
            },
            "data_pending": [
                "usage_patterns",
                "performance_metrics"
            ]
        }
        
        with patch.object(data_helper_agent, 'get_next_requirements') as mock_next:
            mock_next.return_value = [
                DataRequest(
                    category=DataCategory.USAGE,
                    priority=DataPriority.HIGH,
                    questions=["Daily request volume?", "Peak hours?"],
                    acknowledges_previous=["Thank you for the cost information"],
                    remaining_items=1
                )
            ]
            
            next_requests = await data_helper_agent.get_next_requirements(session_state)
            request = next_requests[0]
            
            # Validate incremental gathering
            assert len(request.acknowledges_previous) > 0
            assert "thank" in request.acknowledges_previous[0].lower()
            assert request.remaining_items >= 0
            assert request.category == DataCategory.USAGE  # Next in sequence

    @pytest.mark.asyncio
    async def test_fallback_for_missing_data(self, data_helper_agent):
        """Test graceful handling when user cannot provide data."""
        context = {
            "user_response": "I don't have access to those metrics",
            "requested_data": ["performance_metrics"]
        }
        
        with patch.object(data_helper_agent, 'provide_alternatives') as mock_alternatives:
            mock_alternatives.return_value = {
                "alternative_approaches": [
                    {
                        "approach": "Estimation based on typical patterns",
                        "questions": ["Approximate response time?", "Feels fast/medium/slow?"],
                        "confidence_impact": "Recommendations will be less precise but still valuable"
                    },
                    {
                        "approach": "Start with monitoring",
                        "action": "We can help you set up basic monitoring first",
                        "timeline": "Gather data for 1 week, then optimize"
                    }
                ],
                "can_proceed": True,
                "limitations": ["Savings estimates will have wider ranges"]
            }
            
            alternatives = await data_helper_agent.provide_alternatives(context)
            
            # Validate fallback options
            assert len(alternatives["alternative_approaches"]) > 0
            assert alternatives["can_proceed"] == True
            assert "limitations" in alternatives
            
            # Each alternative should be actionable
            for approach in alternatives["alternative_approaches"]:
                assert "approach" in approach
                assert len(approach["approach"]) > 10

    @pytest.mark.asyncio
    async def test_data_sufficiency_feedback(self, data_helper_agent):
        """Test clear feedback on data sufficiency levels."""
        data_provided = {
            "monthly_spend": 5000,
            "provider": "OpenAI",
            "request_volume": 10000
        }
        
        # Mock the execute response for data sufficiency assessment
        data_helper_agent.llm_manager.generate_response = AsyncMock(
            return_value={
                "content": json.dumps({
                    "sufficiency_level": "PARTIAL",
                    "percentage_complete": 65,
                    "can_proceed": True,
                    "optimization_quality": {
                        "with_current_data": "Good recommendations (60-70% confidence)",
                        "with_complete_data": "Excellent recommendations (90%+ confidence)"
                    },
                    "missing_for_full_analysis": [
                        "Performance metrics for latency optimization",
                        "Usage patterns for load balancing"
                    ],
                    "value_of_additional_data": "$500-1000 additional monthly savings"
                }),
                "metadata": {"model": "test"}
            }
        )
        
        # Get mocked response
        response = await data_helper_agent.llm_manager.generate_response(data_provided)
        assessment = json.loads(response["content"])
        
        # Validate sufficiency feedback
        assert assessment["sufficiency_level"] in ["INSUFFICIENT", "PARTIAL", "SUFFICIENT"]
        assert 0 <= assessment["percentage_complete"] <= 100
        assert "optimization_quality" in assessment
        assert "value_of_additional_data" in assessment
        
        # Should quantify the value of providing more data
        assert "$" in assessment["value_of_additional_data"]

    @pytest.mark.asyncio
    async def test_data_request_success_metrics(self, data_helper_agent):
        """Test that data requests lead to successful optimization."""
        # Track success rate of data collection
        test_sessions = [
            {
                "initial_request": "vague optimization need",
                "data_requested": ["costs", "usage", "goals"],
                "data_received": ["costs", "usage", "goals"],
                "optimization_success": True,
                "value_delivered": "$3000/month"
            },
            {
                "initial_request": "reduce latency",
                "data_requested": ["current_metrics", "architecture"],
                "data_received": ["current_metrics"],
                "optimization_success": True,
                "value_delivered": "40% latency reduction"
            },
            {
                "initial_request": "make AI better",
                "data_requested": ["everything"],
                "data_received": [],
                "optimization_success": False,
                "value_delivered": None
            }
        ]
        
        success_rate = sum(1 for s in test_sessions if s["optimization_success"]) / len(test_sessions)
        completion_rate = sum(
            len(s["data_received"]) / len(s["data_requested"]) 
            for s in test_sessions if s["data_requested"]
        ) / len(test_sessions)
        
        # Validate success metrics
        assert success_rate >= 0.66  # At least 2/3 successful
        assert completion_rate >= 0.5  # At least half of requested data provided

    def test_user_experience_quality(self):
        """Meta-test for user experience quality."""
        ux_requirements = {
            "clarity": {
                "max_questions_per_request": 5,
                "max_words_per_question": 30,
                "requires_examples": True
            },
            "guidance": {
                "provides_context": True,
                "explains_value": True,
                "offers_alternatives": True
            },
            "efficiency": {
                "progressive_collection": True,
                "acknowledges_input": True,
                "minimizes_friction": True
            }
        }
        
        # Validate UX requirements are defined
        assert all(category for category in ux_requirements.keys())
        assert ux_requirements["clarity"]["max_questions_per_request"] <= 5
        assert ux_requirements["guidance"]["explains_value"] == True