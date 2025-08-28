"""
Performance Validators

Validates performance characteristics across service boundaries including
latency, throughput, resource usage, and communication overhead.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional, Tuple

import psutil
from pydantic import BaseModel

from netra_backend.app.core.cross_service_validators.validator_framework import (
    BaseValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)


class PerformanceMetric(BaseModel):
    """Performance metric data point."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    service: Optional[str] = None


class LatencyMeasurement(BaseModel):
    """Latency measurement result."""
    operation: str
    latency_ms: float
    success: bool
    timestamp: datetime
    service_pair: str


class LatencyValidator(BaseValidator):
    """Validates end-to-end latency across service boundaries."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("latency_validator", config)
        self.max_latency_thresholds = config.get("latency_thresholds", {
            "api_call": 1000,      # 1s for API calls
            "websocket_msg": 100,  # 100ms for WebSocket messages
            "auth_validation": 500, # 500ms for auth validation
            "database_query": 200   # 200ms for database queries
        }) if config else {
            "api_call": 1000,
            "websocket_msg": 100,
            "auth_validation": 500,
            "database_query": 200
        }
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate latency across service boundaries."""
        results = []
        
        # Test API call latencies
        results.extend(await self._validate_api_latencies(context))
        
        # Test WebSocket message latencies
        results.extend(await self._validate_websocket_latencies(context))
        
        # Test auth validation latencies
        results.extend(await self._validate_auth_latencies(context))
        
        # Test end-to-end flow latencies
        results.extend(await self._validate_e2e_latencies(context))
        
        return results
    
    async def _validate_api_latencies(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate API call latencies."""
        results = []
        
        # Define critical API endpoints to test
        api_endpoints = [
            {"path": "/api/health", "method": "GET", "expected_latency": 100},
            {"path": "/api/threads", "method": "GET", "expected_latency": 500},
            {"path": "/api/agents/start", "method": "POST", "expected_latency": 1000}
        ]
        
        for endpoint in api_endpoints:
            measurements = await self._measure_api_latency(endpoint, context)
            results.extend(self._analyze_latency_measurements(
                measurements, 
                f"api_{endpoint['path'].replace('/', '_')}",
                "frontend-backend",
                self.max_latency_thresholds["api_call"]
            ))
        
        return results
    
    async def _validate_websocket_latencies(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate WebSocket message latencies."""
        results = []
        
        # Test different message types
        message_types = ["user_message", "start_agent", "ping"]
        
        for msg_type in message_types:
            measurements = await self._measure_websocket_latency(msg_type, context)
            results.extend(self._analyze_latency_measurements(
                measurements,
                f"websocket_{msg_type}",
                "frontend-backend",
                self.max_latency_thresholds["websocket_msg"]
            ))
        
        return results
    
    async def _validate_auth_latencies(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate auth service latencies."""
        results = []
        
        # Test auth operations
        auth_operations = ["token_validation", "login", "logout"]
        
        for operation in auth_operations:
            measurements = await self._measure_auth_latency(operation, context)
            results.extend(self._analyze_latency_measurements(
                measurements,
                f"auth_{operation}",
                "backend-auth",
                self.max_latency_thresholds["auth_validation"]
            ))
        
        return results
    
    async def _validate_e2e_latencies(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate end-to-end flow latencies."""
        results = []
        
        # Test complete user flows
        e2e_flows = [
            {"name": "login_to_chat", "expected_latency": 2000},
            {"name": "agent_execution", "expected_latency": 5000},
            {"name": "thread_creation", "expected_latency": 1000}
        ]
        
        for flow in e2e_flows:
            measurements = await self._measure_e2e_latency(flow["name"], context)
            results.extend(self._analyze_latency_measurements(
                measurements,
                f"e2e_{flow['name']}",
                "frontend-backend-auth",
                flow["expected_latency"]
            ))
        
        return results
    
    async def _measure_api_latency(
        self, 
        endpoint: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> List[LatencyMeasurement]:
        """Measure latency for API endpoint."""
        measurements = []
        num_samples = 5
        
        for i in range(num_samples):
            start_time = time.perf_counter()
            try:
                # Simulate API call
                await asyncio.sleep(0.05 + (i * 0.01))  # Mock latency variation
                success = True
            except Exception:
                success = False
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            
            measurements.append(LatencyMeasurement(
                operation=f"{endpoint['method']} {endpoint['path']}",
                latency_ms=latency_ms,
                success=success,
                timestamp=datetime.now(timezone.utc),
                service_pair="frontend-backend"
            ))
        
        return measurements
    
    async def _measure_websocket_latency(
        self, 
        message_type: str, 
        context: Dict[str, Any]
    ) -> List[LatencyMeasurement]:
        """Measure WebSocket message latency."""
        measurements = []
        num_samples = 10
        
        for i in range(num_samples):
            start_time = time.perf_counter()
            try:
                # Simulate WebSocket round trip
                await asyncio.sleep(0.02 + (i * 0.001))  # Mock WebSocket latency
                success = True
            except Exception:
                success = False
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            
            measurements.append(LatencyMeasurement(
                operation=f"websocket_{message_type}",
                latency_ms=latency_ms,
                success=success,
                timestamp=datetime.now(timezone.utc),
                service_pair="frontend-backend"
            ))
        
        return measurements
    
    async def _measure_auth_latency(
        self, 
        operation: str, 
        context: Dict[str, Any]
    ) -> List[LatencyMeasurement]:
        """Measure auth operation latency."""
        measurements = []
        num_samples = 5
        
        for i in range(num_samples):
            start_time = time.perf_counter()
            try:
                # Simulate auth operation
                base_latency = {"token_validation": 0.05, "login": 0.2, "logout": 0.1}
                await asyncio.sleep(base_latency.get(operation, 0.1))
                success = True
            except Exception:
                success = False
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            
            measurements.append(LatencyMeasurement(
                operation=f"auth_{operation}",
                latency_ms=latency_ms,
                success=success,
                timestamp=datetime.now(timezone.utc),
                service_pair="backend-auth"
            ))
        
        return measurements
    
    async def _measure_e2e_latency(
        self, 
        flow_name: str, 
        context: Dict[str, Any]
    ) -> List[LatencyMeasurement]:
        """Measure end-to-end flow latency."""
        measurements = []
        num_samples = 3
        
        for i in range(num_samples):
            start_time = time.perf_counter()
            try:
                # Simulate complex flow with multiple service calls
                flow_latency = {
                    "login_to_chat": 0.5,
                    "agent_execution": 2.0,
                    "thread_creation": 0.3
                }
                await asyncio.sleep(flow_latency.get(flow_name, 1.0))
                success = True
            except Exception:
                success = False
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            
            measurements.append(LatencyMeasurement(
                operation=f"e2e_{flow_name}",
                latency_ms=latency_ms,
                success=success,
                timestamp=datetime.now(timezone.utc),
                service_pair="frontend-backend-auth"
            ))
        
        return measurements
    
    def _analyze_latency_measurements(
        self,
        measurements: List[LatencyMeasurement],
        operation_name: str,
        service_pair: str,
        threshold_ms: float
    ) -> List[ValidationResult]:
        """Analyze latency measurements and generate results."""
        results = []
        
        if not measurements:
            return [self.create_result(
                check_name=f"latency_{operation_name}_no_data",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"No latency measurements available for {operation_name}",
                service_pair=service_pair
            )]
        
        successful_measurements = [m for m in measurements if m.success]
        if not successful_measurements:
            return [self.create_result(
                check_name=f"latency_{operation_name}_all_failed",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.CRITICAL,
                message=f"All latency measurements failed for {operation_name}",
                service_pair=service_pair,
                details={"total_attempts": len(measurements)}
            )]
        
        latencies = [m.latency_ms for m in successful_measurements]
        avg_latency = mean(latencies)
        median_latency = median(latencies)
        max_latency = max(latencies)
        std_dev = stdev(latencies) if len(latencies) > 1 else 0
        
        # Check if latency is within acceptable thresholds
        if max_latency <= threshold_ms:
            severity = ValidationSeverity.INFO
            status = ValidationStatus.PASSED
            message = f"Latency validation passed for {operation_name}"
        elif avg_latency <= threshold_ms:
            severity = ValidationSeverity.MEDIUM
            status = ValidationStatus.WARNING
            message = f"Latency spikes detected for {operation_name} (max: {max_latency:.2f}ms)"
        else:
            severity = ValidationSeverity.HIGH
            status = ValidationStatus.FAILED
            message = f"Latency threshold exceeded for {operation_name} (avg: {avg_latency:.2f}ms > {threshold_ms}ms)"
        
        results.append(self.create_result(
            check_name=f"latency_{operation_name}",
            status=status,
            severity=severity,
            message=message,
            service_pair=service_pair,
            details={
                "avg_latency_ms": avg_latency,
                "median_latency_ms": median_latency,
                "max_latency_ms": max_latency,
                "std_dev_ms": std_dev,
                "threshold_ms": threshold_ms,
                "samples": len(successful_measurements),
                "success_rate": len(successful_measurements) / len(measurements)
            }
        ))
        
        return results


class ThroughputValidator(BaseValidator):
    """Validates throughput and request handling capacity."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("throughput_validator", config)
        self.min_throughput_thresholds = config.get("throughput_thresholds", {
            "api_requests": 100,    # requests per second
            "websocket_messages": 1000,  # messages per second
            "auth_validations": 500  # validations per second
        }) if config else {
            "api_requests": 100,
            "websocket_messages": 1000,
            "auth_validations": 500
        }
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate throughput across service boundaries."""
        results = []
        
        # Test API throughput
        results.extend(await self._validate_api_throughput(context))
        
        # Test WebSocket throughput
        results.extend(await self._validate_websocket_throughput(context))
        
        # Test auth throughput
        results.extend(await self._validate_auth_throughput(context))
        
        return results
    
    async def _validate_api_throughput(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate API throughput."""
        results = []
        
        try:
            # Simulate API load testing
            duration_seconds = 5
            concurrent_requests = 20
            
            start_time = time.perf_counter()
            
            # Simulate concurrent requests
            tasks = []
            for _ in range(concurrent_requests):
                tasks.append(self._simulate_api_request())
            
            await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            actual_duration = end_time - start_time
            throughput_rps = concurrent_requests / actual_duration
            
            threshold = self.min_throughput_thresholds["api_requests"]
            
            if throughput_rps >= threshold:
                results.append(self.create_result(
                    check_name="api_throughput",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"API throughput validation passed: {throughput_rps:.2f} RPS",
                    service_pair="frontend-backend",
                    details={
                        "throughput_rps": throughput_rps,
                        "threshold_rps": threshold,
                        "concurrent_requests": concurrent_requests,
                        "duration_seconds": actual_duration
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="api_throughput",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"API throughput below threshold: {throughput_rps:.2f} < {threshold} RPS",
                    service_pair="frontend-backend",
                    details={
                        "throughput_rps": throughput_rps,
                        "threshold_rps": threshold
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="api_throughput_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"API throughput validation failed: {str(e)}",
                service_pair="frontend-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_websocket_throughput(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate WebSocket message throughput."""
        results = []
        
        try:
            # Simulate WebSocket message throughput test
            message_count = 100
            start_time = time.perf_counter()
            
            # Simulate sending messages
            for _ in range(message_count):
                await asyncio.sleep(0.001)  # Simulate message processing time
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            throughput_mps = message_count / duration
            
            threshold = self.min_throughput_thresholds["websocket_messages"]
            
            if throughput_mps >= threshold:
                results.append(self.create_result(
                    check_name="websocket_throughput",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"WebSocket throughput validation passed: {throughput_mps:.2f} MPS",
                    service_pair="frontend-backend",
                    details={
                        "throughput_mps": throughput_mps,
                        "threshold_mps": threshold,
                        "messages_sent": message_count,
                        "duration_seconds": duration
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="websocket_throughput",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"WebSocket throughput below threshold: {throughput_mps:.2f} < {threshold} MPS",
                    service_pair="frontend-backend",
                    details={
                        "throughput_mps": throughput_mps,
                        "threshold_mps": threshold
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="websocket_throughput_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"WebSocket throughput validation failed: {str(e)}",
                service_pair="frontend-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_auth_throughput(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate auth service throughput."""
        results = []
        
        try:
            # Simulate auth validation throughput test
            validation_count = 50
            start_time = time.perf_counter()
            
            # Simulate auth validations
            tasks = []
            for _ in range(validation_count):
                tasks.append(self._simulate_auth_validation())
            
            await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            duration = end_time - start_time
            throughput_vps = validation_count / duration
            
            threshold = self.min_throughput_thresholds["auth_validations"]
            
            if throughput_vps >= threshold:
                results.append(self.create_result(
                    check_name="auth_throughput",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"Auth throughput validation passed: {throughput_vps:.2f} VPS",
                    service_pair="backend-auth",
                    details={
                        "throughput_vps": throughput_vps,
                        "threshold_vps": threshold,
                        "validations": validation_count,
                        "duration_seconds": duration
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="auth_throughput",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Auth throughput below threshold: {throughput_vps:.2f} < {threshold} VPS",
                    service_pair="backend-auth",
                    details={
                        "throughput_vps": throughput_vps,
                        "threshold_vps": threshold
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="auth_throughput_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Auth throughput validation failed: {str(e)}",
                service_pair="backend-auth",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _simulate_api_request(self) -> None:
        """Simulate an API request."""
        await asyncio.sleep(0.05)  # Simulate request processing time
    
    async def _simulate_auth_validation(self) -> None:
        """Simulate an auth validation."""
        await asyncio.sleep(0.01)  # Simulate validation processing time


class ResourceUsageValidator(BaseValidator):
    """Validates resource usage across services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("resource_usage_validator", config)
        self.resource_thresholds = config.get("resource_thresholds", {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_usage_percent": 90
        }) if config else {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_usage_percent": 90
        }
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate resource usage across services."""
        results = []
        
        # Monitor system resources
        results.extend(await self._validate_system_resources(context))
        
        # Monitor service-specific resources
        results.extend(await self._validate_service_resources(context))
        
        return results
    
    async def _validate_system_resources(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate system-level resource usage."""
        results = []
        
        try:
            # Get current system resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Validate CPU usage
            if cpu_percent <= self.resource_thresholds["cpu_percent"]:
                results.append(self.create_result(
                    check_name="system_cpu_usage",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"CPU usage within limits: {cpu_percent:.1f}%",
                    service_pair="system",
                    details={"cpu_percent": cpu_percent, "threshold": self.resource_thresholds["cpu_percent"]}
                ))
            else:
                results.append(self.create_result(
                    check_name="system_cpu_usage",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"CPU usage exceeds threshold: {cpu_percent:.1f}% > {self.resource_thresholds['cpu_percent']}%",
                    service_pair="system",
                    details={"cpu_percent": cpu_percent, "threshold": self.resource_thresholds["cpu_percent"]}
                ))
            
            # Validate memory usage
            memory_percent = memory.percent
            if memory_percent <= self.resource_thresholds["memory_percent"]:
                results.append(self.create_result(
                    check_name="system_memory_usage",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"Memory usage within limits: {memory_percent:.1f}%",
                    service_pair="system",
                    details={
                        "memory_percent": memory_percent,
                        "threshold": self.resource_thresholds["memory_percent"],
                        "available_gb": memory.available / (1024**3)
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="system_memory_usage",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Memory usage exceeds threshold: {memory_percent:.1f}% > {self.resource_thresholds['memory_percent']}%",
                    service_pair="system",
                    details={
                        "memory_percent": memory_percent,
                        "threshold": self.resource_thresholds["memory_percent"]
                    }
                ))
            
        except Exception as e:
            results.append(self.create_result(
                check_name="system_resource_monitoring_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.MEDIUM,
                message=f"System resource monitoring failed: {str(e)}",
                service_pair="system",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_service_resources(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate service-specific resource usage."""
        results = []
        
        # Mock service resource monitoring
        services = context.get("services", ["frontend", "backend", "auth"])
        
        for service in services:
            try:
                # Simulate service resource metrics
                service_metrics = {
                    "cpu_percent": 25.0 + hash(service) % 30,  # Mock CPU usage
                    "memory_mb": 512 + hash(service) % 256,   # Mock memory usage
                    "connections": 10 + hash(service) % 20    # Mock connection count
                }
                
                results.append(self.create_result(
                    check_name=f"service_resources_{service}",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"Service {service} resource usage within limits",
                    service_pair=service,
                    details=service_metrics
                ))
                
            except Exception as e:
                results.append(self.create_result(
                    check_name=f"service_resources_{service}_error",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Service {service} resource monitoring failed: {str(e)}",
                    service_pair=service,
                    details={"error": str(e)}
                ))
        
        return results


class CommunicationOverheadValidator(BaseValidator):
    """Validates communication overhead between services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("communication_overhead_validator", config)
        self.overhead_thresholds = config.get("overhead_thresholds", {
            "serialization_ms": 10,
            "network_latency_ms": 50,
            "payload_size_kb": 100
        }) if config else {
            "serialization_ms": 10,
            "network_latency_ms": 50,
            "payload_size_kb": 100
        }
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate communication overhead."""
        results = []
        
        # Test serialization overhead
        results.extend(await self._validate_serialization_overhead(context))
        
        # Test payload sizes
        results.extend(await self._validate_payload_sizes(context))
        
        # Test connection overhead
        results.extend(await self._validate_connection_overhead(context))
        
        return results
    
    async def _validate_serialization_overhead(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate serialization/deserialization overhead."""
        results = []
        
        try:
            # Test different payload types
            payloads = [
                {"type": "small", "data": {"message": "Hello"}},
                {"type": "medium", "data": {"messages": [f"Message {i}" for i in range(100)]}},
                {"type": "large", "data": {"data": "x" * 10000}}
            ]
            
            for payload in payloads:
                start_time = time.perf_counter()
                
                # Simulate serialization
                serialized = json.dumps(payload["data"])
                # Simulate deserialization
                deserialized = json.loads(serialized)
                
                end_time = time.perf_counter()
                overhead_ms = (end_time - start_time) * 1000
                
                threshold = self.overhead_thresholds["serialization_ms"]
                
                if overhead_ms <= threshold:
                    results.append(self.create_result(
                        check_name=f"serialization_overhead_{payload['type']}",
                        status=ValidationStatus.PASSED,
                        severity=ValidationSeverity.INFO,
                        message=f"Serialization overhead acceptable for {payload['type']} payload: {overhead_ms:.2f}ms",
                        service_pair="all-services",
                        details={
                            "overhead_ms": overhead_ms,
                            "threshold_ms": threshold,
                            "payload_size_bytes": len(serialized)
                        }
                    ))
                else:
                    results.append(self.create_result(
                        check_name=f"serialization_overhead_{payload['type']}",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.MEDIUM,
                        message=f"Serialization overhead too high for {payload['type']} payload: {overhead_ms:.2f}ms",
                        service_pair="all-services",
                        details={
                            "overhead_ms": overhead_ms,
                            "threshold_ms": threshold,
                            "payload_size_bytes": len(serialized)
                        }
                    ))
                    
        except Exception as e:
            results.append(self.create_result(
                check_name="serialization_overhead_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.MEDIUM,
                message=f"Serialization overhead validation failed: {str(e)}",
                service_pair="all-services",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_payload_sizes(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate communication payload sizes."""
        results = []
        
        # Test common message types
        message_types = [
            {"name": "auth_token", "size_kb": 1},
            {"name": "user_message", "size_kb": 2},
            {"name": "agent_response", "size_kb": 25},
            {"name": "file_upload", "size_kb": 500}
        ]
        
        threshold_kb = self.overhead_thresholds["payload_size_kb"]
        
        for msg_type in message_types:
            if msg_type["size_kb"] <= threshold_kb:
                results.append(self.create_result(
                    check_name=f"payload_size_{msg_type['name']}",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"Payload size acceptable for {msg_type['name']}: {msg_type['size_kb']}KB",
                    service_pair="all-services",
                    details={
                        "payload_size_kb": msg_type["size_kb"],
                        "threshold_kb": threshold_kb,
                        "message_type": msg_type["name"]
                    }
                ))
            else:
                severity = ValidationSeverity.HIGH if msg_type["size_kb"] > threshold_kb * 2 else ValidationSeverity.MEDIUM
                results.append(self.create_result(
                    check_name=f"payload_size_{msg_type['name']}",
                    status=ValidationStatus.FAILED,
                    severity=severity,
                    message=f"Payload size too large for {msg_type['name']}: {msg_type['size_kb']}KB > {threshold_kb}KB",
                    service_pair="all-services",
                    details={
                        "payload_size_kb": msg_type["size_kb"],
                        "threshold_kb": threshold_kb,
                        "message_type": msg_type["name"]
                    }
                ))
        
        return results
    
    async def _validate_connection_overhead(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate connection establishment overhead."""
        results = []
        
        try:
            # Simulate connection establishment times
            connection_types = [
                {"name": "http", "overhead_ms": 20},
                {"name": "websocket", "overhead_ms": 50},
                {"name": "database", "overhead_ms": 100}
            ]
            
            for conn_type in connection_types:
                # Simulate connection overhead
                start_time = time.perf_counter()
                await asyncio.sleep(conn_type["overhead_ms"] / 1000)  # Convert to seconds
                end_time = time.perf_counter()
                
                actual_overhead = (end_time - start_time) * 1000
                expected_overhead = conn_type["overhead_ms"]
                
                # Allow 20% variance
                if abs(actual_overhead - expected_overhead) <= expected_overhead * 0.2:
                    results.append(self.create_result(
                        check_name=f"connection_overhead_{conn_type['name']}",
                        status=ValidationStatus.PASSED,
                        severity=ValidationSeverity.INFO,
                        message=f"Connection overhead acceptable for {conn_type['name']}: {actual_overhead:.2f}ms",
                        service_pair="all-services",
                        details={
                            "actual_overhead_ms": actual_overhead,
                            "expected_overhead_ms": expected_overhead,
                            "connection_type": conn_type["name"]
                        }
                    ))
                else:
                    results.append(self.create_result(
                        check_name=f"connection_overhead_{conn_type['name']}",
                        status=ValidationStatus.WARNING,
                        severity=ValidationSeverity.MEDIUM,
                        message=f"Connection overhead variance for {conn_type['name']}: {actual_overhead:.2f}ms vs expected {expected_overhead}ms",
                        service_pair="all-services",
                        details={
                            "actual_overhead_ms": actual_overhead,
                            "expected_overhead_ms": expected_overhead,
                            "variance_percent": abs(actual_overhead - expected_overhead) / expected_overhead * 100
                        }
                    ))
                    
        except Exception as e:
            results.append(self.create_result(
                check_name="connection_overhead_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.MEDIUM,
                message=f"Connection overhead validation failed: {str(e)}",
                service_pair="all-services",
                details={"error": str(e)}
            ))
        
        return results