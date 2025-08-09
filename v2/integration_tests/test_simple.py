import pytest
from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient

app = FastAPI()

def get_request_dependent_service(request: Request):
    return {"request_url": str(request.url)}

@app.get("/")
def read_root(service: dict = Depends(get_request_dependent_service)):
    return service

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_simple_dependency(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "http://testserver/" in response.json()["request_url"]