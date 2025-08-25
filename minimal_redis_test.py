"""
Minimal test to isolate the Redis connection issue in 2FA verification.
"""

import asyncio
import json
import time
import uuid
import pytest
import pyotp
from datetime import datetime, timezone

# Import the fixture
from test_framework.fixtures.service_fixtures import isolated_redis_client


@pytest.mark.asyncio
async def test_minimal_redis_setup(isolated_redis_client):
    """Minimal test to reproduce the Redis issue."""
    try:
        print("Starting minimal Redis test")
        
        # Test basic Redis operations
        await isolated_redis_client.ping()
        print("Redis ping successful")
        
        # Test the exact same operation that fails in 2FA test
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        secret_key = pyotp.random_base32()
        
        totp_data = {
            "user_id": user_id,
            "secret_key": secret_key,
            "setup_at": datetime.now(timezone.utc).isoformat(),
            "verified": False,
            "last_used_code": None
        }
        
        totp_key = f"user_totp:{user_id}"
        
        print(f"About to call setex with key: {totp_key}")
        
        # This is the line that's failing in the original test
        await isolated_redis_client.setex(totp_key, 86400 * 30, json.dumps(totp_data))
        
        print("setex call succeeded!")
        
        # Verify it worked
        result = await isolated_redis_client.get(totp_key)
        assert result is not None
        
        data = json.loads(result)
        assert data["user_id"] == user_id
        
        # Cleanup
        await isolated_redis_client.delete(totp_key)
        
        print("Minimal Redis test completed successfully")
        
    except Exception as e:
        print(f"Error in minimal Redis test: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])