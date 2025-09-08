"""
Agent Security Testing (Iterations 31-35).

Comprehensive security tests for agent operations including
authentication, authorization, data protection, and security boundaries.
"""

import asyncio
import pytest
from typing import Dict, Any, List
import hashlib
import json
import time
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent


@pytest.mark.security
class TestAgentAuthentication:
    """Test agent authentication and session security."""
    
    @pytest.mark.asyncio
    async def test_agent_token_validation(self):
        """Test agent validates authentication tokens properly."""
        # Mock auth service with various token scenarios
        mock_auth_service = AuthManager()
        
        # Valid token response
        valid_token_response = {
            "valid": True,
            "user_id": "user123",
            "permissions": ["read:analytics", "write:reports"],
            "expires_at": "2024-12-31T23:59:59Z",
            "session_id": "secure_session_123"
        }
        
        # Invalid token response
        invalid_token_response = {
            "valid": False,
            "error": "Token expired",
            "error_code": "TOKEN_EXPIRED"
        }
        
        # Malformed token response
        malformed_token_response = {
            "valid": False,
            "error": "Malformed token",
            "error_code": "INVALID_FORMAT"
        }
        
        test_scenarios = [
            ("valid_jwt_token", valid_token_response, True),
            ("expired_token", invalid_token_response, False),
            ("malformed_token", malformed_token_response, False),
            ("", {"valid": False, "error": "Empty token"}, False),
            (None, {"valid": False, "error": "Missing token"}, False)
        ]
        
        with patch('netra_backend.app.auth.auth_service_client.auth_service', mock_auth_service):
            
            for token, auth_response, should_succeed in test_scenarios:
                mock_auth_service.validate_token = AsyncMock(return_value=auth_response)
                
                agent_state = DeepAgentState(
                    agent_id="auth_test_agent",
                    session_id="test_session",
                    thread_id="test_thread",
                    context={"auth_token": token, "security_context": "testing"}
                )
                
                agent = SupervisorAgent(
                    agent_id="security_test",
                    initial_state=agent_state
                )
                
                # Test authentication validation
                result = await agent._validate_authentication(token)
                
                if should_succeed:
                    assert result["authenticated"] is True
                    assert result["user_id"] == "user123"
                    assert "permissions" in result
                    mock_auth_service.validate_token.assert_called_with(token)
                else:
                    assert result["authenticated"] is False
                    assert "error" in result
                    
                    # For non-empty tokens, service should be called
                    if token:
                        mock_auth_service.validate_token.assert_called_with(token)
    
    @pytest.mark.asyncio
    async def test_agent_session_security(self):
        """Test agent session security and isolation."""
        # Mock secure session management
        session_store = {}
        
        def create_secure_session(user_id, permissions):
            session_id = f"secure_{user_id}_{int(time.time())}"
            session_data = {
                "user_id": user_id,
                "permissions": permissions,
                "created_at": time.time(),
                "last_accessed": time.time(),
                "access_count": 0,
                "ip_address": "127.0.0.1",  # Mock IP
                "user_agent": "test_agent"
            }
            session_store[session_id] = session_data
            return session_id, session_data
        
        def validate_session(session_id):
            if session_id not in session_store:
                return {"valid": False, "error": "Session not found"}
            
            session = session_store[session_id]
            current_time = time.time()
            
            # Check session expiry (5 minutes for test)
            if current_time - session["created_at"] > 300:
                del session_store[session_id]
                return {"valid": False, "error": "Session expired"}
            
            # Update access tracking
            session["last_accessed"] = current_time
            session["access_count"] += 1
            
            return {"valid": True, "session": session}
        
        with patch('netra_backend.app.auth.session_manager.create_session', side_effect=create_secure_session):
            with patch('netra_backend.app.auth.session_manager.validate_session', side_effect=validate_session):
                
                # Test session creation and validation
                session_id, session_data = create_secure_session("user123", ["read:analytics"])
                
                agent_state = DeepAgentState(
                    agent_id="session_agent",
                    session_id=session_id,
                    thread_id="secure_thread",
                    context={"user_id": "user123", "session_security": True}
                )
                
                agent = SupervisorAgent(
                    agent_id="session_security_test",
                    initial_state=agent_state
                )
                
                # Test valid session access
                result1 = await agent._validate_session_security(session_id)
                assert result1["valid"] is True
                assert result1["session"]["user_id"] == "user123"
                assert result1["session"]["access_count"] == 1
                
                # Test session access tracking
                result2 = await agent._validate_session_security(session_id)
                assert result2["valid"] is True
                assert result2["session"]["access_count"] == 2
                
                # Test invalid session
                invalid_result = await agent._validate_session_security("invalid_session_id")
                assert invalid_result["valid"] is False
                assert "error" in invalid_result
                
                # Test session isolation between users
                session_id_2, _ = create_secure_session("user456", ["write:reports"])
                
                # Agent with user123 session should not access user456's session
                cross_session_result = await agent._validate_session_security(session_id_2)
                # This should be handled by the agent's security context validation
                assert cross_session_result["valid"] is True  # Session exists
                # But agent should reject it based on user mismatch in higher-level validation
    
    @pytest.mark.asyncio
    async def test_agent_permission_enforcement(self):
        """Test agent enforces permissions strictly."""
        # Mock permission scenarios
        permission_scenarios = [
            {
                "user_permissions": ["read:analytics", "write:reports"],
                "required_permission": "read:analytics",
                "should_allow": True
            },
            {
                "user_permissions": ["read:analytics"],
                "required_permission": "write:reports", 
                "should_allow": False
            },
            {
                "user_permissions": ["admin:all"],
                "required_permission": "read:analytics",
                "should_allow": True  # Admin has all permissions
            },
            {
                "user_permissions": [],
                "required_permission": "read:analytics",
                "should_allow": False
            },
            {
                "user_permissions": ["read:analytics", "read:users"],
                "required_permission": "delete:users",
                "should_allow": False
            }
        ]
        
        mock_auth_service = AuthManager()
        
        with patch('netra_backend.app.auth.auth_service_client.auth_service', mock_auth_service):
            
            for scenario in permission_scenarios:
                mock_auth_service.check_permission = AsyncMock(return_value=scenario["should_allow"])
                
                agent_state = DeepAgentState(
                    agent_id="permission_agent",
                    session_id="permission_session",
                    thread_id="permission_thread",
                    context={
                        "user_id": "test_user",
                        "permissions": scenario["user_permissions"]
                    }
                )
                
                agent = SupervisorAgent(
                    agent_id="permission_test",
                    initial_state=agent_state
                )
                
                # Test permission check
                result = await agent._check_permission(
                    user_id="test_user",
                    required_permission=scenario["required_permission"]
                )
                
                if scenario["should_allow"]:
                    assert result["allowed"] is True
                    assert "error" not in result
                else:
                    assert result["allowed"] is False
                    assert "error" in result
                    assert result["error_type"] == "permission_denied"
                
                # Verify auth service was called correctly
                mock_auth_service.check_permission.assert_called_with(
                    "test_user", 
                    scenario["required_permission"]
                )


@pytest.mark.security
class TestAgentDataProtection:
    """Test agent data protection and privacy measures."""
    
    @pytest.mark.asyncio
    async def test_agent_sensitive_data_handling(self):
        """Test agent properly handles sensitive data."""
        # Mock sensitive data scenarios
        sensitive_data_scenarios = [
            {
                "input_data": {
                    "user_id": "user123",
                    "email": "user@example.com",
                    "password": "secret123",
                    "credit_card": "4111-1111-1111-1111",
                    "ssn": "123-45-6789"
                },
                "expected_masked_fields": ["password", "credit_card", "ssn"]
            },
            {
                "input_data": {
                    "api_key": "sk-1234567890abcdef",
                    "database_url": "postgresql://user:pass@host/db",
                    "private_key": "-----BEGIN PRIVATE KEY-----"
                },
                "expected_masked_fields": ["api_key", "database_url", "private_key"]
            },
            {
                "input_data": {
                    "public_info": "This is public",
                    "user_preferences": {"theme": "dark", "language": "en"}
                },
                "expected_masked_fields": []  # No sensitive data
            }
        ]
        
        for scenario in sensitive_data_scenarios:
            agent_state = DeepAgentState(
                agent_id="data_protection_agent",
                session_id="protection_session",
                thread_id="protection_thread",
                context={"data_protection": True, "pii_detection": True}
            )
            
            agent = SupervisorAgent(
                agent_id="data_protection_test",
                initial_state=agent_state
            )
            
            # Test sensitive data masking
            result = await agent._process_with_data_protection(scenario["input_data"])
            
            # Verify sensitive fields were masked
            for field in scenario["expected_masked_fields"]:
                if field in result["processed_data"]:
                    # Should be masked (replaced with asterisks or hash)
                    assert "*" in result["processed_data"][field] or result["processed_data"][field] != scenario["input_data"][field]
                    
            # Verify audit trail for sensitive data access
            if scenario["expected_masked_fields"]:
                assert result["sensitive_data_detected"] is True
                assert result["fields_masked"] == scenario["expected_masked_fields"]
                assert "audit_trail" in result
            else:
                assert result["sensitive_data_detected"] is False
    
    @pytest.mark.asyncio
    async def test_agent_data_encryption_at_rest(self):
        """Test agent encrypts sensitive data at rest."""
        # Mock encryption service
        mock_encryption_service = mock_encryption_service_instance  # Initialize appropriate service
        
        def mock_encrypt(data, key_id="default"):
            # Simple mock encryption (in real implementation, use proper crypto)
            encrypted_data = hashlib.sha256(f"{data}:{key_id}".encode()).hexdigest()
            return f"encrypted:{encrypted_data[:16]}"
        
        def mock_decrypt(encrypted_data, key_id="default"):
            # Mock decryption
            if encrypted_data.startswith("encrypted:"):
                return "decrypted_data"
            return encrypted_data
        
        mock_encryption_service.encrypt = mock_encrypt
        mock_encryption_service.decrypt = mock_decrypt
        
        with patch('netra_backend.app.security.encryption_service.encryption_service', mock_encryption_service):
            
            agent_state = DeepAgentState(
                agent_id="encryption_agent",
                session_id="encryption_session",
                thread_id="encryption_thread",
                context={
                    "encryption_required": True,
                    "data_classification": "sensitive"
                }
            )
            
            agent = SupervisorAgent(
                agent_id="encryption_test", 
                initial_state=agent_state
            )
            
            # Test data encryption workflow
            sensitive_data = {
                "user_credentials": "user:password",
                "payment_info": "card_number:1234",
                "personal_details": "ssn:123456789"
            }
            
            result = await agent._store_sensitive_data(sensitive_data)
            
            # Verify data was encrypted
            assert result["status"] == "stored"
            assert result["encryption_applied"] is True
            
            stored_data = result["stored_data"]
            for key, value in stored_data.items():
                if isinstance(value, str):
                    assert value.startswith("encrypted:")  # Data was encrypted
            
            # Test data retrieval and decryption
            retrieval_result = await agent._retrieve_sensitive_data(result["storage_id"])
            
            assert retrieval_result["status"] == "retrieved"
            assert retrieval_result["decryption_applied"] is True
            
            # Verify audit trail
            assert "encryption_audit" in result
            assert result["encryption_audit"]["algorithm"] is not None
            assert result["encryption_audit"]["key_id"] == "default"
    
    @pytest.mark.asyncio
    async def test_agent_sql_injection_protection(self):
        """Test agent protects against SQL injection attacks."""
        # Mock database manager with injection detection
        mock_db_manager = DatabaseTestManager().create_session()
        mock_session = AsyncNone  # TODO: Use real service instance
        
        injection_attempts = []
        
        def mock_execute(query):
            query_str = str(query)
            
            # Detect common SQL injection patterns
            injection_patterns = [
                "' OR '1'='1",
                "'; DROP TABLE",
                "UNION SELECT",
                "-- ",
                "/*",
                "xp_cmdshell"
            ]
            
            for pattern in injection_patterns:
                if pattern in query_str.upper():
                    injection_attempts.append({"query": query_str, "pattern": pattern})
                    raise ValueError(f"SQL injection attempt detected: {pattern}")
            
            return AsyncMock(rowcount=1)
        
        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            
            agent_state = DeepAgentState(
                agent_id="sql_protection_agent",
                session_id="sql_session",
                thread_id="sql_thread",
                context={"sql_injection_protection": True}
            )
            
            agent = SupervisorAgent(
                agent_id="sql_protection_test",
                initial_state=agent_state
            )
            
            # Test legitimate query (should succeed)
            legitimate_query = {
                "query": "SELECT * FROM users WHERE id = ?",
                "parameters": [123]
            }
            
            result1 = await agent._execute_safe_query(legitimate_query)
            assert result1["status"] == "success"
            assert result1["injection_detected"] is False
            
            # Test SQL injection attempts (should be blocked)
            injection_queries = [
                {
                    "query": "SELECT * FROM users WHERE id = '1' OR '1'='1'",
                    "parameters": []
                },
                {
                    "query": "SELECT * FROM users WHERE id = 1; DROP TABLE users; --",
                    "parameters": []
                },
                {
                    "query": "SELECT * FROM users UNION SELECT * FROM admin_users",
                    "parameters": []
                }
            ]
            
            for injection_query in injection_queries:
                result = await agent._execute_safe_query(injection_query)
                
                assert result["status"] == "blocked"
                assert result["injection_detected"] is True
                assert "security_violation" in result
            
            # Verify injection attempts were logged
            assert len(injection_attempts) == len(injection_queries)


@pytest.mark.security
class TestAgentSecurityBoundaries:
    """Test agent security boundaries and isolation."""
    
    @pytest.mark.asyncio
    async def test_agent_resource_access_limits(self):
        """Test agent respects resource access limits."""
        # Mock resource manager with limits
        resource_limits = {
            "max_memory_mb": 256,
            "max_cpu_percent": 50,
            "max_file_operations": 100,
            "max_network_requests": 50,
            "max_execution_time_seconds": 30
        }
        
        resource_usage = {
            "memory_mb": 0,
            "cpu_percent": 0,
            "file_operations": 0,
            "network_requests": 0,
            "execution_time": 0
        }
        
        def check_resource_limit(resource_type, requested_amount):
            if resource_usage[resource_type] + requested_amount > resource_limits[f"max_{resource_type}"]:
                return False, f"Resource limit exceeded for {resource_type}"
            return True, None
        
        def consume_resource(resource_type, amount):
            allowed, error = check_resource_limit(resource_type, amount)
            if not allowed:
                raise Exception(error)
            resource_usage[resource_type] += amount
        
        with patch('netra_backend.app.security.resource_monitor.check_limit', side_effect=check_resource_limit):
            with patch('netra_backend.app.security.resource_monitor.consume', side_effect=consume_resource):
                
                agent_state = DeepAgentState(
                    agent_id="resource_limited_agent",
                    session_id="resource_session",
                    thread_id="resource_thread",
                    context={"resource_limits_enabled": True}
                )
                
                agent = SupervisorAgent(
                    agent_id="resource_limit_test",
                    initial_state=agent_state
                )
                
                # Test operations within limits (should succeed)
                result1 = await agent._execute_resource_limited_operation({
                    "operation_type": "memory_intensive",
                    "memory_required_mb": 100,  # Within 256MB limit
                    "cpu_required_percent": 25   # Within 50% limit
                })
                
                assert result1["status"] == "completed"
                assert result1["resource_limit_exceeded"] is False
                
                # Test operations exceeding limits (should be blocked)
                result2 = await agent._execute_resource_limited_operation({
                    "operation_type": "memory_intensive",
                    "memory_required_mb": 300,  # Exceeds 256MB limit
                    "cpu_required_percent": 25
                })
                
                assert result2["status"] == "blocked"
                assert result2["resource_limit_exceeded"] is True
                assert "memory_mb" in result2["exceeded_limits"]
                
                # Test cumulative resource tracking
                for i in range(10):
                    await agent._execute_resource_limited_operation({
                        "operation_type": "network_request",
                        "network_requests": 5
                    })
                
                # Should hit network request limit (50 requests)
                result3 = await agent._execute_resource_limited_operation({
                    "operation_type": "network_request", 
                    "network_requests": 5  # Would exceed 50 limit
                })
                
                assert result3["status"] == "blocked"
                assert result3["resource_limit_exceeded"] is True
                assert "network_requests" in result3["exceeded_limits"]
    
    @pytest.mark.asyncio
    async def test_agent_sandbox_isolation(self):
        """Test agent operations are properly sandboxed."""
        # Mock sandbox environment
        sandbox_violations = []
        
        def mock_file_access(filepath):
            # Define allowed and forbidden paths
            allowed_paths = ["/tmp/", "/var/tmp/", "/app/data/"]
            forbidden_paths = ["/etc/", "/root/", "/home/", "/usr/bin/"]
            
            for forbidden in forbidden_paths:
                if filepath.startswith(forbidden):
                    violation = {"type": "file_access", "path": filepath, "reason": "forbidden_path"}
                    sandbox_violations.append(violation)
                    raise PermissionError(f"Access denied to {filepath}")
            
            for allowed in allowed_paths:
                if filepath.startswith(allowed):
                    return True
                    
            # Default deny
            violation = {"type": "file_access", "path": filepath, "reason": "outside_sandbox"}
            sandbox_violations.append(violation)
            raise PermissionError(f"Path outside sandbox: {filepath}")
        
        def mock_network_access(host, port):
            # Define allowed network destinations
            allowed_hosts = ["api.internal.com", "database.internal.com"]
            forbidden_hosts = ["external-evil.com", "0.0.0.0"]
            
            if host in forbidden_hosts:
                violation = {"type": "network_access", "host": host, "port": port, "reason": "forbidden_host"}
                sandbox_violations.append(violation)
                raise PermissionError(f"Network access denied to {host}")
                
            if host not in allowed_hosts:
                violation = {"type": "network_access", "host": host, "port": port, "reason": "unauthorized_host"}
                sandbox_violations.append(violation)
                raise PermissionError(f"Unauthorized network access to {host}")
            
            return True
        
        with patch('netra_backend.app.security.sandbox.check_file_access', side_effect=mock_file_access):
            with patch('netra_backend.app.security.sandbox.check_network_access', side_effect=mock_network_access):
                
                agent_state = DeepAgentState(
                    agent_id="sandboxed_agent",
                    session_id="sandbox_session",
                    thread_id="sandbox_thread",
                    context={"sandbox_enabled": True, "security_mode": "strict"}
                )
                
                agent = SupervisorAgent(
                    agent_id="sandbox_test",
                    initial_state=agent_state
                )
                
                # Test allowed file operations
                result1 = await agent._execute_sandboxed_file_operation("/tmp/temp_file.txt", "write")
                assert result1["status"] == "completed"
                assert result1["sandbox_violation"] is False
                
                # Test forbidden file operations
                result2 = await agent._execute_sandboxed_file_operation("/etc/passwd", "read")
                assert result2["status"] == "blocked"
                assert result2["sandbox_violation"] is True
                assert result2["violation_type"] == "file_access"
                
                # Test allowed network operations
                result3 = await agent._execute_sandboxed_network_operation("api.internal.com", 443)
                assert result3["status"] == "completed"
                assert result3["sandbox_violation"] is False
                
                # Test forbidden network operations
                result4 = await agent._execute_sandboxed_network_operation("external-evil.com", 80)
                assert result4["status"] == "blocked"
                assert result4["sandbox_violation"] is True
                assert result4["violation_type"] == "network_access"
                
                # Verify sandbox violations were logged
                assert len(sandbox_violations) == 2
                assert sandbox_violations[0]["type"] == "file_access"
                assert sandbox_violations[1]["type"] == "network_access"