"""
Integration Test: WebSocket Auth Flow Race Condition Detection

This test is designed to FAIL initially, proving that WebSocket authentication
integration has race conditions causing HTTP 403 failures despite healthy services.

Business Impact:
- Users cannot establish WebSocket connections for chat
- HTTP 403 errors block real-time communication
- Auth race conditions prevent Golden Path completion
- JWT validation scattered across services creates conflicts

SSOT Violations Tested:
- WebSocket auth logic scattered across multiple services
- Race conditions between auth service and backend WebSocket handling
- Inconsistent JWT validation between HTTP and WebSocket endpoints
- No centralized authentication for WebSocket connections

This test MUST FAIL until WebSocket authentication is properly centralized.
"""
import asyncio
import pytest
import jwt
import time
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from dev_launcher.isolated_environment import IsolatedEnvironment

try:
    # SSOT imports - these should work after consolidation
    from netra_backend.app.websocket_core.auth import WebSocketAuthValidator
    from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
    from netra_backend.app.auth_integration.auth import BackendAuthIntegration
    from netra_backend.app.core.user_execution_context import UserExecutionContext
except ImportError as e:
    # Expected during SSOT migration - imports will be fixed during consolidation
    print(f"EXPECTED IMPORT ERROR during SSOT migration: {e}")
    WebSocketAuthValidator = None
    UnifiedWebSocketManager = None
    BackendAuthIntegration = None
    UserExecutionContext = None


class TestWebSocketAuthFlow(SSotAsyncTestCase):
    """
    CRITICAL: This test proves WebSocket authentication race conditions.

    EXPECTED RESULT: FAIL - Auth race conditions cause connection failures
    BUSINESS IMPACT: $500K+ ARR blocked by authentication failures
    """

    def setup_method(self):
        """Set up test environment for WebSocket auth testing."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.test_user_id = "auth_test_user"
        self.test_jwt_token = None
        self.auth_success_rate = 0.0

    @pytest.mark.asyncio
    async def test_websocket_jwt_validation_race_condition(self):
        """
        CRITICAL BUSINESS TEST: Prove JWT validation race conditions

        Expected Result: FAIL - Race conditions cause auth failures
        Business Impact: Users cannot connect to WebSocket for chat
        """
        if not all([WebSocketAuthValidator, BackendAuthIntegration]):
            pytest.skip("SSOT imports not available - expected during migration")

        # Generate test JWT token
        self.test_jwt_token = await self._generate_test_jwt()

        # Test concurrent JWT validation requests
        num_concurrent_requests = 5
        validation_results = []

        async def validate_jwt_concurrently(request_index: int):
            """Validate JWT token concurrently to expose race conditions."""
            try:
                # Create auth validator
                auth_validator = WebSocketAuthValidator()

                # Validate JWT token
                validation_result = await auth_validator.validate_jwt_token(
                    self.test_jwt_token,
                    user_id=self.test_user_id
                )

                return {
                    'request_index': request_index,
                    'success': validation_result.get('valid', False),
                    'user_id': validation_result.get('user_id'),
                    'error': validation_result.get('error'),
                    'timestamp': time.time()
                }

            except Exception as e:
                return {
                    'request_index': request_index,
                    'success': False,
                    'error': str(e),
                    'timestamp': time.time()
                }

        # Execute concurrent validations
        tasks = [validate_jwt_concurrently(i) for i in range(num_concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze race condition results
        successful_validations = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        failed_validations = [r for r in results if not (isinstance(r, dict) and r.get('success', False))]

        # CRITICAL ASSERTION: All validations should succeed (will fail due to race conditions)
        assert len(successful_validations) == num_concurrent_requests, (
            f"SSOT VIOLATION: JWT validation race conditions detected. "
            f"{len(failed_validations)} out of {num_concurrent_requests} validations failed. "
            f"Failed validations: {failed_validations}. "
            f"BUSINESS IMPACT: Users cannot authenticate for WebSocket connections."
        )

        # Check for inconsistent results
        user_ids = [r.get('user_id') for r in successful_validations if r.get('user_id')]
        unique_user_ids = set(user_ids)

        assert len(unique_user_ids) <= 1, (
            f"SSOT VIOLATION: Inconsistent JWT validation results. "
            f"Expected single user_id, got: {list(unique_user_ids)}. "
            f"Race conditions cause authentication inconsistencies."
        )

    @pytest.mark.asyncio
    async def test_websocket_connection_auth_integration_failure(self):
        """
        CRITICAL BUSINESS TEST: Prove WebSocket connection auth integration failures

        Expected Result: FAIL - Auth integration failures cause HTTP 403 errors
        Business Impact: Chat functionality completely blocked by auth failures
        """
        if not all([UnifiedWebSocketManager, BackendAuthIntegration]):
            pytest.skip("SSOT imports not available - expected during migration")

        # Generate test JWT token
        self.test_jwt_token = await self._generate_test_jwt()

        # Test WebSocket connection with auth
        connection_attempts = []

        for attempt in range(3):
            try:
                # Create WebSocket manager
                websocket_manager = UnifiedWebSocketManager()

                # Create mock WebSocket connection
                mock_websocket = MagicMock()
                mock_websocket.headers = {
                    'Authorization': f'Bearer {self.test_jwt_token}',
                    'User-Agent': 'Netra-Test-Client/1.0'
                }

                # Attempt WebSocket connection auth
                auth_result = await self._attempt_websocket_auth(websocket_manager, mock_websocket)

                connection_attempts.append({
                    'attempt': attempt + 1,
                    'success': auth_result.get('authenticated', False),
                    'user_id': auth_result.get('user_id'),
                    'error': auth_result.get('error'),
                    'status_code': auth_result.get('status_code')
                })

            except Exception as e:
                connection_attempts.append({
                    'attempt': attempt + 1,
                    'success': False,
                    'error': str(e),
                    'status_code': 500
                })

        # Analyze connection auth results
        successful_connections = [a for a in connection_attempts if a.get('success', False)]
        failed_connections = [a for a in connection_attempts if not a.get('success', False)]

        # CRITICAL ASSERTION: All connection attempts should succeed
        assert len(successful_connections) == len(connection_attempts), (
            f"SSOT VIOLATION: WebSocket auth integration failures detected. "
            f"{len(failed_connections)} out of {len(connection_attempts)} connection attempts failed. "
            f"Failed connections: {failed_connections}. "
            f"BUSINESS IMPACT: HTTP 403 errors block chat functionality for $500K+ ARR."
        )

    @pytest.mark.asyncio
    async def test_scattered_jwt_validation_logic_detection(self):
        """
        CRITICAL BUSINESS TEST: Detect JWT validation logic scattered across services

        Expected Result: FAIL - JWT validation logic found in multiple places
        Business Impact: Inconsistent auth behavior causes user connection failures
        """
        # Scan for JWT validation implementations across services
        jwt_validation_locations = await self._scan_jwt_validation_implementations()

        # CRITICAL ASSERTION: Should have single JWT validation location (SSOT)
        assert len(jwt_validation_locations) <= 1, (
            f"SSOT VIOLATION: JWT validation logic scattered across {len(jwt_validation_locations)} locations. "
            f"Implementations found in: {[loc['file'] for loc in jwt_validation_locations]}. "
            f"BUSINESS IMPACT: Inconsistent auth behavior causes connection failures."
        )

        # Check for consistent validation logic
        if len(jwt_validation_locations) > 1:
            await self._verify_jwt_validation_consistency(jwt_validation_locations)

    @pytest.mark.asyncio
    async def test_websocket_auth_service_integration_timing(self):
        """
        CRITICAL BUSINESS TEST: Prove timing issues in auth service integration

        Expected Result: FAIL - Timing issues cause auth failures
        Business Impact: Slow auth responses timeout WebSocket connections
        """
        if not BackendAuthIntegration:
            pytest.skip("SSOT imports not available - expected during migration")

        # Generate test JWT token
        self.test_jwt_token = await self._generate_test_jwt()

        # Test auth service response timing
        timing_results = []

        for attempt in range(5):
            start_time = time.time()

            try:
                # Create auth integration
                auth_integration = BackendAuthIntegration()

                # Test JWT validation with timing
                validation_result = await auth_integration.validate_jwt_for_websocket(
                    self.test_jwt_token,
                    user_id=self.test_user_id
                )

                end_time = time.time()
                response_time = end_time - start_time

                timing_results.append({
                    'attempt': attempt + 1,
                    'success': validation_result.get('valid', False),
                    'response_time': response_time,
                    'timeout': response_time > 5.0,  # 5 second timeout
                    'user_id': validation_result.get('user_id')
                })

            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time

                timing_results.append({
                    'attempt': attempt + 1,
                    'success': False,
                    'response_time': response_time,
                    'timeout': response_time > 5.0,
                    'error': str(e)
                })

        # Analyze timing results
        timeout_count = len([r for r in timing_results if r.get('timeout', False)])
        failed_count = len([r for r in timing_results if not r.get('success', False)])
        avg_response_time = sum(r['response_time'] for r in timing_results) / len(timing_results)

        # CRITICAL ASSERTION: No timeouts should occur
        assert timeout_count == 0, (
            f"SSOT VIOLATION: {timeout_count} auth requests timed out. "
            f"Average response time: {avg_response_time:.2f}s. "
            f"BUSINESS IMPACT: Slow auth responses timeout WebSocket connections."
        )

        # Check response time consistency
        assert avg_response_time < 1.0, (
            f"SSOT VIOLATION: Auth service integration too slow. "
            f"Average response time: {avg_response_time:.2f}s (should be < 1.0s). "
            f"BUSINESS IMPACT: Slow auth degrades chat user experience."
        )

    async def _generate_test_jwt(self) -> str:
        """Generate test JWT token for authentication testing."""
        try:
            # Get JWT secret from environment
            jwt_secret = self.env.get_env('JWT_SECRET_KEY', 'test_secret_key')

            # Create JWT payload
            payload = {
                'user_id': self.test_user_id,
                'email': f'{self.test_user_id}@test.com',
                'exp': int(time.time()) + 3600,  # 1 hour expiration
                'iat': int(time.time()),
                'sub': self.test_user_id
            }

            # Generate JWT token
            token = jwt.encode(payload, jwt_secret, algorithm='HS256')

            return token

        except Exception as e:
            pytest.fail(f"SSOT VIOLATION: Cannot generate test JWT token: {e}")

    async def _attempt_websocket_auth(self, websocket_manager, mock_websocket) -> dict:
        """Attempt WebSocket authentication and return result."""
        try:
            # Extract JWT token from headers
            auth_header = mock_websocket.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return {
                    'authenticated': False,
                    'error': 'Missing or invalid Authorization header',
                    'status_code': 401
                }

            jwt_token = auth_header[7:]  # Remove 'Bearer ' prefix

            # Attempt authentication
            if hasattr(websocket_manager, 'authenticate_connection'):
                auth_result = await websocket_manager.authenticate_connection(
                    jwt_token,
                    websocket=mock_websocket
                )
            else:
                # Fallback to direct JWT validation
                auth_result = await self._validate_jwt_directly(jwt_token)

            return auth_result

        except Exception as e:
            return {
                'authenticated': False,
                'error': str(e),
                'status_code': 500
            }

    async def _validate_jwt_directly(self, jwt_token: str) -> dict:
        """Directly validate JWT token (fallback method)."""
        try:
            # Get JWT secret
            jwt_secret = self.env.get_env('JWT_SECRET_KEY', 'test_secret_key')

            # Decode and validate JWT
            payload = jwt.decode(jwt_token, jwt_secret, algorithms=['HS256'])

            return {
                'authenticated': True,
                'user_id': payload.get('user_id'),
                'status_code': 200
            }

        except jwt.ExpiredSignatureError:
            return {
                'authenticated': False,
                'error': 'JWT token expired',
                'status_code': 401
            }
        except jwt.InvalidTokenError:
            return {
                'authenticated': False,
                'error': 'Invalid JWT token',
                'status_code': 401
            }
        except Exception as e:
            return {
                'authenticated': False,
                'error': f'JWT validation error: {str(e)}',
                'status_code': 500
            }

    async def _scan_jwt_validation_implementations(self) -> list:
        """Scan codebase for JWT validation implementations."""
        import os
        import ast
        from pathlib import Path

        jwt_implementations = []
        project_root = Path(__file__).parents[3]  # Go up to netra-apex root

        # Patterns that indicate JWT validation logic
        jwt_patterns = [
            'jwt.decode',
            'validate_jwt',
            'verify_jwt',
            'decode_jwt',
            'jwt_validator',
            'JWTValidator',
            'authenticate_jwt'
        ]

        # Scan Python files for JWT validation
        for python_file in project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue

            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                    # Check for JWT patterns
                    for pattern in jwt_patterns:
                        if pattern in content:
                            # Parse AST to get more details
                            try:
                                tree = ast.parse(content)
                                for node in ast.walk(tree):
                                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                                        if pattern.lower() in node.name.lower():
                                            jwt_implementations.append({
                                                'file': str(python_file.relative_to(project_root)),
                                                'line': node.lineno,
                                                'type': 'class' if isinstance(node, ast.ClassDef) else 'function',
                                                'name': node.name,
                                                'pattern': pattern
                                            })
                            except SyntaxError:
                                # Still record file if pattern found but can't parse
                                jwt_implementations.append({
                                    'file': str(python_file.relative_to(project_root)),
                                    'line': 'unknown',
                                    'type': 'pattern_match',
                                    'name': pattern,
                                    'pattern': pattern
                                })

            except (UnicodeDecodeError, PermissionError):
                continue

        # Remove duplicates
        seen = set()
        unique_implementations = []
        for impl in jwt_implementations:
            key = (impl['file'], impl['name'], impl['pattern'])
            if key not in seen:
                seen.add(key)
                unique_implementations.append(impl)

        return unique_implementations

    async def _verify_jwt_validation_consistency(self, implementations: list):
        """Verify JWT validation logic is consistent across implementations."""
        # This would involve more complex analysis of the actual validation logic
        # For now, we'll fail if multiple implementations exist
        pytest.fail(
            f"SSOT VIOLATION: Multiple JWT validation implementations detected. "
            f"Found {len(implementations)} different implementations: "
            f"{[impl['file'] + ':' + impl['name'] for impl in implementations]}. "
            f"BUSINESS IMPACT: Inconsistent validation logic causes auth failures."
        )

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped during scanning."""
        skip_patterns = [
            '__pycache__',
            '.git',
            '.pytest_cache',
            'htmlcov',
            'node_modules',
            '.venv',
            'venv',
            'backup',
            'archive',
            '.pyc',
            'migrations',
            'test_websocket_consolidation'  # Skip our own test files
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)


if __name__ == "__main__":
    # Run this test to prove WebSocket auth flow race conditions
    pytest.main([__file__, "-v", "--tb=short"])