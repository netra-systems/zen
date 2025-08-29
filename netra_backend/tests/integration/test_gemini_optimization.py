"""Integration tests for Gemini 2.5 Flash optimization features.

This module tests the optimized circuit breaker settings, health checks, and 
provider-specific configurations for Gemini models to ensure they provide
better performance and reliability compared to generic configurations.

Test Categories:
- Circuit breaker optimization validation
- Health check functionality
- Performance characteristic verification
- Fallback chain testing
- Configuration validation
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from netra_backend.app.llm.llm_defaults import LLMModel
from netra_backend.app.llm.gemini_config import (
    get_gemini_config, 
    create_gemini_circuit_config,
    create_gemini_health_config,
    is_gemini_model,
    get_gemini_fallback_chain,
    GeminiModelTier,
    GEMINI_2_5_FLASH_CONFIG,
    GEMINI_2_5_PRO_CONFIG
)
from netra_backend.app.core.resilience.domain_circuit_breakers import LLMCircuitBreaker
from netra_backend.app.core.health.gemini_health import (
    GeminiHealthChecker, 
    GeminiHealthStatus,
    create_gemini_health_checker
)
from netra_backend.app.core.shared_health_types import HealthStatus


class TestGeminiConfiguration:
    """Test Gemini-specific configuration loading and validation."""
    
    def test_gemini_2_5_flash_config_loaded(self):
        """Test that Gemini 2.5 Flash configuration is properly loaded."""
        config = get_gemini_config(LLMModel.GEMINI_2_5_FLASH)
        
        assert config.model_name == "gemini-2.5-flash"
        assert config.tier == GeminiModelTier.FLASH
        assert config.avg_response_time_seconds == 0.8  # Fast response time
        assert config.max_response_time_seconds == 3.0   # Quick timeout
        assert config.requests_per_minute == 100         # High rate limit
        
    def test_gemini_2_5_pro_config_loaded(self):
        """Test that Gemini 2.5 Pro configuration is properly loaded."""
        config = get_gemini_config(LLMModel.GEMINI_2_5_PRO)
        
        assert config.model_name == "gemini-2.5-pro"
        assert config.tier == GeminiModelTier.PRO
        assert config.avg_response_time_seconds == 2.5   # Slower but more capable
        assert config.max_response_time_seconds == 15.0  # Longer timeout
        assert config.requests_per_minute == 30          # Lower rate limit
        
    def test_non_gemini_model_raises_error(self):
        """Test that non-Gemini models raise appropriate errors."""
        with pytest.raises(ValueError, match="No Gemini configuration"):
            get_gemini_config(LLMModel.GPT_4)
        
        with pytest.raises(ValueError, match="No Gemini configuration"):
            get_gemini_config(LLMModel.CLAUDE_3_OPUS)
    
    def test_is_gemini_model_detection(self):
        """Test detection of Gemini models."""
        assert is_gemini_model("gemini-2.5-flash")
        assert is_gemini_model("gemini-2.5-pro")
        assert is_gemini_model("gemini-1.5-pro")  # Should work for other versions
        
        assert not is_gemini_model("gpt-4")
        assert not is_gemini_model("claude-3-opus")
        assert not is_gemini_model("mock")
    
    def test_gemini_fallback_chains(self):
        """Test that appropriate fallback chains are defined."""
        flash_chain = get_gemini_fallback_chain(LLMModel.GEMINI_2_5_FLASH)
        assert flash_chain[0] == LLMModel.GEMINI_2_5_PRO  # Fallback to Pro first
        
        pro_chain = get_gemini_fallback_chain(LLMModel.GEMINI_2_5_PRO)
        assert pro_chain[0] == LLMModel.GEMINI_2_5_FLASH  # Fallback to Flash first


class TestGeminiCircuitBreakerOptimization:
    """Test optimized circuit breaker configurations for Gemini models."""
    
    def test_gemini_flash_circuit_config_optimization(self):
        """Test that Gemini Flash gets optimized circuit breaker settings."""
        config = create_gemini_circuit_config(LLMModel.GEMINI_2_5_FLASH)
        
        # Should have fast timeout for Flash model
        assert config["timeout_seconds"] <= 5.0  # Fast timeout
        assert config["failure_threshold"] == 10  # Higher threshold for stable model
        assert config["recovery_timeout"] == 5.0  # Quick recovery
        assert config["slow_call_threshold"] <= 3.0  # Mark slow calls quickly
        
        # Should have Flash-specific optimizations
        assert config.get("aggressive_recovery") is True
        assert config.get("adaptive_timeout") is True
        assert config.get("burst_capacity", 0) > 0
    
    def test_gemini_pro_circuit_config_optimization(self):
        """Test that Gemini Pro gets balanced circuit breaker settings."""
        config = create_gemini_circuit_config(LLMModel.GEMINI_2_5_PRO)
        
        # Should have longer timeout for Pro model
        assert config["timeout_seconds"] > 10.0  # Longer timeout
        assert config["failure_threshold"] >= 6   # Moderate threshold
        assert config["recovery_timeout"] == 10.0 # Standard recovery
        
        # Should have Pro-specific optimizations
        assert config.get("conservative_recovery") is True
        assert config.get("context_preservation") is True
        assert config.get("fallback_to_flash") is True
    
    @pytest.mark.asyncio
    async def test_llm_circuit_breaker_uses_gemini_config(self):
        """Test that LLMCircuitBreaker applies Gemini optimizations."""
        # Mock the unified circuit breaker manager
        with patch("netra_backend.app.core.resilience.domain_circuit_breakers.get_unified_circuit_breaker_manager") as mock_manager:
            mock_circuit_breaker = Mock()
            mock_manager.return_value.create_circuit_breaker.return_value = mock_circuit_breaker
            
            # Create LLM circuit breaker for Gemini Flash
            breaker = LLMCircuitBreaker("test", model="gemini-2.5-flash")
            
            # Verify that create_circuit_breaker was called
            mock_manager.return_value.create_circuit_breaker.assert_called_once()
            
            # Get the config that was passed
            call_args = mock_manager.return_value.create_circuit_breaker.call_args
            unified_config = call_args[0][1]  # Second argument is the config
            
            # Verify Gemini optimizations were applied
            assert unified_config.timeout_seconds <= 5.0  # Fast timeout for Flash
            assert unified_config.failure_threshold == 10  # Optimized threshold
            assert unified_config.recovery_timeout == 5.0  # Quick recovery
    
    @pytest.mark.asyncio
    async def test_non_gemini_model_uses_default_config(self):
        """Test that non-Gemini models use default configuration."""
        with patch("netra_backend.app.core.resilience.domain_circuit_breakers.get_unified_circuit_breaker_manager") as mock_manager:
            mock_circuit_breaker = Mock()
            mock_manager.return_value.create_circuit_breaker.return_value = mock_circuit_breaker
            
            # Create LLM circuit breaker for non-Gemini model
            breaker = LLMCircuitBreaker("test", model="gpt-4")
            
            # Get the config that was passed
            call_args = mock_manager.return_value.create_circuit_breaker.call_args
            unified_config = call_args[0][1]
            
            # Should use default configuration (not Gemini-optimized)
            assert unified_config.timeout_seconds == 60.0  # Default timeout
            assert unified_config.failure_threshold == 10  # Default threshold


class TestGeminiHealthChecker:
    """Test Gemini-specific health monitoring functionality."""
    
    def test_gemini_health_checker_creation(self):
        """Test creation of Gemini health checker."""
        checker = create_gemini_health_checker(LLMModel.GEMINI_2_5_FLASH)
        
        assert isinstance(checker, GeminiHealthChecker)
        assert checker.model == LLMModel.GEMINI_2_5_FLASH
        assert checker.model_config.model_name == "gemini-2.5-flash"
    
    def test_non_gemini_model_health_checker_fails(self):
        """Test that non-Gemini models cannot create health checker."""
        with pytest.raises(ValueError, match="is not a Gemini model"):
            create_gemini_health_checker(LLMModel.GPT_4)
    
    @pytest.mark.asyncio
    async def test_gemini_health_config_creation(self):
        """Test health configuration creation for Gemini models."""
        config = create_gemini_health_config(LLMModel.GEMINI_2_5_FLASH)
        
        assert config["check_interval_seconds"] > 0
        assert config["timeout_seconds"] <= 10.0  # Quick health check
        assert config["min_success_rate"] >= 0.95  # High success rate requirement
        assert "max_avg_latency_ms" in config
        assert config["validate_api_key"] is True
        assert config["check_quota_usage"] is True
    
    @pytest.mark.asyncio
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_api_key"})
    async def test_health_check_with_mock_responses(self):
        """Test health check with mocked HTTP responses."""
        checker = create_gemini_health_checker(LLMModel.GEMINI_2_5_FLASH)
        
        # Mock successful API responses
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"supportedGenerationMethods": ["generateContent"]})
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Perform health check
            status = await checker.check_health()
            
            # Should return healthy status
            assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        
        # Clean up
        await checker.cleanup()
    
    @pytest.mark.asyncio
    async def test_health_check_handles_api_errors(self):
        """Test that health check properly handles API errors."""
        checker = create_gemini_health_checker(LLMModel.GEMINI_2_5_FLASH)
        
        # Mock API failure
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = Exception("API connection failed")
            
            # Perform health check
            status = await checker.check_health()
            
            # Should return unhealthy status
            assert status == HealthStatus.UNHEALTHY
        
        # Clean up
        await checker.cleanup()
    
    def test_health_status_evaluation_logic(self):
        """Test health status evaluation based on different metrics."""
        checker = create_gemini_health_checker(LLMModel.GEMINI_2_5_FLASH)
        
        # Mock metrics for optimal status
        from netra_backend.app.core.health.gemini_health import GeminiHealthMetrics
        
        optimal_metrics = GeminiHealthMetrics(
            api_available=True,
            api_response_time_ms=500.0,  # Fast response
            api_key_valid=True,
            model_available=True,
            model_name="gemini-2.5-flash",
            model_version=None,
            avg_latency_ms=600.0,        # Under avg response time threshold
            p95_latency_ms=800.0,
            success_rate=0.995,          # Very high success rate
            error_rate=0.005,            # Very low error rate
            quota_remaining=1000,
            quota_limit=2000,
            quota_reset_time=None,
            daily_usage=500,
            recent_errors=[],
            error_patterns={},
            region=None,
            service_status="operational",
            rate_limit_status="normal"
        )
        
        status = checker._evaluate_health_status(optimal_metrics)
        assert status == GeminiHealthStatus.OPTIMAL


class TestGeminiPerformanceCharacteristics:
    """Test that Gemini optimizations provide expected performance benefits."""
    
    def test_flash_model_has_faster_timeouts_than_pro(self):
        """Test that Flash model has faster timeouts than Pro model."""
        flash_config = create_gemini_circuit_config(LLMModel.GEMINI_2_5_FLASH)
        pro_config = create_gemini_circuit_config(LLMModel.GEMINI_2_5_PRO)
        
        assert flash_config["timeout_seconds"] < pro_config["timeout_seconds"]
        assert flash_config["recovery_timeout"] <= pro_config["recovery_timeout"]
        assert flash_config["slow_call_threshold"] < pro_config["slow_call_threshold"]
    
    def test_gemini_models_have_faster_timeouts_than_defaults(self):
        """Test that Gemini models have faster timeouts than default LLM config."""
        from netra_backend.app.core.resilience.domain_circuit_breakers import LLMCircuitBreakerConfig
        
        default_config = LLMCircuitBreakerConfig()
        flash_config = create_gemini_circuit_config(LLMModel.GEMINI_2_5_FLASH)
        
        # Flash should be much faster than default
        assert flash_config["timeout_seconds"] < default_config.request_timeout_seconds / 2
        # Recovery timeout should be equal or better than half default
        assert flash_config["recovery_timeout"] <= default_config.recovery_timeout_seconds / 2
    
    def test_cost_optimization_values(self):
        """Test that cost optimization values are realistic."""
        flash_config = get_gemini_config(LLMModel.GEMINI_2_5_FLASH)
        pro_config = get_gemini_config(LLMModel.GEMINI_2_5_PRO)
        
        # Flash should be cheaper than Pro
        assert flash_config.input_cost_per_1k_tokens < pro_config.input_cost_per_1k_tokens
        assert flash_config.output_cost_per_1k_tokens < pro_config.output_cost_per_1k_tokens
        
        # Both should have reasonable cost values
        assert 0 < flash_config.input_cost_per_1k_tokens < 0.01
        assert 0 < pro_config.input_cost_per_1k_tokens < 0.01
    
    def test_rate_limiting_characteristics(self):
        """Test that rate limiting reflects actual API characteristics."""
        flash_config = get_gemini_config(LLMModel.GEMINI_2_5_FLASH)
        pro_config = get_gemini_config(LLMModel.GEMINI_2_5_PRO)
        
        # Flash should have higher throughput than Pro
        assert flash_config.requests_per_minute > pro_config.requests_per_minute
        assert flash_config.tokens_per_minute > pro_config.tokens_per_minute
        
        # Should have reasonable values
        assert flash_config.requests_per_minute >= 50  # Minimum reasonable rate
        assert pro_config.requests_per_minute >= 10    # Minimum reasonable rate


class TestGeminiIntegrationScenarios:
    """Test end-to-end integration scenarios with Gemini optimization."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_speed(self):
        """Test that Gemini circuit breaker recovers faster than default."""
        # This would be a more complex integration test that actually
        # measures recovery times, but for now we verify configuration
        
        flash_config = create_gemini_circuit_config(LLMModel.GEMINI_2_5_FLASH)
        
        # Recovery should be very fast for Flash
        assert flash_config["recovery_timeout"] <= 10.0
        assert flash_config.get("aggressive_recovery", False) is True
    
    def test_fallback_chain_integration(self):
        """Test that fallback chains are properly configured."""
        # Test Flash fallback chain
        flash_chain = get_gemini_fallback_chain(LLMModel.GEMINI_2_5_FLASH)
        
        # Should fallback to Pro first (same provider)
        assert flash_chain[0] == LLMModel.GEMINI_2_5_PRO
        
        # Then to external providers
        assert LLMModel.GPT_3_5_TURBO in flash_chain or LLMModel.CLAUDE_3_OPUS in flash_chain
        
        # Test Pro fallback chain
        pro_chain = get_gemini_fallback_chain(LLMModel.GEMINI_2_5_PRO)
        
        # Should fallback to Flash first (faster same-provider option)
        assert pro_chain[0] == LLMModel.GEMINI_2_5_FLASH
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self):
        """Test integration between health monitoring and circuit breaker."""
        checker = create_gemini_health_checker(LLMModel.GEMINI_2_5_FLASH)
        
        # Get detailed status
        status = checker.get_detailed_status()
        
        assert status["service"] == "gemini"
        assert status["model"] == "gemini-2.5-flash"
        assert "configuration" in status
        assert "model_config" in status["configuration"]
        assert status["configuration"]["model_config"]["tier"] == "flash"
        
        # Clean up
        await checker.cleanup()


class TestBackwardCompatibility:
    """Test that Gemini optimizations don't break existing functionality."""
    
    def test_existing_llm_models_still_work(self):
        """Test that existing non-Gemini models still function."""
        from netra_backend.app.core.resilience.domain_circuit_breakers import LLMCircuitBreakerConfig
        
        # Default config should still be valid
        config = LLMCircuitBreakerConfig()
        assert config.failure_threshold > 0
        assert config.recovery_timeout_seconds > 0
        assert config.request_timeout_seconds > 0
    
    @pytest.mark.asyncio 
    async def test_llm_circuit_breaker_backward_compatibility(self):
        """Test that LLMCircuitBreaker works with non-Gemini models."""
        with patch("netra_backend.app.core.resilience.domain_circuit_breakers.get_unified_circuit_breaker_manager") as mock_manager:
            mock_circuit_breaker = Mock()
            mock_manager.return_value.create_circuit_breaker.return_value = mock_circuit_breaker
            
            # Should work with legacy models
            breaker = LLMCircuitBreaker("test", model="gpt-4")
            assert breaker is not None
            
            # Should work without specifying model
            breaker_no_model = LLMCircuitBreaker("test")
            assert breaker_no_model is not None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])