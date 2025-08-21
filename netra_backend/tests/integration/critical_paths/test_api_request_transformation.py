"""API Request Transformation L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (API compatibility and integration)
- Business Goal: Enable seamless API integration and data transformation
- Value Impact: Supports legacy systems, enables API evolution
- Strategic Impact: $15K MRR protection through API gateway flexibility

Critical Path: Request ingress -> Schema validation -> Transformation rules -> Data mapping -> Response transformation
Coverage: Request/response transformation, data mapping, schema evolution, legacy support
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from netra_backend.app.services.api_gateway.data_converter import DataConverter
from netra_backend.app.services.api_gateway.schema_mapper import SchemaMapper

# Add project root to path
from netra_backend.app.services.api_gateway.transformation_engine import (
    TransformationEngine,
)
from netra_backend.app.services.validation.schema_validator import SchemaValidator

# Add project root to path

logger = logging.getLogger(__name__)


@dataclass
class TransformationRule:
    """Transformation rule configuration."""
    endpoint_pattern: str
    direction: str  # request, response, both
    source_schema: str
    target_schema: str
    transformation_type: str  # field_mapping, data_conversion, schema_evolution
    rules: Dict[str, Any]  # Transformation rules
    enabled: bool = True


class ApiTransformationManager:
    """Manages L3 API transformation tests with real data transformation."""
    
    def __init__(self):
        self.transformation_engine = None
        self.schema_mapper = None
        self.data_converter = None
        self.schema_validator = None
        self.test_server = None
        self.backend_server = None
        self.transformation_rules = {}
        self.transformation_metrics = []
        self.validation_errors = []
        self.schema_cache = {}
        
    async def initialize_transformation(self):
        """Initialize API transformation services for L3 testing."""
        try:
            self.transformation_engine = TransformationEngine()
            await self.transformation_engine.initialize()
            
            self.schema_mapper = SchemaMapper()
            await self.schema_mapper.initialize()
            
            self.data_converter = DataConverter()
            await self.data_converter.initialize()
            
            self.schema_validator = SchemaValidator()
            await self.schema_validator.initialize()
            
            # Configure transformation rules
            await self.setup_transformation_rules()
            
            # Load test schemas
            await self.load_test_schemas()
            
            # Start test servers
            await self.start_backend_server()
            await self.start_transformation_gateway()
            
            logger.info("API transformation services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize transformation services: {e}")
            raise
    
    async def setup_transformation_rules(self):
        """Configure transformation rules for different endpoints."""
        self.transformation_rules = {
            # User data transformation (v1 to v2)
            "/api/v1/users": TransformationRule(
                endpoint_pattern="/api/v1/users",
                direction="both",
                source_schema="user_v1",
                target_schema="user_v2", 
                transformation_type="schema_evolution",
                rules={
                    "request_mapping": {
                        "name": "full_name",
                        "email": "email_address",
                        "phone": "phone_number"
                    },
                    "response_mapping": {
                        "full_name": "name",
                        "email_address": "email",
                        "phone_number": "phone",
                        "created_timestamp": "created_at"
                    },
                    "data_conversion": {
                        "created_timestamp": "iso_to_epoch",
                        "phone_number": "normalize_phone"
                    }
                }
            ),
            # Thread data legacy support
            "/api/legacy/threads": TransformationRule(
                endpoint_pattern="/api/legacy/threads",
                direction="both",
                source_schema="thread_legacy",
                target_schema="thread_v2",
                transformation_type="field_mapping",
                rules={
                    "request_mapping": {
                        "thread_title": "title",
                        "thread_content": "content",
                        "user_uuid": "user_id",
                        "created_time": "created_at"
                    },
                    "response_mapping": {
                        "title": "thread_title",
                        "content": "thread_content",
                        "user_id": "user_uuid",
                        "created_at": "created_time",
                        "updated_at": "modified_time"
                    },
                    "nested_mapping": {
                        "messages": {
                            "msg_content": "content",
                            "msg_timestamp": "timestamp",
                            "sender_uuid": "sender_id"
                        }
                    }
                }
            ),
            # Agent configuration format conversion
            "/api/v1/agents/config": TransformationRule(
                endpoint_pattern="/api/v1/agents/config",
                direction="response",
                source_schema="agent_config_internal",
                target_schema="agent_config_public",
                transformation_type="data_conversion",
                rules={
                    "filter_fields": ["internal_id", "debug_info", "system_prompts"],
                    "data_conversion": {
                        "temperature": "float_to_percentage",
                        "max_tokens": "add_units",
                        "timeout_ms": "ms_to_seconds"
                    },
                    "add_computed_fields": {
                        "estimated_cost": "calculate_cost_estimate",
                        "capabilities": "extract_capabilities"
                    }
                }
            ),
            # Metrics aggregation transformation
            "/api/v1/metrics/aggregate": TransformationRule(
                endpoint_pattern="/api/v1/metrics/aggregate",
                direction="both",
                source_schema="metrics_request_v1",
                target_schema="metrics_request_v2",
                transformation_type="schema_evolution",
                rules={
                    "request_mapping": {
                        "start_date": "time_range.start",
                        "end_date": "time_range.end",
                        "metric_names": "metrics",
                        "group_by": "grouping.dimensions"
                    },
                    "response_mapping": {
                        "time_range": "period",
                        "data_points": "results",
                        "summary": "aggregated_stats"
                    },
                    "array_transformations": {
                        "metrics": "flatten_metric_objects",
                        "results": "normalize_data_points"
                    }
                }
            ),
            # Webhook payload standardization
            "/api/webhooks/inbound": TransformationRule(
                endpoint_pattern="/api/webhooks/inbound",
                direction="request",
                source_schema="webhook_external",
                target_schema="webhook_internal",
                transformation_type="field_mapping",
                rules={
                    "request_mapping": {
                        "event_type": "type",
                        "event_data": "payload",
                        "timestamp": "received_at",
                        "source_system": "origin"
                    },
                    "validation_rules": {
                        "required_fields": ["event_type", "timestamp"],
                        "field_types": {
                            "timestamp": "iso_datetime",
                            "event_data": "object"
                        }
                    }
                }
            )
        }
        
        # Register transformation rules
        for pattern, rule in self.transformation_rules.items():
            await self.transformation_engine.register_rule(pattern, rule)
    
    async def load_test_schemas(self):
        """Load test schemas for transformation."""
        self.schema_cache = {
            "user_v1": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "phone": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"}
                },
                "required": ["name", "email"]
            },
            "user_v2": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "email_address": {"type": "string", "format": "email"},
                    "phone_number": {"type": "string", "pattern": "^\\+?[1-9]\\d{1,14}$"},
                    "created_timestamp": {"type": "integer"}
                },
                "required": ["full_name", "email_address"]
            },
            "thread_legacy": {
                "type": "object",
                "properties": {
                    "thread_title": {"type": "string"},
                    "thread_content": {"type": "string"},
                    "user_uuid": {"type": "string", "format": "uuid"},
                    "created_time": {"type": "string"}
                }
            },
            "thread_v2": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "user_id": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"}
                }
            }
        }
        
        # Load schemas into validator
        for schema_name, schema_definition in self.schema_cache.items():
            await self.schema_validator.load_schema(schema_name, schema_definition)
    
    async def start_backend_server(self):
        """Start mock backend server."""
        from aiohttp import web
        
        async def handle_users(request):
            """Handle user requests (v2 format)."""
            if request.method == "POST":
                data = await request.json()
                
                # Backend expects v2 format
                response_data = {
                    "id": str(uuid.uuid4()),
                    "full_name": data.get("full_name", ""),
                    "email_address": data.get("email_address", ""),
                    "phone_number": data.get("phone_number", ""),
                    "created_timestamp": int(time.time()),
                    "status": "active"
                }
            else:
                # GET request
                user_id = request.match_info.get("user_id", "default")
                response_data = {
                    "id": user_id,
                    "full_name": "John Doe",
                    "email_address": "john@example.com",
                    "phone_number": "+1234567890",
                    "created_timestamp": 1609459200,
                    "status": "active"
                }
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json=response_data
            )
        
        async def handle_threads(request):
            """Handle thread requests (v2 format)."""
            if request.method == "POST":
                data = await request.json()
                
                response_data = {
                    "id": str(uuid.uuid4()),
                    "title": data.get("title", ""),
                    "content": data.get("content", ""),
                    "user_id": data.get("user_id", ""),
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "status": "active"
                }
            else:
                response_data = {
                    "id": "thread_123",
                    "title": "Sample Thread",
                    "content": "Thread content",
                    "user_id": "user_456",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "status": "active"
                }
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json=response_data
            )
        
        async def handle_agent_config(request):
            """Handle agent config requests (internal format)."""
            response_data = {
                "internal_id": "agent_001",
                "name": "Primary Agent",
                "temperature": 0.7,
                "max_tokens": 4096,
                "timeout_ms": 30000,
                "system_prompts": ["internal prompt"],
                "debug_info": {"version": "1.0", "build": "123"},
                "model": "gpt-4",
                "capabilities": ["text", "analysis", "code"]
            }
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json=response_data
            )
        
        async def handle_metrics(request):
            """Handle metrics requests (v2 format)."""
            if request.method == "POST":
                data = await request.json()
                
                response_data = {
                    "time_range": data.get("time_range", {}),
                    "data_points": [
                        {"timestamp": 1609459200, "value": 100},
                        {"timestamp": 1609462800, "value": 150}
                    ],
                    "summary": {
                        "total": 250,
                        "average": 125,
                        "count": 2
                    }
                }
            else:
                response_data = {"error": "Method not allowed"}
            
            return web.Response(
                status=200 if request.method == "POST" else 405,
                headers={"Content-Type": "application/json"},
                json=response_data
            )
        
        async def handle_webhooks(request):
            """Handle webhook requests (internal format)."""
            data = await request.json()
            
            response_data = {
                "id": str(uuid.uuid4()),
                "type": data.get("type", ""),
                "payload": data.get("payload", {}),
                "received_at": data.get("received_at", ""),
                "origin": data.get("origin", ""),
                "processed": True
            }
            
            return web.Response(
                status=200,
                headers={"Content-Type": "application/json"},
                json=response_data
            )
        
        app = web.Application()
        
        # Register backend routes (v2/internal format)
        app.router.add_route('*', '/internal/v2/users', handle_users)
        app.router.add_route('*', '/internal/v2/users/{user_id}', handle_users)
        app.router.add_route('*', '/internal/v2/threads', handle_threads)
        app.router.add_route('*', '/internal/v2/threads/{thread_id}', handle_threads)
        app.router.add_get('/internal/agent/config', handle_agent_config)
        app.router.add_post('/internal/metrics/query', handle_metrics)
        app.router.add_post('/internal/webhooks/process', handle_webhooks)
        
        self.backend_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 8100)
        )
        
        logger.info("Backend server started on port 8100")
    
    async def start_transformation_gateway(self):
        """Start API gateway with transformation middleware."""
        from aiohttp import web
        
        async def transformation_middleware(request, handler):
            """Transformation middleware for API gateway."""
            start_time = time.time()
            
            try:
                # Find transformation rule
                rule = await self.find_transformation_rule(request.path)
                
                if not rule or not rule.enabled:
                    # No transformation - pass through
                    return await handler(request)
                
                # Transform request if needed
                if rule.direction in ["request", "both"]:
                    transformed_request = await self.transform_request(request, rule)
                else:
                    transformed_request = request
                
                # Forward to backend
                backend_response = await self.forward_to_backend(transformed_request, rule)
                
                # Transform response if needed
                if rule.direction in ["response", "both"]:
                    transformed_response = await self.transform_response(backend_response, rule)
                else:
                    transformed_response = backend_response
                
                # Record metrics
                self.record_transformation_metric(
                    request.path, rule, time.time() - start_time, "success"
                )
                
                return transformed_response
                
            except Exception as e:
                self.record_transformation_metric(
                    request.path, rule if 'rule' in locals() else None, 
                    time.time() - start_time, "error", str(e)
                )
                
                return web.Response(
                    status=500,
                    json={"error": "Transformation failed", "details": str(e)}
                )
        
        async def handle_default(request):
            """Default handler (should not be reached due to middleware)."""
            return web.Response(
                status=404,
                json={"error": "Endpoint not found"}
            )
        
        app = web.Application(middlewares=[transformation_middleware])
        
        # Register gateway routes
        app.router.add_route('*', '/api/v1/users{path:.*}', handle_default)
        app.router.add_route('*', '/api/legacy/threads{path:.*}', handle_default)
        app.router.add_get('/api/v1/agents/config', handle_default)
        app.router.add_post('/api/v1/metrics/aggregate', handle_default)
        app.router.add_post('/api/webhooks/inbound', handle_default)
        
        self.test_server = await asyncio.create_task(
            aiohttp.web.create_server(app, "localhost", 0)
        )
        
        logger.info(f"Transformation gateway started on {self.test_server.sockets[0].getsockname()}")
    
    async def find_transformation_rule(self, path: str) -> Optional[TransformationRule]:
        """Find transformation rule for path."""
        for pattern, rule in self.transformation_rules.items():
            if path.startswith(pattern.rstrip('*')):
                return rule
        return None
    
    async def transform_request(self, request, rule: TransformationRule) -> Dict[str, Any]:
        """Transform request data according to rule."""
        if request.method in ["GET", "DELETE"]:
            return request  # No body to transform
        
        try:
            request_data = await request.json()
        except:
            return request  # Not JSON data
        
        # Apply transformation based on type
        if rule.transformation_type == "field_mapping":
            transformed_data = await self.apply_field_mapping(
                request_data, rule.rules.get("request_mapping", {})
            )
        elif rule.transformation_type == "schema_evolution":
            transformed_data = await self.apply_schema_evolution(
                request_data, rule.rules.get("request_mapping", {}),
                rule.rules.get("data_conversion", {})
            )
        elif rule.transformation_type == "data_conversion":
            transformed_data = await self.apply_data_conversion(
                request_data, rule.rules.get("data_conversion", {})
            )
        else:
            transformed_data = request_data
        
        # Validate transformed data
        if rule.target_schema:
            validation_result = await self.schema_validator.validate(
                transformed_data, rule.target_schema
            )
            if not validation_result["valid"]:
                raise ValueError(f"Transformed request validation failed: {validation_result['errors']}")
        
        # Create new request object with transformed data
        # For testing purposes, we'll store the transformed data
        request._transformed_data = transformed_data
        
        return request
    
    async def transform_response(self, response, rule: TransformationRule):
        """Transform response data according to rule."""
        try:
            response_data = await response.json()
        except:
            return response  # Not JSON response
        
        # Apply transformation based on type
        if rule.transformation_type == "field_mapping":
            transformed_data = await self.apply_field_mapping(
                response_data, rule.rules.get("response_mapping", {})
            )
        elif rule.transformation_type == "schema_evolution":
            transformed_data = await self.apply_schema_evolution(
                response_data, rule.rules.get("response_mapping", {}),
                rule.rules.get("data_conversion", {})
            )
        elif rule.transformation_type == "data_conversion":
            transformed_data = await self.apply_response_data_conversion(
                response_data, rule.rules
            )
        else:
            transformed_data = response_data
        
        # Validate transformed response
        if rule.source_schema:  # Validate against source (client expects this format)
            validation_result = await self.schema_validator.validate(
                transformed_data, rule.source_schema
            )
            if not validation_result["valid"]:
                self.validation_errors.append({
                    "type": "response_validation",
                    "schema": rule.source_schema,
                    "errors": validation_result["errors"],
                    "data": transformed_data
                })
        
        return web.Response(
            status=response.status,
            headers=response.headers,
            json=transformed_data
        )
    
    async def apply_field_mapping(self, data: Dict[str, Any], 
                                mapping: Dict[str, str]) -> Dict[str, Any]:
        """Apply field mapping transformation."""
        transformed = {}
        
        for source_field, target_field in mapping.items():
            if source_field in data:
                # Handle nested field mapping
                if "." in target_field:
                    self.set_nested_field(transformed, target_field, data[source_field])
                else:
                    transformed[target_field] = data[source_field]
        
        # Copy unmapped fields
        for field, value in data.items():
            if field not in mapping and field not in transformed:
                transformed[field] = value
        
        return transformed
    
    async def apply_schema_evolution(self, data: Dict[str, Any], 
                                   field_mapping: Dict[str, str],
                                   data_conversion: Dict[str, str]) -> Dict[str, Any]:
        """Apply schema evolution transformation."""
        # First apply field mapping
        transformed = await self.apply_field_mapping(data, field_mapping)
        
        # Then apply data conversions
        for field, conversion_type in data_conversion.items():
            if field in transformed:
                transformed[field] = await self.convert_data_type(
                    transformed[field], conversion_type
                )
        
        return transformed
    
    async def apply_data_conversion(self, data: Dict[str, Any], 
                                  conversions: Dict[str, str]) -> Dict[str, Any]:
        """Apply data type conversions."""
        transformed = data.copy()
        
        for field, conversion_type in conversions.items():
            if field in transformed:
                transformed[field] = await self.convert_data_type(
                    transformed[field], conversion_type
                )
        
        return transformed
    
    async def apply_response_data_conversion(self, data: Dict[str, Any], 
                                           rules: Dict[str, Any]) -> Dict[str, Any]:
        """Apply response-specific data conversion."""
        transformed = data.copy()
        
        # Filter sensitive fields
        filter_fields = rules.get("filter_fields", [])
        for field in filter_fields:
            transformed.pop(field, None)
        
        # Apply data conversions
        data_conversion = rules.get("data_conversion", {})
        for field, conversion_type in data_conversion.items():
            if field in transformed:
                transformed[field] = await self.convert_data_type(
                    transformed[field], conversion_type
                )
        
        # Add computed fields
        computed_fields = rules.get("add_computed_fields", {})
        for field, computation in computed_fields.items():
            transformed[field] = await self.compute_field_value(
                transformed, computation
            )
        
        return transformed
    
    async def convert_data_type(self, value: Any, conversion_type: str) -> Any:
        """Convert data type based on conversion type."""
        if conversion_type == "iso_to_epoch":
            # Convert ISO datetime to epoch timestamp
            if isinstance(value, str):
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return int(dt.timestamp())
                except:
                    return value
        
        elif conversion_type == "epoch_to_iso":
            # Convert epoch timestamp to ISO datetime
            if isinstance(value, (int, float)):
                from datetime import datetime
                dt = datetime.fromtimestamp(value)
                return dt.isoformat() + "Z"
        
        elif conversion_type == "normalize_phone":
            # Normalize phone number format
            if isinstance(value, str):
                # Simple normalization
                normalized = "".join(filter(str.isdigit, value))
                if len(normalized) >= 10:
                    return f"+{normalized}"
        
        elif conversion_type == "float_to_percentage":
            # Convert float to percentage
            if isinstance(value, (int, float)):
                return f"{value * 100}%"
        
        elif conversion_type == "add_units":
            # Add units to numeric value
            if isinstance(value, (int, float)):
                return f"{value} tokens"
        
        elif conversion_type == "ms_to_seconds":
            # Convert milliseconds to seconds
            if isinstance(value, (int, float)):
                return value / 1000
        
        return value
    
    async def compute_field_value(self, data: Dict[str, Any], computation: str) -> Any:
        """Compute field value based on computation type."""
        if computation == "calculate_cost_estimate":
            # Calculate estimated cost based on tokens
            max_tokens = data.get("max_tokens", 0)
            if isinstance(max_tokens, str) and "tokens" in max_tokens:
                tokens = int(max_tokens.split()[0])
                return f"${tokens * 0.0001:.4f}"
            return "$0.0000"
        
        elif computation == "extract_capabilities":
            # Extract capabilities from model
            capabilities = data.get("capabilities", [])
            if isinstance(capabilities, list):
                return capabilities
            return []
        
        return None
    
    def set_nested_field(self, data: Dict[str, Any], field_path: str, value: Any):
        """Set nested field value."""
        parts = field_path.split(".")
        current = data
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    async def forward_to_backend(self, request, rule: TransformationRule):
        """Forward transformed request to backend."""
        # Map external endpoints to internal endpoints
        endpoint_mapping = {
            "/api/v1/users": "/internal/v2/users",
            "/api/legacy/threads": "/internal/v2/threads",
            "/api/v1/agents/config": "/internal/agent/config",
            "/api/v1/metrics/aggregate": "/internal/metrics/query",
            "/api/webhooks/inbound": "/internal/webhooks/process"
        }
        
        backend_path = endpoint_mapping.get(rule.endpoint_pattern, request.path)
        backend_url = f"http://localhost:8100{backend_path}"
        
        # Prepare request data
        if hasattr(request, '_transformed_data'):
            request_data = request._transformed_data
        else:
            try:
                request_data = await request.json() if request.method in ["POST", "PUT"] else None
            except:
                request_data = None
        
        # Forward request
        async with aiohttp.ClientSession() as session:
            request_method = getattr(session, request.method.lower())
            
            kwargs = {
                "headers": {"Content-Type": "application/json"}
            }
            
            if request_data:
                kwargs["json"] = request_data
            
            async with request_method(backend_url, **kwargs) as response:
                return response
    
    def record_transformation_metric(self, endpoint: str, rule: Optional[TransformationRule],
                                   processing_time: float, status: str, error: str = None):
        """Record transformation metrics."""
        metric = {
            "endpoint": endpoint,
            "rule_pattern": rule.endpoint_pattern if rule else None,
            "transformation_type": rule.transformation_type if rule else None,
            "processing_time": processing_time,
            "status": status,
            "error": error,
            "timestamp": time.time()
        }
        self.transformation_metrics.append(metric)
    
    async def make_transformed_request(self, path: str, method: str = "GET",
                                     data: Optional[Dict[str, Any]] = None,
                                     headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make request through transformation gateway."""
        base_url = f"http://localhost:{self.test_server.sockets[0].getsockname()[1]}"
        url = f"{base_url}{path}"
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                request_method = getattr(session, method.lower())
                
                kwargs = {}
                if data:
                    kwargs["json"] = data
                if headers:
                    kwargs["headers"] = headers
                
                async with request_method(url, **kwargs) as response:
                    response_time = time.time() - start_time
                    
                    result = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers)
                    }
                    
                    if response.status == 200:
                        result["body"] = await response.json()
                    else:
                        try:
                            result["body"] = await response.json()
                        except:
                            result["body"] = await response.text()
                    
                    return result
                    
        except Exception as e:
            return {
                "status_code": 500,
                "response_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def test_transformation_accuracy(self, endpoint: str, test_data: Dict[str, Any],
                                         expected_transformations: Dict[str, Any]) -> Dict[str, Any]:
        """Test transformation accuracy with known data."""
        # Make request with test data
        result = await self.make_transformed_request(endpoint, "POST", test_data)
        
        if result["status_code"] != 200:
            return {
                "success": False,
                "error": f"Request failed: {result.get('error', 'Unknown error')}"
            }
        
        response_data = result["body"]
        
        # Check expected transformations
        transformation_accuracy = {}
        
        for field, expected_value in expected_transformations.items():
            if field in response_data:
                actual_value = response_data[field]
                transformation_accuracy[field] = {
                    "expected": expected_value,
                    "actual": actual_value,
                    "matches": actual_value == expected_value
                }
            else:
                transformation_accuracy[field] = {
                    "expected": expected_value,
                    "actual": None,
                    "matches": False
                }
        
        accuracy_score = sum(1 for t in transformation_accuracy.values() if t["matches"]) / len(transformation_accuracy) * 100
        
        return {
            "success": True,
            "accuracy_score": accuracy_score,
            "transformation_accuracy": transformation_accuracy,
            "response_data": response_data
        }
    
    async def get_transformation_metrics(self) -> Dict[str, Any]:
        """Get comprehensive transformation metrics."""
        total_transformations = len(self.transformation_metrics)
        total_errors = len([m for m in self.transformation_metrics if m["status"] == "error"])
        total_validation_errors = len(self.validation_errors)
        
        if total_transformations == 0:
            return {"total_transformations": 0}
        
        # Success rate
        success_rate = ((total_transformations - total_errors) / total_transformations) * 100
        
        # Processing time statistics
        processing_times = [m["processing_time"] for m in self.transformation_metrics]
        avg_processing_time = sum(processing_times) / len(processing_times)
        max_processing_time = max(processing_times)
        
        # Transformation type breakdown
        type_breakdown = {}
        for metric in self.transformation_metrics:
            trans_type = metric["transformation_type"]
            if trans_type:
                type_breakdown[trans_type] = type_breakdown.get(trans_type, 0) + 1
        
        # Endpoint breakdown
        endpoint_breakdown = {}
        for metric in self.transformation_metrics:
            endpoint = metric["endpoint"]
            if endpoint not in endpoint_breakdown:
                endpoint_breakdown[endpoint] = {"total": 0, "errors": 0}
            
            endpoint_breakdown[endpoint]["total"] += 1
            if metric["status"] == "error":
                endpoint_breakdown[endpoint]["errors"] += 1
        
        return {
            "total_transformations": total_transformations,
            "total_errors": total_errors,
            "total_validation_errors": total_validation_errors,
            "success_rate": success_rate,
            "average_processing_time": avg_processing_time,
            "max_processing_time": max_processing_time,
            "configured_rules": len(self.transformation_rules),
            "type_breakdown": type_breakdown,
            "endpoint_breakdown": endpoint_breakdown
        }
    
    async def cleanup(self):
        """Clean up transformation resources."""
        try:
            if self.test_server:
                self.test_server.close()
                await self.test_server.wait_closed()
            
            if self.backend_server:
                self.backend_server.close()
                await self.backend_server.wait_closed()
            
            if self.transformation_engine:
                await self.transformation_engine.shutdown()
            
            if self.schema_mapper:
                await self.schema_mapper.shutdown()
            
            if self.data_converter:
                await self.data_converter.shutdown()
            
            if self.schema_validator:
                await self.schema_validator.shutdown()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def transformation_manager():
    """Create transformation manager for L3 testing."""
    manager = ApiTransformationManager()
    await manager.initialize_transformation()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_field_mapping_transformation(transformation_manager):
    """Test field mapping transformation for user data."""
    # Test data in v1 format
    test_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "1234567890",
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    # Expected response transformations (v2 to v1 mapping)
    expected_transformations = {
        "name": "John Doe",  # full_name -> name
        "email": "john@example.com",  # email_address -> email  
        "phone": "+1234567890",  # phone_number -> phone (normalized)
        "created_at": "2024-01-01T00:00:00Z"  # created_timestamp -> created_at (converted)
    }
    
    # Test transformation accuracy
    result = await transformation_manager.test_transformation_accuracy(
        "/api/v1/users", test_data, expected_transformations
    )
    
    assert result["success"] is True
    assert result["accuracy_score"] >= 80  # At least 80% accuracy
    
    # Check specific field transformations
    assert "name" in result["response_data"]
    assert "email" in result["response_data"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_legacy_thread_transformation(transformation_manager):
    """Test legacy thread format transformation."""
    # Test data in legacy format
    test_data = {
        "thread_title": "Legacy Thread",
        "thread_content": "This is legacy content",
        "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "created_time": "2024-01-01 00:00:00"
    }
    
    result = await transformation_manager.make_transformed_request(
        "/api/legacy/threads", "POST", test_data
    )
    
    assert result["status_code"] == 200
    
    response_data = result["body"]
    
    # Check legacy format response
    assert "thread_title" in response_data
    assert "thread_content" in response_data
    assert "user_uuid" in response_data
    assert response_data["thread_title"] == "Legacy Thread"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_agent_config_data_conversion(transformation_manager):
    """Test agent configuration data conversion and filtering."""
    result = await transformation_manager.make_transformed_request(
        "/api/v1/agents/config", "GET"
    )
    
    assert result["status_code"] == 200
    
    response_data = result["body"]
    
    # Check that sensitive fields are filtered
    assert "internal_id" not in response_data
    assert "debug_info" not in response_data
    assert "system_prompts" not in response_data
    
    # Check data conversions
    assert "temperature" in response_data
    assert isinstance(response_data["temperature"], str)
    assert "%" in response_data["temperature"]  # Converted to percentage
    
    assert "max_tokens" in response_data
    assert "tokens" in response_data["max_tokens"]  # Units added
    
    # Check computed fields
    assert "estimated_cost" in response_data
    assert "$" in response_data["estimated_cost"]
    
    assert "capabilities" in response_data
    assert isinstance(response_data["capabilities"], list)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_metrics_schema_evolution(transformation_manager):
    """Test metrics API schema evolution transformation."""
    # Test data in v1 format
    test_data = {
        "start_date": "2024-01-01",
        "end_date": "2024-01-02",
        "metric_names": ["requests", "errors"],
        "group_by": ["service", "endpoint"]
    }
    
    result = await transformation_manager.make_transformed_request(
        "/api/v1/metrics/aggregate", "POST", test_data
    )
    
    assert result["status_code"] == 200
    
    response_data = result["body"]
    
    # Check transformed response structure (v2 to v1)
    assert "period" in response_data  # time_range -> period
    assert "results" in response_data  # data_points -> results
    assert "aggregated_stats" in response_data  # summary -> aggregated_stats
    
    # Check nested structure
    assert isinstance(response_data["results"], list)
    assert isinstance(response_data["aggregated_stats"], dict)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_webhook_payload_standardization(transformation_manager):
    """Test webhook payload standardization."""
    # Test data in external webhook format
    test_data = {
        "event_type": "user.created",
        "event_data": {
            "user_id": "123",
            "email": "test@example.com"
        },
        "timestamp": "2024-01-01T00:00:00Z",
        "source_system": "external_crm"
    }
    
    result = await transformation_manager.make_transformed_request(
        "/api/webhooks/inbound", "POST", test_data
    )
    
    assert result["status_code"] == 200
    
    response_data = result["body"]
    
    # Check standardized response format
    assert "type" in response_data  # event_type -> type
    assert "payload" in response_data  # event_data -> payload
    assert "received_at" in response_data  # timestamp -> received_at
    assert "origin" in response_data  # source_system -> origin
    assert response_data["processed"] is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_transformation_error_handling(transformation_manager):
    """Test transformation error handling with invalid data."""
    # Test with invalid data structure
    invalid_data = {
        "invalid_field": "invalid_value",
        "missing_required": None
    }
    
    result = await transformation_manager.make_transformed_request(
        "/api/v1/users", "POST", invalid_data
    )
    
    # Should handle transformation gracefully
    # Either succeed with partial transformation or return meaningful error
    assert result["status_code"] in [200, 400, 422, 500]
    
    if result["status_code"] != 200:
        # Check error response format
        assert "error" in result["body"] or "details" in result["body"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_concurrent_transformations(transformation_manager):
    """Test concurrent transformation requests."""
    # Test data for different endpoints
    test_scenarios = [
        ("/api/v1/users", "POST", {"name": "User1", "email": "user1@example.com"}),
        ("/api/legacy/threads", "POST", {"thread_title": "Thread1", "user_uuid": "user1"}),
        ("/api/v1/agents/config", "GET", None),
        ("/api/webhooks/inbound", "POST", {"event_type": "test", "timestamp": "2024-01-01T00:00:00Z"})
    ]
    
    # Make concurrent requests
    concurrent_tasks = []
    for path, method, data in test_scenarios:
        task = transformation_manager.make_transformed_request(path, method, data)
        concurrent_tasks.append(task)
    
    results = await asyncio.gather(*concurrent_tasks)
    
    # All transformations should succeed
    successful_results = [r for r in results if r["status_code"] == 200]
    assert len(successful_results) >= 3  # Most should succeed
    
    # Check that different transformations were applied
    for result in successful_results:
        assert "body" in result
        assert isinstance(result["body"], dict)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_transformation_performance(transformation_manager):
    """Test transformation performance requirements."""
    # Test performance with user transformation
    response_times = []
    
    test_data = {
        "name": "Performance Test",
        "email": "perf@example.com",
        "phone": "1234567890"
    }
    
    for i in range(20):
        result = await transformation_manager.make_transformed_request(
            "/api/v1/users", "POST", test_data
        )
        if result["status_code"] == 200:
            response_times.append(result["response_time"])
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    
    # Transformation should add minimal overhead
    assert avg_response_time < 0.3  # Average < 300ms
    assert max_response_time < 1.0  # Max < 1 second
    
    # Test concurrent performance
    concurrent_tasks = []
    for i in range(10):
        task = transformation_manager.make_transformed_request(
            "/api/v1/users", "POST", test_data
        )
        concurrent_tasks.append(task)
    
    start_time = time.time()
    concurrent_results = await asyncio.gather(*concurrent_tasks)
    concurrent_duration = time.time() - start_time
    
    # Should handle concurrent transformations efficiently
    assert concurrent_duration < 2.0  # 10 requests in < 2 seconds
    
    successful_concurrent = [r for r in concurrent_results if r["status_code"] == 200]
    assert len(successful_concurrent) >= 8  # Most should succeed


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L3
async def test_transformation_metrics_accuracy(transformation_manager):
    """Test accuracy of transformation metrics collection."""
    # Generate test traffic across endpoints
    test_requests = [
        ("/api/v1/users", "POST", {"name": "Test1", "email": "test1@example.com"}),
        ("/api/legacy/threads", "POST", {"thread_title": "Test Thread"}),
        ("/api/v1/agents/config", "GET", None),
    ]
    
    for path, method, data in test_requests * 2:  # 6 total requests
        await transformation_manager.make_transformed_request(path, method, data)
    
    # Get transformation metrics
    metrics = await transformation_manager.get_transformation_metrics()
    
    # Verify metrics accuracy
    assert metrics["total_transformations"] == 6
    assert metrics["configured_rules"] == 5
    assert 0 <= metrics["success_rate"] <= 100
    
    # Verify processing time metrics
    assert metrics["average_processing_time"] > 0
    assert metrics["max_processing_time"] >= metrics["average_processing_time"]
    
    # Verify breakdown metrics
    assert "type_breakdown" in metrics
    assert "endpoint_breakdown" in metrics
    
    # Check that different transformation types were used
    type_breakdown = metrics["type_breakdown"]
    assert len(type_breakdown) >= 2  # Multiple transformation types used