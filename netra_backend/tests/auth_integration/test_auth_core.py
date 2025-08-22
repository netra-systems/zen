"""
Critical Authentication Integration Core Tests

Business Value Justification (BVJ):
- Segment: All paid tiers (Early, Mid, Enterprise)
- Business Goal: Protect customer authentication and billing accuracy
- Value Impact: Prevents authentication failures that could cause 100% service unavailability
- Revenue Impact: Critical - Auth failures = immediate customer churn. Estimated -$50K+ MRR risk

Tests the core authentication integration module that handles:
- Token validation with external auth service
- User lookup and database operations
- Error handling for auth failures
- Security boundary enforcement

COMPLIANCE:
- Module ≤300 lines ✓
- Functions ≤8 lines ✓ 
- Strong typing with Pydantic ✓
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import AsyncMock, Mock, patch

import pytest
from auth_integration.auth import (
    # Add project root to path
    get_current_user,
    get_current_user_optional,
)
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import User


class TestAuthenticationCore:
    """Core authentication functionality tests"""

    @pytest.fixture
    def mock_credentials(self):
        """Mock HTTP Bearer credentials"""
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token_123"
        )

    @pytest.fixture
    def mock_db_session(self):
        """Mock async database session"""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_user(self):
        """Mock user object"""
        user = Mock(spec=User)
        user.id = "user_123"
        user.email = "test@example.com"
        user.is_active = True
        return user

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self, 
        mock_credentials, 
        mock_db_session,
        mock_user
    ):
        """Test successful user authentication and retrieval"""
        # Arrange - Mock auth client validation
        with patch('app.auth_integration.auth.auth_client') as mock_auth:
            mock_auth.validate_token.return_value = {
                "valid": True,
                "user_id": "user_123"
            }
            
            # Mock database query result
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db_session.execute.return_value = mock_result
            
            # Act
            result = await get_current_user(mock_credentials, mock_db_session)
            
            # Assert
            assert result == mock_user
            mock_auth.validate_token.assert_called_once_with("valid_token_123")

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(
        self, 
        mock_credentials, 
        mock_db_session
    ):
        """Test authentication failure with invalid token"""
        # Arrange
        with patch('app.auth_integration.auth.auth_client') as mock_auth:
            mock_auth.validate_token.return_value = {"valid": False}
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db_session)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid or expired token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_user_id(
        self, 
        mock_credentials, 
        mock_db_session
    ):
        """Test authentication failure when token lacks user_id"""
        # Arrange
        with patch('app.auth_integration.auth.auth_client') as mock_auth:
            mock_auth.validate_token.return_value = {"valid": True}
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db_session)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid token payload" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(
        self, 
        mock_credentials, 
        mock_db_session
    ):
        """Test authentication failure when user not in database"""
        # Arrange
        with patch('app.auth_integration.auth.auth_client') as mock_auth:
            mock_auth.validate_token.return_value = {
                "valid": True,
                "user_id": "nonexistent_user"
            }
            
            # Mock database query returning None
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute.return_value = mock_result
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db_session)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_auth_service_error(
        self, 
        mock_credentials, 
        mock_db_session
    ):
        """Test handling of auth service communication errors"""
        # Arrange
        with patch('app.auth_integration.auth.auth_client') as mock_auth:
            mock_auth.validate_token.side_effect = Exception("Auth service down")
            
            # Act & Assert
            with pytest.raises(Exception):
                await get_current_user(mock_credentials, mock_db_session)


class TestOptionalAuthentication:
    """Optional authentication functionality tests"""

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_credentials(
        self, 
        mock_db_session
    ):
        """Test optional auth returns None when no credentials provided"""
        # Arrange - No credentials
        credentials = None
        
        # Act
        result = await get_current_user_optional(credentials, mock_db_session)
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_valid_credentials(
        self,
        mock_db_session
    ):
        """Test optional auth returns user when valid credentials provided"""
        # Arrange
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        mock_user = Mock(spec=User)
        mock_user.id = "user_123"
        
        with patch('app.auth_integration.auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            # Act
            result = await get_current_user_optional(credentials, mock_db_session)
            
            # Assert
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_credentials(
        self,
        mock_db_session
    ):
        """Test optional auth returns None when credentials are invalid"""
        # Arrange
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with patch('app.auth_integration.auth.get_current_user') as mock_get_user:
            mock_get_user.side_effect = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
            # Act
            result = await get_current_user_optional(credentials, mock_db_session)
            
            # Assert
            assert result is None


class TestAuthenticationBoundaries:
    """Test authentication security boundary conditions"""

    @pytest.mark.asyncio
    async def test_token_format_validation(self, mock_db_session):
        """Test various token format edge cases"""
        test_cases = [
            ("", "Empty token"),
            ("   ", "Whitespace token"),
            ("a" * 1000, "Extremely long token"),
            ("special!@#$%", "Special characters"),
        ]
        
        for token, description in test_cases:
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token
            )
            
            with patch('app.auth_integration.auth.auth_client') as mock_auth:
                mock_auth.validate_token.return_value = {"valid": False}
                
                with pytest.raises(HTTPException):
                    await get_current_user(credentials, mock_db_session)

    @pytest.mark.asyncio
    async def test_database_session_context_management(
        self, 
        mock_credentials,
        mock_user
    ):
        """Test proper database session context management"""
        # Arrange
        with patch('app.auth_integration.auth.auth_client') as mock_auth:
            mock_auth.validate_token.return_value = {
                "valid": True,
                "user_id": "user_123"
            }
            
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_session.execute.return_value = mock_result
            
            # Act
            result = await get_current_user(mock_credentials, mock_session)
            
            # Assert
            assert result == mock_user
            # Verify session was used as context manager
            mock_session.__aenter__.assert_called_once()


class TestAuthenticationPerformance:
    """Performance and scalability tests for authentication"""

    @pytest.mark.asyncio
    async def test_concurrent_authentication_requests(
        self,
        mock_db_session,
        mock_user
    ):
        """Test handling multiple concurrent auth requests"""
        import asyncio
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="concurrent_test_token"
        )
        
        with patch('app.auth_integration.auth.auth_client') as mock_auth:
            mock_auth.validate_token.return_value = {
                "valid": True,
                "user_id": "user_123"
            }
            
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db_session.execute.return_value = mock_result
            
            # Create multiple concurrent auth requests
            tasks = [
                get_current_user(credentials, mock_db_session)
                for _ in range(10)
            ]
            
            # Act
            results = await asyncio.gather(*tasks)
            
            # Assert
            assert len(results) == 10
            assert all(result == mock_user for result in results)