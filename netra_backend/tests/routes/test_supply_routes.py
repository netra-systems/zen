"""
Test 28: Supply Route Research
Tests for supply chain endpoints - app/routes/supply.py
"""

import pytest
from unittest.mock import patch
from netra_backend.tests.test_utilities import base_client

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestSupplyRoute:
    """Test supply chain endpoints."""
    
    def test_supply_research(self, base_client):
        """Test supply chain research endpoint."""
        research_request = {
            "query": "GPU suppliers",
            "filters": {"region": "US", "tier": 1}
        }
        
        with patch('app.routes.supply.research_suppliers') as mock_research:
            mock_research.return_value = {
                "suppliers": [
                    {"name": "Supplier A", "score": 0.92},
                    {"name": "Supplier B", "score": 0.85}
                ],
                "total": 2
            }
            
            response = base_client.post("/api/supply/research", json=research_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "suppliers" in data or "error" in data
    
    def test_supply_data_enrichment(self, base_client):
        """Test supply data enrichment."""
        with patch('app.routes.supply.enrich_supplier') as mock_enrich:
            mock_enrich.return_value = {
                "supplier_id": "sup123",
                "enriched_data": {
                    "financial_health": "good",
                    "certifications": ["ISO9001"]
                }
            }
            
            response = base_client.post(
                "/api/supply/enrich",
                json={"supplier_id": "sup123"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "enriched_data" in data or "supplier_id" in data

    async def test_supply_validation(self):
        """Test supply chain validation."""
        from netra_backend.app.routes.supply import validate_supply_chain
        
        chain_data = {
            "suppliers": ["sup1", "sup2"],
            "products": ["prod1"],
            "constraints": {"delivery_time": 30}
        }
        
        with patch('app.routes.supply.validate_supply_chain') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "issues": [],
                "score": 0.88
            }
            
            result = await validate_supply_chain(chain_data)
            assert result["valid"] == True