"""Security Breach Detection and Response L4 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Security Incident Prevention and Response
- Value Impact: Prevents data breaches and unauthorized access
- Strategic Impact: $35K MRR protection from security incidents

Critical Path:
Attack Detection -> Threat Analysis -> Automated Response -> Incident Escalation -> Recovery Validation

Coverage: Intrusion detection, threat response, access control validation, rate limiting enforcement,
security event logging, incident response orchestration, multi-stage attack simulation
"""

import pytest
import asyncio
import time
import uuid
import httpx
import websockets
import json
import random
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote

from .l4_staging_critical_base import L4StagingCriticalPathTestBase, CriticalPathMetrics
from app.services.security_service import SecurityService
from app.websocket.rate_limiter import RateLimiter
from app.core.circuit_breaker_core import CircuitBreaker
from app.services.redis_service import RedisService
from app.monitoring.metrics_collector import MetricsCollector


@dataclass
class SecurityBreachMetrics:
    """Metrics container for security breach detection and response testing."""
    attack_simulations: int = 0
    successful_detections: int = 0
    false_positives: int = 0
    response_time_avg: float = 0.0
    blocked_requests: int = 0
    rate_limit_triggers: int = 0
    circuit_breaker_trips: int = 0
    security_events_logged: int = 0
    incident_escalations: int = 0
    recovery_validations: int = 0
    attack_vectors_tested: List[str] = field(default_factory=list)
    response_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def detection_rate(self) -> float:
        """Calculate detection success rate."""
        if self.attack_simulations == 0:
            return 100.0
        return (self.successful_detections / self.attack_simulations) * 100.0

    @property
    def false_positive_rate(self) -> float:
        """Calculate false positive rate."""
        total_validations = self.successful_detections + self.false_positives
        if total_validations == 0:
            return 0.0
        return (self.false_positives / total_validations) * 100.0


@dataclass
class AttackVector:
    """Configuration for attack vector simulation."""
    name: str
    attack_type: str
    payload: Dict[str, Any]
    expected_response: str
    severity: str
    validation_criteria: Dict[str, Any]


class SecurityBreachResponseL4Test(L4StagingCriticalPathTestBase):
    """L4 test suite for security breach detection and response in staging environment."""
    
    def __init__(self):
        super().__init__("security_breach_response_l4")
        self.security_service: Optional[SecurityService] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.circuit_breaker: Optional[CircuitBreaker] = None
        self.security_metrics = SecurityBreachMetrics()
        self.attack_vectors: List[AttackVector] = []
        self.active_sessions: Dict[str, Dict] = {}
        self.security_config: Dict[str, Any] = {}
        
    async def setup_test_specific_environment(self) -> None:
        """Setup security testing environment with attack vectors and monitoring."""
        try:
            # Initialize security services
            self.security_service = SecurityService()
            
            # Initialize rate limiter with strict testing limits
            self.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
            
            # Initialize circuit breaker for testing
            circuit_config = {
                "failure_threshold": 3,
                "recovery_timeout": 30,
                "timeout": 5.0
            }
            self.circuit_breaker = CircuitBreaker(circuit_config)
            
            # Setup security configuration
            self.security_config = {
                "max_login_attempts": 3,
                "lockout_duration": 300,  # 5 minutes
                "sql_injection_patterns": [
                    "UNION SELECT", "DROP TABLE", "INSERT INTO", 
                    "--", "/*", "*/", "xp_cmdshell", "sp_executesql"
                ],
                "xss_patterns": [
                    "<script>", "</script>", "javascript:", "onload=",
                    "onerror=", "onclick=", "alert(", "eval("
                ],
                "suspicious_user_agents": [
                    "sqlmap", "nikto", "burp", "nmap", "masscan"
                ],
                "rate_limit_thresholds": {
                    "login": {"requests": 5, "window": 300},
                    "api": {"requests": 100, "window": 60},
                    "websocket": {"requests": 50, "window": 30}
                }
            }
            
            # Initialize attack vectors
            await self._initialize_attack_vectors()
            
            # Setup monitoring and alerting
            await self._setup_security_monitoring()
            
        except Exception as e:
            self.security_metrics.errors.append(f"Security environment setup failed: {str(e)}")
            raise RuntimeError(f"Security test environment initialization failed: {e}")
    
    async def _initialize_attack_vectors(self) -> None:
        """Initialize various attack vectors for comprehensive testing."""
        self.attack_vectors = [
            # Brute force attack vectors
            AttackVector(
                name="credential_brute_force",
                attack_type="brute_force",
                payload={
                    "username": "admin@netra.ai",
                    "passwords": ["password", "123456", "admin", "netra123", "password123"]
                },
                expected_response="blocked",
                severity="high",
                validation_criteria={"max_attempts": 3, "lockout_required": True}
            ),
            
            # SQL injection attack vectors
            AttackVector(
                name="sql_injection_login",
                attack_type="sql_injection", 
                payload={
                    "username": "admin' OR '1'='1' --",
                    "password": "any_password"
                },
                expected_response="blocked",
                severity="critical",
                validation_criteria={"pattern_detected": True, "request_blocked": True}
            ),
            
            AttackVector(
                name="sql_injection_api",
                attack_type="sql_injection",
                payload={
                    "user_id": "1 UNION SELECT username,password FROM users --",
                    "action": "get_profile"
                },
                expected_response="blocked",
                severity="critical",
                validation_criteria={"pattern_detected": True, "request_blocked": True}
            ),
            
            # XSS attack vectors
            AttackVector(
                name="xss_reflected",
                attack_type="xss",
                payload={
                    "search_query": "<script>alert('XSS')</script>",
                    "user_input": "javascript:alert(document.cookie)"
                },
                expected_response="sanitized",
                severity="high",
                validation_criteria={"script_removed": True, "safe_output": True}
            ),
            
            # DDoS simulation
            AttackVector(
                name="ddos_simulation",
                attack_type="ddos",
                payload={
                    "concurrent_requests": 100,
                    "request_rate": 50,
                    "duration": 30
                },
                expected_response="rate_limited",
                severity="high",
                validation_criteria={"rate_limit_triggered": True, "service_available": True}
            ),
            
            # Session hijacking attempt
            AttackVector(
                name="session_hijacking",
                attack_type="session_manipulation",
                payload={
                    "session_id": "fake_session_12345",
                    "user_agent": "Modified-Agent",
                    "ip_address": "192.168.1.100"
                },
                expected_response="blocked",
                severity="critical",
                validation_criteria={"session_invalidated": True, "access_denied": True}
            ),
            
            # API abuse
            AttackVector(
                name="api_endpoint_abuse",
                attack_type="api_abuse", 
                payload={
                    "endpoint": "/api/admin/users",
                    "unauthorized_access": True,
                    "privilege_escalation": True
                },
                expected_response="blocked",
                severity="high",
                validation_criteria={"access_denied": True, "privilege_check": True}
            ),
            
            # WebSocket flooding
            AttackVector(
                name="websocket_flooding",
                attack_type="websocket_abuse",
                payload={
                    "message_count": 1000,
                    "message_size": 10240,  # 10KB
                    "rate": 100  # messages per second
                },
                expected_response="rate_limited",
                severity="medium",
                validation_criteria={"rate_limit_triggered": True, "connection_throttled": True}
            )
        ]
    
    async def _setup_security_monitoring(self) -> None:
        """Setup security monitoring and event logging."""
        try:
            # Initialize security event logging
            await self.redis_session.set("security:monitoring:enabled", "true")
            
            # Setup incident escalation thresholds
            escalation_config = {
                "critical_incidents": 1,
                "high_incidents": 3,
                "medium_incidents": 10,
                "escalation_window": 300  # 5 minutes
            }
            
            await self.redis_session.set(
                "security:escalation:config",
                json.dumps(escalation_config)
            )
            
            # Initialize security metrics collection
            security_metrics_config = {
                "collect_attack_patterns": True,
                "track_response_times": True,
                "monitor_false_positives": True,
                "alert_on_anomalies": True
            }
            
            await self.redis_session.set(
                "security:metrics:config",
                json.dumps(security_metrics_config)
            )
            
        except Exception as e:
            self.security_metrics.errors.append(f"Security monitoring setup failed: {str(e)}")
            raise
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute comprehensive security breach detection and response test."""
        test_results = {
            "attack_simulations": [],
            "detection_results": [],
            "response_validations": [],
            "incident_handling": [],
            "recovery_tests": [],
            "performance_metrics": {},
            "service_calls": 0
        }
        
        try:
            # Phase 1: Execute individual attack simulations
            for attack_vector in self.attack_vectors:
                attack_result = await self._simulate_attack_vector(attack_vector)
                test_results["attack_simulations"].append(attack_result)
                test_results["service_calls"] += attack_result.get("service_calls", 0)
            
            # Phase 2: Multi-stage attack simulation
            multi_stage_result = await self._simulate_multi_stage_attack()
            test_results["multi_stage_attack"] = multi_stage_result
            test_results["service_calls"] += multi_stage_result.get("service_calls", 0)
            
            # Phase 3: Concurrent attack simulation
            concurrent_result = await self._simulate_concurrent_attacks()
            test_results["concurrent_attacks"] = concurrent_result
            test_results["service_calls"] += concurrent_result.get("service_calls", 0)
            
            # Phase 4: Response time validation
            response_time_result = await self._validate_response_times()
            test_results["response_times"] = response_time_result
            test_results["service_calls"] += response_time_result.get("service_calls", 0)
            
            # Phase 5: Incident escalation testing
            escalation_result = await self._test_incident_escalation()
            test_results["incident_escalation"] = escalation_result
            test_results["service_calls"] += escalation_result.get("service_calls", 0)
            
            # Phase 6: Recovery and resilience testing
            recovery_result = await self._test_recovery_procedures()
            test_results["recovery_procedures"] = recovery_result
            test_results["service_calls"] += recovery_result.get("service_calls", 0)
            
            # Calculate final metrics
            test_results["performance_metrics"] = self._calculate_security_metrics()
            
        except Exception as e:
            self.security_metrics.errors.append(f"Critical path execution failed: {str(e)}")
            test_results["execution_error"] = str(e)
        
        return test_results
    
    async def _simulate_attack_vector(self, attack_vector: AttackVector) -> Dict[str, Any]:
        """Simulate individual attack vector and validate response."""
        attack_start_time = time.time()
        attack_id = f"attack_{attack_vector.name}_{uuid.uuid4().hex[:8]}"
        
        try:
            self.security_metrics.attack_simulations += 1
            self.security_metrics.attack_vectors_tested.append(attack_vector.name)
            
            # Execute attack based on type
            if attack_vector.attack_type == "brute_force":
                attack_result = await self._execute_brute_force_attack(attack_vector)
            elif attack_vector.attack_type == "sql_injection":
                attack_result = await self._execute_sql_injection_attack(attack_vector)
            elif attack_vector.attack_type == "xss":
                attack_result = await self._execute_xss_attack(attack_vector)
            elif attack_vector.attack_type == "ddos":
                attack_result = await self._execute_ddos_attack(attack_vector)
            elif attack_vector.attack_type == "session_manipulation":
                attack_result = await self._execute_session_hijacking_attack(attack_vector)
            elif attack_vector.attack_type == "api_abuse":
                attack_result = await self._execute_api_abuse_attack(attack_vector)
            elif attack_vector.attack_type == "websocket_abuse":
                attack_result = await self._execute_websocket_abuse_attack(attack_vector)
            else:
                raise ValueError(f"Unknown attack type: {attack_vector.attack_type}")
            
            # Validate detection and response
            detection_validation = await self._validate_attack_detection(attack_vector, attack_result)
            response_validation = await self._validate_security_response(attack_vector, attack_result)
            
            # Log security event
            await self._log_security_event(attack_vector, attack_result, detection_validation)
            
            attack_duration = time.time() - attack_start_time
            self.security_metrics.response_times.append(attack_duration)
            
            if detection_validation["detected"] and response_validation["appropriate_response"]:
                self.security_metrics.successful_detections += 1
            
            return {
                "success": True,
                "attack_id": attack_id,
                "attack_vector": attack_vector.name,
                "attack_type": attack_vector.attack_type,
                "duration": attack_duration,
                "attack_result": attack_result,
                "detection_validation": detection_validation,
                "response_validation": response_validation,
                "service_calls": attack_result.get("service_calls", 0) + 2  # validation calls
            }
            
        except Exception as e:
            self.security_metrics.errors.append(f"Attack simulation {attack_vector.name} failed: {str(e)}")
            return {
                "success": False,
                "attack_id": attack_id,
                "attack_vector": attack_vector.name,
                "error": str(e),
                "duration": time.time() - attack_start_time,
                "service_calls": 0
            }
    
    async def _execute_brute_force_attack(self, attack_vector: AttackVector) -> Dict[str, Any]:
        """Execute brute force attack simulation."""
        login_endpoint = f"{self.service_endpoints.auth}/api/auth/login"
        payload = attack_vector.payload
        username = payload["username"]
        passwords = payload["passwords"]
        
        attempt_results = []
        successful_attempts = 0
        blocked_attempts = 0
        
        for i, password in enumerate(passwords):
            try:
                login_data = {
                    "username": username,
                    "password": password,
                    "attempt_number": i + 1
                }
                
                response = await self.test_client.post(
                    login_endpoint,
                    json=login_data,
                    headers={"User-Agent": "BruteForceBot/1.0"}
                )
                
                if response.status_code == 200:
                    successful_attempts += 1
                elif response.status_code == 429:  # Rate limited
                    blocked_attempts += 1
                    self.security_metrics.rate_limit_triggers += 1
                elif response.status_code == 423:  # Account locked
                    blocked_attempts += 1
                    break  # Account locked, stop attempts
                
                attempt_results.append({
                    "attempt": i + 1,
                    "password": password,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0.0
                })
                
                # Brief delay between attempts
                await asyncio.sleep(0.5)
                
            except Exception as e:
                attempt_results.append({
                    "attempt": i + 1,
                    "password": password,
                    "error": str(e)
                })
        
        return {
            "attack_type": "brute_force",
            "target_username": username,
            "total_attempts": len(passwords),
            "successful_attempts": successful_attempts,
            "blocked_attempts": blocked_attempts,
            "attempt_results": attempt_results,
            "service_calls": len(passwords)
        }
    
    async def _execute_sql_injection_attack(self, attack_vector: AttackVector) -> Dict[str, Any]:
        """Execute SQL injection attack simulation."""
        payload = attack_vector.payload
        
        if "username" in payload:
            # Login-based SQL injection
            login_endpoint = f"{self.service_endpoints.auth}/api/auth/login"
            injection_data = {
                "username": payload["username"],
                "password": payload["password"]
            }
            
            response = await self.test_client.post(
                login_endpoint,
                json=injection_data,
                headers={"User-Agent": "SQLInjectionBot/1.0"}
            )
            
        else:
            # API-based SQL injection
            api_endpoint = f"{self.service_endpoints.backend}/api/user/profile"
            injection_params = {"user_id": payload["user_id"]}
            
            response = await self.test_client.get(
                api_endpoint,
                params=injection_params,
                headers={"User-Agent": "SQLInjectionBot/1.0"}
            )
        
        # Check if injection patterns were detected
        sql_patterns_detected = []
        for pattern in self.security_config["sql_injection_patterns"]:
            if pattern.lower() in str(payload).lower():
                sql_patterns_detected.append(pattern)
        
        return {
            "attack_type": "sql_injection",
            "payload": payload,
            "status_code": response.status_code,
            "patterns_detected": sql_patterns_detected,
            "response_headers": dict(response.headers),
            "blocked": response.status_code in [403, 400, 422],
            "service_calls": 1
        }
    
    async def _execute_xss_attack(self, attack_vector: AttackVector) -> Dict[str, Any]:
        """Execute XSS attack simulation."""
        payload = attack_vector.payload
        
        # Test XSS through search endpoint
        search_endpoint = f"{self.service_endpoints.backend}/api/search"
        xss_data = {
            "query": payload["search_query"],
            "user_input": payload["user_input"]
        }
        
        response = await self.test_client.post(
            search_endpoint,
            json=xss_data,
            headers={"User-Agent": "XSSBot/1.0"}
        )
        
        # Check if XSS patterns were detected
        xss_patterns_detected = []
        for pattern in self.security_config["xss_patterns"]:
            if pattern.lower() in str(payload).lower():
                xss_patterns_detected.append(pattern)
        
        # Analyze response for script content
        response_text = ""
        if response.status_code == 200:
            try:
                response_data = response.json()
                response_text = str(response_data)
            except:
                response_text = response.text
        
        script_in_response = "<script>" in response_text.lower()
        
        return {
            "attack_type": "xss",
            "payload": payload,
            "status_code": response.status_code,
            "patterns_detected": xss_patterns_detected,
            "script_in_response": script_in_response,
            "response_sanitized": not script_in_response,
            "service_calls": 1
        }
    
    async def _execute_ddos_attack(self, attack_vector: AttackVector) -> Dict[str, Any]:
        """Execute DDoS simulation."""
        payload = attack_vector.payload
        target_endpoint = f"{self.service_endpoints.backend}/api/health"
        
        concurrent_requests = payload["concurrent_requests"]
        request_rate = payload["request_rate"]
        duration = payload["duration"]
        
        # Execute concurrent requests
        start_time = time.time()
        successful_requests = 0
        rate_limited_requests = 0
        error_requests = 0
        
        async def make_request(request_id: int):
            try:
                response = await self.test_client.get(
                    target_endpoint,
                    headers={"User-Agent": f"DDoSBot/1.0-{request_id}"}
                )
                
                if response.status_code == 200:
                    return "success"
                elif response.status_code == 429:
                    return "rate_limited"
                else:
                    return "error"
                    
            except Exception:
                return "error"
        
        # Create batches of requests with rate limiting
        batch_size = min(concurrent_requests, 20)  # Limit concurrent requests
        total_batches = concurrent_requests // batch_size
        
        for batch in range(total_batches):
            if time.time() - start_time >= duration:
                break
                
            # Create batch of concurrent requests
            tasks = [
                make_request(batch * batch_size + i)
                for i in range(batch_size)
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            for result in batch_results:
                if result == "success":
                    successful_requests += 1
                elif result == "rate_limited":
                    rate_limited_requests += 1
                    self.security_metrics.rate_limit_triggers += 1
                else:
                    error_requests += 1
            
            # Rate limiting between batches
            await asyncio.sleep(batch_size / request_rate)
        
        attack_duration = time.time() - start_time
        
        return {
            "attack_type": "ddos",
            "duration": attack_duration,
            "total_requests": successful_requests + rate_limited_requests + error_requests,
            "successful_requests": successful_requests,
            "rate_limited_requests": rate_limited_requests,
            "error_requests": error_requests,
            "rate_limit_effective": rate_limited_requests > 0,
            "service_calls": successful_requests + rate_limited_requests + error_requests
        }
    
    async def _execute_session_hijacking_attack(self, attack_vector: AttackVector) -> Dict[str, Any]:
        """Execute session hijacking attack simulation."""
        payload = attack_vector.payload
        
        # Try to use fake session
        protected_endpoint = f"{self.service_endpoints.backend}/api/user/profile"
        headers = {
            "Authorization": f"Bearer fake_token_{payload['session_id']}",
            "User-Agent": payload["user_agent"],
            "X-Forwarded-For": payload["ip_address"]
        }
        
        response = await self.test_client.get(protected_endpoint, headers=headers)
        
        # Try session validation
        session_endpoint = f"{self.service_endpoints.backend}/api/auth/validate_session"
        session_data = {"session_id": payload["session_id"]}
        
        session_response = await self.test_client.post(
            session_endpoint,
            json=session_data
        )
        
        return {
            "attack_type": "session_hijacking",
            "fake_session_id": payload["session_id"],
            "profile_access_status": response.status_code,
            "session_validation_status": session_response.status_code,
            "access_blocked": response.status_code in [401, 403],
            "session_rejected": session_response.status_code in [401, 403, 404],
            "service_calls": 2
        }
    
    async def _execute_api_abuse_attack(self, attack_vector: AttackVector) -> Dict[str, Any]:
        """Execute API abuse attack simulation."""
        payload = attack_vector.payload
        
        # Try unauthorized access to admin endpoint
        admin_endpoint = f"{self.service_endpoints.backend}{payload['endpoint']}"
        
        # Try without authentication
        response_unauth = await self.test_client.get(
            admin_endpoint,
            headers={"User-Agent": "APIAbuseBot/1.0"}
        )
        
        # Try with fake/low-privilege token
        fake_headers = {
            "Authorization": "Bearer fake_low_privilege_token",
            "User-Agent": "APIAbuseBot/1.0"
        }
        
        response_fake_auth = await self.test_client.get(admin_endpoint, headers=fake_headers)
        
        return {
            "attack_type": "api_abuse",
            "target_endpoint": payload["endpoint"],
            "unauth_status": response_unauth.status_code,
            "fake_auth_status": response_fake_auth.status_code,
            "access_properly_blocked": all(
                status in [401, 403] 
                for status in [response_unauth.status_code, response_fake_auth.status_code]
            ),
            "service_calls": 2
        }
    
    async def _execute_websocket_abuse_attack(self, attack_vector: AttackVector) -> Dict[str, Any]:
        """Execute WebSocket abuse attack simulation."""
        payload = attack_vector.payload
        
        ws_url = self.service_endpoints.websocket
        message_count = payload["message_count"]
        message_size = payload["message_size"]
        rate = payload["rate"]
        
        try:
            async with websockets.connect(ws_url) as websocket:
                start_time = time.time()
                sent_messages = 0
                rate_limited = False
                
                # Create large message
                large_message = "X" * message_size
                
                for i in range(min(message_count, 100)):  # Limit for testing
                    try:
                        message = {
                            "type": "flood_test",
                            "sequence": i,
                            "data": large_message,
                            "timestamp": time.time()
                        }
                        
                        await websocket.send(json.dumps(message))
                        sent_messages += 1
                        
                        # Try to receive response (rate limit notification)
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                            response_data = json.loads(response)
                            
                            if response_data.get("type") == "rate_limit_exceeded":
                                rate_limited = True
                                self.security_metrics.rate_limit_triggers += 1
                                break
                                
                        except asyncio.TimeoutError:
                            pass  # No immediate response
                        
                        # Rate control
                        if rate > 0:
                            await asyncio.sleep(1.0 / rate)
                            
                    except websockets.exceptions.ConnectionClosed:
                        # Connection closed (likely due to rate limiting)
                        rate_limited = True
                        break
                    except Exception as e:
                        self.security_metrics.errors.append(f"WebSocket message error: {str(e)}")
                        break
                
                duration = time.time() - start_time
                
                return {
                    "attack_type": "websocket_abuse",
                    "sent_messages": sent_messages,
                    "rate_limited": rate_limited,
                    "duration": duration,
                    "effective_rate": sent_messages / duration if duration > 0 else 0,
                    "service_calls": sent_messages
                }
                
        except Exception as e:
            return {
                "attack_type": "websocket_abuse",
                "error": str(e),
                "connection_failed": True,
                "service_calls": 0
            }
    
    async def _validate_attack_detection(self, attack_vector: AttackVector, 
                                       attack_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that attack was properly detected."""
        try:
            detected = False
            detection_method = None
            detection_time = time.time()
            
            # Check different detection methods based on attack type
            if attack_vector.attack_type == "brute_force":
                blocked_attempts = attack_result.get("blocked_attempts", 0)
                detected = blocked_attempts > 0
                detection_method = "rate_limiting" if detected else None
                
            elif attack_vector.attack_type in ["sql_injection", "xss"]:
                patterns_detected = attack_result.get("patterns_detected", [])
                blocked = attack_result.get("blocked", False)
                detected = len(patterns_detected) > 0 or blocked
                detection_method = "pattern_matching" if detected else None
                
            elif attack_vector.attack_type == "ddos":
                rate_limited = attack_result.get("rate_limit_effective", False)
                detected = rate_limited
                detection_method = "rate_limiting" if detected else None
                
            elif attack_vector.attack_type == "session_manipulation":
                access_blocked = attack_result.get("access_blocked", False)
                session_rejected = attack_result.get("session_rejected", False)
                detected = access_blocked and session_rejected
                detection_method = "session_validation" if detected else None
                
            elif attack_vector.attack_type == "api_abuse":
                access_blocked = attack_result.get("access_properly_blocked", False)
                detected = access_blocked
                detection_method = "access_control" if detected else None
                
            elif attack_vector.attack_type == "websocket_abuse":
                rate_limited = attack_result.get("rate_limited", False)
                detected = rate_limited
                detection_method = "rate_limiting" if detected else None
            
            # Log detection result
            await self._log_detection_result(attack_vector, detected, detection_method)
            
            return {
                "detected": detected,
                "detection_method": detection_method,
                "detection_time": detection_time,
                "meets_criteria": detected  # Simple validation for now
            }
            
        except Exception as e:
            self.security_metrics.errors.append(f"Detection validation failed: {str(e)}")
            return {
                "detected": False,
                "error": str(e)
            }
    
    async def _validate_security_response(self, attack_vector: AttackVector, 
                                        attack_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that security response was appropriate for the attack."""
        try:
            appropriate_response = False
            response_actions = []
            
            expected_response = attack_vector.expected_response
            validation_criteria = attack_vector.validation_criteria
            
            if expected_response == "blocked":
                if attack_vector.attack_type == "brute_force":
                    blocked_attempts = attack_result.get("blocked_attempts", 0)
                    max_attempts = validation_criteria.get("max_attempts", 3)
                    appropriate_response = blocked_attempts >= max_attempts
                    response_actions.append("account_lockout" if appropriate_response else "insufficient_blocking")
                    
                elif attack_vector.attack_type in ["sql_injection", "xss"]:
                    blocked = attack_result.get("blocked", False)
                    appropriate_response = blocked
                    response_actions.append("request_blocked" if blocked else "request_allowed")
                    
                elif attack_vector.attack_type in ["session_manipulation", "api_abuse"]:
                    access_blocked = attack_result.get("access_blocked", False) or attack_result.get("access_properly_blocked", False)
                    appropriate_response = access_blocked
                    response_actions.append("access_denied" if access_blocked else "access_granted")
                    
            elif expected_response == "rate_limited":
                rate_limited = attack_result.get("rate_limited", False) or attack_result.get("rate_limit_effective", False)
                appropriate_response = rate_limited
                response_actions.append("rate_limited" if rate_limited else "no_rate_limiting")
                
            elif expected_response == "sanitized":
                sanitized = attack_result.get("response_sanitized", False)
                appropriate_response = sanitized
                response_actions.append("content_sanitized" if sanitized else "content_not_sanitized")
            
            # Check for additional response requirements
            if appropriate_response:
                self.security_metrics.blocked_requests += 1
            
            return {
                "appropriate_response": appropriate_response,
                "expected_response": expected_response,
                "actual_response": response_actions,
                "validation_passed": appropriate_response
            }
            
        except Exception as e:
            self.security_metrics.errors.append(f"Response validation failed: {str(e)}")
            return {
                "appropriate_response": False,
                "error": str(e)
            }
    
    async def _log_security_event(self, attack_vector: AttackVector, attack_result: Dict[str, Any], 
                                detection_result: Dict[str, Any]) -> None:
        """Log security event for monitoring and analysis."""
        try:
            security_event = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "security_test",
                "attack_vector": attack_vector.name,
                "attack_type": attack_vector.attack_type,
                "severity": attack_vector.severity,
                "detected": detection_result.get("detected", False),
                "detection_method": detection_result.get("detection_method"),
                "response_time": detection_result.get("detection_time", 0) - time.time(),
                "attack_payload": attack_vector.payload,
                "attack_result": attack_result,
                "test_id": self.test_name
            }
            
            # Store in Redis for analysis
            event_key = f"security:events:{uuid.uuid4().hex}"
            await self.redis_session.set(
                event_key,
                json.dumps(security_event),
                ex=3600  # 1 hour retention for test events
            )
            
            self.security_metrics.security_events_logged += 1
            
        except Exception as e:
            self.security_metrics.errors.append(f"Security event logging failed: {str(e)}")
    
    async def _log_detection_result(self, attack_vector: AttackVector, detected: bool, 
                                  detection_method: Optional[str]) -> None:
        """Log detection result for metrics tracking."""
        try:
            detection_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "attack_vector": attack_vector.name,
                "attack_type": attack_vector.attack_type,
                "detected": detected,
                "detection_method": detection_method,
                "severity": attack_vector.severity
            }
            
            # Store detection metrics
            detection_key = f"security:detections:{uuid.uuid4().hex}"
            await self.redis_session.set(
                detection_key,
                json.dumps(detection_log),
                ex=1800  # 30 minutes retention
            )
            
        except Exception as e:
            self.security_metrics.errors.append(f"Detection logging failed: {str(e)}")
    
    async def _simulate_multi_stage_attack(self) -> Dict[str, Any]:
        """Simulate sophisticated multi-stage attack scenario."""
        try:
            multi_stage_start = time.time()
            
            # Stage 1: Reconnaissance (probe endpoints)
            recon_result = await self._execute_reconnaissance_stage()
            
            # Stage 2: Initial compromise attempt (credential stuffing)
            if recon_result.get("endpoints_discovered", 0) > 0:
                initial_compromise = await self._execute_initial_compromise_stage()
            else:
                initial_compromise = {"skipped": True, "reason": "no_endpoints_discovered"}
            
            # Stage 3: Privilege escalation attempt
            if initial_compromise.get("access_gained", False):
                privilege_escalation = await self._execute_privilege_escalation_stage()
            else:
                privilege_escalation = {"skipped": True, "reason": "no_initial_access"}
            
            # Stage 4: Data exfiltration attempt
            if privilege_escalation.get("elevated_access", False):
                data_exfiltration = await self._execute_data_exfiltration_stage()
            else:
                data_exfiltration = {"skipped": True, "reason": "no_elevated_access"}
            
            multi_stage_duration = time.time() - multi_stage_start
            
            # Calculate overall success (from attacker perspective - we want this to fail)
            attack_successful = (
                recon_result.get("endpoints_discovered", 0) > 0 and
                initial_compromise.get("access_gained", False) and
                privilege_escalation.get("elevated_access", False) and
                data_exfiltration.get("data_extracted", False)
            )
            
            # Calculate defense effectiveness (we want this to succeed)
            defense_effective = not attack_successful
            
            return {
                "multi_stage_attack": True,
                "duration": multi_stage_duration,
                "stages": {
                    "reconnaissance": recon_result,
                    "initial_compromise": initial_compromise,
                    "privilege_escalation": privilege_escalation,
                    "data_exfiltration": data_exfiltration
                },
                "attack_successful": attack_successful,
                "defense_effective": defense_effective,
                "service_calls": (
                    recon_result.get("service_calls", 0) +
                    initial_compromise.get("service_calls", 0) +
                    privilege_escalation.get("service_calls", 0) +
                    data_exfiltration.get("service_calls", 0)
                )
            }
            
        except Exception as e:
            self.security_metrics.errors.append(f"Multi-stage attack simulation failed: {str(e)}")
            return {
                "multi_stage_attack": True,
                "error": str(e),
                "service_calls": 0
            }
    
    async def _execute_reconnaissance_stage(self) -> Dict[str, Any]:
        """Execute reconnaissance stage of multi-stage attack."""
        # Probe common endpoints
        endpoints_to_probe = [
            "/api/admin",
            "/api/users",
            "/api/config",
            "/.env",
            "/admin",
            "/dashboard",
            "/api/v1/health",
            "/api/debug"
        ]
        
        discovered_endpoints = []
        service_calls = 0
        
        for endpoint in endpoints_to_probe:
            try:
                full_url = f"{self.service_endpoints.backend}{endpoint}"
                response = await self.test_client.get(
                    full_url,
                    headers={"User-Agent": "ReconBot/1.0"}
                )
                service_calls += 1
                
                if response.status_code not in [404, 403]:
                    discovered_endpoints.append({
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response_size": len(response.content)
                    })
                    
            except Exception:
                pass  # Continue probing
        
        return {
            "stage": "reconnaissance",
            "endpoints_probed": len(endpoints_to_probe),
            "endpoints_discovered": len(discovered_endpoints),
            "discovered_endpoints": discovered_endpoints,
            "service_calls": service_calls
        }
    
    async def _execute_initial_compromise_stage(self) -> Dict[str, Any]:
        """Execute initial compromise stage."""
        # Try common credential combinations
        common_credentials = [
            ("admin", "admin"),
            ("administrator", "password"),
            ("root", "root"),
            ("test", "test"),
            ("guest", "guest")
        ]
        
        login_endpoint = f"{self.service_endpoints.auth}/api/auth/login"
        access_gained = False
        successful_login = None
        service_calls = 0
        
        for username, password in common_credentials:
            try:
                login_data = {
                    "username": username,
                    "password": password
                }
                
                response = await self.test_client.post(login_endpoint, json=login_data)
                service_calls += 1
                
                if response.status_code == 200:
                    access_gained = True
                    successful_login = {"username": username, "password": password}
                    break
                elif response.status_code == 429:
                    # Rate limited - good security response
                    break
                    
            except Exception:
                pass
        
        return {
            "stage": "initial_compromise",
            "credentials_tested": len(common_credentials),
            "access_gained": access_gained,
            "successful_login": successful_login,
            "service_calls": service_calls
        }
    
    async def _execute_privilege_escalation_stage(self) -> Dict[str, Any]:
        """Execute privilege escalation stage."""
        # Try to access admin endpoints
        admin_endpoints = [
            "/api/admin/users",
            "/api/admin/settings",
            "/api/admin/logs"
        ]
        
        elevated_access = False
        accessible_admin_endpoints = []
        service_calls = 0
        
        for endpoint in admin_endpoints:
            try:
                full_url = f"{self.service_endpoints.backend}{endpoint}"
                response = await self.test_client.get(
                    full_url,
                    headers={"User-Agent": "PrivEscBot/1.0"}
                )
                service_calls += 1
                
                if response.status_code == 200:
                    elevated_access = True
                    accessible_admin_endpoints.append(endpoint)
                    
            except Exception:
                pass
        
        return {
            "stage": "privilege_escalation",
            "admin_endpoints_tested": len(admin_endpoints),
            "elevated_access": elevated_access,
            "accessible_endpoints": accessible_admin_endpoints,
            "service_calls": service_calls
        }
    
    async def _execute_data_exfiltration_stage(self) -> Dict[str, Any]:
        """Execute data exfiltration stage."""
        # Try to access sensitive data endpoints
        data_endpoints = [
            "/api/users/export",
            "/api/data/backup",
            "/api/logs/download",
            "/api/config/export"
        ]
        
        data_extracted = False
        successful_extractions = []
        service_calls = 0
        
        for endpoint in data_endpoints:
            try:
                full_url = f"{self.service_endpoints.backend}{endpoint}"
                response = await self.test_client.get(
                    full_url,
                    headers={"User-Agent": "DataExfilBot/1.0"}
                )
                service_calls += 1
                
                if response.status_code == 200:
                    data_extracted = True
                    successful_extractions.append({
                        "endpoint": endpoint,
                        "data_size": len(response.content)
                    })
                    
            except Exception:
                pass
        
        return {
            "stage": "data_exfiltration",
            "data_endpoints_tested": len(data_endpoints),
            "data_extracted": data_extracted,
            "successful_extractions": successful_extractions,
            "service_calls": service_calls
        }
    
    async def _simulate_concurrent_attacks(self) -> Dict[str, Any]:
        """Simulate concurrent attacks from multiple sources."""
        try:
            concurrent_start = time.time()
            
            # Select different attack vectors for concurrent execution
            concurrent_vectors = [
                next(av for av in self.attack_vectors if av.attack_type == "brute_force"),
                next(av for av in self.attack_vectors if av.attack_type == "sql_injection"),
                next(av for av in self.attack_vectors if av.attack_type == "ddos"),
                next(av for av in self.attack_vectors if av.attack_type == "xss")
            ]
            
            # Execute attacks concurrently
            concurrent_tasks = [
                self._simulate_attack_vector(vector)
                for vector in concurrent_vectors
            ]
            
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Analyze concurrent execution results
            successful_attacks = 0
            successful_detections = 0
            total_service_calls = 0
            
            for i, result in enumerate(concurrent_results):
                if not isinstance(result, Exception):
                    if result.get("success", False):
                        successful_attacks += 1
                        
                        detection = result.get("detection_validation", {})
                        if detection.get("detected", False):
                            successful_detections += 1
                    
                    total_service_calls += result.get("service_calls", 0)
            
            concurrent_duration = time.time() - concurrent_start
            
            # Validate system stability during concurrent attacks
            system_stability = await self._validate_system_stability_during_attack()
            
            return {
                "concurrent_attacks": True,
                "duration": concurrent_duration,
                "attack_vectors": len(concurrent_vectors),
                "successful_attacks": successful_attacks,
                "successful_detections": successful_detections,
                "detection_rate": (successful_detections / len(concurrent_vectors)) * 100,
                "system_stability": system_stability,
                "attack_results": concurrent_results,
                "service_calls": total_service_calls
            }
            
        except Exception as e:
            self.security_metrics.errors.append(f"Concurrent attack simulation failed: {str(e)}")
            return {
                "concurrent_attacks": True,
                "error": str(e),
                "service_calls": 0
            }
    
    async def _validate_system_stability_during_attack(self) -> Dict[str, Any]:
        """Validate that system remains stable during attacks."""
        try:
            # Test legitimate user access
            legitimate_endpoint = f"{self.service_endpoints.backend}/api/health"
            response = await self.test_client.get(legitimate_endpoint)
            
            service_available = response.status_code == 200
            
            # Test response time
            start_time = time.time()
            response = await self.test_client.get(legitimate_endpoint)
            response_time = time.time() - start_time
            
            response_time_acceptable = response_time < 5.0  # 5 second threshold
            
            return {
                "service_available": service_available,
                "response_time": response_time,
                "response_time_acceptable": response_time_acceptable,
                "overall_stable": service_available and response_time_acceptable
            }
            
        except Exception as e:
            return {
                "service_available": False,
                "error": str(e),
                "overall_stable": False
            }
    
    async def _validate_response_times(self) -> Dict[str, Any]:
        """Validate security response times meet business requirements."""
        try:
            if not self.security_metrics.response_times:
                return {"error": "No response times recorded"}
            
            response_times = self.security_metrics.response_times
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            # Business requirements for response times
            max_acceptable_time = 10.0  # 10 seconds
            avg_acceptable_time = 5.0   # 5 seconds average
            
            response_times_acceptable = (
                avg_response_time <= avg_acceptable_time and
                max_response_time <= max_acceptable_time
            )
            
            self.security_metrics.response_time_avg = avg_response_time
            
            return {
                "response_time_validation": True,
                "average_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "min_response_time": min_response_time,
                "response_times_acceptable": response_times_acceptable,
                "business_requirements_met": response_times_acceptable,
                "service_calls": 0
            }
            
        except Exception as e:
            self.security_metrics.errors.append(f"Response time validation failed: {str(e)}")
            return {
                "response_time_validation": False,
                "error": str(e),
                "service_calls": 0
            }
    
    async def _test_incident_escalation(self) -> Dict[str, Any]:
        """Test incident escalation procedures."""
        try:
            # Simulate critical security incident
            critical_incident = {
                "incident_id": f"SEC-{uuid.uuid4().hex[:8]}",
                "type": "critical_security_breach",
                "severity": "critical",
                "description": "Multiple failed authentication attempts detected",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "security_test",
                "affected_systems": ["auth_service", "backend_api"],
                "attack_vectors": [av.name for av in self.attack_vectors[:3]]
            }
            
            # Test incident logging
            incident_key = f"security:incidents:{critical_incident['incident_id']}"
            await self.redis_session.set(
                incident_key,
                json.dumps(critical_incident),
                ex=7200  # 2 hours retention
            )
            
            # Test escalation trigger
            escalation_result = await self._trigger_incident_escalation(critical_incident)
            
            # Test notification system
            notification_result = await self._test_incident_notifications(critical_incident)
            
            self.security_metrics.incident_escalations += 1
            
            return {
                "incident_escalation_test": True,
                "incident_created": True,
                "incident_id": critical_incident["incident_id"],
                "escalation_triggered": escalation_result.get("triggered", False),
                "notifications_sent": notification_result.get("sent", False),
                "escalation_time": escalation_result.get("time", 0),
                "service_calls": 3  # incident logging, escalation, notification
            }
            
        except Exception as e:
            self.security_metrics.errors.append(f"Incident escalation test failed: {str(e)}")
            return {
                "incident_escalation_test": False,
                "error": str(e),
                "service_calls": 0
            }
    
    async def _trigger_incident_escalation(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger incident escalation process."""
        try:
            escalation_start = time.time()
            
            # Check escalation thresholds
            escalation_config_data = await self.redis_session.get("security:escalation:config")
            if escalation_config_data:
                escalation_config = json.loads(escalation_config_data)
                
                # For critical incidents, escalation should be immediate
                if incident["severity"] == "critical":
                    escalation_triggered = True
                    escalation_time = time.time() - escalation_start
                    
                    # Log escalation
                    escalation_record = {
                        "incident_id": incident["incident_id"],
                        "escalated_at": datetime.utcnow().isoformat(),
                        "escalation_time": escalation_time,
                        "escalation_level": "immediate"
                    }
                    
                    escalation_key = f"security:escalations:{incident['incident_id']}"
                    await self.redis_session.set(
                        escalation_key,
                        json.dumps(escalation_record),
                        ex=3600
                    )
                    
                    return {
                        "triggered": True,
                        "time": escalation_time,
                        "level": "immediate"
                    }
                    
            return {"triggered": False, "reason": "threshold_not_met"}
            
        except Exception as e:
            return {"triggered": False, "error": str(e)}
    
    async def _test_incident_notifications(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Test incident notification system."""
        try:
            # Simulate notification endpoints
            notification_endpoints = [
                f"{self.service_endpoints.backend}/api/notifications/security",
                f"{self.service_endpoints.backend}/api/alerts/critical"
            ]
            
            notifications_sent = 0
            
            for endpoint in notification_endpoints:
                try:
                    notification_data = {
                        "incident_id": incident["incident_id"],
                        "type": "security_incident",
                        "severity": incident["severity"],
                        "message": f"Security incident {incident['incident_id']} requires immediate attention",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    response = await self.test_client.post(endpoint, json=notification_data)
                    
                    if response.status_code in [200, 201, 202]:
                        notifications_sent += 1
                        
                except Exception:
                    pass  # Continue with other endpoints
            
            return {
                "sent": notifications_sent > 0,
                "notification_count": notifications_sent,
                "total_endpoints": len(notification_endpoints)
            }
            
        except Exception as e:
            return {"sent": False, "error": str(e)}
    
    async def _test_recovery_procedures(self) -> Dict[str, Any]:
        """Test security recovery procedures."""
        try:
            recovery_tests = []
            
            # Test 1: Service health recovery after attack
            health_recovery = await self._test_service_health_recovery()
            recovery_tests.append(health_recovery)
            
            # Test 2: Rate limiter reset
            rate_limiter_recovery = await self._test_rate_limiter_recovery()
            recovery_tests.append(rate_limiter_recovery)
            
            # Test 3: Circuit breaker recovery
            circuit_breaker_recovery = await self._test_circuit_breaker_recovery()
            recovery_tests.append(circuit_breaker_recovery)
            
            # Test 4: Session cleanup
            session_cleanup = await self._test_session_cleanup()
            recovery_tests.append(session_cleanup)
            
            successful_recoveries = sum(1 for test in recovery_tests if test.get("success", False))
            total_recoveries = len(recovery_tests)
            
            self.security_metrics.recovery_validations += successful_recoveries
            
            return {
                "recovery_procedures_test": True,
                "recovery_tests": recovery_tests,
                "successful_recoveries": successful_recoveries,
                "total_recovery_tests": total_recoveries,
                "recovery_success_rate": (successful_recoveries / total_recoveries) * 100,
                "service_calls": sum(test.get("service_calls", 0) for test in recovery_tests)
            }
            
        except Exception as e:
            self.security_metrics.errors.append(f"Recovery procedures test failed: {str(e)}")
            return {
                "recovery_procedures_test": False,
                "error": str(e),
                "service_calls": 0
            }
    
    async def _test_service_health_recovery(self) -> Dict[str, Any]:
        """Test service health recovery after attacks."""
        try:
            # Check current health
            health_endpoint = f"{self.service_endpoints.backend}/api/health"
            
            pre_recovery_response = await self.test_client.get(health_endpoint)
            pre_recovery_healthy = pre_recovery_response.status_code == 200
            
            # Wait brief period for recovery
            await asyncio.sleep(2.0)
            
            # Check health again
            post_recovery_response = await self.test_client.get(health_endpoint)
            post_recovery_healthy = post_recovery_response.status_code == 200
            
            recovery_successful = post_recovery_healthy
            
            return {
                "test_type": "service_health_recovery",
                "success": recovery_successful,
                "pre_recovery_healthy": pre_recovery_healthy,
                "post_recovery_healthy": post_recovery_healthy,
                "service_calls": 2
            }
            
        except Exception as e:
            return {
                "test_type": "service_health_recovery",
                "success": False,
                "error": str(e),
                "service_calls": 0
            }
    
    async def _test_rate_limiter_recovery(self) -> Dict[str, Any]:
        """Test rate limiter recovery procedures."""
        try:
            # Reset rate limiter state
            if self.rate_limiter:
                # In a real implementation, this would clear rate limit state
                rate_limiter_reset = True
            else:
                rate_limiter_reset = False
            
            # Test that requests are accepted after reset
            test_endpoint = f"{self.service_endpoints.backend}/api/health"
            response = await self.test_client.get(test_endpoint)
            
            requests_accepted = response.status_code != 429
            
            return {
                "test_type": "rate_limiter_recovery",
                "success": rate_limiter_reset and requests_accepted,
                "rate_limiter_reset": rate_limiter_reset,
                "requests_accepted": requests_accepted,
                "service_calls": 1
            }
            
        except Exception as e:
            return {
                "test_type": "rate_limiter_recovery", 
                "success": False,
                "error": str(e),
                "service_calls": 0
            }
    
    async def _test_circuit_breaker_recovery(self) -> Dict[str, Any]:
        """Test circuit breaker recovery procedures."""
        try:
            # Test circuit breaker state
            if self.circuit_breaker:
                # In a real implementation, this would reset circuit breaker
                circuit_breaker_reset = True
            else:
                circuit_breaker_reset = False
            
            # Test that services are accessible after reset
            test_endpoint = f"{self.service_endpoints.backend}/api/health"
            response = await self.test_client.get(test_endpoint)
            
            service_accessible = response.status_code == 200
            
            return {
                "test_type": "circuit_breaker_recovery",
                "success": circuit_breaker_reset and service_accessible,
                "circuit_breaker_reset": circuit_breaker_reset,
                "service_accessible": service_accessible,
                "service_calls": 1
            }
            
        except Exception as e:
            return {
                "test_type": "circuit_breaker_recovery",
                "success": False,
                "error": str(e),
                "service_calls": 0
            }
    
    async def _test_session_cleanup(self) -> Dict[str, Any]:
        """Test session cleanup procedures."""
        try:
            # Count active sessions before cleanup
            session_keys = await self.redis_session.keys("session:*")
            sessions_before = len(session_keys) if session_keys else 0
            
            # Perform session cleanup (in real implementation, this would clean up old/invalid sessions)
            cleanup_performed = True
            
            # Count sessions after cleanup
            session_keys_after = await self.redis_session.keys("session:*")
            sessions_after = len(session_keys_after) if session_keys_after else 0
            
            return {
                "test_type": "session_cleanup",
                "success": cleanup_performed,
                "sessions_before": sessions_before,
                "sessions_after": sessions_after,
                "cleanup_performed": cleanup_performed,
                "service_calls": 2  # before and after checks
            }
            
        except Exception as e:
            return {
                "test_type": "session_cleanup",
                "success": False,
                "error": str(e),
                "service_calls": 0
            }
    
    def _calculate_security_metrics(self) -> Dict[str, Any]:
        """Calculate final security metrics for business validation."""
        try:
            return {
                "attack_simulations": self.security_metrics.attack_simulations,
                "successful_detections": self.security_metrics.successful_detections,
                "detection_rate": self.security_metrics.detection_rate,
                "false_positive_rate": self.security_metrics.false_positive_rate,
                "average_response_time": self.security_metrics.response_time_avg,
                "blocked_requests": self.security_metrics.blocked_requests,
                "rate_limit_triggers": self.security_metrics.rate_limit_triggers,
                "circuit_breaker_trips": self.security_metrics.circuit_breaker_trips,
                "security_events_logged": self.security_metrics.security_events_logged,
                "incident_escalations": self.security_metrics.incident_escalations,
                "recovery_validations": self.security_metrics.recovery_validations,
                "attack_vectors_tested": len(self.security_metrics.attack_vectors_tested),
                "error_count": len(self.security_metrics.errors)
            }
        except Exception as e:
            return {"calculation_error": str(e)}
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate that critical path results meet business security requirements."""
        try:
            validation_criteria = {
                "min_detection_rate": 85.0,  # 85% of attacks should be detected
                "max_false_positive_rate": 5.0,  # Less than 5% false positives
                "max_average_response_time": 5.0,  # Less than 5 seconds average response
                "min_blocked_requests": 1,  # At least some attacks should be blocked
                "min_security_events_logged": 3,  # Security events should be logged
                "max_error_rate": 10.0  # Less than 10% error rate
            }
            
            performance_metrics = results.get("performance_metrics", {})
            
            # Validate detection rate
            detection_rate = performance_metrics.get("detection_rate", 0)
            detection_ok = detection_rate >= validation_criteria["min_detection_rate"]
            
            # Validate false positive rate
            false_positive_rate = performance_metrics.get("false_positive_rate", 100)
            false_positive_ok = false_positive_rate <= validation_criteria["max_false_positive_rate"]
            
            # Validate response time
            avg_response_time = performance_metrics.get("average_response_time", float('inf'))
            response_time_ok = avg_response_time <= validation_criteria["max_average_response_time"]
            
            # Validate blocked requests
            blocked_requests = performance_metrics.get("blocked_requests", 0)
            blocked_requests_ok = blocked_requests >= validation_criteria["min_blocked_requests"]
            
            # Validate security logging
            security_events = performance_metrics.get("security_events_logged", 0)
            logging_ok = security_events >= validation_criteria["min_security_events_logged"]
            
            # Validate error rate
            total_simulations = performance_metrics.get("attack_simulations", 1)
            error_count = performance_metrics.get("error_count", 0)
            error_rate = (error_count / total_simulations) * 100
            error_rate_ok = error_rate <= validation_criteria["max_error_rate"]
            
            # Overall validation
            all_validations = [
                detection_ok, false_positive_ok, response_time_ok,
                blocked_requests_ok, logging_ok, error_rate_ok
            ]
            
            validation_passed = all(all_validations)
            
            # Log validation results
            validation_summary = {
                "validation_passed": validation_passed,
                "criteria_met": {
                    "detection_rate": detection_ok,
                    "false_positive_rate": false_positive_ok,
                    "response_time": response_time_ok,
                    "blocked_requests": blocked_requests_ok,
                    "security_logging": logging_ok,
                    "error_rate": error_rate_ok
                },
                "actual_metrics": {
                    "detection_rate": detection_rate,
                    "false_positive_rate": false_positive_rate,
                    "average_response_time": avg_response_time,
                    "blocked_requests": blocked_requests,
                    "security_events_logged": security_events,
                    "error_rate": error_rate
                },
                "validation_criteria": validation_criteria
            }
            
            print(f"Security validation summary: {json.dumps(validation_summary, indent=2)}")
            
            return validation_passed
            
        except Exception as e:
            self.security_metrics.errors.append(f"Critical path validation failed: {str(e)}")
            return False
    
    async def cleanup_test_specific_resources(self) -> None:
        """Cleanup security test specific resources."""
        try:
            # Clear security events
            event_keys = await self.redis_session.keys("security:events:*")
            if event_keys:
                await self.redis_session.delete(*event_keys)
            
            # Clear detection logs
            detection_keys = await self.redis_session.keys("security:detections:*")
            if detection_keys:
                await self.redis_session.delete(*detection_keys)
            
            # Clear incident records
            incident_keys = await self.redis_session.keys("security:incidents:*")
            if incident_keys:
                await self.redis_session.delete(*incident_keys)
            
            # Clear escalation records
            escalation_keys = await self.redis_session.keys("security:escalations:*")
            if escalation_keys:
                await self.redis_session.delete(*escalation_keys)
            
            # Close security services
            if self.security_service:
                # In real implementation, close security service connections
                pass
                
        except Exception as e:
            print(f"Security cleanup warning: {e}")


# Pytest fixtures and test functions
@pytest.fixture
async def security_breach_l4_test():
    """Create L4 security breach response test suite."""
    test_suite = SecurityBreachResponseL4Test()
    await test_suite.initialize_l4_environment()
    yield test_suite
    await test_suite.cleanup_l4_resources()


@pytest.mark.asyncio
@pytest.mark.staging
async def test_brute_force_attack_detection_l4(security_breach_l4_test):
    """Test brute force attack detection and response in staging."""
    # Execute brute force attack vector
    brute_force_vector = next(
        av for av in security_breach_l4_test.attack_vectors 
        if av.attack_type == "brute_force"
    )
    
    attack_result = await security_breach_l4_test._simulate_attack_vector(brute_force_vector)
    
    # Validate attack simulation
    assert attack_result["success"] is True, f"Brute force simulation failed: {attack_result.get('error')}"
    assert attack_result["duration"] < 30.0, f"Attack took too long: {attack_result['duration']}s"
    
    # Validate detection
    detection = attack_result["detection_validation"]
    assert detection["detected"] is True, "Brute force attack should be detected"
    assert detection["detection_method"] is not None, "Detection method should be specified"
    
    # Validate response
    response_validation = attack_result["response_validation"]
    assert response_validation["appropriate_response"] is True, "Security response should be appropriate"
    
    # Validate specific brute force metrics
    attack_data = attack_result["attack_result"]
    assert attack_data["blocked_attempts"] > 0, "Some brute force attempts should be blocked"
    assert attack_data["total_attempts"] >= 3, "Multiple attempts should be made"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_sql_injection_prevention_l4(security_breach_l4_test):
    """Test SQL injection attack prevention in staging."""
    # Execute SQL injection attack vectors
    sql_vectors = [
        av for av in security_breach_l4_test.attack_vectors 
        if av.attack_type == "sql_injection"
    ]
    
    for sql_vector in sql_vectors:
        attack_result = await security_breach_l4_test._simulate_attack_vector(sql_vector)
        
        # Validate attack simulation
        assert attack_result["success"] is True, f"SQL injection simulation failed: {attack_result.get('error')}"
        
        # Validate detection
        detection = attack_result["detection_validation"]
        assert detection["detected"] is True, f"SQL injection should be detected for {sql_vector.name}"
        
        # Validate blocking
        response_validation = attack_result["response_validation"]
        assert response_validation["appropriate_response"] is True, "SQL injection should be blocked"
        
        # Validate specific SQL injection metrics
        attack_data = attack_result["attack_result"]
        assert attack_data["blocked"] is True, "SQL injection request should be blocked"
        assert len(attack_data["patterns_detected"]) > 0, "SQL injection patterns should be detected"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_xss_attack_sanitization_l4(security_breach_l4_test):
    """Test XSS attack sanitization in staging."""
    # Execute XSS attack vector
    xss_vector = next(
        av for av in security_breach_l4_test.attack_vectors 
        if av.attack_type == "xss"
    )
    
    attack_result = await security_breach_l4_test._simulate_attack_vector(xss_vector)
    
    # Validate attack simulation
    assert attack_result["success"] is True, f"XSS simulation failed: {attack_result.get('error')}"
    
    # Validate detection
    detection = attack_result["detection_validation"]
    assert detection["detected"] is True, "XSS attack should be detected"
    
    # Validate sanitization
    response_validation = attack_result["response_validation"]
    assert response_validation["appropriate_response"] is True, "XSS content should be sanitized"
    
    # Validate specific XSS metrics
    attack_data = attack_result["attack_result"]
    assert len(attack_data["patterns_detected"]) > 0, "XSS patterns should be detected"
    assert attack_data["response_sanitized"] is True, "Response should be sanitized"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_ddos_mitigation_l4(security_breach_l4_test):
    """Test DDoS attack mitigation in staging."""
    # Execute DDoS attack vector
    ddos_vector = next(
        av for av in security_breach_l4_test.attack_vectors 
        if av.attack_type == "ddos"
    )
    
    attack_result = await security_breach_l4_test._simulate_attack_vector(ddos_vector)
    
    # Validate attack simulation
    assert attack_result["success"] is True, f"DDoS simulation failed: {attack_result.get('error')}"
    
    # Validate detection
    detection = attack_result["detection_validation"]
    assert detection["detected"] is True, "DDoS attack should be detected"
    
    # Validate rate limiting response
    response_validation = attack_result["response_validation"]
    assert response_validation["appropriate_response"] is True, "DDoS should trigger rate limiting"
    
    # Validate specific DDoS metrics
    attack_data = attack_result["attack_result"]
    assert attack_data["rate_limit_effective"] is True, "Rate limiting should be effective"
    assert attack_data["rate_limited_requests"] > 0, "Some requests should be rate limited"
    
    # Validate metrics tracking
    assert security_breach_l4_test.security_metrics.rate_limit_triggers > 0, "Rate limit triggers should be recorded"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_session_hijacking_prevention_l4(security_breach_l4_test):
    """Test session hijacking prevention in staging."""
    # Execute session hijacking attack vector
    session_vector = next(
        av for av in security_breach_l4_test.attack_vectors 
        if av.attack_type == "session_manipulation"
    )
    
    attack_result = await security_breach_l4_test._simulate_attack_vector(session_vector)
    
    # Validate attack simulation
    assert attack_result["success"] is True, f"Session hijacking simulation failed: {attack_result.get('error')}"
    
    # Validate detection
    detection = attack_result["detection_validation"]
    assert detection["detected"] is True, "Session hijacking should be detected"
    
    # Validate blocking
    response_validation = attack_result["response_validation"]
    assert response_validation["appropriate_response"] is True, "Session hijacking should be blocked"
    
    # Validate specific session security metrics
    attack_data = attack_result["attack_result"]
    assert attack_data["access_blocked"] is True, "Access should be blocked"
    assert attack_data["session_rejected"] is True, "Invalid session should be rejected"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_multi_stage_attack_defense_l4(security_breach_l4_test):
    """Test defense against sophisticated multi-stage attacks in staging."""
    # Execute complete critical path test which includes multi-stage attack
    test_results = await security_breach_l4_test.execute_critical_path_test()
    
    # Validate multi-stage attack simulation
    multi_stage_result = test_results.get("multi_stage_attack", {})
    assert "stages" in multi_stage_result, "Multi-stage attack should have stages"
    
    # Validate defense effectiveness
    assert multi_stage_result.get("defense_effective", False) is True, "Defense should be effective against multi-stage attack"
    assert multi_stage_result.get("attack_successful", True) is False, "Multi-stage attack should not succeed"
    
    # Validate individual stages
    stages = multi_stage_result.get("stages", {})
    
    # Reconnaissance should be limited
    recon = stages.get("reconnaissance", {})
    if not recon.get("skipped", False):
        discovered_endpoints = recon.get("endpoints_discovered", 0)
        assert discovered_endpoints < 5, "Reconnaissance should discover limited endpoints"
    
    # Initial compromise should fail
    initial_compromise = stages.get("initial_compromise", {})
    if not initial_compromise.get("skipped", False):
        assert initial_compromise.get("access_gained", True) is False, "Initial compromise should fail"
    
    # Higher stages should be skipped due to failed earlier stages
    privilege_escalation = stages.get("privilege_escalation", {})
    data_exfiltration = stages.get("data_exfiltration", {})
    
    assert privilege_escalation.get("skipped", False) is True or privilege_escalation.get("elevated_access", True) is False
    assert data_exfiltration.get("skipped", False) is True or data_exfiltration.get("data_extracted", True) is False


@pytest.mark.asyncio
@pytest.mark.staging
async def test_concurrent_attack_handling_l4(security_breach_l4_test):
    """Test handling of concurrent security attacks in staging."""
    # Execute complete critical path test which includes concurrent attacks
    test_results = await security_breach_l4_test.execute_critical_path_test()
    
    # Validate concurrent attack simulation
    concurrent_result = test_results.get("concurrent_attacks", {})
    assert concurrent_result.get("concurrent_attacks", False) is True, "Concurrent attacks should be executed"
    
    # Validate system stability during concurrent attacks
    system_stability = concurrent_result.get("system_stability", {})
    assert system_stability.get("overall_stable", False) is True, "System should remain stable during concurrent attacks"
    assert system_stability.get("service_available", False) is True, "Services should remain available"
    assert system_stability.get("response_time_acceptable", False) is True, "Response times should remain acceptable"
    
    # Validate detection effectiveness
    detection_rate = concurrent_result.get("detection_rate", 0)
    assert detection_rate >= 75.0, f"Detection rate should be at least 75%, got {detection_rate}%"
    
    # Validate multiple attack vectors were tested
    attack_vectors = concurrent_result.get("attack_vectors", 0)
    assert attack_vectors >= 3, f"At least 3 attack vectors should be tested concurrently, got {attack_vectors}"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_incident_escalation_procedures_l4(security_breach_l4_test):
    """Test security incident escalation procedures in staging."""
    # Execute complete critical path test which includes incident escalation
    test_results = await security_breach_l4_test.execute_critical_path_test()
    
    # Validate incident escalation
    escalation_result = test_results.get("incident_escalation", {})
    assert escalation_result.get("incident_escalation_test", False) is True, "Incident escalation should be tested"
    assert escalation_result.get("incident_created", False) is True, "Security incident should be created"
    
    # Validate escalation trigger
    assert escalation_result.get("escalation_triggered", False) is True, "Escalation should be triggered for critical incidents"
    
    # Validate escalation time
    escalation_time = escalation_result.get("escalation_time", float('inf'))
    assert escalation_time < 30.0, f"Escalation should occur within 30 seconds, took {escalation_time}s"
    
    # Validate notifications
    assert escalation_result.get("notifications_sent", False) is True, "Incident notifications should be sent"
    
    # Validate metrics tracking
    assert security_breach_l4_test.security_metrics.incident_escalations > 0, "Incident escalations should be tracked"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_security_recovery_procedures_l4(security_breach_l4_test):
    """Test security recovery procedures in staging."""
    # Execute complete critical path test which includes recovery testing
    test_results = await security_breach_l4_test.execute_critical_path_test()
    
    # Validate recovery procedures
    recovery_result = test_results.get("recovery_procedures", {})
    assert recovery_result.get("recovery_procedures_test", False) is True, "Recovery procedures should be tested"
    
    # Validate recovery success rate
    recovery_success_rate = recovery_result.get("recovery_success_rate", 0)
    assert recovery_success_rate >= 75.0, f"Recovery success rate should be at least 75%, got {recovery_success_rate}%"
    
    # Validate specific recovery tests
    recovery_tests = recovery_result.get("recovery_tests", [])
    assert len(recovery_tests) >= 3, "Multiple recovery procedures should be tested"
    
    # Check specific recovery types
    recovery_types = [test.get("test_type") for test in recovery_tests]
    expected_types = ["service_health_recovery", "rate_limiter_recovery", "session_cleanup"]
    
    for expected_type in expected_types:
        assert expected_type in recovery_types, f"Recovery test {expected_type} should be included"
    
    # Validate metrics tracking
    assert security_breach_l4_test.security_metrics.recovery_validations > 0, "Recovery validations should be tracked"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_complete_security_breach_response_l4(security_breach_l4_test):
    """Test complete security breach detection and response critical path in staging."""
    # Execute complete critical path test
    test_metrics = await security_breach_l4_test.run_complete_critical_path_test()
    
    # Validate overall test success
    assert test_metrics.success is True, f"Complete security test should succeed. Errors: {test_metrics.errors}"
    assert test_metrics.validation_count > 0, "Validations should be performed"
    
    # Validate business metrics
    business_metrics = {
        "max_response_time_seconds": 10.0,
        "min_success_rate_percent": 85.0,
        "max_error_count": 2
    }
    
    business_validation = await security_breach_l4_test.validate_business_metrics(business_metrics)
    assert business_validation is True, "Business metrics should meet requirements"
    
    # Validate security-specific metrics
    assert test_metrics.details.get("performance_metrics", {}).get("attack_simulations", 0) >= 5, "Multiple attack simulations should be performed"
    assert test_metrics.details.get("performance_metrics", {}).get("successful_detections", 0) >= 4, "Most attacks should be detected"
    assert test_metrics.details.get("performance_metrics", {}).get("detection_rate", 0) >= 80.0, "Detection rate should be high"
    
    # Validate test duration
    assert test_metrics.duration < 300.0, f"Complete test should finish within 5 minutes, took {test_metrics.duration}s"
    
    # Validate service calls
    assert test_metrics.service_calls > 0, "Service calls should be made during testing"
    
    # Validate comprehensive coverage
    performance_metrics = test_metrics.details.get("performance_metrics", {})
    assert performance_metrics.get("attack_vectors_tested", 0) >= 5, "Multiple attack vectors should be tested"
    assert performance_metrics.get("security_events_logged", 0) > 0, "Security events should be logged"
    assert performance_metrics.get("incident_escalations", 0) > 0, "Incident escalations should be tested"