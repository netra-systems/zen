"""
Focused tests for Real Data Services - corpus generation and data processing
Tests real data generation, corpus management, and synthetic data creation
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

import os
import sys
import asyncio
import pytest
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar
from pathlib import Path
import functools
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

T = TypeVar('T')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.synthetic_data_service import SyntheticDataService
from app.services.corpus_service import CorpusService
from app.services.supply_research_service import SupplyResearchService
from app.services.supply_catalog_service import SupplyCatalogService
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Test markers for data services
pytestmark = [
    pytest.mark.real_services,
    pytest.mark.real_data,
    pytest.mark.e2e
]

# Skip tests if real services not enabled
skip_if_no_real_services = pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_LLM_TESTING") != "true",
    reason="Real service tests disabled. Set ENABLE_REAL_LLM_TESTING=true to run"
)


class TestRealDataServices:
    """Test real data services integration"""
    
    # Timeout configurations for data services
    DATA_TIMEOUT = 60  # seconds
    CORPUS_TIMEOUT = 90  # seconds
    
    @staticmethod
    def with_retry_and_timeout(timeout: int = 30, max_attempts: int = 3):
        """Decorator to add retry logic and timeout to service calls"""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry_if=retry_if_exception_type((ConnectionError, TimeoutError, asyncio.TimeoutError))
            )
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            return wrapper
        return decorator
    
    @pytest.fixture(scope="class")
    async def test_user_data(self):
        """Create test user data for real service tests"""
        return {
            "user_id": f"test_user_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "name": "Test User Real Data Services"
        }
    
    @pytest.fixture(scope="class")
    async def synthetic_data_service(self):
        """Initialize real synthetic data service for testing"""
        return SyntheticDataService()
    
    @pytest.fixture(scope="class")
    async def corpus_service(self):
        """Initialize real corpus service for testing"""
        return CorpusService()
    
    @pytest.fixture(scope="class")
    async def supply_research_service(self):
        """Initialize real supply research service for testing"""
        return SupplyResearchService()

    def _create_corpus_generation_config(self):
        """Create configuration for corpus generation testing"""
        return {
            "domain": "automotive_supply_chain",
            "topics": ["risk_assessment", "cost_optimization", "supplier_evaluation"],
            "sample_size": 10,
            "quality_threshold": 0.8
        }

    def _validate_corpus_generation_result(self, result, config):
        """Validate corpus generation results"""
        assert result is not None
        assert "generated_samples" in result or "corpus_data" in result
        sample_count = len(result.get("generated_samples", result.get("corpus_data", [])))
        assert sample_count >= config["sample_size"] * 0.8  # Allow 20% variance
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=90)
    async def test_corpus_generation_with_real_data(self):
        """Test corpus generation with real data sources"""
        config = self._create_corpus_generation_config()
        corpus_service = CorpusService()
        result = await corpus_service.generate_corpus(
            domain=config["domain"],
            topics=config["topics"],
            sample_size=config["sample_size"]
        )
        self._validate_corpus_generation_result(result, config)
        logger.info(f"Corpus generation completed for domain: {config['domain']}")

    def _create_synthetic_data_spec(self):
        """Create specification for synthetic data generation"""
        return {
            "data_type": "supply_chain_metrics",
            "schema": {
                "supplier_id": "string",
                "performance_score": "float",
                "delivery_time": "int",
                "quality_rating": "float"
            },
            "record_count": 100,
            "constraints": {
                "performance_score": {"min": 0.0, "max": 1.0},
                "quality_rating": {"min": 1.0, "max": 5.0}
            }
        }

    def _validate_synthetic_data_result(self, result, spec):
        """Validate synthetic data generation results"""
        assert result is not None
        assert "data" in result or isinstance(result, list)
        data = result.get("data", result) if isinstance(result, dict) else result
        assert len(data) >= spec["record_count"] * 0.9  # Allow 10% variance
        
        # Validate schema compliance for first few records
        for record in data[:3]:
            for field in spec["schema"]:
                assert field in record
        
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=60)
    async def test_synthetic_data_generation_real(self, synthetic_data_service):
        """Test synthetic data generation with real constraints"""
        spec = self._create_synthetic_data_spec()
        result = await synthetic_data_service.generate_data(
            data_type=spec["data_type"],
            schema=spec["schema"],
            record_count=spec["record_count"],
            constraints=spec["constraints"]
        )
        self._validate_synthetic_data_result(result, spec)
        logger.info(f"Synthetic data generation completed: {len(result)} records")

    def _create_supply_research_query(self):
        """Create supply research query for testing"""
        return {
            "industry": "automotive",
            "category": "semiconductors",
            "geographic_region": "asia_pacific",
            "research_depth": "comprehensive"
        }

    def _validate_supply_research_result(self, result, query):
        """Validate supply research results"""
        assert result is not None
        assert "suppliers" in result or "research_data" in result
        suppliers = result.get("suppliers", result.get("research_data", []))
        assert len(suppliers) > 0
        
        # Validate supplier data structure
        for supplier in suppliers[:3]:
            assert "name" in supplier or "supplier_name" in supplier
            assert "location" in supplier or "geographic_region" in supplier
        
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=120)
    async def test_supply_chain_analysis_real(self):
        """Test real supply chain analysis and research"""
        query = self._create_supply_research_query()
        research_service = SupplyResearchService()
        result = await research_service.research_suppliers(
            industry=query["industry"],
            category=query["category"],
            region=query["geographic_region"]
        )
        self._validate_supply_research_result(result, query)
        logger.info(f"Supply chain analysis completed for {query['industry']}")

    def _create_data_quality_spec(self):
        """Create data quality testing specification"""
        return {
            "completeness_threshold": 0.95,
            "accuracy_threshold": 0.90,
            "consistency_threshold": 0.85,
            "sample_size": 50
        }

    def _validate_data_quality_metrics(self, metrics, spec):
        """Validate data quality metrics"""
        assert "completeness" in metrics
        assert "accuracy" in metrics
        assert metrics["completeness"] >= spec["completeness_threshold"]
        assert metrics["accuracy"] >= spec["accuracy_threshold"]
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=60)
    async def test_data_quality_validation_real(self, synthetic_data_service):
        """Test real data quality validation"""
        spec = self._create_data_quality_spec()
        
        # Generate test data
        test_data = await synthetic_data_service.generate_data(
            data_type="quality_test",
            record_count=spec["sample_size"]
        )
        
        # Validate quality
        metrics = await synthetic_data_service.validate_quality(test_data)
        self._validate_data_quality_metrics(metrics, spec)
        logger.info("Data quality validation completed successfully")

    def _create_corpus_search_query(self):
        """Create corpus search query for testing"""
        return {
            "query": "supply chain risk management",
            "domain": "automotive",
            "max_results": 20,
            "relevance_threshold": 0.7
        }

    def _validate_corpus_search_results(self, results, query):
        """Validate corpus search results"""
        assert results is not None
        assert isinstance(results, list)
        assert len(results) <= query["max_results"]
        
        # Validate result structure
        for result in results[:3]:
            assert "content" in result or "text" in result
            assert "relevance_score" in result or "score" in result
        
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=45)
    async def test_corpus_search_functionality(self, corpus_service):
        """Test corpus search functionality with real data"""
        query = self._create_corpus_search_query()
        results = await corpus_service.search(
            query=query["query"],
            domain=query["domain"],
            max_results=query["max_results"]
        )
        self._validate_corpus_search_results(results, query)
        logger.info(f"Corpus search completed: {len(results)} results found")

    def _create_data_pipeline_config(self):
        """Create data pipeline configuration for testing"""
        return {
            "source": "external_api",
            "transformation": "normalize_and_validate",
            "destination": "corpus_storage",
            "batch_size": 25
        }

    def _validate_data_pipeline_result(self, result, config):
        """Validate data pipeline execution results"""
        assert result is not None
        assert "processed_records" in result
        assert "errors" in result
        assert result["processed_records"] > 0
        assert result["errors"] <= result["processed_records"] * 0.1  # Max 10% error rate
        return True

    @skip_if_no_real_services
    @with_retry_and_timeout(timeout=90)
    async def test_data_pipeline_integration(self, synthetic_data_service):
        """Test data pipeline integration with real services"""
        config = self._create_data_pipeline_config()
        result = await synthetic_data_service.run_pipeline(
            source=config["source"],
            transformation=config["transformation"],
            destination=config["destination"],
            batch_size=config["batch_size"]
        )
        self._validate_data_pipeline_result(result, config)
        logger.info("Data pipeline integration test completed successfully")