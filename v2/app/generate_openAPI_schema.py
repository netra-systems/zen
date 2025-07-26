# generate_schema.py
import json
import uvicorn
from fastapi.testclient import TestClient
from main import app # Import your FastAPI app instance

def generate_openapi_schema():
    """Generates and saves the OpenAPI schema."""
    client = TestClient(app)
    response = client.get("/openapi.json")
    
    with open("openapi.json", "w") as f:
        json.dump(response.json(), f, indent=2)
    
    print("✅ OpenAPI schema saved to openapi.json")

if __name__ == "__main__":
    generate_openapi_schema()