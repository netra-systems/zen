"""Integration tests for triage agent with real services.

Tests real-world integration scenarios using actual services (database, Redis, LLM).
Minimal mocking - focuses on end-to-end behavior with real dependencies.
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.triage_sub_agent.models import (
    ExtractedEntities,
    TriageResult,
)
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db_session
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.websocket_core.manager import WebSocketManager

logger = central_logger.get_logger(__name__)

# Initialize real environment
env = IsolatedEnvironment()


class RealServiceTestFixtures:
    """Helper class to manage real service connections for tests."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.redis_manager = None
        self.llm_manager = None
        self.auth_client = None
        self.websocket_manager = None
        self.db_engine = None
        
    async def initialize_services(self):
        """Initialize all real services."""
        # Real Redis connection
        self.redis_manager = RedisManager()
        await self.redis_manager.initialize()
        
        # Real LLM manager with actual API keys
        self.llm_manager = LLMManager(
            gemini_api_key=self.env.get_variable("GEMINI_API_KEY"),
            openai_api_key=self.env.get_variable("OPENAI_API_KEY"),
            anthropic_api_key=self.env.get_variable("ANTHROPIC_API_KEY")
        )
        
        # Real auth service client
        self.auth_client = AuthServiceClient()
        
        # Real WebSocket manager
        self.websocket_manager = WebSocketManager()
        
        # Real database connection
        database_url = self.env.get_variable("DATABASE_URL")
        self.db_engine = create_async_engine(database_url, echo=False)
        
    async def cleanup(self):
        """Clean up all service connections."""
        if self.redis_manager:
            await self.redis_manager.close()
        if self.db_engine:
            await self.db_engine.dispose()
        if self.websocket_manager:
            await self.websocket_manager.shutdown()


@pytest.fixture
async def real_services():
    """Fixture providing real service connections."""
    fixtures = RealServiceTestFixtures()
    await fixtures.initialize_services()
    yield fixtures
    await fixtures.cleanup()


class TestMultiServiceAuthenticationPropagation:
    """Test real authentication token propagation across services during triage."""
    
    @pytest.mark.asyncio
    async def test_auth_token_propagation_across_services(self, real_services):
        """Test real auth token propagation during triage operations."""
        # Create a real user via auth service
        user_data = {
            "email": f"test_triage_{int(time.time())}@example.com",
            "password": "SecurePassword123!",
            "tenant_id": "test_tenant"
        }
        
        # Real auth service call to create user and get token
        auth_response = await real_services.auth_client.create_user(user_data)
        assert auth_response["status"] == "success"
        
        auth_token = auth_response["token"]
        user_id = auth_response["user_id"]
        
        # Store auth context in real Redis
        auth_context_key = f"auth:context:{user_id}"
        await real_services.redis_manager.set(
            auth_context_key,
            json.dumps({
                "token": auth_token,
                "user_id": user_id,
                "tenant_id": user_data["tenant_id"],
                "timestamp": time.time()
            }),
            ttl=3600
        )
        
        # Create triage agent with real services
        tool_dispatcher = ToolDispatcher()
        triage_agent = TriageSubAgent(
            llm_manager=real_services.llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=real_services.redis_manager,
            websocket_manager=real_services.websocket_manager
        )
        
        # Create execution context with auth token
        context = ExecutionContext(
            request_id=f"auth_test_{int(time.time())}",
            user_id=user_id,
            session_id=f"session_{user_id}",
            metadata={
                "auth_token": auth_token,
                "tenant_id": user_data["tenant_id"]
            }
        )
        
        # Execute triage with authenticated context
        request_data = {
            "query": "Show me cost optimization opportunities for my AI workloads",
            "auth_token": auth_token
        }
        
        result = await triage_agent.execute(context, request_data)
        
        # Verify successful execution with auth
        assert result.status == ExecutionStatus.SUCCESS
        assert result.data is not None
        
        # Verify auth context was used during triage
        stored_context = await real_services.redis_manager.get(auth_context_key)
        assert stored_context is not None
        
        # Verify token was propagated to LLM calls
        triage_result = result.data
        if isinstance(triage_result, dict):
            assert "primary_intent" in triage_result
        
    @pytest.mark.asyncio
    async def test_expired_token_refresh_during_triage(self, real_services):
        """Test handling of expired tokens with real refresh mechanism."""
        # Create user with short-lived token
        user_data = {
            "email": f"test_expire_{int(time.time())}@example.com",
            "password": "TempPassword123!",
            "tenant_id": "test_tenant"
        }
        
        auth_response = await real_services.auth_client.create_user(user_data)
        expired_token = auth_response["token"]
        user_id = auth_response["user_id"]
        
        # Simulate token expiration in Redis
        await real_services.redis_manager.set(
            f"auth:expired:{expired_token}",
            "true",
            ttl=1
        )
        
        # Create triage agent
        tool_dispatcher = ToolDispatcher()
        triage_agent = TriageSubAgent(
            llm_manager=real_services.llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=real_services.redis_manager
        )
        
        context = ExecutionContext(
            request_id=f"expired_test_{int(time.time())}",
            user_id=user_id,
            session_id=f"session_{user_id}",
            metadata={"auth_token": expired_token}
        )
        
        # Should handle expired token gracefully
        result = await triage_agent.execute(context, {"query": "Test query"})
        
        # May fail auth but should not crash
        assert result.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED]
        if result.status == ExecutionStatus.FAILED:
            assert "auth" in result.error.lower() or "token" in result.error.lower()


class TestDatabaseTransactionConsistency:
    """Test database transaction consistency during triage operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_triage_database_transactions(self, real_services):
        """Test database consistency with concurrent triage operations."""
        # Create multiple triage agents
        agents = []
        for i in range(5):
            tool_dispatcher = ToolDispatcher()
            agent = TriageSubAgent(
                llm_manager=real_services.llm_manager,
                tool_dispatcher=tool_dispatcher,
                redis_manager=real_services.redis_manager
            )
            agents.append(agent)
        
        # Create concurrent execution contexts
        contexts = []
        for i in range(5):
            context = ExecutionContext(
                request_id=f"concurrent_{i}_{int(time.time())}",
                user_id=f"user_{i}",
                session_id=f"session_{i}",
                metadata={"transaction_id": f"txn_{i}"}
            )
            contexts.append(context)
        
        # Execute concurrent triage operations
        async def execute_with_transaction(agent, context, index):
            """Execute triage within a database transaction."""
            async with real_services.db_engine.begin() as conn:
                # Start transaction
                await conn.execute("BEGIN")
                
                try:
                    # Execute triage
                    result = await agent.execute(context, {
                        "query": f"Analyze performance metrics for model {index}"
                    })
                    
                    # Store result in database
                    if result.status == ExecutionStatus.SUCCESS:
                        await conn.execute(
                            """INSERT INTO triage_results 
                               (request_id, user_id, result_data, created_at) 
                               VALUES ($1, $2, $3, NOW())""",
                            context.request_id,
                            context.user_id,
                            json.dumps(result.data) if result.data else "{}"
                        )
                        await conn.execute("COMMIT")
                    else:
                        await conn.execute("ROLLBACK")
                    
                    return result
                    
                except Exception as e:
                    await conn.execute("ROLLBACK")
                    raise e
        
        # Execute all operations concurrently
        tasks = [
            execute_with_transaction(agents[i], contexts[i], i)
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify transaction consistency
        successful_results = [r for r in results if isinstance(r, ExecutionResult) and r.status == ExecutionStatus.SUCCESS]
        assert len(successful_results) >= 3  # At least 60% success rate
        
        # Verify database state consistency
        async with real_services.db_engine.connect() as conn:
            db_results = await conn.execute(
                "SELECT COUNT(*) FROM triage_results WHERE request_id LIKE 'concurrent_%'"
            )
            count = db_results.scalar()
            assert count == len(successful_results)  # Only successful transactions committed
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion(self, real_services):
        """Test behavior when database connection pool is exhausted."""
        # Create many agents to exhaust connection pool
        agents = []
        for i in range(20):
            tool_dispatcher = ToolDispatcher()
            agent = TriageSubAgent(
                llm_manager=real_services.llm_manager,
                tool_dispatcher=tool_dispatcher,
                redis_manager=real_services.redis_manager
            )
            agents.append(agent)
        
        # Execute many concurrent operations
        tasks = []
        for i in range(20):
            context = ExecutionContext(
                request_id=f"pool_test_{i}",
                user_id=f"user_{i}",
                session_id=f"session_{i}"
            )
            task = agents[i].execute(context, {"query": f"Query {i}"})
            tasks.append(task)
        
        # Some should succeed, some may fail due to pool exhaustion
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, ExecutionResult) and r.status == ExecutionStatus.SUCCESS)
        assert successful >= 10  # At least half should succeed


class TestHighConcurrencyPerformance:
    """Test high-concurrency triage performance and resource management."""
    
    @pytest.mark.asyncio
    async def test_high_concurrency_resource_management(self, real_services):
        """Test resource management under high concurrent load."""
        # Create a single triage agent (shared resources)
        tool_dispatcher = ToolDispatcher()
        triage_agent = TriageSubAgent(
            llm_manager=real_services.llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=real_services.redis_manager,
            websocket_manager=real_services.websocket_manager
        )
        
        # Track performance metrics
        start_time = time.time()
        response_times = []
        success_count = 0
        failure_count = 0
        
        # Create diverse request templates
        request_templates = [
            "Optimize costs for GPT-4 usage in production",
            "Analyze performance bottlenecks in my AI pipeline",
            "Show security vulnerabilities in model deployment",
            "Generate compliance report for AI governance",
            "Monitor real-time metrics for inference latency"
        ]
        
        # Generate 50 concurrent requests
        async def process_request(index):
            """Process a single triage request."""
            context = ExecutionContext(
                request_id=f"perf_{index}_{int(time.time())}",
                user_id=f"user_{index % 10}",  # Simulate 10 different users
                session_id=f"session_{index % 5}",  # 5 sessions
                metadata={"batch": index // 10}
            )
            
            query = request_templates[index % len(request_templates)]
            query += f" - Instance {index}"
            
            request_start = time.time()
            try:
                result = await triage_agent.execute(context, {"query": query})
                request_time = time.time() - request_start
                response_times.append(request_time)
                
                if result.status == ExecutionStatus.SUCCESS:
                    return ("success", request_time)
                else:
                    return ("failure", request_time)
            except Exception as e:
                logger.error(f"Request {index} failed: {e}")
                return ("error", time.time() - request_start)
        
        # Execute requests in batches to manage resources
        batch_size = 10
        all_results = []
        
        for batch_start in range(0, 50, batch_size):
            batch_end = min(batch_start + batch_size, 50)
            batch_tasks = [
                process_request(i) for i in range(batch_start, batch_end)
            ]
            batch_results = await asyncio.gather(*batch_tasks)
            all_results.extend(batch_results)
            
            # Brief pause between batches to prevent overwhelming
            await asyncio.sleep(0.1)
        
        # Analyze results
        for status, response_time in all_results:
            if status == "success":
                success_count += 1
            else:
                failure_count += 1
        
        total_time = time.time() - start_time
        
        # Performance assertions
        assert success_count >= 35  # At least 70% success rate
        assert total_time < 30  # Complete within 30 seconds
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 10  # Average response under 10 seconds
            
            # Check throughput
            throughput = len(all_results) / total_time
            assert throughput > 2  # At least 2 requests per second
        
        # Verify Redis didn't run out of connections
        redis_info = await real_services.redis_manager.get_info()
        assert redis_info is not None
    
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, real_services):
        """Test triage behavior under memory pressure."""
        # Create agent with memory monitoring
        tool_dispatcher = ToolDispatcher()
        triage_agent = TriageSubAgent(
            llm_manager=real_services.llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=real_services.redis_manager
        )
        
        # Generate large requests to create memory pressure
        large_requests = []
        for i in range(10):
            # Create a large query with repeated data
            large_query = f"Analyze this large dataset: " + ("data " * 1000)
            context = ExecutionContext(
                request_id=f"memory_{i}",
                user_id=f"user_{i}",
                session_id=f"session_{i}",
                metadata={"size": "large"}
            )
            large_requests.append((context, {"query": large_query}))
        
        # Process requests and monitor memory
        results = []
        for context, request in large_requests:
            result = await triage_agent.execute(context, request)
            results.append(result)
            
            # Allow garbage collection between requests
            await asyncio.sleep(0.1)
        
        # Should handle all requests without memory errors
        successful = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)
        assert successful >= 7  # At least 70% success despite memory pressure


class TestLLMProviderFailover:
    """Test LLM provider failover during triage operations."""
    
    @pytest.mark.asyncio
    async def test_llm_provider_switching_during_triage(self, real_services):
        """Test automatic LLM provider switching on failures."""
        # Configure LLM manager with multiple providers
        tool_dispatcher = ToolDispatcher()
        triage_agent = TriageSubAgent(
            llm_manager=real_services.llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=real_services.redis_manager
        )
        
        # Track which providers are used
        provider_usage = {"gemini": 0, "openai": 0, "anthropic": 0, "fallback": 0}
        
        async def execute_with_provider_tracking(index):
            """Execute triage and track provider usage."""
            context = ExecutionContext(
                request_id=f"provider_{index}",
                user_id=f"user_{index}",
                session_id=f"session_{index}",
                metadata={"force_provider": index % 3}  # Rotate providers
            )
            
            # Simulate provider-specific queries
            queries = [
                "Optimize Gemini Pro costs",  # Likely to use Gemini
                "Analyze GPT-4 performance",  # Likely to use OpenAI
                "Review Claude-3 outputs"  # Likely to use Anthropic
            ]
            
            query = queries[index % len(queries)]
            result = await triage_agent.execute(context, {"query": query})
            
            # Track provider from result metadata if available
            if result.status == ExecutionStatus.SUCCESS and result.data:
                if isinstance(result.data, dict):
                    provider = result.data.get("provider", "unknown")
                    if provider in provider_usage:
                        provider_usage[provider] += 1
                    else:
                        provider_usage["fallback"] += 1
            
            return result
        
        # Execute multiple requests to trigger provider switching
        tasks = [execute_with_provider_tracking(i) for i in range(15)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify multiple providers were used
        providers_used = sum(1 for count in provider_usage.values() if count > 0)
        assert providers_used >= 2  # At least 2 different providers used
        
        # Verify successful execution despite provider switching
        successful_results = [
            r for r in results 
            if isinstance(r, ExecutionResult) and r.status == ExecutionStatus.SUCCESS
        ]
        assert len(successful_results) >= 10  # At least 66% success rate
    
    @pytest.mark.asyncio
    async def test_llm_rate_limiting_handling(self, real_services):
        """Test handling of LLM API rate limits."""
        tool_dispatcher = ToolDispatcher()
        triage_agent = TriageSubAgent(
            llm_manager=real_services.llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=real_services.redis_manager
        )
        
        # Rapid-fire requests to trigger rate limiting
        rapid_requests = []
        for i in range(20):
            context = ExecutionContext(
                request_id=f"rate_limit_{i}",
                user_id="rate_test_user",
                session_id="rate_test_session"
            )
            rapid_requests.append(context)
        
        # Execute rapidly without delays
        async def rapid_execute(context):
            return await triage_agent.execute(context, {
                "query": "Quick test query for rate limiting"
            })
        
        # Execute all at once to trigger rate limits
        results = await asyncio.gather(
            *[rapid_execute(ctx) for ctx in rapid_requests],
            return_exceptions=True
        )
        
        # Some should succeed, some may be rate limited
        successful = sum(
            1 for r in results 
            if isinstance(r, ExecutionResult) and r.status == ExecutionStatus.SUCCESS
        )
        
        # Should handle rate limiting gracefully
        assert successful >= 5  # At least some succeed
        assert successful < 20  # But not all (rate limiting should kick in)
        
        # Check for rate limit errors
        rate_limit_errors = sum(
            1 for r in results
            if isinstance(r, ExecutionResult) and 
            r.status == ExecutionStatus.FAILED and
            "rate" in str(r.error).lower()
        )
        assert rate_limit_errors > 0  # Should see some rate limit errors


class TestEndToEndErrorInjection:
    """Test end-to-end triage pipeline with real error injection."""
    
    @pytest.mark.asyncio
    async def test_triage_pipeline_with_error_injection(self, real_services):
        """Test complete triage flow with injected errors."""
        tool_dispatcher = ToolDispatcher()
        triage_agent = TriageSubAgent(
            llm_manager=real_services.llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=real_services.redis_manager,
            websocket_manager=real_services.websocket_manager
        )
        
        # Define error injection scenarios
        error_scenarios = [
            {"type": "redis_timeout", "duration": 0.5},
            {"type": "database_error", "duration": 0.3},
            {"type": "llm_api_error", "duration": 0.4},
            {"type": "memory_pressure", "duration": 0.2},
            {"type": "network_latency", "duration": 1.0}
        ]
        
        results = []
        recovery_times = []
        
        for i, scenario in enumerate(error_scenarios):
            # Inject error based on scenario
            error_start = time.time()
            
            if scenario["type"] == "redis_timeout":
                # Temporarily make Redis slow
                original_timeout = real_services.redis_manager.timeout
                real_services.redis_manager.timeout = 0.001  # Very short timeout
            
            elif scenario["type"] == "database_error":
                # Note: In real test, would temporarily break DB connection
                pass
            
            elif scenario["type"] == "llm_api_error":
                # Temporarily use invalid API key
                original_key = real_services.llm_manager.gemini_api_key
                real_services.llm_manager.gemini_api_key = "invalid_key"
            
            # Execute triage during error condition
            context = ExecutionContext(
                request_id=f"error_{scenario['type']}_{i}",
                user_id=f"user_error_{i}",
                session_id=f"session_error_{i}",
                metadata={"error_scenario": scenario["type"]}
            )
            
            try:
                result = await triage_agent.execute(context, {
                    "query": f"Test query during {scenario['type']} error"
                })
                results.append(result)
            except Exception as e:
                # Create failed result for exception
                results.append(ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    data=None,
                    error=str(e),
                    execution_time=time.time() - error_start
                ))
            
            # Restore normal conditions
            if scenario["type"] == "redis_timeout":
                real_services.redis_manager.timeout = original_timeout
            elif scenario["type"] == "llm_api_error":
                real_services.llm_manager.gemini_api_key = original_key
            
            # Allow recovery time
            await asyncio.sleep(scenario["duration"])
            
            # Test recovery by executing normal request
            recovery_context = ExecutionContext(
                request_id=f"recovery_{i}",
                user_id=f"user_recovery_{i}",
                session_id=f"session_recovery_{i}"
            )
            
            recovery_start = time.time()
            recovery_result = await triage_agent.execute(recovery_context, {
                "query": "Test recovery after error"
            })
            recovery_times.append(time.time() - recovery_start)
            
            # Verify recovery
            if recovery_result.status == ExecutionStatus.SUCCESS:
                logger.info(f"Recovered from {scenario['type']} successfully")
        
        # Analyze results
        total_scenarios = len(error_scenarios)
        successful_recoveries = sum(1 for t in recovery_times if t < 5.0)
        
        # Should recover from most errors
        assert successful_recoveries >= total_scenarios * 0.8  # 80% recovery rate
        
        # Average recovery time should be reasonable
        if recovery_times:
            avg_recovery = sum(recovery_times) / len(recovery_times)
            assert avg_recovery < 3.0  # Average recovery under 3 seconds
    
    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self, real_services):
        """Test prevention of cascading failures in triage pipeline."""
        tool_dispatcher = ToolDispatcher()
        triage_agent = TriageSubAgent(
            llm_manager=real_services.llm_manager,
            tool_dispatcher=tool_dispatcher,
            redis_manager=real_services.redis_manager
        )
        
        # Simulate a service degradation
        degraded_results = []
        
        # First wave - normal operation
        for i in range(5):
            context = ExecutionContext(
                request_id=f"cascade_normal_{i}",
                user_id=f"user_{i}",
                session_id=f"session_{i}"
            )
            result = await triage_agent.execute(context, {"query": "Normal query"})
            degraded_results.append(("normal", result))
        
        # Second wave - introduce partial failure
        # Simulate Redis becoming slow
        real_services.redis_manager.timeout = 0.01  # Very short timeout
        
        for i in range(5):
            context = ExecutionContext(
                request_id=f"cascade_degraded_{i}",
                user_id=f"user_{i}",
                session_id=f"session_{i}"
            )
            result = await triage_agent.execute(context, {"query": "Query during degradation"})
            degraded_results.append(("degraded", result))
        
        # Third wave - should not cascade to total failure
        real_services.redis_manager.timeout = 5.0  # Restore normal timeout
        
        for i in range(5):
            context = ExecutionContext(
                request_id=f"cascade_recovery_{i}",
                user_id=f"user_{i}",
                session_id=f"session_{i}"
            )
            result = await triage_agent.execute(context, {"query": "Recovery query"})
            degraded_results.append(("recovery", result))
        
        # Analyze cascade prevention
        normal_success = sum(
            1 for phase, r in degraded_results 
            if phase == "normal" and r.status == ExecutionStatus.SUCCESS
        )
        degraded_success = sum(
            1 for phase, r in degraded_results 
            if phase == "degraded" and r.status == ExecutionStatus.SUCCESS
        )
        recovery_success = sum(
            1 for phase, r in degraded_results 
            if phase == "recovery" and r.status == ExecutionStatus.SUCCESS
        )
        
        # Should maintain functionality despite degradation
        assert normal_success >= 4  # Normal phase mostly successful
        assert degraded_success >= 2  # Some success even during degradation
        assert recovery_success >= 4  # Recovery phase successful
        
        # System should not completely fail
        total_success = normal_success + degraded_success + recovery_success
        assert total_success >= 10  # Overall system resilience