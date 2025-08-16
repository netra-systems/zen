"""Test to verify the security headers middleware fix works properly."""

import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from app.middleware.security_headers import SecurityHeadersMiddleware

app = FastAPI()

# Add the security headers middleware
app.add_middleware(SecurityHeadersMiddleware, environment="development")

@app.get("/test")
async def test_endpoint():
    return {"message": "test"}

@app.get("/error")
async def error_endpoint():
    raise ValueError("Test error")

def test_middleware_works():
    """Test that the middleware adds security headers properly."""
    client = TestClient(app)
    
    # Test normal endpoint
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    print("[PASS] Security headers added successfully to normal response")
    
    # Test error endpoint - this would previously cause the assertion error
    response = client.get("/error")
    assert response.status_code == 500
    print("[PASS] Error endpoint handled without assertion error")
    
    print("\n[SUCCESS] All tests passed! The middleware fix is working correctly.")

if __name__ == "__main__":
    test_middleware_works()