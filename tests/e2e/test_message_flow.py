"""Unified Message Flow Testing - Phase 3 Implementation

# Complete message lifecycle testing for core chat functionality that delivers customer value. # Possibly broken comprehension
Tests the complete flow: User input → Backend routing → Agent processing → Response streaming.

Business Value Justification (BVJ):
    - Segment: All customer tiers (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable chat functionality that drives user engagement and conversion
- Value Impact: Chat reliability directly impacts user satisfaction and paid tier conversion
- Revenue Impact: Prevents chat failures that could lose customers, protecting 100% of revenue

Architecture:
#     - 450-line file limit enforced through focused test modules # Possibly broken comprehension
# - 25-line function limit for all functions # Possibly broken comprehension
- Tests real message flow end-to-end with all persistence layers
- Validates both success and failure scenarios for comprehensive coverage
"""

import asyncio
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio

from tests.e2e.config import (
    TEST_CONFIG,
    TestDataFactory,
    TestUser,
    UnifiedTestConfig,
)
from tests.e2e.harness_complete import TestHarnessContext
from tests.e2e.message_flow_helpers import (
    create_concurrent_messages,
    send_concurrent_message,
    test_cache_persistence,
    test_interruption_recovery,
    test_message_processing,
    test_message_send,
    test_mid_stream_interruption,
    test_postgres_persistence,
    test_response_streaming,
    validate_complete_flow,
from tests.e2e.message_flow_validators import (
    MessageFlowValidator,
    MessagePersistenceValidator,
    StreamInterruptionHandler,
    validate_graceful_degradation,
    validate_persistence_consistency,

@pytest_asyncio.fixture
async def message_flow_config():
    """Setup message flow test configuration"""
    config = TEST_CONFIG
    return config

@pytest_asyncio.fixture
async def flow_validator():
    """Setup message flow validator"""
    return MessageFlowValidator()

@pytest_asyncio.fixture
async def persistence_validator():
    """Setup persistence validator"""
    return MessagePersistenceValidator()

@pytest_asyncio.fixture
async def interruption_handler():
    """Setup stream interruption handler"""
    return StreamInterruptionHandler()

# BVJ: Core value delivery - Complete message lifecycle ensures customer satisfaction
@pytest.mark.asyncio
async def test_complete_message_lifecycle(, message_flow_config, flow_validator
):
    """Test complete message lifecycle: Send → Process → Stream → Display
    
    BVJ: This is the core chat experience that drives customer value and conversion.
    """
    async with TestHarnessContext("message_lifecycle") as harness:
        user = message_flow_config.users["free"]
        message_data = TestDataFactory.create_message_data(
            user.id, "Test message for complete lifecycle"
        
        sent_result = await test_message_send(harness, message_data)
        assert sent_result["success"], "Message send failed"
        
        process_result = await test_message_processing(harness, message_data)
        assert process_result["processed"], "Message processing failed"
        
        stream_result = await test_response_streaming(harness, flow_validator)
        assert stream_result["streamed"], "Response streaming failed"
        
        flow_complete = await validate_complete_flow(flow_validator)
        assert flow_complete, "Complete message flow validation failed"

# # BVJ: Concurrent handling ensures enterprise-grade reliability for high-value customers # Possibly broken comprehension
@pytest.mark.asyncio
async def test_message_ordering_concurrent(message_flow_config, flow_validator):
    """Test correct message ordering under concurrent load
    
    BVJ: Enterprise customers need reliable concurrent message handling.
    """
    async with TestHarnessContext("concurrent_ordering") as harness:
        user = message_flow_config.users["enterprise"]
        concurrent_messages = create_concurrent_messages(user, count=5)
        
        tasks = [
            send_concurrent_message(harness, msg, i, flow_validator)
            for i, msg in enumerate(concurrent_messages)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ordering_valid = flow_validator.validate_ordering()
        success_count = sum(1 for r in results if r and not isinstance(r, Exception))
        
        assert ordering_valid, "Message ordering was not maintained"
        assert success_count == len(concurrent_messages), "Not all messages processed"

# BVJ: Data persistence ensures customer data is never lost, critical for trust
@pytest.mark.asyncio 
async def test_message_persistence(, message_flow_config, persistence_validator
):
    """Test messages saved across all databases correctly
    
    BVJ: Data persistence builds customer trust and enables conversation history.
    """
    async with TestHarnessContext("message_persistence") as harness:
        user = message_flow_config.users["mid"]
        message_data = TestDataFactory.create_message_data(
            user.id, "Test persistence message"
        
        postgres_saved = await test_postgres_persistence(
            message_data, persistence_validator
        assert postgres_saved, "PostgreSQL persistence failed"
        
        cache_saved = await test_cache_persistence(
            message_data, persistence_validator
        assert cache_saved, "Cache persistence failed"
        
        consistency_valid = await validate_persistence_consistency(
            persistence_validator
        assert consistency_valid, "Persistence consistency validation failed"

# BVJ: Stream interruption handling prevents customer frustration and support tickets
@pytest.mark.asyncio
async def test_streaming_interruption(, message_flow_config, interruption_handler
):
    """Test graceful handling of stream interrupts
    
    BVJ: Robust error handling reduces support burden and maintains customer satisfaction.
    """
    async with TestHarnessContext("stream_interruption") as harness:
        user = message_flow_config.users["early"]
        message_data = TestDataFactory.create_message_data(
            user.id, "Test stream interruption"
        
        interruption_handled = await test_mid_stream_interruption(
            harness, message_data, interruption_handler
        assert interruption_handled, "Mid-stream interruption not handled"
        
        recovery_successful = await test_interruption_recovery(
            harness, interruption_handler
        assert recovery_successful, "Recovery after interruption failed"
        
        degradation_valid = await validate_graceful_degradation(
            interruption_handler
        assert degradation_valid, "Graceful degradation validation failed"
