#!/usr/bin/env python
"""
Script to create a test user in the database
"""
import os
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from netra_backend.app.config import settings
from netra_backend.app.db.models_postgres import User
from netra_backend.app.services.key_manager import KeyManager
from netra_backend.app.services.security_service import SecurityService


async def create_test_user():
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Initialize security service for password hashing
    key_manager = KeyManager.load_from_settings(settings)
    security_service = SecurityService(key_manager)
    
    async with async_session() as session:
        # Check if test user already exists
        existing_user = await security_service.get_user(session, "test@example.com")
        if existing_user:
            print(f"\nTest user already exists with ID: {existing_user.id}")
            return existing_user.id
        
        # Create new test user
        user_id = str(uuid.uuid4())
        hashed_password = security_service.get_password_hash("testpassword123")
        
        test_user = User(
            id=user_id,
            email="test@example.com",
            full_name="Test User",
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False
        )
        
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)
        
        print(f"\n{'='*60}")
        print(f"Test user created successfully!")
        print(f"{'='*60}")
        print(f"ID: {test_user.id}")
        print(f"Email: {test_user.email}")
        print(f"Password: testpassword123")
        print(f"{'='*60}")
        print(f"\nYou can now login with these credentials")
        
        return test_user.id
    
    await engine.dispose()

if __name__ == "__main__":
    user_id = asyncio.run(create_test_user())
    print(f"\nUser ID for testing: {user_id}")