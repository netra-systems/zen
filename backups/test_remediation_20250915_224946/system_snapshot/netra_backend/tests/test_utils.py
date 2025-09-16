"""Central testing utilities module.

Provides common utilities for all test files.
"""

import sys
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.db.models_postgres import User


def setup_test_path() -> Path:
    """Set up test path for imports.
    
    Adds the netra_backend directory to sys.path if it's not already there
    so that all tests can import from the netra_backend module.
    
    Handles Windows and Unix path differences automatically.
    
    Returns:
        Path: The project root path
    """
    # Navigate from tests/ -> netra_backend/ -> project_root/
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    netra_backend_dir = current_file.parent.parent
    
    netra_backend_str = str(netra_backend_dir)
    if netra_backend_str not in sys.path:
        sys.path.insert(0, netra_backend_str)
    
    return project_root


async def create_test_user(db: AsyncSession, email: str = "test@example.com", 
                          name: str = "Test User") -> User:
    """Create a test user in the database.
    
    Args:
        db: Database session
        email: User email
        name: User name
        
    Returns:
        User: Created user instance
    """
    from netra_backend.app.services.database.user_crud import UserCRUD
    
    user_crud = UserCRUD()
    
    # Check if user exists
    existing = await user_crud.get_user_by_email(db, email)
    if existing:
        return existing
    
    # Create new user
    user_data = {
        "email": email,
        "name": name,
        "hashed_password": "hashed_test_password",
        "is_active": True,
        "is_verified": True
    }
    
    user = User(**user_data)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


def create_test_token(user_id: str, expires_in: int = 3600) -> str:
    """Create a test JWT token for authentication.
    
    DEPRECATED: Use tests.helpers.auth_test_utils.TestAuthHelper instead.
    This function is maintained for backward compatibility only.
    
    Args:
        user_id: User ID to encode in token
        expires_in: Token expiration time in seconds (ignored - uses standard expiry)
        
    Returns:
        str: JWT token
    """
    from tests.helpers.auth_test_utils import TestAuthHelper
    
    auth_helper = TestAuthHelper()
    return auth_helper.create_test_token(user_id)