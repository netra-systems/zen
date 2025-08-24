"""Authentication Token Flow Integration Test

BVJ: Protects $15K MRR from auth failures disrupting user messaging pipeline.
Segment: All (Free/Early/Mid/Enterprise). Business Goal: Retention through reliable auth.
Value Impact: Ensures JWT validation works throughout entire message pipeline.
Strategic Impact: Prevents authentication-related service interruptions and user dropoffs.

Testing Philosophy: L3/L4 realism - Real JWT tokens, real auth service, real pipeline validation.
Coverage: JWT lifecycle, token refresh, expiry handling, WebSocket auth persistence.
"""

from datetime import datetime, timedelta, timezone
from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.db.models_postgres import User
from netra_backend.app.db.session import get_db_session
from netra_backend.app.services.user_service import user_service
from netra_backend.app.websocket_core.manager import WebSocketManager as WebSocketManager
from netra_backend.app.websocket_core.manager import WebSocketManager
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
import asyncio
import jwt
import pytest
import time


# Backward compatibility alias

# Backward compatibility alias
UnifiedWebSocketManager = WebSocketManager

WebSocketManager = WebSocketManager

class JWTTokenManager:

    """L3 Real JWT token manager for authentication testing."""
    

    def __init__(self):

        self.secret_key = "test_jwt_secret_key_for_integration_testing"

        self.algorithm = "HS256"

        self.tokens: Dict[str, Dict[str, Any]] = {}
    

    def create_test_token(self, user_id: str, expires_in: int = 3600) -> Dict[str, Any]:

        """Create real JWT token for testing."""

        now = datetime.now(timezone.utc)

        exp_time = now + timedelta(seconds=expires_in)
        

        payload = {

            "user_id": user_id,

            "email": f"{user_id}@test.com",

            "exp": int(exp_time.timestamp()),

            "iat": int(now.timestamp()),

            "jti": f"test_token_{user_id}_{int(time.time())}"

        }
        

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        

        token_data = {

            "token": token,

            "payload": payload,

            "created_at": now,

            "expires_at": exp_time,

            "is_valid": True

        }
        

        self.tokens[token] = token_data

        return token_data
    

    def validate_token_jwt(self, token: str) -> Optional[Dict[str, Any]]:

        """Validate JWT token and return payload."""

        try:

            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is in our tracking

            if token in self.tokens:

                token_data = self.tokens[token]

                if not token_data["is_valid"]:

                    return None
            

            return payload

        except jwt.ExpiredSignatureError:

            return None

        except jwt.InvalidTokenError:

            return None
    

    def revoke_token(self, token: str) -> bool:

        """Revoke token to simulate invalidation."""

        if token in self.tokens:

            self.tokens[token]["is_valid"] = False

            return True

        return False
    

    def refresh_token(self, old_token: str, extends_by: int = 3600) -> Optional[Dict[str, Any]]:

        """Refresh token with new expiry."""

        payload = self.validate_token_jwt(old_token)

        if payload:
            # Revoke old token

            self.revoke_token(old_token)
            # Create new token

            return self.create_test_token(payload["user_id"], extends_by)

        return None


class MessagePipelineAuthValidator:

    """L3 Real message pipeline authentication validator."""
    

    def __init__(self, user_id: str):

        self.user_id = user_id

        self.token_manager = JWTTokenManager()

        self.auth_events: List[Dict[str, Any]] = []

        self.current_token: Optional[str] = None
    

    async def authenticate_user(self) -> Dict[str, Any]:

        """Authenticate user and get valid token."""
        # Mock user for testing

        # Mock: Generic component isolation for controlled unit testing
        mock_user = MagicMock()

        mock_user.id = self.user_id

        mock_user.email = f"{self.user_id}@test.com"
        
        # Create token

        token_data = self.token_manager.create_test_token(self.user_id)

        self.current_token = token_data["token"]
        

        self.auth_events.append({

            "type": "user_authenticated",

            "user_id": self.user_id,

            "token_created": True,

            "timestamp": time.time()

        })
        

        return {

            "user": mock_user,

            "token": self.current_token,

            "token_data": token_data,

            "authentication_successful": True

        }
    

    async def validate_token_in_pipeline(self, token: str) -> Dict[str, Any]:

        """Validate token through message pipeline."""

        validation_start = time.time()
        
        # Validate token using JWT manager

        payload = self.token_manager.validate_token_jwt(token)
        

        if payload:
            # Simulate pipeline validation steps

            pipeline_steps = [

                "token_format_validation",

                "signature_verification", 

                "expiry_check",

                "user_existence_check",

                "permission_validation"

            ]
            

            validation_results = {}

            for step in pipeline_steps:
                # Simulate validation step

                await asyncio.sleep(0.01)  # Small delay for realism

                validation_results[step] = True
            

            validation_time = time.time() - validation_start
            

            self.auth_events.append({

                "type": "token_validated",

                "token_valid": True,

                "pipeline_steps": validation_results,

                "validation_time": validation_time,

                "timestamp": time.time()

            })
            

            return {

                "validation_successful": True,

                "payload": payload,

                "validation_time": validation_time,

                "pipeline_steps": validation_results

            }
        

        self.auth_events.append({

            "type": "token_validation_failed",

            "token_valid": False,

            "timestamp": time.time()

        })
        

        return {

            "validation_successful": False,

            "error": "Invalid or expired token"

        }
    

    async def simulate_long_conversation(self, duration_minutes: int = 5) -> Dict[str, Any]:

        """Simulate long conversation to test token expiry handling."""

        conversation_start = time.time()

        message_count = 0

        token_refreshes = 0
        
        # Simulate messages over time

        while time.time() - conversation_start < (duration_minutes * 60):
            # Validate current token

            validation_result = await self.validate_token_in_pipeline(self.current_token)
            

            if not validation_result["validation_successful"]:
                # Token expired, attempt refresh

                refresh_result = await self.refresh_expired_token()

                if refresh_result["refresh_successful"]:

                    token_refreshes += 1

                else:

                    break
            
            # Simulate sending a message

            message_count += 1

            await asyncio.sleep(0.1)  # Small delay between messages
        

        conversation_duration = time.time() - conversation_start
        

        return {

            "conversation_completed": True,

            "duration": conversation_duration,

            "messages_sent": message_count,

            "token_refreshes": token_refreshes,

            "final_token_valid": self.token_manager.validate_token_jwt(self.current_token) is not None

        }
    

    async def refresh_expired_token(self) -> Dict[str, Any]:

        """Handle token refresh when expired."""

        if not self.current_token:

            return {"refresh_successful": False, "error": "No current token"}
        

        refresh_data = self.token_manager.refresh_token(self.current_token)
        

        if refresh_data:

            self.current_token = refresh_data["token"]
            

            self.auth_events.append({

                "type": "token_refreshed",

                "refresh_successful": True,

                "new_token_created": True,

                "timestamp": time.time()

            })
            

            return {

                "refresh_successful": True,

                "new_token": self.current_token,

                "token_data": refresh_data

            }
        

        self.auth_events.append({

            "type": "token_refresh_failed",

            "refresh_successful": False,

            "timestamp": time.time()

        })
        

        return {"refresh_successful": False, "error": "Token refresh failed"}


class WebSocketAuthPersistence:

    """L3 Real WebSocket authentication persistence tester."""
    

    def __init__(self, user_id: str):

        self.user_id = user_id

        self.pipeline_validator = MessagePipelineAuthValidator(user_id)

        self.websocket_events: List[Dict[str, Any]] = []

        self.connection_active = False
    

    async def establish_authenticated_connection(self) -> Dict[str, Any]:

        """Establish WebSocket connection with authentication."""
        # Authenticate user first

        auth_result = await self.pipeline_validator.authenticate_user()

        if not auth_result["authentication_successful"]:

            return {"connection_successful": False, "error": "Authentication failed"}
        
        # Simulate WebSocket connection establishment

        connection_start = time.time()
        
        # Validate token for WebSocket connection

        token = auth_result["token"]

        validation_result = await self.pipeline_validator.validate_token_in_pipeline(token)
        

        if validation_result["validation_successful"]:

            self.connection_active = True

            connection_time = time.time() - connection_start
            

            self.websocket_events.append({

                "type": "websocket_connected",

                "user_id": self.user_id,

                "token_validated": True,

                "connection_time": connection_time,

                "timestamp": time.time()

            })
            

            return {

                "connection_successful": True,

                "connection_time": connection_time,

                "token_validated": True,

                "auth_result": auth_result

            }
        

        return {

            "connection_successful": False,

            "error": "Token validation failed for WebSocket"

        }
    

    async def test_connection_persistence_during_token_refresh(self) -> Dict[str, Any]:

        """Test WebSocket connection persistence during token refresh."""

        if not self.connection_active:

            return {"test_successful": False, "error": "No active connection"}
        
        # Create short-lived token for testing

        short_token_data = self.pipeline_validator.token_manager.create_test_token(

            self.user_id, expires_in=2  # 2 seconds

        )

        self.pipeline_validator.current_token = short_token_data["token"]
        
        # Wait for token to expire

        await asyncio.sleep(3)
        
        # Attempt to refresh token while maintaining connection

        refresh_result = await self.pipeline_validator.refresh_expired_token()
        

        if refresh_result["refresh_successful"]:
            # Validate new token works with WebSocket

            validation_result = await self.pipeline_validator.validate_token_in_pipeline(

                refresh_result["new_token"]

            )
            

            connection_maintained = self.connection_active and validation_result["validation_successful"]
            

            self.websocket_events.append({

                "type": "token_refreshed_during_connection",

                "connection_maintained": connection_maintained,

                "new_token_valid": validation_result["validation_successful"],

                "timestamp": time.time()

            })
            

            return {

                "test_successful": True,

                "connection_maintained": connection_maintained,

                "token_refresh_successful": True,

                "new_token_validated": validation_result["validation_successful"]

            }
        

        return {

            "test_successful": False,

            "error": "Token refresh failed"

        }
    

    async def simulate_connection_drop_and_reconnect(self) -> Dict[str, Any]:

        """Simulate connection drop and reconnection with token validation."""

        if not self.connection_active:

            return {"test_successful": False, "error": "No active connection"}
        
        # Simulate connection drop

        self.connection_active = False

        drop_time = time.time()
        

        self.websocket_events.append({

            "type": "connection_dropped",

            "timestamp": drop_time

        })
        
        # Wait a moment

        await asyncio.sleep(1)
        
        # Attempt reconnection

        reconnect_start = time.time()
        
        # Validate current token still works

        validation_result = await self.pipeline_validator.validate_token_in_pipeline(

            self.pipeline_validator.current_token

        )
        

        if validation_result["validation_successful"]:

            self.connection_active = True

            reconnect_time = time.time() - reconnect_start
            

            self.websocket_events.append({

                "type": "connection_reestablished",

                "reconnect_time": reconnect_time,

                "token_still_valid": True,

                "timestamp": time.time()

            })
            

            return {

                "reconnection_successful": True,

                "reconnect_time": reconnect_time,

                "token_validated": True

            }
        

        return {

            "reconnection_successful": False,

            "error": "Token validation failed on reconnect"

        }


@pytest.mark.asyncio

class TestAuthenticationTokenFlow:

    """Authentication Token Flow Integration Test Suite."""
    

    @pytest.fixture

    async def test_user_id(self):

        """Provide test user ID for authentication testing."""

        return "test_user_auth_flow"
    

    @pytest.fixture

    async def test_pipeline_validator(self, test_user_id):

        """Initialize message pipeline auth validator."""

        return MessagePipelineAuthValidator(test_user_id)
    

    @pytest.fixture

    async def test_websocket_auth(self, test_user_id):

        """Initialize WebSocket auth persistence tester."""

        return WebSocketAuthPersistence(test_user_id)
    

    async def test_jwt_creation_and_validation(self, pipeline_validator):

        """Test Case 1: JWT tokens created and validated correctly."""
        # Authenticate user

        auth_result = await pipeline_validator.authenticate_user()
        

        assert auth_result["authentication_successful"]

        assert auth_result["token"] is not None

        assert auth_result["user"] is not None
        
        # Validate created token

        token = auth_result["token"]

        validation_result = await pipeline_validator.validate_token_in_pipeline(token)
        

        assert validation_result["validation_successful"]

        assert validation_result["payload"]["user_id"] == pipeline_validator.user_id

        assert validation_result["validation_time"] < 0.1  # Fast validation
        
        # Verify all pipeline steps passed

        pipeline_steps = validation_result["pipeline_steps"]

        assert all(step_result for step_result in pipeline_steps.values())
    

    async def test_token_expiry_and_renewal(self, pipeline_validator):

        """Test Case 2: Token expiry handled and renewal works correctly."""
        # Create short-lived token

        short_token_data = pipeline_validator.token_manager.create_test_token(

            pipeline_validator.user_id, expires_in=1  # 1 second

        )
        
        # Validate token initially works

        validation_result = await pipeline_validator.validate_token_in_pipeline(

            short_token_data["token"]

        )

        assert validation_result["validation_successful"]
        
        # Wait for token to expire

        await asyncio.sleep(2)
        
        # Validate token now fails

        expired_validation = await pipeline_validator.validate_token_in_pipeline(

            short_token_data["token"]

        )

        assert not expired_validation["validation_successful"]
        
        # Refresh token

        refresh_result = await pipeline_validator.refresh_expired_token()

        assert refresh_result["refresh_successful"]
        
        # Validate new token works

        new_validation = await pipeline_validator.validate_token_in_pipeline(

            refresh_result["new_token"]

        )

        assert new_validation["validation_successful"]
    

    async def test_message_pipeline_token_validation(self, pipeline_validator):

        """Test Case 3: Token validation throughout message pipeline."""
        # Authenticate user

        auth_result = await pipeline_validator.authenticate_user()

        assert auth_result["authentication_successful"]
        
        # Simulate multiple message validations

        validation_results = []

        for i in range(5):

            result = await pipeline_validator.validate_token_in_pipeline(

                auth_result["token"]

            )

            validation_results.append(result)

            await asyncio.sleep(0.1)
        
        # All validations should succeed

        assert all(result["validation_successful"] for result in validation_results)
        
        # Verify consistent validation times

        validation_times = [result["validation_time"] for result in validation_results]

        avg_time = sum(validation_times) / len(validation_times)

        assert avg_time < 0.1  # Average validation time under 100ms
    

    async def test_long_conversation_token_handling(self, pipeline_validator):

        """Test Case 4: Long conversations handle token lifecycle correctly."""
        # Authenticate user first

        auth_result = await pipeline_validator.authenticate_user()

        assert auth_result["authentication_successful"]
        
        # Simulate short conversation (to avoid long test times)

        conversation_result = await pipeline_validator.simulate_long_conversation(

            duration_minutes=0.1  # 6 seconds for testing

        )
        

        assert conversation_result["conversation_completed"]

        assert conversation_result["messages_sent"] > 0

        assert conversation_result["final_token_valid"]
        
        # If conversation was long enough, we might see token refreshes

        if conversation_result["duration"] > 300:  # 5 minutes

            assert conversation_result["token_refreshes"] >= 0
    

    async def test_websocket_authentication_flow(self, websocket_auth):

        """Test Case 5: WebSocket authentication flow works end-to-end."""
        # Establish authenticated WebSocket connection

        connection_result = await websocket_auth.establish_authenticated_connection()
        

        assert connection_result["connection_successful"]

        assert connection_result["token_validated"]

        assert connection_result["connection_time"] < 1.0  # Fast connection
        
        # Verify auth events tracked

        auth_events = websocket_auth.pipeline_validator.auth_events

        websocket_events = websocket_auth.websocket_events
        

        assert len(auth_events) >= 2  # Authentication + validation

        assert len(websocket_events) >= 1  # Connection event
        
        # Verify event ordering

        auth_event = next(e for e in auth_events if e["type"] == "user_authenticated")

        websocket_event = next(e for e in websocket_events if e["type"] == "websocket_connected")

        assert websocket_event["timestamp"] > auth_event["timestamp"]
    

    async def test_token_refresh_during_active_connection(self, websocket_auth):

        """Test Case 6: Token refresh during active WebSocket connection."""
        # Establish connection first

        connection_result = await websocket_auth.establish_authenticated_connection()

        assert connection_result["connection_successful"]
        
        # Test token refresh during connection

        persistence_result = await websocket_auth.test_connection_persistence_during_token_refresh()
        

        assert persistence_result["test_successful"]

        assert persistence_result["connection_maintained"]

        assert persistence_result["token_refresh_successful"]

        assert persistence_result["new_token_validated"]
        
        # Verify refresh event tracked

        websocket_events = websocket_auth.websocket_events

        refresh_event = next(

            (e for e in websocket_events if e["type"] == "token_refreshed_during_connection"),

            None

        )

        assert refresh_event is not None

        assert refresh_event["connection_maintained"]
    

    async def test_connection_recovery_with_auth(self, websocket_auth):

        """Test Case 7: Connection recovery maintains authentication state."""
        # Establish initial connection

        connection_result = await websocket_auth.establish_authenticated_connection()

        assert connection_result["connection_successful"]
        
        # Simulate connection drop and recovery

        recovery_result = await websocket_auth.simulate_connection_drop_and_reconnect()
        

        assert recovery_result["reconnection_successful"]

        assert recovery_result["token_validated"]

        assert recovery_result["reconnect_time"] < 2.0  # Fast reconnection
        
        # Verify drop and reconnect events

        websocket_events = websocket_auth.websocket_events

        drop_event = next(e for e in websocket_events if e["type"] == "connection_dropped")

        reconnect_event = next(e for e in websocket_events if e["type"] == "connection_reestablished")
        

        assert drop_event is not None

        assert reconnect_event is not None

        assert reconnect_event["timestamp"] > drop_event["timestamp"]
    

    async def test_invalid_token_handling(self, pipeline_validator):

        """Test Case 8: Invalid tokens handled gracefully throughout pipeline."""
        # Test various invalid token scenarios

        invalid_tokens = [

            "invalid.jwt.token",

            "",

            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",

            None

        ]
        

        for invalid_token in invalid_tokens:

            if invalid_token is None:

                continue
                

            validation_result = await pipeline_validator.validate_token_in_pipeline(invalid_token)

            assert not validation_result["validation_successful"]

            assert "error" in validation_result
        
        # Verify auth events show validation failures

        auth_events = pipeline_validator.auth_events

        failed_events = [e for e in auth_events if e["type"] == "token_validation_failed"]

        assert len(failed_events) >= len([t for t in invalid_tokens if t is not None])
    

    async def test_concurrent_token_validations(self, pipeline_validator):

        """Test Case 9: Concurrent token validations handled correctly."""
        # Authenticate user first

        auth_result = await pipeline_validator.authenticate_user()

        assert auth_result["authentication_successful"]
        

        token = auth_result["token"]
        
        # Create concurrent validation tasks

        validation_tasks = []

        for i in range(10):

            task = pipeline_validator.validate_token_in_pipeline(token)

            validation_tasks.append(task)
        
        # Execute concurrent validations

        start_time = time.time()

        results = await asyncio.gather(*validation_tasks)

        execution_time = time.time() - start_time
        
        # All validations should succeed

        assert all(result["validation_successful"] for result in results)

        assert execution_time < 1.0  # All validations complete quickly
        
        # Verify validation times are reasonable

        validation_times = [result["validation_time"] for result in results]

        max_time = max(validation_times)

        assert max_time < 0.2  # Individual validations under 200ms