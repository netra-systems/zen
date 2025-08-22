#!/usr/bin/env python
"""
Diagnostic script to check users in the database
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from netra_backend.app.config import settings
from netra_backend.app.db.models_postgres import User


async def check_users():
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        print(f"\n{'='*60}")
        print(f"Total users in database: {len(users)}")
        print(f"{'='*60}\n")
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Full Name: {user.full_name}")
            print(f"Active: {user.is_active}")
            print(f"Created: {user.created_at}")
            print(f"{'-'*40}")
        
        # Check for the specific user that was not found
        specific_user_id = "84f70a8b-86e4-45bd-ad62-962f270d39d7"
        specific_result = await session.execute(
            select(User).where(User.id == specific_user_id)
        )
        specific_user = specific_result.scalars().first()
        
        print(f"\nLooking for specific user ID: {specific_user_id}")
        if specific_user:
            print(f"Found: {specific_user.email}")
        else:
            print("NOT FOUND - This user does not exist in the database")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_users())