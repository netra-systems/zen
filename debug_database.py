#!/usr/bin/env python3
"""Debug script to test database operations and find the parameter binding issue."""

import asyncio
import sys
import os

# Add the backend path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netra_backend'))

async def test_database_operations():
    """Test basic database operations to find the issue."""
    try:
        from netra_backend.app.services.thread_service import ThreadService
        from netra_backend.app.db.postgres import async_session_factory, initialize_postgres
        
        print("[OK] Imports successful")
        
        # Check database configuration
        from netra_backend.app.config import get_config
        config = get_config()
        print(f"[INFO] Database URL configured: {config.database_url is not None}")
        print(f"[INFO] Database URL: {config.database_url[:50] if config.database_url else None}...")
        
        # Use current session factory or initialize if needed
        current_factory = async_session_factory
        
        if current_factory is None:
            print("[WARNING] Database not initialized - attempting to initialize...")
            try:
                current_factory = initialize_postgres()
                print(f"[INFO] Initialize returned: {current_factory}")
                print("[OK] Database initialized successfully")
                if current_factory is None:
                    print("[ERROR] Database initialization failed - session factory is None")
                    return
            except Exception as e:
                print(f"[ERROR] Database initialization failed: {e}")
                import traceback
                traceback.print_exc()
                return
        
        print("[OK] Database factory available")
        
        # Test thread creation
        thread_service = ThreadService()
        
        # Create a session and test thread operations
        async with current_factory() as session:
            print("[OK] Database session created")
            
            # Test thread creation
            user_id = "test_user_123"
            print(f"Testing thread creation for user: {user_id}")
            
            try:
                thread = await thread_service.get_or_create_thread(user_id, session)
                print(f"[OK] Thread created successfully: {thread.id}")
                
                # Test message creation
                message = await thread_service.create_message(
                    thread_id=thread.id,
                    role="user",
                    content="Test message",
                    db=session
                )
                print(f"[OK] Message created successfully: {message.id}")
                
                # Test message retrieval
                messages = await thread_service.get_thread_messages(thread.id, db=session)
                print(f"[OK] Retrieved {len(messages)} messages")
                
            except Exception as e:
                print(f"[ERROR] Database operation failed: {e}")
                print(f"Error type: {type(e)}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database_operations())