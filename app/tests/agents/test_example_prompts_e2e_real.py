"""
Comprehensive End-to-End Tests for Example Prompts with Real LLM Calls
Tests all 9 example prompts with 10 variations each (90 tests total)
Uses real LLM calls, synthetic data generation, and quality gates
"""

import pytest
import asyncio
import json
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
from unittest.mock import patch, AsyncMock

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.state import DeepAgentState
from app.schemas import SubAgentState
from app.llm.llm_manager import LLMManager
from app.services.agent_service import AgentService
from app.services.synthetic_data_service import SyntheticDataService, WorkloadCategory
from app.services.quality_gate_service import QualityGateService, ContentType, QualityLevel
from app.services.corpus_service import CorpusService
from app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from app.services.state_persistence_service import state_persistence_service
from app.ws_manager import WebSocketManager
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# The 9 example prompts from frontend/lib/examplePrompts.ts
EXAMPLE_PROMPTS = [
    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
    "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
    "I want to audit all uses of KV caching in my system to find optimization opportunities.",
    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",
    "@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",
    "@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher"
]


class TestExamplePromptsE2ERealLLM:
    """
    Comprehensive E2E test class that makes REAL LLM calls
    Tests each example prompt with 10 unique variations
    """
    
    @pytest.fixture(scope="class")
    async def setup_real_infrastructure(self):
        """Setup infrastructure with real LLM calls enabled"""
        settings = get_settings()
        
        # Create real database session
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True
        )
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as db_session:
            # Create real LLM Manager
            llm_manager = LLMManager()
            
            # Create real WebSocket Manager
            websocket_manager = WebSocketManager()
            
            # Create real Tool Dispatcher
            tool_dispatcher = ApexToolSelector()
            
            # Create real services
            synthetic_service = SyntheticDataService()
            quality_service = QualityGateService()
            corpus_service = CorpusService(db_session)
            
            # Create Supervisor with real components
            supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
            supervisor.thread_id = str(uuid.uuid4())
            supervisor.user_id = str(uuid.uuid4())
            
            # Create Agent Service
            agent_service = AgentService(supervisor)
            agent_service.websocket_manager = websocket_manager
            
            yield {
                "supervisor": supervisor,
                "agent_service": agent_service,
                "db_session": db_session,
                "llm_manager": llm_manager,
                "websocket_manager": websocket_manager,
                "tool_dispatcher": tool_dispatcher,
                "synthetic_service": synthetic_service,
                "quality_service": quality_service,
                "corpus_service": corpus_service,
                "settings": settings
            }
            
            await engine.dispose()
    
    def generate_synthetic_context(self, prompt_type: str) -> Dict[str, Any]:
        """Generate synthetic context data for a given prompt type"""
        context_generators = {
            "cost_optimization": self._generate_cost_context,
            "latency_optimization": self._generate_latency_context,
            "capacity_planning": self._generate_capacity_context,
            "function_optimization": self._generate_function_context,
            "model_selection": self._generate_model_context,
            "audit": self._generate_audit_context,
            "multi_objective": self._generate_multi_objective_context,
            "tool_migration": self._generate_tool_migration_context,
            "rollback_analysis": self._generate_rollback_context
        }
        
        return context_generators.get(prompt_type, self._generate_default_context)()
    
    def _generate_cost_context(self) -> Dict[str, Any]:
        """Generate synthetic cost optimization context"""
        return {
            "current_costs": {
                "daily": random.uniform(100, 1000),
                "monthly": random.uniform(3000, 30000),
                "per_request": random.uniform(0.001, 0.01)
            },
            "features": {
                "feature_X": {
                    "current_latency": random.uniform(100, 400),
                    "acceptable_latency": 500,
                    "usage_percentage": random.uniform(10, 40)
                },
                "feature_Y": {
                    "current_latency": 200,
                    "required_latency": 200,
                    "usage_percentage": random.uniform(20, 60)
                }
            },
            "models_in_use": ["gpt-4", "claude-2", "gpt-3.5-turbo"],
            "total_requests_daily": random.randint(10000, 1000000)
        }
    
    def _generate_latency_context(self) -> Dict[str, Any]:
        """Generate synthetic latency optimization context"""
        return {
            "current_latency": {
                "p50": random.uniform(100, 300),
                "p95": random.uniform(300, 800),
                "p99": random.uniform(500, 1500)
            },
            "target_improvement": 3.0,
            "budget_constraint": "maintain_current",
            "infrastructure": {
                "gpu_type": random.choice(["A100", "V100", "T4"]),
                "gpu_count": random.randint(1, 8),
                "memory_gb": random.choice([16, 32, 64, 128])
            }
        }
    
    def _generate_capacity_context(self) -> Dict[str, Any]:
        """Generate synthetic capacity planning context"""
        return {
            "current_usage": {
                "requests_per_day": random.randint(10000, 100000),
                "peak_rps": random.randint(10, 1000),
                "average_rps": random.randint(5, 500)
            },
            "expected_growth": 1.5,  # 50% increase
            "rate_limits": {
                "gpt-4": {"rpm": 10000, "tpm": 150000},
                "claude-2": {"rpm": 5000, "tpm": 100000}
            },
            "cost_per_1k_tokens": {
                "gpt-4": 0.03,
                "claude-2": 0.024
            }
        }
    
    def _generate_function_context(self) -> Dict[str, Any]:
        """Generate synthetic function optimization context"""
        return {
            "function_name": "user_authentication",
            "current_metrics": {
                "avg_execution_time_ms": random.uniform(50, 200),
                "memory_usage_mb": random.uniform(100, 500),
                "success_rate": random.uniform(0.95, 0.999),
                "daily_invocations": random.randint(10000, 1000000)
            },
            "bottlenecks": [
                "database_queries",
                "token_generation",
                "cache_misses"
            ],
            "optimization_methods_available": [
                "caching",
                "batching",
                "async_processing",
                "connection_pooling"
            ]
        }
    
    def _generate_model_context(self) -> Dict[str, Any]:
        """Generate synthetic model selection context"""
        return {
            "current_models": {
                "primary": "gpt-4",
                "fallback": "gpt-3.5-turbo"
            },
            "candidate_models": ["gpt-4o", "claude-3-sonnet"],
            "evaluation_metrics": {
                "quality_threshold": 0.9,
                "latency_target_ms": 200,
                "cost_budget_daily": 500
            },
            "workload_characteristics": {
                "avg_prompt_tokens": random.randint(100, 1000),
                "avg_completion_tokens": random.randint(50, 500),
                "complexity": random.choice(["low", "medium", "high"])
            }
        }
    
    def _generate_audit_context(self) -> Dict[str, Any]:
        """Generate synthetic audit context"""
        return {
            "kv_cache_instances": random.randint(5, 20),
            "cache_configurations": [
                {
                    "name": f"cache_{i}",
                    "size_mb": random.randint(100, 1000),
                    "hit_rate": random.uniform(0.3, 0.9),
                    "ttl_seconds": random.choice([60, 300, 3600])
                }
                for i in range(random.randint(3, 8))
            ],
            "optimization_opportunities": [
                "increase_ttl",
                "implement_lru",
                "add_compression",
                "optimize_key_structure"
            ]
        }
    
    def _generate_multi_objective_context(self) -> Dict[str, Any]:
        """Generate synthetic multi-objective optimization context"""
        return {
            "objectives": {
                "cost_reduction": 0.2,  # 20%
                "latency_improvement": 2.0,  # 2x
                "usage_increase": 0.3  # 30%
            },
            "constraints": {
                "min_quality_score": 0.85,
                "max_error_rate": 0.01,
                "budget_limit": 10000
            },
            "current_state": {
                "daily_cost": random.uniform(500, 2000),
                "avg_latency_ms": random.uniform(100, 500),
                "daily_requests": random.randint(10000, 100000)
            }
        }
    
    def _generate_tool_migration_context(self) -> Dict[str, Any]:
        """Generate synthetic tool migration context"""
        return {
            "agent_tools": [
                {
                    "name": f"tool_{i}",
                    "current_model": random.choice(["gpt-4", "gpt-3.5", "claude-2"]),
                    "usage_frequency": random.choice(["high", "medium", "low"]),
                    "complexity": random.choice(["simple", "moderate", "complex"])
                }
                for i in range(random.randint(5, 15))
            ],
            "new_model": "GPT-5",
            "migration_criteria": {
                "min_quality_improvement": 0.1,
                "max_cost_increase": 1.5,
                "verbosity_options": ["concise", "standard", "detailed"]
            }
        }
    
    def _generate_rollback_context(self) -> Dict[str, Any]:
        """Generate synthetic rollback analysis context"""
        return {
            "upgrade_timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
            "upgraded_model": "GPT-5",
            "previous_model": "GPT-4",
            "metrics_comparison": {
                "before": {
                    "quality_score": random.uniform(0.8, 0.9),
                    "cost_per_1k_tokens": 0.03,
                    "avg_latency_ms": random.uniform(100, 200)
                },
                "after": {
                    "quality_score": random.uniform(0.82, 0.95),
                    "cost_per_1k_tokens": 0.06,
                    "avg_latency_ms": random.uniform(80, 180)
                }
            },
            "affected_endpoints": random.randint(10, 50)
        }
    
    def _generate_default_context(self) -> Dict[str, Any]:
        """Generate default synthetic context"""
        return {
            "system_info": {
                "version": "1.0.0",
                "environment": "production",
                "region": random.choice(["us-east-1", "us-west-2", "eu-west-1"])
            },
            "metrics": {
                "uptime_percentage": random.uniform(99.0, 99.99),
                "error_rate": random.uniform(0.001, 0.01),
                "avg_response_time_ms": random.uniform(50, 500)
            }
        }
    
    def create_prompt_variation(self, base_prompt: str, variation_num: int, context: Dict[str, Any]) -> str:
        """Create a unique variation of the base prompt"""
        variations = {
            0: lambda p, c: p,  # Original
            1: lambda p, c: f"{p} Also, my current budget is ${c.get('current_costs', {}).get('daily', 500)}/day.",
            2: lambda p, c: f"URGENT: {p} Need solution within 24 hours.",
            3: lambda p, c: f"{p} PS: We're using {c.get('infrastructure', {}).get('gpu_type', 'A100')} GPUs.",
            4: lambda p, c: p.replace("I need", "Our team needs").replace("my", "our"),
            5: lambda p, c: f"Context: Running in {c.get('system_info', {}).get('region', 'us-east-1')}. {p}",
            6: lambda p, c: f"{p} (Error rate must stay below {c.get('constraints', {}).get('max_error_rate', 0.01)})",
            7: lambda p, c: p.upper(),  # Urgency through caps
            8: lambda p, c: f"Following up on yesterday's discussion: {p}",
            9: lambda p, c: f"{p} Note: We have {c.get('infrastructure', {}).get('gpu_count', 4)} GPUs available."
        }
        
        return variations.get(variation_num, variations[0])(base_prompt, context)
    
    async def validate_response_quality(self, response: str, quality_service: QualityGateService, content_type: ContentType) -> bool:
        """Validate response quality using quality gates"""
        result = await quality_service.validate_content(
            response,
            content_type=content_type,
            strict_mode=False
        )
        return result.passed and result.metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD, QualityLevel.ACCEPTABLE]
    
    async def generate_corpus_if_needed(self, corpus_service: CorpusService, context: Dict[str, Any]):
        """Generate default corpus data if none exists"""
        # Check if corpus exists
        existing_corpus = await corpus_service.get_all_corpus_data()
        if not existing_corpus or len(existing_corpus) < 10:
            # Generate synthetic corpus data
            corpus_data = {
                "workload_metrics": {
                    "gpu_utilization": random.uniform(0.4, 0.9),
                    "memory_usage": random.uniform(0.3, 0.8),
                    "request_patterns": "periodic_spikes"
                },
                "model_performance": {
                    "gpt-4": {"quality": 0.92, "latency": 150, "cost": 0.03},
                    "claude-2": {"quality": 0.89, "latency": 120, "cost": 0.024},
                    "gpt-3.5": {"quality": 0.85, "latency": 80, "cost": 0.002}
                },
                "historical_optimizations": [
                    "Implemented batching - 30% latency reduction",
                    "Added caching - 40% cost reduction",
                    "Optimized prompts - 15% quality improvement"
                ]
            }
            await corpus_service.store_corpus_data("default_test_corpus", corpus_data)
    
    async def run_single_test(self, prompt: str, context: Dict[str, Any], infra: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single E2E test with real LLM calls"""
        supervisor = infra["supervisor"]
        quality_service = infra["quality_service"]
        corpus_service = infra["corpus_service"]
        
        # Generate corpus if needed
        await self.generate_corpus_if_needed(corpus_service, context)
        
        # Create unique run ID
        run_id = str(uuid.uuid4())
        
        # Execute with real LLM calls
        start_time = datetime.now()
        
        try:
            # Run the supervisor with the prompt
            with patch.object(state_persistence_service, 'save_agent_state', AsyncMock()):
                with patch.object(state_persistence_service, 'load_agent_state', AsyncMock(return_value=None)):
                    with patch.object(state_persistence_service, 'get_thread_context', AsyncMock(return_value=context)):
                        result_state = await supervisor.run(prompt, run_id, stream_updates=True)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Validate response quality
            response_text = ""
            if result_state:
                # Extract response from different result fields
                if hasattr(result_state, 'final_response') and result_state.final_response:
                    response_text = result_state.final_response
                elif hasattr(result_state, 'reporting_result') and result_state.reporting_result:
                    response_text = str(result_state.reporting_result)
                elif hasattr(result_state, 'optimizations_result') and result_state.optimizations_result:
                    response_text = str(result_state.optimizations_result)
            
            # Determine content type based on prompt
            content_type = ContentType.OPTIMIZATION
            if "audit" in prompt.lower():
                content_type = ContentType.DATA_ANALYSIS
            elif "rollback" in prompt.lower():
                content_type = ContentType.ACTION_PLAN
            
            quality_passed = await self.validate_response_quality(
                response_text,
                quality_service,
                content_type
            )
            
            return {
                "success": True,
                "prompt": prompt,
                "execution_time": execution_time,
                "quality_passed": quality_passed,
                "response_length": len(response_text),
                "state": result_state,
                "response": response_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "prompt": prompt,
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    # ========== PROMPT 1: Cost Optimization Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_0(self, setup_real_infrastructure):
        """Test cost optimization - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
        assert result["response_length"] > 100, "Response too short"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_1(self, setup_real_infrastructure):
        """Test cost optimization - with budget context"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_2(self, setup_real_infrastructure):
        """Test cost optimization - urgent request"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_3(self, setup_real_infrastructure):
        """Test cost optimization - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_4(self, setup_real_infrastructure):
        """Test cost optimization - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_5(self, setup_real_infrastructure):
        """Test cost optimization - with region context"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_6(self, setup_real_infrastructure):
        """Test cost optimization - with error rate constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_7(self, setup_real_infrastructure):
        """Test cost optimization - urgent caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_8(self, setup_real_infrastructure):
        """Test cost optimization - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_1_variation_9(self, setup_real_infrastructure):
        """Test cost optimization - with GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("cost_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[0], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    # ========== PROMPT 2: Latency Optimization Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_0(self, setup_real_infrastructure):
        """Test latency optimization - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_1(self, setup_real_infrastructure):
        """Test latency optimization - with budget"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_2(self, setup_real_infrastructure):
        """Test latency optimization - urgent"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_3(self, setup_real_infrastructure):
        """Test latency optimization - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_4(self, setup_real_infrastructure):
        """Test latency optimization - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_5(self, setup_real_infrastructure):
        """Test latency optimization - with region"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_6(self, setup_real_infrastructure):
        """Test latency optimization - with error constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_7(self, setup_real_infrastructure):
        """Test latency optimization - caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_8(self, setup_real_infrastructure):
        """Test latency optimization - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_2_variation_9(self, setup_real_infrastructure):
        """Test latency optimization - GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("latency_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[1], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    # ========== PROMPT 3: Capacity Planning Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_0(self, setup_real_infrastructure):
        """Test capacity planning - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_1(self, setup_real_infrastructure):
        """Test capacity planning - with budget"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_2(self, setup_real_infrastructure):
        """Test capacity planning - urgent"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_3(self, setup_real_infrastructure):
        """Test capacity planning - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_4(self, setup_real_infrastructure):
        """Test capacity planning - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_5(self, setup_real_infrastructure):
        """Test capacity planning - with region"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_6(self, setup_real_infrastructure):
        """Test capacity planning - with error constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_7(self, setup_real_infrastructure):
        """Test capacity planning - caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_8(self, setup_real_infrastructure):
        """Test capacity planning - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_3_variation_9(self, setup_real_infrastructure):
        """Test capacity planning - GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("capacity_planning")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[2], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    # ========== PROMPT 4: Function Optimization Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_0(self, setup_real_infrastructure):
        """Test function optimization - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_1(self, setup_real_infrastructure):
        """Test function optimization - with budget"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_2(self, setup_real_infrastructure):
        """Test function optimization - urgent"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_3(self, setup_real_infrastructure):
        """Test function optimization - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_4(self, setup_real_infrastructure):
        """Test function optimization - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_5(self, setup_real_infrastructure):
        """Test function optimization - with region"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_6(self, setup_real_infrastructure):
        """Test function optimization - with error constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_7(self, setup_real_infrastructure):
        """Test function optimization - caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_8(self, setup_real_infrastructure):
        """Test function optimization - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_4_variation_9(self, setup_real_infrastructure):
        """Test function optimization - GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("function_optimization")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[3], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    # ========== PROMPT 5: Model Selection Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_0(self, setup_real_infrastructure):
        """Test model selection - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_1(self, setup_real_infrastructure):
        """Test model selection - with budget"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_2(self, setup_real_infrastructure):
        """Test model selection - urgent"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_3(self, setup_real_infrastructure):
        """Test model selection - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_4(self, setup_real_infrastructure):
        """Test model selection - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_5(self, setup_real_infrastructure):
        """Test model selection - with region"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_6(self, setup_real_infrastructure):
        """Test model selection - with error constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_7(self, setup_real_infrastructure):
        """Test model selection - caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_8(self, setup_real_infrastructure):
        """Test model selection - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_5_variation_9(self, setup_real_infrastructure):
        """Test model selection - GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("model_selection")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[4], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    # ========== PROMPT 6: Audit Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_0(self, setup_real_infrastructure):
        """Test audit - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_1(self, setup_real_infrastructure):
        """Test audit - with budget"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_2(self, setup_real_infrastructure):
        """Test audit - urgent"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_3(self, setup_real_infrastructure):
        """Test audit - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_4(self, setup_real_infrastructure):
        """Test audit - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_5(self, setup_real_infrastructure):
        """Test audit - with region"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_6(self, setup_real_infrastructure):
        """Test audit - with error constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_7(self, setup_real_infrastructure):
        """Test audit - caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_8(self, setup_real_infrastructure):
        """Test audit - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_6_variation_9(self, setup_real_infrastructure):
        """Test audit - GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("audit")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[5], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    # ========== PROMPT 7: Multi-Objective Optimization Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_0(self, setup_real_infrastructure):
        """Test multi-objective - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_1(self, setup_real_infrastructure):
        """Test multi-objective - with budget"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_2(self, setup_real_infrastructure):
        """Test multi-objective - urgent"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_3(self, setup_real_infrastructure):
        """Test multi-objective - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_4(self, setup_real_infrastructure):
        """Test multi-objective - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_5(self, setup_real_infrastructure):
        """Test multi-objective - with region"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_6(self, setup_real_infrastructure):
        """Test multi-objective - with error constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_7(self, setup_real_infrastructure):
        """Test multi-objective - caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_8(self, setup_real_infrastructure):
        """Test multi-objective - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_7_variation_9(self, setup_real_infrastructure):
        """Test multi-objective - GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("multi_objective")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[6], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    # ========== PROMPT 8: Tool Migration Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_0(self, setup_real_infrastructure):
        """Test tool migration - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_1(self, setup_real_infrastructure):
        """Test tool migration - with budget"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_2(self, setup_real_infrastructure):
        """Test tool migration - urgent"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_3(self, setup_real_infrastructure):
        """Test tool migration - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_4(self, setup_real_infrastructure):
        """Test tool migration - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_5(self, setup_real_infrastructure):
        """Test tool migration - with region"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_6(self, setup_real_infrastructure):
        """Test tool migration - with error constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_7(self, setup_real_infrastructure):
        """Test tool migration - caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_8(self, setup_real_infrastructure):
        """Test tool migration - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_8_variation_9(self, setup_real_infrastructure):
        """Test tool migration - GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("tool_migration")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[7], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    # ========== PROMPT 9: Rollback Analysis Tests (10 variations) ==========
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_0(self, setup_real_infrastructure):
        """Test rollback analysis - original prompt"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 0, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_1(self, setup_real_infrastructure):
        """Test rollback analysis - with budget"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 1, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_2(self, setup_real_infrastructure):
        """Test rollback analysis - urgent"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 2, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_3(self, setup_real_infrastructure):
        """Test rollback analysis - with GPU info"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 3, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_4(self, setup_real_infrastructure):
        """Test rollback analysis - team perspective"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 4, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_5(self, setup_real_infrastructure):
        """Test rollback analysis - with region"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 5, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_6(self, setup_real_infrastructure):
        """Test rollback analysis - with error constraint"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 6, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_7(self, setup_real_infrastructure):
        """Test rollback analysis - caps"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 7, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_8(self, setup_real_infrastructure):
        """Test rollback analysis - follow-up"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 8, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"
    
    @pytest.mark.asyncio
    async def test_prompt_9_variation_9(self, setup_real_infrastructure):
        """Test rollback analysis - GPU count"""
        infra = await setup_real_infrastructure.__anext__()
        context = self.generate_synthetic_context("rollback_analysis")
        prompt = self.create_prompt_variation(EXAMPLE_PROMPTS[8], 9, context)
        result = await self.run_single_test(prompt, context, infra)
        assert result["success"], f"Test failed: {result.get('error')}"
        assert result["quality_passed"], "Response quality check failed"


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "-s"])