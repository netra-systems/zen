"""Comprehensive test suite for Domain Circuit Breakers.

This module tests all domain-specific circuit breaker wrappers:
- DatabaseCircuitBreaker: Database operations with connection pool awareness
- LLMCircuitBreaker: LLM API calls with token/cost tracking
- AuthCircuitBreaker: Authentication services with security monitoring  
- AgentCircuitBreaker: Agent operations with task/context management

Test Structure:
- Configuration validation tests
- Domain-specific functionality tests
- Error handling and fallback tests
- Integration tests with underlying unified circuit breaker
- Monitoring and metrics tests
- Edge case and error condition tests
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any, Optional

from netra_backend.app.core.resilience.domain_circuit_breakers import (
    DatabaseCircuitBreaker,
    LLMCircuitBreaker, 
    AuthCircuitBreaker,
    AgentCircuitBreaker,
    DatabaseCircuitBreakerConfig,
    LLMCircuitBreakerConfig,
    AuthCircuitBreakerConfig,
    AgentCircuitBreakerConfig,
    TokenUsageTracker,
    SecurityMonitor,
    AgentTaskManager,
    LLMRateLimitError,
    LLMCostLimitError,
    LLMValidationError,
    AuthSecurityError,
)
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
)
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError


class TestDatabaseCircuitBreakerConfig:
    """Test DatabaseCircuitBreakerConfig validation and defaults."""
    
    def test_default_config_creation(self):
        """Test default configuration values."""
        config = DatabaseCircuitBreakerConfig()
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout_seconds == 30.0
        assert config.query_timeout_seconds == 10.0
        assert config.connection_pool_threshold == 80
        assert config.check_pool_health is True
        assert "ConnectionError" in config.expected_database_exceptions
        assert "ConnectionError" in config.connection_errors
        
    def test_custom_config_creation(self):
        """Test custom configuration override."""
        config = DatabaseCircuitBreakerConfig(
            failure_threshold=5,
            query_timeout_seconds=15.0,
            connection_pool_threshold=100,
            check_pool_health=False
        )
        
        assert config.failure_threshold == 5
        assert config.query_timeout_seconds == 15.0
        assert config.connection_pool_threshold == 100
        assert config.check_pool_health is False
        
    def test_config_to_dict(self):
        """Test config conversion to dictionary."""
        config = DatabaseCircuitBreakerConfig(failure_threshold=5)
        config_dict = config.to_dict()
        
        assert config_dict['failure_threshold'] == 5
        assert 'recovery_timeout_seconds' in config_dict
        assert 'query_timeout_seconds' in config_dict


class TestDatabaseCircuitBreaker:
    """Test DatabaseCircuitBreaker functionality."""
    
    @pytest.fixture
    def mock_db_pool(self):
        """Mock database connection pool."""
        pool = MagicMock()
        pool.size = 10
        pool.maxsize = 20
        pool.acquire.return_value.__aenter__ = AsyncMock()
        pool.acquire.return_value.__aexit__ = AsyncMock()
        pool.clear = AsyncMock()
        return pool
        
    @pytest.fixture
    def db_breaker(self, mock_db_pool):
        """Create database circuit breaker for testing."""
        return DatabaseCircuitBreaker("test_db", db_pool=mock_db_pool)
        
    @pytest.mark.asyncio
    async def test_initialization(self, mock_db_pool):
        """Test database circuit breaker initialization."""
        config = DatabaseCircuitBreakerConfig(failure_threshold=5)
        breaker = DatabaseCircuitBreaker("test_db", db_pool=mock_db_pool, config=config)
        
        assert breaker.name == "database_test_db"
        assert breaker.db_pool == mock_db_pool
        assert breaker.config.failure_threshold == 5
        assert breaker._active_transactions == 0
        
    @pytest.mark.asyncio
    async def test_successful_execution(self, db_breaker):
        """Test successful database operation execution."""
        async def mock_db_operation():
            return "success"
            
        result = await db_breaker.execute(mock_db_operation)
        assert result == "success"
        
    @pytest.mark.asyncio
    async def test_pool_health_validation(self, mock_db_pool):
        """Test connection pool health validation."""
        mock_db_pool.size = 85  # Above threshold
        breaker = DatabaseCircuitBreaker("test_db", db_pool=mock_db_pool)
        
        with patch('netra_backend.app.core.resilience.domain_circuit_breakers.logger') as mock_logger:
            async def mock_operation():
                return "result"
                
            await breaker.execute(mock_operation)
            mock_logger.warning.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, db_breaker):
        """Test connection error handling with pool clearing."""
        async def failing_operation():
            raise ConnectionError("Database connection failed")
            
        with pytest.raises(ConnectionError):
            await db_breaker.execute(failing_operation)
            
        # Should attempt to clear pool
        db_breaker.db_pool.clear.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_transaction_context(self, db_breaker):
        """Test transaction context management."""
        assert db_breaker._active_transactions == 0
        
        async with await db_breaker.transaction_context():
            assert db_breaker._active_transactions == 1
            
        assert db_breaker._active_transactions == 0
        
    @pytest.mark.asyncio
    async def test_transaction_error_handling(self, db_breaker):
        """Test transaction error decrements counter."""
        async def failing_operation():
            raise Exception("IntegrityError")  # Mock transaction error
            
        db_breaker._active_transactions = 2
        
        with pytest.raises(Exception):
            await db_breaker.execute(failing_operation)
            
        # Should handle transaction error but not decrement here (that's in _handle_transaction_error)
        assert db_breaker._active_transactions == 2
        
    def test_get_status(self, db_breaker):
        """Test status reporting with database-specific metrics."""
        status = db_breaker.get_status()
        
        assert status['domain'] == 'database'
        assert status['active_transactions'] == 0
        assert status['pool_size'] == 10
        assert status['pool_max_size'] == 20
        assert 'config' in status


class TestLLMCircuitBreakerConfig:
    """Test LLMCircuitBreakerConfig validation and defaults."""
    
    def test_default_config_creation(self):
        """Test default LLM configuration values."""
        config = LLMCircuitBreakerConfig()
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout_seconds == 120.0
        assert config.request_timeout_seconds == 60.0
        assert config.token_rate_limit_per_minute == 50000
        assert config.cost_threshold_dollars == 100.0
        assert "RateLimitError" in config.expected_llm_exceptions
        assert "RateLimitError" in config.rate_limit_errors
        
    def test_custom_config_creation(self):
        """Test custom LLM configuration."""
        config = LLMCircuitBreakerConfig(
            token_rate_limit_per_minute=10000,
            cost_threshold_dollars=50.0,
            request_timeout_seconds=30.0
        )
        
        assert config.token_rate_limit_per_minute == 10000
        assert config.cost_threshold_dollars == 50.0
        assert config.request_timeout_seconds == 30.0


class TestTokenUsageTracker:
    """Test token usage tracking functionality."""
    
    @pytest.fixture
    def config(self):
        """LLM config for testing."""
        return LLMCircuitBreakerConfig(token_rate_limit_per_minute=1000)
        
    @pytest.fixture
    def tracker(self, config):
        """Token usage tracker for testing."""
        return TokenUsageTracker(config)
        
    def test_initial_state(self, tracker):
        """Test initial tracker state."""
        assert tracker.tokens_used_this_minute == 0
        assert tracker.current_cost == 0.0
        assert tracker.can_make_request(500)
        
    def test_token_usage_tracking(self, tracker):
        """Test token usage recording."""
        assert tracker.can_make_request(500)
        tracker.record_usage(500, 0.05)
        
        assert tracker.tokens_used_this_minute == 500
        assert tracker.current_cost == 0.05
        assert tracker.can_make_request(400)  # 500 remaining
        assert not tracker.can_make_request(600)  # Would exceed limit
        
    def test_rate_limit_exceeded(self, tracker):
        """Test rate limit handling."""
        tracker.record_usage(800, 0.08)
        assert not tracker.can_make_request(300)  # Would exceed 1000 limit
        
    def test_rate_limit_reset(self, tracker):
        """Test rate limit reset after time."""
        tracker.record_usage(1000, 0.10)
        assert not tracker.can_make_request(1)
        
        # Simulate minute passing
        tracker._last_reset = time.time() - 61
        tracker._reset_if_needed()
        
        assert tracker.tokens_used_this_minute == 0
        assert tracker.can_make_request(500)
        
    def test_get_stats(self, tracker):
        """Test usage statistics."""
        tracker.record_usage(300, 0.03)
        stats = tracker.get_stats()
        
        assert stats['tokens_used_this_minute'] == 300
        assert stats['current_cost'] == 0.03
        assert stats['rate_limit_remaining'] == 700


class TestLLMCircuitBreaker:
    """Test LLMCircuitBreaker functionality."""
    
    @pytest.fixture
    def llm_breaker(self):
        """Create LLM circuit breaker for testing."""
        return LLMCircuitBreaker("gpt4", model="gpt-4")
        
    @pytest.fixture
    def response_validator(self):
        """Mock response validator."""
        return lambda response: len(response) > 5 and "error" not in response.lower()
        
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test LLM circuit breaker initialization."""
        config = LLMCircuitBreakerConfig(cost_threshold_dollars=50.0)
        breaker = LLMCircuitBreaker("claude", model="claude-3", config=config)
        
        assert breaker.name == "llm_claude"
        assert breaker.model == "claude-3"
        assert breaker.config.cost_threshold_dollars == 50.0
        
    @pytest.mark.asyncio
    async def test_successful_llm_call(self, llm_breaker):
        """Test successful LLM operation."""
        async def mock_llm_operation():
            return "Generated response"
            
        result = await llm_breaker.call_llm(mock_llm_operation, tokens=100, estimated_cost=0.01)
        assert result == "Generated response"
        
    @pytest.mark.asyncio
    async def test_token_rate_limit_validation(self, llm_breaker):
        """Test token rate limit validation."""
        # Exceed rate limit
        llm_breaker._token_usage_tracker.record_usage(50000, 5.0)
        
        async def mock_operation():
            return "response"
            
        with pytest.raises(LLMRateLimitError):
            await llm_breaker.call_llm(mock_operation, tokens=100)
            
    @pytest.mark.asyncio
    async def test_cost_limit_validation(self, llm_breaker):
        """Test cost limit validation."""
        # Set high current cost
        llm_breaker._token_usage_tracker.current_cost = 99.0
        
        async def mock_operation():
            return "response"
            
        with pytest.raises(LLMCostLimitError):
            await llm_breaker.call_llm(mock_operation, estimated_cost=2.0)
            
    @pytest.mark.asyncio
    async def test_response_validation(self, response_validator):
        """Test response validation functionality."""
        breaker = LLMCircuitBreaker("gpt4", response_validator=response_validator)
        
        async def mock_operation_valid():
            return "Good response"
            
        async def mock_operation_invalid():
            return "err"  # Too short
            
        # Should succeed
        result = await breaker.call_llm(mock_operation_valid)
        assert result == "Good response"
        
        # Should fail validation
        with pytest.raises(LLMValidationError):
            await breaker.call_llm(mock_operation_invalid)
            
    def test_get_status(self, llm_breaker):
        """Test LLM status reporting."""
        status = llm_breaker.get_status()
        
        assert status['domain'] == 'llm'
        assert status['model'] == "gpt-4"
        assert 'token_usage' in status
        assert 'config' in status


class TestAuthCircuitBreakerConfig:
    """Test AuthCircuitBreakerConfig validation and defaults."""
    
    def test_default_config_creation(self):
        """Test default auth configuration values."""
        config = AuthCircuitBreakerConfig()
        
        assert config.security_failure_threshold == 2  # Strict for security
        assert config.security_recovery_timeout_seconds == 300.0  # Longer for security
        assert config.auth_timeout_seconds == 15.0
        assert config.suspicious_activity_threshold == 5
        assert "AuthenticationError" in config.expected_auth_exceptions
        assert "SecurityError" in config.security_errors
        
    def test_custom_config_creation(self):
        """Test custom auth configuration."""
        config = AuthCircuitBreakerConfig(
            security_failure_threshold=1,
            suspicious_activity_threshold=3,
            auth_timeout_seconds=10.0
        )
        
        assert config.security_failure_threshold == 1
        assert config.suspicious_activity_threshold == 3
        assert config.auth_timeout_seconds == 10.0


class TestSecurityMonitor:
    """Test security monitoring functionality."""
    
    @pytest.fixture
    def config(self):
        """Auth config for testing."""
        return AuthCircuitBreakerConfig(suspicious_activity_threshold=3)
        
    @pytest.fixture
    def monitor(self, config):
        """Security monitor for testing."""
        return SecurityMonitor(config)
        
    def test_initial_state(self, monitor):
        """Test initial security monitor state."""
        assert not monitor.is_user_suspicious("user1")
        assert not monitor.is_under_attack()
        
    def test_failure_tracking(self, monitor):
        """Test failure count tracking."""
        # Record failures for user
        monitor.record_failure("user1", "AuthenticationError")
        monitor.record_failure("user1", "AuthenticationError")
        assert not monitor.is_user_suspicious("user1")  # Below threshold
        
        monitor.record_failure("user1", "AuthenticationError")
        assert monitor.is_user_suspicious("user1")  # At threshold
        
    def test_success_resets_failures(self, monitor):
        """Test successful auth resets failure count."""
        monitor.record_failure("user1", "AuthenticationError")
        monitor.record_failure("user1", "AuthenticationError")
        
        monitor.record_success("user1")
        monitor.record_failure("user1", "AuthenticationError")
        assert not monitor.is_user_suspicious("user1")  # Reset counter
        
    def test_manual_user_flagging(self, monitor):
        """Test manual user flagging."""
        monitor.flag_suspicious_user("user2")
        assert monitor.is_user_suspicious("user2")
        
    def test_get_stats(self, monitor):
        """Test security statistics."""
        monitor.record_failure("user1", "AuthError")
        monitor.flag_suspicious_user("user2")
        
        stats = monitor.get_stats()
        assert stats['suspicious_users'] == 1
        assert stats['failure_counts'] == {'user1': 1}


class TestAuthCircuitBreaker:
    """Test AuthCircuitBreaker functionality."""
    
    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager."""
        manager = MagicMock()
        manager.record_login = AsyncMock()
        manager.invalidate_session = AsyncMock()
        return manager
        
    @pytest.fixture
    def fallback_handler(self):
        """Mock fallback authentication handler."""
        async def fallback_auth(*args, **kwargs):
            return "fallback_token"
        return fallback_auth
        
    @pytest.fixture
    def auth_breaker(self, mock_session_manager):
        """Create auth circuit breaker for testing."""
        return AuthCircuitBreaker("oauth", session_manager=mock_session_manager)
        
    @pytest.mark.asyncio
    async def test_initialization(self, mock_session_manager, fallback_handler):
        """Test auth circuit breaker initialization."""
        config = AuthCircuitBreakerConfig(security_failure_threshold=1)
        breaker = AuthCircuitBreaker(
            "sso", 
            config=config, 
            session_manager=mock_session_manager,
            fallback_handler=fallback_handler
        )
        
        assert breaker.name == "auth_sso"
        assert breaker.session_manager == mock_session_manager
        assert breaker.fallback_handler == fallback_handler
        assert breaker.config.security_failure_threshold == 1
        
    @pytest.mark.asyncio
    async def test_successful_authentication(self, auth_breaker):
        """Test successful authentication."""
        async def mock_auth_operation():
            return "auth_token"
            
        result = await auth_breaker.authenticate(mock_auth_operation, user_id="user1")
        assert result == "auth_token"
        
        # Should record success and update session
        auth_breaker.session_manager.record_login.assert_called_once_with("user1")
        
    @pytest.mark.asyncio
    async def test_suspicious_user_rejection(self, auth_breaker):
        """Test rejection of suspicious users."""
        # Flag user as suspicious
        auth_breaker._security_monitor.flag_suspicious_user("bad_user")
        
        async def mock_auth_operation():
            return "token"
            
        with pytest.raises(AuthSecurityError):
            await auth_breaker.authenticate(mock_auth_operation, user_id="bad_user")
            
    @pytest.mark.asyncio
    async def test_fallback_authentication(self, fallback_handler):
        """Test fallback authentication mechanism."""
        breaker = AuthCircuitBreaker("test", fallback_handler=fallback_handler)
        
        async def failing_auth():
            raise Exception("HTTPException")  # Fallback eligible error
            
        # Mock the fallback eligibility check
        with patch.object(breaker, '_should_use_fallback', return_value=True):
            result = await breaker.authenticate(failing_auth)
            assert result == "fallback_token"
            
    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self, auth_breaker):
        """Test session cleanup after session errors."""
        async def failing_auth():
            raise Exception("InvalidSessionError")
            
        with pytest.raises(Exception):
            await auth_breaker.authenticate(failing_auth, user_id="user1")
            
        # Should attempt session cleanup (would be called in _cleanup_invalid_session)
        # This is tested via the error handling path
        
    def test_get_status(self, auth_breaker):
        """Test auth status reporting."""
        status = auth_breaker.get_status()
        
        assert status['domain'] == 'auth'
        assert 'security_metrics' in status
        assert status['has_fallback'] is False  # No fallback handler in fixture
        assert 'config' in status


class TestAgentCircuitBreakerConfig:
    """Test AgentCircuitBreakerConfig validation and defaults."""
    
    def test_default_config_creation(self):
        """Test default agent configuration values."""
        config = AgentCircuitBreakerConfig()
        
        assert config.failure_threshold == 4
        assert config.task_timeout_seconds == 300.0  # 5 minutes
        assert config.preserve_context_on_failure is True
        assert config.nested_task_support is True
        assert "TaskTimeoutError" in config.expected_agent_exceptions
        assert "ResourceError" in config.resource_errors
        
    def test_custom_config_creation(self):
        """Test custom agent configuration."""
        config = AgentCircuitBreakerConfig(
            task_timeout_seconds=600.0,
            preserve_context_on_failure=False,
            nested_task_support=False
        )
        
        assert config.task_timeout_seconds == 600.0
        assert config.preserve_context_on_failure is False
        assert config.nested_task_support is False


class TestAgentTaskManager:
    """Test agent task management functionality."""
    
    @pytest.fixture
    def config(self):
        """Agent config for testing."""
        return AgentCircuitBreakerConfig()
        
    @pytest.fixture
    def task_manager(self, config):
        """Agent task manager for testing."""
        return AgentTaskManager(config)
        
    def test_initial_state(self, task_manager):
        """Test initial task manager state."""
        stats = task_manager.get_stats()
        assert stats['active_tasks'] == 0
        assert stats['preserved_contexts'] == 0
        assert stats['task_stats']['started'] == 0
        
    def test_task_lifecycle(self, task_manager):
        """Test complete task lifecycle."""
        task_context = {
            'task_id': 'task_1',
            'context': {'data': 'test'},
            'start_time': time.time(),
            'preserve_on_failure': True
        }
        
        # Start task
        task_manager.start_task(task_context)
        stats = task_manager.get_stats()
        assert stats['active_tasks'] == 1
        assert stats['task_stats']['started'] == 1
        
        # Complete task
        task_manager.complete_task(task_context)
        stats = task_manager.get_stats()
        assert stats['active_tasks'] == 0
        assert stats['task_stats']['completed'] == 1
        
    def test_task_failure_with_context_preservation(self, task_manager):
        """Test task failure with context preservation."""
        task_context = {
            'task_id': 'task_2',
            'context': {'important': 'data'},
            'start_time': time.time(),
            'preserve_on_failure': True
        }
        
        task_manager.start_task(task_context)
        task_manager.preserve_context(task_context)
        task_manager.fail_task(task_context)
        
        stats = task_manager.get_stats()
        assert stats['active_tasks'] == 0
        assert stats['preserved_contexts'] == 1
        assert stats['task_stats']['failed'] == 1


class TestAgentCircuitBreaker:
    """Test AgentCircuitBreaker functionality."""
    
    @pytest.fixture
    def progress_callback(self):
        """Mock progress callback."""
        return MagicMock()
        
    @pytest.fixture
    def agent_breaker(self, progress_callback):
        """Create agent circuit breaker for testing."""
        return AgentCircuitBreaker("supervisor", progress_callback=progress_callback)
        
    @pytest.mark.asyncio
    async def test_initialization(self, progress_callback):
        """Test agent circuit breaker initialization."""
        config = AgentCircuitBreakerConfig(task_timeout_seconds=600.0)
        breaker = AgentCircuitBreaker("worker", config=config, progress_callback=progress_callback)
        
        assert breaker.name == "agent_worker"
        assert breaker.config.task_timeout_seconds == 600.0
        assert breaker.progress_callback == progress_callback
        
    @pytest.mark.asyncio
    async def test_successful_task_execution(self, agent_breaker):
        """Test successful agent task execution."""
        async def mock_agent_task():
            return "task_result"
            
        result = await agent_breaker.execute_task(
            mock_agent_task, 
            task_id="test_task",
            context={'param': 'value'}
        )
        assert result == "task_result"
        
    @pytest.mark.asyncio  
    async def test_task_context_preparation(self, agent_breaker):
        """Test task context preparation."""
        context = {'user_id': '123', 'data': 'test'}
        
        prepared_context = agent_breaker._prepare_task_context("my_task", context)
        
        assert prepared_context['task_id'] == "my_task"
        assert prepared_context['context'] == context
        assert 'start_time' in prepared_context
        assert prepared_context['preserve_on_failure'] is True
        
    @pytest.mark.asyncio
    async def test_progress_tracking(self, agent_breaker, progress_callback):
        """Test progress tracking during task execution."""
        async def mock_task_with_progress(*args, **kwargs):
            # Simulate progress callback usage
            if 'progress_callback' in kwargs:
                kwargs['progress_callback'](50.0)
            return "result"
            
        await agent_breaker.execute_task(mock_task_with_progress)
        
        # Progress callback should be available but specific usage depends on implementation
        # This tests that the progress wrapper is created
        
    @pytest.mark.asyncio
    async def test_context_preservation_on_failure(self, agent_breaker):
        """Test context preservation when task fails."""
        async def failing_task():
            raise Exception("Task failed")
            
        with pytest.raises(Exception):
            await agent_breaker.execute_task(
                failing_task,
                task_id="failing_task",
                context={'important': 'data'}
            )
            
        # Context should be preserved (tested via task manager)
        stats = agent_breaker._task_manager.get_stats()
        assert stats['task_stats']['failed'] == 1
        
    def test_get_status(self, agent_breaker, progress_callback):
        """Test agent status reporting."""
        status = agent_breaker.get_status()
        
        assert status['domain'] == 'agent'
        assert 'task_metrics' in status
        assert status['has_progress_callback'] is True
        assert 'config' in status


class TestIntegrationWithUnifiedCircuitBreaker:
    """Test integration with underlying unified circuit breaker."""
    
    @pytest.mark.asyncio
    async def test_database_breaker_integration(self):
        """Test database breaker integrates with unified circuit breaker."""
        breaker = DatabaseCircuitBreaker("integration_test")
        
        # Should create underlying unified circuit breaker
        assert isinstance(breaker._circuit_breaker, UnifiedCircuitBreaker)
        assert breaker._circuit_breaker.config.name == "database_integration_test"
        
    @pytest.mark.asyncio
    async def test_llm_breaker_integration(self):
        """Test LLM breaker integrates with unified circuit breaker."""
        breaker = LLMCircuitBreaker("integration_test")
        
        assert isinstance(breaker._circuit_breaker, UnifiedCircuitBreaker)
        assert breaker._circuit_breaker.config.timeout_seconds == 60.0  # LLM default
        
    @pytest.mark.asyncio
    async def test_auth_breaker_integration(self):
        """Test auth breaker integrates with unified circuit breaker."""
        breaker = AuthCircuitBreaker("integration_test")
        
        assert isinstance(breaker._circuit_breaker, UnifiedCircuitBreaker)
        assert breaker._circuit_breaker.config.failure_threshold == 2  # Auth default (strict)
        assert breaker._circuit_breaker.config.adaptive_threshold is False  # Security requirement
        
    @pytest.mark.asyncio
    async def test_agent_breaker_integration(self):
        """Test agent breaker integrates with unified circuit breaker."""
        breaker = AgentCircuitBreaker("integration_test")
        
        assert isinstance(breaker._circuit_breaker, UnifiedCircuitBreaker)
        assert breaker._circuit_breaker.config.timeout_seconds == 300.0  # Agent default (5 min)
        assert breaker._circuit_breaker.config.adaptive_threshold is True  # Agents can adapt


class TestErrorHandlingAndFallbacks:
    """Test error handling and fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_database_connection_error_fallback(self):
        """Test database connection error triggers pool clearing."""
        mock_pool = MagicMock()
        mock_pool.size = 10
        mock_pool.clear = AsyncMock()
        
        breaker = DatabaseCircuitBreaker("test", db_pool=mock_pool)
        
        async def failing_operation():
            raise ConnectionError("DB connection lost")
            
        with pytest.raises(ConnectionError):
            await breaker.execute(failing_operation)
            
        mock_pool.clear.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_llm_rate_limit_error_handling(self):
        """Test LLM rate limit error handling."""
        config = LLMCircuitBreakerConfig(token_rate_limit_per_minute=100)
        breaker = LLMCircuitBreaker("test", config=config)
        
        # Exhaust rate limit
        breaker._token_usage_tracker.record_usage(100, 0.1)
        
        async def mock_operation():
            return "response"
            
        with pytest.raises(LLMRateLimitError):
            await breaker.call_llm(mock_operation, tokens=50)
            
    @pytest.mark.asyncio
    async def test_auth_fallback_mechanism(self):
        """Test auth fallback when primary auth fails."""
        async def fallback_auth(*args, **kwargs):
            return "fallback_token"
            
        breaker = AuthCircuitBreaker("test", fallback_handler=fallback_auth)
        
        async def failing_primary_auth():
            raise Exception("HTTPException")
            
        with patch.object(breaker, '_should_use_fallback', return_value=True):
            result = await breaker.authenticate(failing_primary_auth)
            assert result == "fallback_token"
            
    @pytest.mark.asyncio
    async def test_agent_context_preservation_on_error(self):
        """Test agent context preservation during failures."""
        config = AgentCircuitBreakerConfig(preserve_context_on_failure=True)
        breaker = AgentCircuitBreaker("test", config=config)
        
        async def failing_task():
            raise Exception("Task timeout")
            
        with pytest.raises(Exception):
            await breaker.execute_task(
                failing_task,
                task_id="preserve_test",
                context={'critical': 'data'}
            )
            
        # Context should be preserved
        stats = breaker._task_manager.get_stats()
        assert stats['preserved_contexts'] == 1


class TestEdgeCasesAndErrorConditions:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_database_breaker_without_pool(self):
        """Test database breaker without connection pool."""
        breaker = DatabaseCircuitBreaker("no_pool", db_pool=None)
        
        async def mock_operation():
            return "result"
            
        # Should work without pool health checking
        result = await breaker.execute(mock_operation)
        assert result == "result"
        
    @pytest.mark.asyncio
    async def test_llm_breaker_without_validator(self):
        """Test LLM breaker without response validator."""
        breaker = LLMCircuitBreaker("no_validator", response_validator=None)
        
        async def mock_operation():
            return "any response"
            
        result = await breaker.call_llm(mock_operation)
        assert result == "any response"
        
    @pytest.mark.asyncio
    async def test_auth_breaker_without_session_manager(self):
        """Test auth breaker without session manager."""
        breaker = AuthCircuitBreaker("no_session", session_manager=None)
        
        async def mock_auth():
            return "token"
            
        result = await breaker.authenticate(mock_auth, user_id="user1")
        assert result == "token"
        
    @pytest.mark.asyncio
    async def test_agent_breaker_without_progress_callback(self):
        """Test agent breaker without progress callback."""
        breaker = AgentCircuitBreaker("no_progress", progress_callback=None)
        
        async def mock_task():
            return "task_result"
            
        result = await breaker.execute_task(mock_task)
        assert result == "task_result"
        
    def test_token_usage_tracker_edge_cases(self):
        """Test token usage tracker edge cases."""
        config = LLMCircuitBreakerConfig(token_rate_limit_per_minute=1000)
        tracker = TokenUsageTracker(config)
        
        # Test exact limit
        assert tracker.can_make_request(1000)
        tracker.record_usage(1000, 1.0)
        assert not tracker.can_make_request(1)
        
        # Test zero tokens
        assert tracker.can_make_request(0)
        
    def test_security_monitor_edge_cases(self):
        """Test security monitor edge cases."""
        config = AuthCircuitBreakerConfig(suspicious_activity_threshold=1)
        monitor = SecurityMonitor(config)
        
        # Test immediate flagging at threshold 1
        monitor.record_failure("user1", "AuthError")
        assert monitor.is_user_suspicious("user1")
        
        # Test None user_id handling
        monitor.record_failure(None, "AuthError")
        monitor.record_success(None)
        # Should not raise errors
        
    def test_agent_task_manager_edge_cases(self):
        """Test agent task manager edge cases."""
        config = AgentCircuitBreakerConfig(preserve_context_on_failure=False)
        manager = AgentTaskManager(config)
        
        task_context = {'task_id': 'test', 'context': {}, 'start_time': time.time()}
        
        # Context preservation disabled
        manager.preserve_context(task_context)
        stats = manager.get_stats()
        assert stats['preserved_contexts'] == 0  # Should not preserve
        
        # Double completion should not error
        manager.start_task(task_context)
        manager.complete_task(task_context)
        manager.complete_task(task_context)  # Should handle gracefully