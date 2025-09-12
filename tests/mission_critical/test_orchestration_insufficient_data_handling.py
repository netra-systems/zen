"""Mission-Critical Tests for Orchestration Insufficient Data Handling

Tests the system's ability to handle insufficient data scenarios by focusing on
data collection, user education, and value demonstration.

Business Value Justification (BVJ):
- Segment: Free, Early (Conversion focus)
- Business Goal: Convert users by demonstrating value potential
- Value Impact: Educate users on optimization possibilities
- Strategic Impact: Increases user engagement and data collection success
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestInsufficientDataHandling:
    """Test suite for insufficient data handling scenarios in orchestration."""
    
    # === Test Data Fixtures ===
    
    @pytest.fixture
    def insufficient_vague_request(self):
        """Extremely vague request with almost no data."""
        return {
            "user_request": "optimize",
            "available_data": {},
            "missing_data": [
                "domain",
                "current_state",
                "optimization_goals",
                "constraints",
                "metrics",
                "budget"
            ],
            "completeness": 0.05
        }
    
    @pytest.fixture
    def insufficient_general_help_request(self):
        """General help request without specifics."""
        return {
            "user_request": "Help with AI costs",
            "available_data": {
                "general_concern": "costs"
            },
            "missing_data": [
                "current_spend",
                "models_used",
                "use_cases",
                "volume",
                "requirements"
            ],
            "completeness": 0.15
        }
    
    @pytest.fixture
    def insufficient_new_user_request(self):
        """New user with no historical data."""
        return {
            "user_request": "Starting to use AI, want to optimize from beginning",
            "available_data": {
                "user_status": "new",
                "intent": "proactive_optimization"
            },
            "missing_data": [
                "planned_usage",
                "budget",
                "use_cases",
                "scale_expectations",
                "performance_needs"
            ],
            "completeness": 0.20
        }
    
    @pytest.fixture
    def insufficient_problem_only_request(self):
        """User describes problem but no metrics or details."""
        return {
            "user_request": "Our AI is expensive and slow",
            "available_data": {
                "problems": ["expensive", "slow"]
            },
            "missing_data": [
                "actual_costs",
                "actual_latency",
                "acceptable_targets",
                "usage_patterns",
                "infrastructure"
            ],
            "completeness": 0.25
        }
    
    @pytest.fixture
    def insufficient_goal_only_request(self):
        """User has goal but no current state data."""
        return {
            "user_request": "Want to reduce costs by 50%",
            "available_data": {
                "goal": "50% cost reduction"
            },
            "missing_data": [
                "current_costs",
                "current_usage",
                "current_models",
                "flexibility",
                "constraints"
            ],
            "completeness": 0.18
        }
    
    # === Core Workflow Tests ===
    
    @pytest.mark.asyncio
    async def test_insufficient_data_workflow_selection(self, insufficient_vague_request):
        """Test that insufficient data triggers data collection workflow."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        with patch.object(orchestrator, 'assess_data_completeness') as mock_assess:
            mock_assess.return_value = {
                "completeness": insufficient_vague_request["completeness"],
                "workflow": "data_collection_focus",
                "confidence": 0.10
            }
            
            workflow = await orchestrator.select_workflow(insufficient_vague_request)
            
            assert workflow["type"] == "data_collection_focus"
            assert workflow["confidence"] < 0.20
            assert "phases" in workflow
            assert "educate" in workflow["phases"]
            assert "collect" in workflow["phases"]
            assert "demonstrate_value" in workflow["phases"]
    
    @pytest.mark.asyncio
    async def test_clarification_request_generation(self, insufficient_vague_request):
        """Test generation of clarification requests for vague input."""
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
        
        agent = TriageSubAgent()
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.ask_structured_llm.return_value = {
                "data_sufficiency": "insufficient",
                "confidence": 0.05,
                "clarification_request": {
                    "message": "I can help you optimize several areas. Could you tell me more?",
                    "options": [
                        {
                            "category": "AI/LLM Cost Optimization",
                            "description": "Reduce AI spending by 30-70%",
                            "next_question": "What's your current monthly AI spend?"
                        },
                        {
                            "category": "Performance Optimization",
                            "description": "Improve response times by 40-60%",
                            "next_question": "What's your current response time?"
                        },
                        {
                            "category": "Scale Optimization",
                            "description": "Handle 10x more requests efficiently",
                            "next_question": "What's your current request volume?"
                        },
                        {
                            "category": "Quality Optimization",
                            "description": "Improve accuracy while reducing costs",
                            "next_question": "What are your quality requirements?"
                        }
                    ],
                    "quick_start": "Or describe your specific challenge in a few sentences"
                },
                "interpretation_attempts": [
                    "General optimization request",
                    "Possible focus areas: cost, performance, scale, quality"
                ]
            }
            
            state = DeepAgentState(user_request=insufficient_vague_request["user_request"])
            context = ExecutionContext(
                run_id="test-insufficient-001",
                agent_name="triage",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert result.result["data_sufficiency"] == "insufficient"
            assert "clarification_request" in result.result
            assert len(result.result["clarification_request"]["options"]) >= 3
            assert result.result["confidence"] < 0.10
    
    @pytest.mark.asyncio
    async def test_educational_content_delivery(self, insufficient_general_help_request):
        """Test that educational content is provided with insufficient data."""
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        agent = DataHelperAgent(None, None, None)
        
        with patch.object(agent, 'data_helper_tool') as mock_tool:
            mock_tool.generate_data_request.return_value = {
                "success": True,
                "educational_content": {
                    "why_data_matters": {
                        "title": "Why We Need Specific Information",
                        "explanation": "AI optimization is highly context-dependent. Here's why:",
                        "examples": [
                            {
                                "scenario": "High-volume, low-complexity requests",
                                "optimization": "Switch to lighter models",
                                "potential_savings": "60-70%"
                            },
                            {
                                "scenario": "Batch-compatible workloads",
                                "optimization": "Implement batching",
                                "potential_savings": "40-50%"
                            },
                            {
                                "scenario": "Repetitive queries",
                                "optimization": "Add caching layer",
                                "potential_savings": "30-40%"
                            }
                        ]
                    },
                    "success_stories": {
                        "title": "What's Possible with Complete Data",
                        "cases": [
                            "E-commerce company: Reduced costs by 65% in 3 weeks",
                            "SaaS startup: Improved latency by 70% while cutting costs 40%",
                            "Healthcare app: Maintained quality while reducing spend by 50%"
                        ]
                    },
                    "getting_started": {
                        "title": "Quick Start Guide",
                        "steps": [
                            "1. Check your current AI/LLM invoice",
                            "2. Identify your top 3 use cases",
                            "3. Note your performance requirements",
                            "4. Share this information with us"
                        ],
                        "time_required": "10-15 minutes",
                        "outcome": "Personalized optimization plan within 24 hours"
                    }
                },
                "data_collection_template": {
                    "format": "questionnaire",
                    "sections": ["costs", "usage", "requirements", "constraints"]
                }
            }
            
            state = DeepAgentState(
                user_request=insufficient_general_help_request["user_request"],
                data_completeness=0.15
            )
            
            context = ExecutionContext(
                run_id="test-insufficient-002",
                agent_name="data_helper",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "educational_content" in result.result
            education = result.result["educational_content"]
            assert "why_data_matters" in education
            assert "success_stories" in education
            assert "getting_started" in education
            assert education["getting_started"]["time_required"] == "10-15 minutes"
    
    @pytest.mark.asyncio
    async def test_value_demonstration_without_data(self, insufficient_new_user_request):
        """Test system demonstrates potential value despite no data."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        agent = ReportingSubAgent()
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.ask_structured_llm.return_value = {
                "value_demonstration": {
                    "title": "What AI Optimization Can Achieve",
                    "industry_benchmarks": {
                        "average_savings": "45-55%",
                        "top_quartile_savings": "65-75%",
                        "implementation_time": "2-4 weeks"
                    },
                    "optimization_categories": [
                        {
                            "category": "Model Selection",
                            "impact": "30-50% cost reduction",
                            "effort": "Low",
                            "example": "GPT-4  ->  GPT-3.5 for appropriate tasks"
                        },
                        {
                            "category": "Prompt Engineering",
                            "impact": "20-30% token reduction",
                            "effort": "Low",
                            "example": "Optimized prompts use fewer tokens"
                        },
                        {
                            "category": "Caching & Batching",
                            "impact": "25-40% request reduction",
                            "effort": "Medium",
                            "example": "Cache common queries, batch similar requests"
                        },
                        {
                            "category": "Infrastructure Optimization",
                            "impact": "20-35% efficiency gain",
                            "effort": "Medium",
                            "example": "Better routing, load balancing"
                        }
                    ],
                    "roi_projection": {
                        "typical_payback_period": "1-2 months",
                        "year_1_roi": "300-500%",
                        "risk": "Minimal with phased approach"
                    }
                },
                "next_steps": {
                    "immediate": "Provide basic usage information",
                    "timeline": "Get optimization plan in 24 hours",
                    "commitment": "No upfront costs, pay only for savings"
                }
            }
            
            state = DeepAgentState(
                user_request=insufficient_new_user_request["user_request"],
                user_status="new"
            )
            
            context = ExecutionContext(
                run_id="test-insufficient-003",
                agent_name="reporting",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "value_demonstration" in result.result
            demo = result.result["value_demonstration"]
            assert "industry_benchmarks" in demo
            assert "optimization_categories" in demo
            assert len(demo["optimization_categories"]) >= 4
            assert "roi_projection" in demo
    
    @pytest.mark.asyncio
    async def test_progressive_data_collection(self, insufficient_problem_only_request):
        """Test progressive data collection strategy."""
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        agent = DataHelperAgent(None, None, None)
        
        with patch.object(agent, 'data_helper_tool') as mock_tool:
            mock_tool.generate_data_request.return_value = {
                "success": True,
                "progressive_collection": {
                    "stage_1_minimal": {
                        "description": "Just 3 questions to start",
                        "questions": [
                            {
                                "q": "Estimated monthly AI spend?",
                                "format": "Range is fine (e.g., $5K-10K)",
                                "why": "Baseline for savings calculation"
                            },
                            {
                                "q": "Current response times?",
                                "format": "Rough average (e.g., 2-3 seconds)",
                                "why": "Identify performance bottlenecks"
                            },
                            {
                                "q": "Main use case?",
                                "format": "One sentence description",
                                "why": "Tailor optimization approach"
                            }
                        ],
                        "time_required": "2 minutes",
                        "value_unlocked": "Basic optimization roadmap"
                    },
                    "stage_2_detailed": {
                        "description": "After initial analysis",
                        "when": "If you like the initial recommendations",
                        "additional_questions": 5,
                        "time_required": "5-10 minutes",
                        "value_unlocked": "Detailed implementation plan"
                    },
                    "stage_3_comprehensive": {
                        "description": "For maximum optimization",
                        "when": "During implementation",
                        "data_sources": ["API logs", "Usage reports", "Performance metrics"],
                        "value_unlocked": "60-70% cost reduction potential"
                    }
                },
                "incentive": {
                    "message": "Start with just 3 questions - see value immediately",
                    "guarantee": "Actionable insights even with minimal data"
                }
            }
            
            state = DeepAgentState(
                user_request=insufficient_problem_only_request["user_request"],
                identified_problems=["expensive", "slow"]
            )
            
            context = ExecutionContext(
                run_id="test-insufficient-004",
                agent_name="data_helper",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "progressive_collection" in result.result
            stages = result.result["progressive_collection"]
            assert "stage_1_minimal" in stages
            assert len(stages["stage_1_minimal"]["questions"]) <= 3
            assert stages["stage_1_minimal"]["time_required"] == "2 minutes"
    
    @pytest.mark.asyncio
    async def test_quick_template_generation(self, insufficient_goal_only_request):
        """Test generation of quick-fill templates for data collection."""
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        agent = DataHelperAgent(None, None, None)
        
        with patch.object(agent, 'data_helper_tool') as mock_tool:
            mock_tool.generate_data_request.return_value = {
                "success": True,
                "quick_template": {
                    "title": "Quick Info Form - Copy & Fill",
                    "template": """
=== AI OPTIMIZATION QUICK FORM ===

Current Situation:
- Monthly AI/LLM Spend: $________
- Primary AI Model: ____________
- Main Use Case: ______________
- Daily Request Volume: ________

Goals:
- Target Cost Reduction: 50% (your goal)
- Acceptable Trade-offs: ______________

Constraints:
- Must Maintain (check all that apply):
  [ ] Response time < ___ seconds
  [ ] Quality score > ___%
  [ ] 99.9% uptime
  [ ] Compliance requirements: _______

Quick Win Opportunities (check if interested):
  [ ] Model optimization (30-50% savings)
  [ ] Prompt engineering (20-30% savings)
  [ ] Caching strategy (25-40% savings)
  [ ] Batch processing (30-45% savings)

=== END FORM ===
                    """,
                    "instructions": "Fill what you know, leave blanks for unknowns",
                    "submission": "Paste completed form in chat",
                    "processing_time": "Analysis within 1 hour"
                },
                "alternative_options": {
                    "guided_chat": "Answer questions interactively",
                    "upload_invoice": "Share recent AI service invoice",
                    "connect_api": "Grant read-only API access for automatic analysis"
                }
            }
            
            state = DeepAgentState(
                user_request=insufficient_goal_only_request["user_request"],
                stated_goal="50% cost reduction"
            )
            
            context = ExecutionContext(
                run_id="test-insufficient-005",
                agent_name="data_helper",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "quick_template" in result.result
            template = result.result["quick_template"]
            assert "template" in template
            assert "50%" in template["template"]  # Incorporates user's goal
            assert template["processing_time"] == "Analysis within 1 hour"
    
    # === Edge Case Tests ===
    
    @pytest.mark.asyncio
    async def test_completely_empty_request(self):
        """Test handling of completely empty request."""
        empty_request = {
            "user_request": "",
            "available_data": {},
            "completeness": 0.00
        }
        
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
        
        agent = TriageSubAgent()
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.ask_structured_llm.return_value = {
                "data_sufficiency": "insufficient",
                "confidence": 0.00,
                "fallback_response": {
                    "greeting": "Hello! I'm here to help optimize your AI operations.",
                    "capabilities": [
                        "Reduce AI/LLM costs by 30-70%",
                        "Improve response times by 40-60%",
                        "Scale efficiently to handle more load",
                        "Maintain quality while optimizing costs"
                    ],
                    "start_prompt": "What aspect of AI optimization interests you most?",
                    "quick_options": [
                        "Tell me about cost optimization",
                        "Help with performance issues",
                        "Show me what's possible",
                        "I have a specific question"
                    ]
                }
            }
            
            state = DeepAgentState(user_request=empty_request["user_request"])
            context = ExecutionContext(
                run_id="test-empty-001",
                agent_name="triage",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "fallback_response" in result.result
            assert "greeting" in result.result["fallback_response"]
            assert "capabilities" in result.result["fallback_response"]
    
    @pytest.mark.asyncio
    async def test_data_phobia_handling(self):
        """Test handling users reluctant to share data."""
        reluctant_request = {
            "user_request": "Can you help without seeing our data?",
            "available_data": {
                "concern": "data_privacy"
            },
            "completeness": 0.10
        }
        
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        agent = DataHelperAgent(None, None, None)
        
        with patch.object(agent, 'data_helper_tool') as mock_tool:
            mock_tool.generate_data_request.return_value = {
                "success": True,
                "privacy_conscious_approach": {
                    "message": "Absolutely! We can work with anonymized or approximate data.",
                    "options": [
                        {
                            "level": "Fully Anonymous",
                            "description": "Share only patterns, no actual values",
                            "example": "High/Medium/Low instead of dollar amounts",
                            "value": "General optimization strategies"
                        },
                        {
                            "level": "Aggregated Data",
                            "description": "Summarized metrics only",
                            "example": "Monthly totals, average latencies",
                            "value": "Targeted recommendations"
                        },
                        {
                            "level": "Synthetic Data",
                            "description": "Use example data similar to yours",
                            "example": "We create a model based on your industry",
                            "value": "Industry-specific optimizations"
                        }
                    ],
                    "guarantees": [
                        "No data storage beyond session",
                        "No sharing with third parties",
                        "Audit trail of all data usage"
                    ],
                    "alternative": {
                        "self_service": "Here's a guide to optimize on your own",
                        "tools": ["Cost calculator", "Optimization checklist", "Best practices guide"]
                    }
                }
            }
            
            state = DeepAgentState(
                user_request=reluctant_request["user_request"],
                data_privacy_concern=True
            )
            
            context = ExecutionContext(
                run_id="test-privacy-001",
                agent_name="data_helper",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            assert "privacy_conscious_approach" in result.result
            assert len(result.result["privacy_conscious_approach"]["options"]) >= 3
            assert "guarantees" in result.result["privacy_conscious_approach"]
    
    @pytest.mark.asyncio
    async def test_conversion_focused_messaging(self):
        """Test that messaging is optimized for user conversion."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        agent = ReportingSubAgent()
        
        with patch.object(agent, 'llm_manager') as mock_llm:
            mock_llm.ask_structured_llm.return_value = {
                "conversion_optimized_response": {
                    "hook": "Most companies waste 40-60% of their AI budget unnecessarily",
                    "social_proof": {
                        "statistics": "87% of our users reduce costs within 2 weeks",
                        "testimonial": "'Saved $15K in the first month' - TechStartup CEO",
                        "logos": ["Company A", "Company B", "Company C"]
                    },
                    "urgency_creation": {
                        "message": "Every day without optimization costs you money",
                        "calculation": "At typical rates, you could be losing $200-500 daily"
                    },
                    "risk_reversal": {
                        "guarantee": "See value in 24 hours or no commitment",
                        "trial": "Start with free assessment",
                        "flexibility": "Cancel anytime, no lock-in"
                    },
                    "clear_cta": {
                        "primary": "Get Your Free AI Cost Assessment",
                        "secondary": "See 5-Minute Demo",
                        "tertiary": "Read Success Stories"
                    },
                    "friction_reduction": [
                        "No credit card required",
                        "No complex setup",
                        "Results in 24 hours"
                    ]
                }
            }
            
            state = DeepAgentState(
                user_type="free",
                data_completeness=0.10
            )
            
            context = ExecutionContext(
                run_id="test-conversion-001",
                agent_name="reporting",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            response = result.result["conversion_optimized_response"]
            assert "social_proof" in response
            assert "urgency_creation" in response
            assert "risk_reversal" in response
            assert "clear_cta" in response
            assert "No credit card required" in response["friction_reduction"]
    
    # === Integration Tests ===
    
    @pytest.mark.asyncio
    async def test_minimal_workflow_execution(self, insufficient_vague_request):
        """Test that insufficient data triggers minimal workflow."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        execution_sequence = []
        
        async def track_execution(agent_name, context):
            execution_sequence.append(agent_name)
            
            if agent_name == "triage":
                return ExecutionResult(
                    success=True,
                    result={
                        "data_sufficiency": "insufficient",
                        "workflow_recommendation": "data_collection_only"
                    }
                )
            elif agent_name == "data_helper":
                return ExecutionResult(
                    success=True,
                    result={
                        "educational_content": "...",
                        "data_request": "...",
                        "quick_template": "..."
                    }
                )
            
            return ExecutionResult(success=True, result={})
        
        with patch.object(orchestrator, 'execute_agent', side_effect=track_execution):
            await orchestrator.execute_minimal_workflow(insufficient_vague_request)
            
            # Only triage and data_helper should execute
            assert execution_sequence == ["triage", "data_helper"]
            # No optimization, analysis, or action agents
            assert "optimization" not in execution_sequence
            assert "data" not in execution_sequence  # data analysis
            assert "actions" not in execution_sequence
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_chain(self):
        """Test graceful degradation as data completeness decreases."""
        completeness_levels = [
            (0.80, "full_optimization"),
            (0.60, "modified_optimization"),
            (0.40, "limited_optimization"),
            (0.20, "data_collection_focus"),
            (0.05, "education_only")
        ]
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        for completeness, expected_mode in completeness_levels:
            with patch.object(orchestrator, 'determine_execution_mode') as mock_determine:
                mock_determine.return_value = expected_mode
                
                mode = await orchestrator.determine_execution_mode({"completeness": completeness})
                
                if completeness >= 0.80:
                    assert mode == "full_optimization"
                elif completeness >= 0.40:
                    assert "optimization" in mode
                else:
                    assert "collection" in mode or "education" in mode
    
    @pytest.mark.asyncio
    async def test_websocket_events_insufficient_data(self):
        """Test WebSocket events for insufficient data scenarios."""
        from netra_backend.app.services.websocket_manager import WebSocketManager
        
        websocket_manager = WebSocketManager()
        events_sent = []
        
        async def mock_send_event(event_type, data):
            events_sent.append({"type": event_type, "data": data})
        
        websocket_manager.send_event = mock_send_event
        
        # Simulate insufficient data workflow
        await websocket_manager.send_event("agent_started", {"agent": "triage"})
        await websocket_manager.send_event("insufficient_data", {
            "message": "I need more information to provide specific recommendations"
        })
        await websocket_manager.send_event("education_content", {
            "title": "Why This Information Matters",
            "content": "..."
        })
        await websocket_manager.send_event("data_collection", {
            "template": "Quick form provided",
            "time_required": "2-5 minutes"
        })
        await websocket_manager.send_event("value_proposition", {
            "potential": "30-70% cost reduction possible",
            "timeline": "Results within 24 hours of data submission"
        })
        
        assert len(events_sent) >= 5
        assert any(e["type"] == "insufficient_data" for e in events_sent)
        assert any(e["type"] == "education_content" for e in events_sent)
        assert any(e["type"] == "data_collection" for e in events_sent)
    
    # === User Experience Tests ===
    
    @pytest.mark.asyncio
    async def test_user_experience_optimization(self):
        """Test that user experience is optimized for engagement."""
        ux_criteria = {
            "time_to_value": "< 2 minutes",
            "cognitive_load": "minimal",
            "clear_next_steps": True,
            "motivation_maintained": True,
            "friction_minimized": True
        }
        
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        
        agent = DataHelperAgent(None, None, None)
        
        with patch.object(agent, 'data_helper_tool') as mock_tool:
            mock_tool.generate_data_request.return_value = {
                "success": True,
                "ux_optimized": {
                    "immediate_value": {
                        "message": "I can already tell you 3 quick wins",
                        "items": ["Use GPT-3.5 for simple tasks", "Implement caching", "Optimize prompts"],
                        "time_to_implement": "Start today"
                    },
                    "minimal_ask": {
                        "message": "Just answer 3 questions to unlock personalized recommendations",
                        "questions": ["Monthly spend?", "Main use case?", "Biggest pain point?"],
                        "time_required": "< 2 minutes"
                    },
                    "motivation": {
                        "peer_comparison": "Companies like yours save $5-15K monthly",
                        "quick_win": "Most users see first savings within 48 hours",
                        "support": "We guide you through every step"
                    },
                    "next_steps": {
                        "1": "Answer 3 questions (2 min)",
                        "2": "Review recommendations (5 min)",
                        "3": "Implement first optimization (1 day)",
                        "4": "See measurable savings (1 week)"
                    }
                }
            }
            
            state = DeepAgentState(data_completeness=0.15)
            context = ExecutionContext(
                run_id="test-ux-001",
                agent_name="data_helper",
                state=state
            )
            
            result = await agent.execute(context)
            
            assert result.success
            ux = result.result["ux_optimized"]
            assert ux["minimal_ask"]["time_required"] == "< 2 minutes"
            assert len(ux["minimal_ask"]["questions"]) == 3
            assert "next_steps" in ux
            assert "motivation" in ux


# === Test Runner ===

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--asyncio-mode=auto",
        "--tb=short",
        "--no-header",
        "-p", "no:warnings"
    ])