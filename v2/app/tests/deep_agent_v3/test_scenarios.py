import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models_clickhouse import AnalysisRequest

client = TestClient(app)
