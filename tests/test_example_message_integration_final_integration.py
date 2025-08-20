"""Integration Tests - Split from test_example_message_integration_final.py"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.routes.example_messages_enhanced import (
from app.handlers.example_message_handler_enhanced import (
from app.logging_config import central_logger
from app.handlers.example_message_handler_enhanced import ExampleMessageMetadata
from app.routes.example_messages_enhanced import example_message_websocket_enhanced

    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration across components"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test circuit breaker is properly configured
        assert handler.processing_circuit_breaker is not None
        assert handler.real_agent_integration.circuit_breaker is not None
        
        # Test circuit breaker state
        assert handler.processing_circuit_breaker.state in ["CLOSED", "HALF_OPEN", "OPEN"]
        assert handler.real_agent_integration.circuit_breaker.state in ["CLOSED", "HALF_OPEN", "OPEN"]
        
        # Test circuit breaker reset functionality
        handler.processing_circuit_breaker.reset()
        assert handler.processing_circuit_breaker.state == "CLOSED"

    def test_error_handling_integration(self):
        """Test integrated error handling across all components"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test validation error handling
        invalid_message = {
            "content": "short",  # Too short
            "user_id": "test"
            # Missing required fields
        }
        
        response = asyncio.run(handler.handle_example_message(invalid_message))
        assert response.status == 'error'
        assert response.error is not None
        assert 'validation' in response.execution_metadata.get('error_stage', '')

    def test_business_value_integration(self):
        """Test business value features work end-to-end"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Test different business value scenarios
        business_values = ['conversion', 'retention', 'expansion']
        categories = ['cost-optimization', 'latency-optimization', 'model-selection']
        
        for bv in business_values:
            for category in categories:
                metadata_dict = {
                    "title": f"{category} for {bv}",
                    "category": category,
                    "complexity": "intermediate",
                    "businessValue": bv,
                    "estimatedTime": "30s"
                }
                
                from app.handlers.example_message_handler_enhanced import ExampleMessageMetadata
                metadata = ExampleMessageMetadata(**metadata_dict)
                
                result = {"real_agent_execution": True, "agent_name": "Test"}
                processing_time = 20000  # 20 seconds
                
                insights = handler._generate_enhanced_business_insights(metadata, result, processing_time)
                
                assert insights['business_value_type'] == bv
                assert insights['revenue_impact_category'] == category
                assert insights['real_agent_execution'] == True
                assert 'conversion_indicators' in insights
