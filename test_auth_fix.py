"""Test auth service connectivity fix."""
import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_auth_service():
    """Test auth service connectivity."""
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        try:
            health_response = await client.get('http://127.0.0.1:8081/auth/health')
            logger.info(f"Health check: {health_response.status_code} - {health_response.text}")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        # Test validation endpoint
        try:
            validate_response = await client.post(
                'http://127.0.0.1:8081/auth/validate',
                json={'token': 'test-token'}
            )
            logger.info(f"Validation: {validate_response.status_code} - {validate_response.text}")
        except Exception as e:
            logger.error(f"Validation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth_service())