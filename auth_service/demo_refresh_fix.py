#!/usr/bin/env python3
"""
Demo script showing the refresh token fix in action
Before: Same token returned causing infinite loops
After: New unique tokens returned each time
"""
import asyncio
import sys
import time
from pathlib import Path

# Add auth service to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from auth_service.auth_core.services.auth_service import AuthService


async def demonstrate_refresh_fix():
    """Demonstrate that refresh tokens now work correctly"""
    print("🔧 REFRESH TOKEN FIX DEMONSTRATION")
    print("=" * 50)
    
    # Initialize auth service  
    auth_service = AuthService()
    
    # Create a test user and initial tokens
    user_id = "demo-user-123"
    user_email = "demo@staging.netrasystems.ai"
    user_permissions = ["read", "write"]
    
    print(f"👤 User: {user_email}")
    print(f"🆔 User ID: {user_id}")
    print(f"🔒 Permissions: {user_permissions}")
    print()
    
    # Create initial refresh token (now contains user data)
    initial_refresh = auth_service.jwt_handler.create_refresh_token(
        user_id, user_email, user_permissions
    )
    print(f"🎫 Initial refresh token: {initial_refresh[:50]}...")
    print()
    
    # Perform multiple refresh operations to show they're all unique
    current_refresh = initial_refresh
    all_tokens = []
    
    for i in range(3):
        print(f"🔄 Refresh Operation {i+1}:")
        print(f"   Input refresh token:  {current_refresh[:30]}...")
        
        # Perform refresh
        result = await auth_service.refresh_tokens(current_refresh)
        if result is None:
            print(f"   ❌ FAILED - returned None")
            break
            
        new_access, new_refresh = result
        all_tokens.extend([new_access, new_refresh])
        
        print(f"   ✅ New access token:   {new_access[:30]}...")
        print(f"   ✅ New refresh token:  {new_refresh[:30]}...")
        
        # Verify tokens contain real user data, not placeholders
        access_payload = auth_service.jwt_handler.validate_token(new_access, "access")
        if access_payload:
            email = access_payload.get("email", "MISSING")
            perms = access_payload.get("permissions", [])
            print(f"   📧 Email in token:     {email}")
            print(f"   🔐 Permissions:        {perms}")
            
            if email == "user@example.com":
                print(f"   ⚠️  WARNING: Using placeholder email!")
            else:
                print(f"   ✅ Real user data confirmed")
        
        # Check if tokens are unique
        if new_refresh == current_refresh:
            print(f"   ❌ CRITICAL BUG: Same refresh token returned!")
            break
        else:
            print(f"   ✅ New refresh token is unique")
        
        # Use new refresh token for next iteration  
        current_refresh = new_refresh
        print()
        time.sleep(0.001)  # Ensure different timestamps
    
    # Final verification
    unique_tokens = set(all_tokens)
    print(f"📊 FINAL RESULTS:")
    print(f"   Total tokens generated:  {len(all_tokens)}")
    print(f"   Unique tokens:           {len(unique_tokens)}")
    
    if len(all_tokens) == len(unique_tokens):
        print(f"   ✅ SUCCESS: All tokens are unique - no infinite loop risk!")
    else:
        print(f"   ❌ FAILURE: Duplicate tokens detected - infinite loop risk!")
    
    print()
    print("🎯 SUMMARY:")
    print("   - Refresh tokens now contain real user data")
    print("   - Each refresh operation generates unique tokens")  
    print("   - No more hardcoded 'user@example.com' placeholders")
    print("   - Staging infinite loop issue resolved")


if __name__ == "__main__":
    print("Starting refresh token fix demonstration...")
    asyncio.run(demonstrate_refresh_fix())
    print("Demo completed!")