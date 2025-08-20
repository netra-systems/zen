"""Comprehensive Test Suite for Example Message Flow System

Tests all aspects of the example message flow including:
- Message selection and sending
- Message validation and parsing
- Agent routing and processing
- Response generation
- Error scenarios and recovery
- Timeout handling
- Message ordering
- Concurrent message handling
- Agent fallback mechanisms
- Response quality validation

Business Value: Ensures reliable demonstration of AI optimization capabilities
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.handlers.example_message_handler import (
    ExampleMessageHandler,
    ExampleMessageRequest,
    ExampleMessageResponse,
    handle_example_message
)
from app.agents.example_message_processor import (
    ExampleMessageProcessor,
    ExampleMessageSupervisor,
    get_example_message_supervisor
)
from app.formatters.example_response_formatter import (
    format_example_response,
    ResponseFormat
)
from app.error_handling.example_message_errors import (
    ExampleMessageErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy,
    handle_example_message_error
)


class TestExampleMessageValidation:
    """Test message validation and parsing"""
    
    def test_valid_message_parsing(self):
        """Test parsing of valid example message"""
        valid_message = {
            "content": "I need to reduce costs but keep quality the same.",
            "example_message_id": "test_123",
            "example_message_metadata": {
                "title": "Cost Optimization",
                "category": "cost-optimization",
                "complexity": "basic",
                "businessValue": "conversion",
                "estimatedTime": "30-60s"
            },
            "user_id": "user_123",
            "timestamp": 1234567890
        }
        
        request = ExampleMessageRequest(**valid_message)
        
        assert request.content == "I need to reduce costs but keep quality the same."
        assert request.example_message_id == "test_123"
        assert request.example_message_metadata.category == "cost-optimization"
        assert request.user_id == "user_123"
        
    def test_invalid_category_validation(self):
        """Test validation of invalid category"""
        invalid_message = {
            "content": "Test message",
            "example_message_id": "test_123",
            "example_message_metadata": {
                "title": "Test",
                "category": "invalid-category",  # Invalid
                "complexity": "basic",
                "businessValue": "conversion",
                "estimatedTime": "30s"
            },
            "user_id": "user_123",
            "timestamp": 1234567890
        }
        
        with pytest.raises(Exception):  # Should raise ValidationError
            ExampleMessageRequest(**invalid_message)
            
    def test_message_content_length_validation(self):
        """Test content length validation"""
        # Too short
        short_message = {
            "content": "Short",  # < 10 chars
            "example_message_id": "test_123",
            "example_message_metadata": {
                "title": "Test",
                "category": "cost-optimization",
                "complexity": "basic",
                "businessValue": "conversion",
                "estimatedTime": "30s"
            },
            "user_id": "user_123",
            "timestamp": 1234567890
        }
        
        with pytest.raises(Exception):  # Should raise ValidationError
            ExampleMessageRequest(**short_message)
            
    def test_missing_required_fields(self):
        """Test validation with missing required fields"""
        incomplete_message = {
            "content": "Valid content here",
            # Missing example_message_id
            "example_message_metadata": {
                "title": "Test",
                "category": "cost-optimization",
                "complexity": "basic",
                "businessValue": "conversion",
                "estimatedTime": "30s"
            },
            "user_id": "user_123",
            "timestamp": 1234567890
        }
        
        with pytest.raises(Exception):  # Should raise ValidationError
            ExampleMessageRequest(**incomplete_message)


class TestExampleMessageHandler:
    """Test the main message handler"""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance"""
        return ExampleMessageHandler()
        
    @pytest.fixture
    def valid_message(self):
        """Valid test message"""
        return {
            "content": "I need to reduce costs by 20% while maintaining quality",
            "example_message_id": "cost_test_123",
            "example_message_metadata": {
                "title": "Cost Optimization Test",
                "category": "cost-optimization",
                "complexity": "intermediate",
                "businessValue": "conversion",
                "estimatedTime": "60-90s"
            },
            "user_id": "test_user_456",
            "timestamp": int(datetime.now().timestamp())
        }
        
    @pytest.mark.asyncio
    async def test_successful_message_processing(self, handler, valid_message):
        """Test successful processing of valid message"""
        with patch.object(handler, 'supervisor') as mock_supervisor:
            mock_supervisor.process_example_message.return_value = {
                'optimization_type': 'cost_optimization',
                'agent_name': 'Cost Optimization Agent',
                'result': 'Success'
            }
            
            with patch.object(handler, '_send_completion_notification') as mock_notify:
                mock_notify.return_value = None
                
                response = await handler.handle_example_message(valid_message)
                
                assert response.status == 'completed'
                assert response.message_id == 'cost_test_123'
                assert response.processing_time_ms is not None
                assert response.agent_used is not None
                
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, handler):
        """Test handling of validation errors"""
        invalid_message = {
            "content": "Too short",  # Invalid
            "example_message_id": "test_123",
            "user_id": "test_user"
        }
        
        response = await handler.handle_example_message(invalid_message)
        
        assert response.status == 'error'
        assert response.error is not None
        assert 'invalid' in response.error.lower() or 'validation' in response.error.lower()
        
    @pytest.mark.asyncio
    async def test_processing_error_handling(self, handler, valid_message):
        """Test handling of processing errors"""
        with patch.object(handler, 'supervisor') as mock_supervisor:
            mock_supervisor.process_example_message.side_effect = Exception("Processing failed")
            
            response = await handler.handle_example_message(valid_message)
            
            assert response.status == 'error'
            assert response.error is not None


class TestExampleMessageProcessor:
    """Test the agent message processor"""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance"""
        return ExampleMessageProcessor()
        
    @pytest.fixture
    def cost_metadata(self):
        """Cost optimization metadata"""
        return {
            'example_message_id': 'cost_123',
            'category': 'cost-optimization',
            'complexity': 'basic',
            'business_value': 'conversion'
        }
        
    @pytest.mark.asyncio
    async def test_cost_optimization_processing(self, processor, cost_metadata):
        """Test cost optimization message processing"""
        content = "Reduce costs while maintaining quality"
        
        with patch.object(processor, '_send_update') as mock_update:
            mock_update.return_value = None
            
            result = await processor.process_example_message(
                'test_user',
                content,
                cost_metadata
            )
            
            assert result['optimization_type'] == 'cost_optimization'
            assert 'analysis' in result
            assert 'optimization_opportunities' in result.get('analysis', {})
            assert processor.state.value == 'completed'
            
    @pytest.mark.asyncio
    async def test_latency_optimization_processing(self, processor):
        """Test latency optimization processing"""
        metadata = {
            'example_message_id': 'latency_123',
            'category': 'latency-optimization',
            'complexity': 'intermediate'
        }
        
        with patch.object(processor, '_send_update') as mock_update:
            mock_update.return_value = None
            
            result = await processor.process_example_message(
                'test_user',
                "Need 3x latency improvement",
                metadata
            )
            
            assert result['optimization_type'] == 'latency_optimization'
            assert 'current_performance' in result
            assert 'optimization_strategies' in result
            
    @pytest.mark.asyncio
    async def test_processing_with_updates(self, processor, cost_metadata):
        """Test that processing sends real-time updates"""
        updates_sent = []
        
        async def mock_send_update(update_type, content):
            updates_sent.append((update_type, content))
            
        processor._send_update = mock_send_update
        
        await processor.process_example_message(
            'test_user',
            "Test content",
            cost_metadata
        )
        
        # Should send multiple updates during processing
        assert len(updates_sent) >= 3  # agent_started, thinking, partial_result, completed
        
        update_types = [update[0] for update in updates_sent]
        assert 'agent_started' in update_types
        assert 'agent_completed' in update_types
        
    @pytest.mark.asyncio
    async def test_processing_error_handling(self, processor, cost_metadata):
        """Test error handling during processing"""
        # Mock WebSocket manager to fail
        with patch.object(processor, '_send_update') as mock_update:
            mock_update.side_effect = Exception("WebSocket failed")
            
            # Should still complete processing despite WebSocket errors
            result = await processor.process_example_message(
                'test_user',
                "Test content",
                cost_metadata
            )
            
            assert result is not None
            assert result['optimization_type'] == 'cost_optimization'


class TestExampleMessageSupervisor:
    """Test the message processing supervisor"""
    
    @pytest.fixture
    def supervisor(self):
        """Create supervisor instance"""
        return ExampleMessageSupervisor()
        
    @pytest.mark.asyncio
    async def test_supervisor_message_processing(self, supervisor):
        """Test supervisor handles message processing"""
        metadata = {
            'example_message_id': 'super_123',
            'category': 'model-selection',
            'complexity': 'advanced'
        }
        
        result = await supervisor.process_example_message(
            'test_user',
            "Compare GPT-4 vs Claude-3",
            metadata
        )
        
        assert result is not None
        assert result['optimization_type'] == 'model_selection'
        assert 'super_123' not in supervisor.active_processors  # Should be cleaned up
        
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, supervisor):
        """Test handling multiple concurrent messages"""
        messages = [
            ('user1', 'Cost optimization', {'example_message_id': 'msg1', 'category': 'cost-optimization'}),
            ('user2', 'Latency optimization', {'example_message_id': 'msg2', 'category': 'latency-optimization'}),
            ('user3', 'Model selection', {'example_message_id': 'msg3', 'category': 'model-selection'})
        ]
        
        # Process all messages concurrently
        tasks = [
            supervisor.process_example_message(user_id, content, metadata)
            for user_id, content, metadata in messages
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(result is not None for result in results)
        
        # All should be cleaned up
        assert len(supervisor.active_processors) == 0
        
    def test_supervisor_stats(self, supervisor):
        """Test supervisor statistics"""
        stats = supervisor.get_processor_stats()
        
        assert 'active_processors' in stats
        assert 'processing_stages' in stats
        assert stats['active_processors'] == 0  # Should start with 0


class TestResponseFormatting:
    """Test response formatting"""
    
    @pytest.fixture
    def cost_result(self):
        """Sample cost optimization result"""
        return {
            'optimization_type': 'cost_optimization',
            'analysis': {
                'current_spending': {'monthly_total': '$1500'},
                'optimization_opportunities': [
                    {
                        'strategy': 'Model Selection',
                        'description': 'Use appropriate models for tasks',
                        'potential_savings': '$300/month',
                        'implementation_effort': 'Medium'
                    }
                ]
            },
            'expected_outcomes': {
                'monthly_savings': '$300',
                'savings_percentage': '20%',
                'payback_period': '2 weeks'
            }
        }
        
    def test_cost_optimization_formatting(self, cost_result):
        """Test formatting of cost optimization results"""
        formatted = format_example_response(
            cost_result,
            ResponseFormat.BUSINESS_FOCUSED,
            'free'
        )
        
        assert formatted.title.startswith('💰')
        assert 'Cost Optimization' in formatted.title
        assert len(formatted.metrics) >= 3
        assert len(formatted.recommendations) >= 1
        assert formatted.business_impact['monthly_savings'] == '$300'
        
    def test_different_format_modes(self, cost_result):
        """Test different formatting modes"""
        formats = [
            ResponseFormat.DETAILED,
            ResponseFormat.SUMMARY,
            ResponseFormat.BUSINESS_FOCUSED,
            ResponseFormat.TECHNICAL
        ]
        
        for fmt in formats:
            formatted = format_example_response(cost_result, fmt, 'free')
            assert formatted.title is not None
            assert formatted.summary is not None
            assert len(formatted.metrics) > 0
            
    def test_error_response_formatting(self):
        """Test formatting of error responses"""
        error_result = {
            'optimization_type': 'error',
            'error': 'Test error occurred'
        }
        
        formatted = format_example_response(error_result)
        
        assert '⚠️' in formatted.title or 'Error' in formatted.title
        assert 'error' in formatted.summary.lower()


class TestErrorHandling:
    """Test comprehensive error handling"""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler instance"""
        return ExampleMessageErrorHandler()
        
    @pytest.fixture
    def error_context(self):
        """Sample error context"""
        return ErrorContext(
            user_id='test_user',
            message_id='test_msg',
            category='cost-optimization',
            processing_stage='processing'
        )
        
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, error_handler, error_context):
        """Test handling of validation errors"""
        validation_error = ValueError("Validation failed: invalid category")
        
        with patch.object(error_handler, 'ws_manager') as mock_ws:
            mock_ws.send_message_to_user.return_value = None
            
            error_info = await error_handler.handle_error(
                validation_error, 
                error_context
            )
            
            assert error_info.category == ErrorCategory.VALIDATION
            assert error_info.severity == ErrorSeverity.MEDIUM
            assert error_info.is_recoverable is True
            assert error_info.recovery_strategy == RecoveryStrategy.USER_NOTIFICATION
            
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, error_handler, error_context):
        """Test handling of timeout errors"""
        timeout_error = TimeoutError("Operation timed out")
        
        with patch.object(error_handler, 'ws_manager') as mock_ws:
            mock_ws.send_message_to_user.return_value = None
            
            error_info = await error_handler.handle_error(
                timeout_error,
                error_context
            )
            
            assert error_info.category == ErrorCategory.TIMEOUT
            assert error_info.severity == ErrorSeverity.HIGH
            assert error_info.recovery_strategy == RecoveryStrategy.RETRY
            assert error_info.max_retries == 2
            
    @pytest.mark.asyncio
    async def test_retry_recovery_strategy(self, error_handler, error_context):
        """Test retry recovery strategy"""
        retry_count = 0
        
        async def mock_operation():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 2:
                raise Exception("Temporary failure")
            return "Success"
            
        error_info = await error_handler.handle_error(
            Exception("Temporary failure"),
            error_context,
            mock_operation
        )
        
        # Should have attempted retry
        assert error_info.retry_count >= 1
        
    @pytest.mark.asyncio
    async def test_fallback_recovery_strategy(self, error_handler, error_context):
        """Test fallback recovery strategy"""
        error_context.processing_stage = 'agent_processing'
        
        agent_error = Exception("Agent processing failed")
        
        with patch.object(error_handler, 'ws_manager') as mock_ws:
            mock_ws.send_message_to_user.return_value = None
            
            error_info = await error_handler.handle_error(
                agent_error,
                error_context
            )
            
            assert error_info.category == ErrorCategory.AGENT_FAILURE
            assert error_info.recovery_strategy == RecoveryStrategy.FALLBACK
            
    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, error_handler, error_context):
        """Test error statistics are properly tracked"""
        initial_stats = error_handler.get_error_stats()
        initial_total = initial_stats['error_counts'].get('total_errors', 0)
        
        # Generate several errors
        errors = [
            ValueError("Validation error"),
            TimeoutError("Timeout error"),
            Exception("General error")
        ]
        
        with patch.object(error_handler, 'ws_manager') as mock_ws:
            mock_ws.send_message_to_user.return_value = None
            
            for error in errors:
                await error_handler.handle_error(error, error_context)
                
        final_stats = error_handler.get_error_stats()
        final_total = final_stats['error_counts'].get('total_errors', 0)
        
        assert final_total == initial_total + len(errors)
        assert len(final_stats['top_error_categories']) > 0


class TestMessageOrdering:
    """Test message ordering and sequencing"""
    
    @pytest.mark.asyncio
    async def test_message_order_preservation(self):
        """Test that messages are processed in order for same user"""
        handler = ExampleMessageHandler()
        messages = []
        
        # Mock supervisor to track order
        async def mock_process(user_id, content, metadata):
            messages.append(metadata['example_message_id'])
            await asyncio.sleep(0.1)  # Small delay
            return {'optimization_type': 'test', 'result': 'ok'}
            
        with patch.object(handler, 'supervisor') as mock_supervisor:
            mock_supervisor.process_example_message.side_effect = mock_process
            
            with patch.object(handler, '_send_completion_notification'):
                # Send messages sequentially for same user
                message_ids = ['msg1', 'msg2', 'msg3']
                for msg_id in message_ids:
                    message = {
                        "content": f"Test message {msg_id}",
                        "example_message_id": msg_id,
                        "example_message_metadata": {
                            "title": "Test",
                            "category": "cost-optimization",
                            "complexity": "basic",
                            "businessValue": "conversion",
                            "estimatedTime": "30s"
                        },
                        "user_id": "same_user",
                        "timestamp": int(datetime.now().timestamp())
                    }
                    await handler.handle_example_message(message)
                    
                # Messages should be processed in order
                assert messages == message_ids


class TestConcurrentMessageHandling:
    """Test concurrent message handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_multiple_users_concurrent_processing(self):
        """Test processing messages from multiple users concurrently"""
        handler = ExampleMessageHandler()
        results = {}
        
        async def mock_process(user_id, content, metadata):
            # Simulate different processing times
            delay = 0.1 if user_id == 'fast_user' else 0.2
            await asyncio.sleep(delay)
            results[user_id] = metadata['example_message_id']
            return {'optimization_type': 'test', 'result': 'ok'}
            
        with patch.object(handler, 'supervisor') as mock_supervisor:
            mock_supervisor.process_example_message.side_effect = mock_process
            
            with patch.object(handler, '_send_completion_notification'):
                # Create messages for different users
                messages = [
                    {
                        "content": "Fast user message",
                        "example_message_id": "fast_msg",
                        "example_message_metadata": {
                            "title": "Fast Test",
                            "category": "cost-optimization",
                            "complexity": "basic",
                            "businessValue": "conversion",
                            "estimatedTime": "30s"
                        },
                        "user_id": "fast_user",
                        "timestamp": int(datetime.now().timestamp())
                    },
                    {
                        "content": "Slow user message",
                        "example_message_id": "slow_msg",
                        "example_message_metadata": {
                            "title": "Slow Test",
                            "category": "latency-optimization",
                            "complexity": "advanced",
                            "businessValue": "retention",
                            "estimatedTime": "120s"
                        },
                        "user_id": "slow_user",
                        "timestamp": int(datetime.now().timestamp())
                    }
                ]
                
                # Process concurrently
                tasks = [handler.handle_example_message(msg) for msg in messages]
                responses = await asyncio.gather(*tasks)
                
                assert len(responses) == 2
                assert all(resp.status == 'completed' for resp in responses)
                assert results['fast_user'] == 'fast_msg'
                assert results['slow_user'] == 'slow_msg'


class TestQualityValidation:
    """Test response quality validation"""
    
    def test_response_completeness(self):
        """Test that responses contain all required elements"""
        sample_result = {
            'optimization_type': 'cost_optimization',
            'analysis': {
                'current_spending': {'monthly_total': '$1000'},
                'optimization_opportunities': []
            }
        }
        
        formatted = format_example_response(sample_result)
        
        # Check all required elements are present
        assert formatted.title is not None
        assert formatted.summary is not None
        assert isinstance(formatted.metrics, list)
        assert isinstance(formatted.recommendations, list)
        assert isinstance(formatted.implementation_steps, list)
        assert isinstance(formatted.business_impact, dict)
        
    def test_business_value_calculation(self):
        """Test business value metrics calculation"""
        cost_result = {
            'optimization_type': 'cost_optimization',
            'expected_outcomes': {
                'monthly_savings': '$500',
                'savings_percentage': '25%'
            }
        }
        
        formatted = format_example_response(cost_result)
        
        assert formatted.business_impact['monthly_savings'] == '$500'
        # Should calculate annual impact
        assert 'annual' in str(formatted.business_impact)
        
    def test_error_response_quality(self):
        """Test quality of error responses"""
        error_handler = ExampleMessageErrorHandler()
        
        # Test different error types produce appropriate messages
        errors = [
            (ValueError("Invalid input"), "user-friendly validation message"),
            (TimeoutError("Timeout"), "timeout handling message"),
            (Exception("Unknown"), "general error message")
        ]
        
        for error, expected_type in errors:
            context = ErrorContext(user_id='test', message_id='test')
            # We can't easily test the async parts without mocking, 
            # but we can test the classification
            error_info = error_handler._classify_error(error, 'test_id', context)
            
            assert error_info.user_message is not None
            assert len(error_info.user_message) > 10  # Should be descriptive
            assert error_info.user_message != str(error)  # Should be user-friendly


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])