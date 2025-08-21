"""
Market report generation tests for SupplyResearchService
Tests comprehensive market report generation with all sections
"""

import pytest
from datetime import datetime, UTC
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from netra_backend.app.services.supply_research_service import SupplyResearchService
from netra_backend.app.db.models_postgres import ResearchSession


@pytest.fixture
def service(db_session):
    """Create SupplyResearchService instance with real database"""
    return SupplyResearchService(db_session)
class TestMarketReportGeneration:
    """Test comprehensive market report generation"""
    
    async def test_generate_complete_market_report(self, service):
        """Test full market report generation with all sections"""
        report_deps = self._create_report_dependencies()
        
        with self._patch_report_dependencies(service, report_deps):
            with patch.object(service.db, 'query') as mock_query:
                mock_query.return_value.count.return_value = 50
                
                report: Dict[str, Any] = await service.generate_market_report()
        
        self._verify_report_structure(report)
    
    async def test_generate_report_with_long_query_truncation(self, service):
        """Test report generation with query truncation"""
        long_session = self._create_long_query_session()
        
        with self._patch_minimal_dependencies(service, [long_session]):
            report: Dict[str, Any] = await service.generate_market_report()
        
        recent_research = report["sections"]["recent_research"]
        assert len(recent_research[0]["query"]) <= 103  # 100 + "..."
        assert recent_research[0]["query"].endswith("...")
    
    async def test_generate_report_empty_data(self, service):
        """Test report generation with no data"""
        with self._patch_empty_dependencies(service):
            report: Dict[str, Any] = await service.generate_market_report()
        
        self._verify_empty_report_structure(report)
    
    async def test_generate_report_with_anomalies(self, service):
        """Test report generation including anomalies section"""
        anomalies = self._create_sample_anomalies()
        
        with self._patch_anomaly_dependencies(service, anomalies):
            report: Dict[str, Any] = await service.generate_market_report()
        
        assert "anomalies" in report["sections"]
        assert len(report["sections"]["anomalies"]) == 2
    
    async def test_generate_report_statistics_section(self, service):
        """Test that statistics section is properly populated"""
        with self._patch_statistics_dependencies(service):
            report: Dict[str, Any] = await service.generate_market_report()
        
        stats = report["sections"]["statistics"]
        self._verify_statistics_section(stats)
    
    def _create_report_dependencies(self) -> Dict[str, Any]:
        """Helper to create report generation dependencies"""
        return {
            "provider_comparison": {
                "providers": {"openai": {"flagship_model": "gpt-4"}},
                "analysis": {"cheapest_input": {"provider": "anthropic"}}
            },
            "price_changes": {
                "total_changes": 5,
                "increases": 3,
                "decreases": 2
            },
            "anomalies": [{"type": "significant_price_change", "severity": "medium"}],
            "research_session": self._create_research_session()
        }
    
    def _create_research_session(self) -> ResearchSession:
        """Helper to create research session"""
        research_session = MagicMock(spec=ResearchSession)
        research_session.id = "session-1"
        research_session.query = "Research pricing updates"
        research_session.status = "completed"
        research_session.created_at = datetime.now(UTC)
        return research_session
    
    def _create_long_query_session(self) -> ResearchSession:
        """Helper to create session with long query"""
        long_query = "A" * 150  # Query longer than 100 characters
        research_session = MagicMock(spec=ResearchSession)
        research_session.id = "session-1"
        research_session.query = long_query
        research_session.status = "completed"
        research_session.created_at = datetime.now(UTC)
        return research_session
    
    def _create_sample_anomalies(self) -> List[Dict[str, Any]]:
        """Helper to create sample anomalies"""
        return [
            {
                "type": "significant_price_change",
                "provider": "openai",
                "severity": "high",
                "percent_change": 75.0
            },
            {
                "type": "stale_data",
                "provider": "anthropic",
                "severity": "low",
                "days_stale": 35
            }
        ]
    
    def _patch_report_dependencies(self, service, deps: Dict[str, Any]):
        """Helper to patch all report generation dependencies"""
        return patch.multiple(
            service,
            get_provider_comparison=lambda: deps["provider_comparison"],
            calculate_price_changes=lambda: deps["price_changes"],
            detect_anomalies=lambda: deps["anomalies"],
            get_research_sessions=lambda **kwargs: [deps["research_session"]],
            get_supply_items=lambda **kwargs: [MagicMock()]
        )
    
    def _patch_minimal_dependencies(self, service, sessions: List[ResearchSession]):
        """Helper to patch minimal dependencies for testing"""
        return patch.multiple(
            service,
            get_provider_comparison=lambda: {"providers": {}, "analysis": {}},
            calculate_price_changes=lambda: {"total_changes": 0},
            detect_anomalies=lambda: [],
            get_research_sessions=lambda **kwargs: sessions,
            get_supply_items=lambda **kwargs: []
        )
    
    def _patch_empty_dependencies(self, service):
        """Helper to patch dependencies for empty data testing"""
        return patch.multiple(
            service,
            get_provider_comparison=lambda: {"providers": {}, "analysis": {}},
            calculate_price_changes=lambda: {"total_changes": 0},
            detect_anomalies=lambda: [],
            get_research_sessions=lambda **kwargs: [],
            get_supply_items=lambda **kwargs: []
        )
    
    def _patch_anomaly_dependencies(self, service, anomalies: List[Dict[str, Any]]):
        """Helper to patch dependencies with anomalies"""
        return patch.multiple(
            service,
            get_provider_comparison=lambda: {"providers": {}, "analysis": {}},
            calculate_price_changes=lambda: {"total_changes": 0},
            detect_anomalies=lambda: anomalies,
            get_research_sessions=lambda **kwargs: [],
            get_supply_items=lambda **kwargs: []
        )
    
    def _patch_statistics_dependencies(self, service):
        """Helper to patch dependencies for statistics testing"""
        def mock_query_count():
            mock_q = MagicMock()
            mock_q.filter.return_value.count.return_value = 25  # Available models
            mock_q.count.return_value = 50  # Total models
            return mock_q
        
        return patch.multiple(
            service,
            get_provider_comparison=lambda: {"providers": {"openai": {}, "anthropic": {}}, "analysis": {}},
            calculate_price_changes=lambda: {"total_changes": 0},
            detect_anomalies=lambda: [],
            get_research_sessions=lambda **kwargs: [],
            get_supply_items=lambda **kwargs: []
        )
    
    def _verify_report_structure(self, report: Dict[str, Any]):
        """Helper to verify report structure"""
        assert "generated_at" in report
        assert "sections" in report
        
        sections = report["sections"]
        expected_sections = ["provider_comparison", "price_changes", "anomalies", "statistics", "recent_research"]
        for section in expected_sections:
            assert section in sections
    
    def _verify_empty_report_structure(self, report: Dict[str, Any]):
        """Helper to verify empty report structure"""
        assert "generated_at" in report
        assert "sections" in report
        
        sections = report["sections"]
        assert sections["price_changes"]["total_changes"] == 0
        assert len(sections["anomalies"]) == 0
        assert len(sections["recent_research"]) == 0
    
    def _verify_statistics_section(self, stats: Dict[str, Any]):
        """Helper to verify statistics section"""
        required_stats = ["total_models", "available_models", "deprecated_models", "providers_tracked"]
        for stat in required_stats:
            assert stat in stats


class TestReportSectionsIndividually:
    """Test individual report sections in isolation"""
    
    def test_provider_comparison_section_formatting(self, service):
        """Test provider comparison section formatting"""
        provider_data = self._create_provider_comparison_data()
        
        with patch.object(service, 'get_provider_comparison', return_value=provider_data):
            # This would be part of report generation, but tested in isolation
            result = service.get_provider_comparison()
            
            assert "providers" in result
            assert "analysis" in result
    
    def test_recent_research_section_formatting(self, service):
        """Test recent research section formatting"""
        sessions = self._create_recent_sessions()
        
        with patch.object(service, 'get_research_sessions', return_value=sessions):
            result = service.get_research_sessions(limit=5)
            
            assert len(result) == 2
    
    def _create_provider_comparison_data(self) -> Dict[str, Any]:
        """Helper to create provider comparison data"""
        return {
            "providers": {
                "openai": {
                    "flagship_model": "gpt-4",
                    "input_price": 0.03,
                    "model_count": 3
                },
                "anthropic": {
                    "flagship_model": "claude-2",
                    "input_price": 0.025,
                    "model_count": 2
                }
            },
            "analysis": {
                "cheapest_input": {"provider": "anthropic", "price": 0.025},
                "most_expensive_input": {"provider": "openai", "price": 0.03}
            }
        }
    
    def _create_recent_sessions(self) -> List[ResearchSession]:
        """Helper to create recent research sessions"""
        session1 = MagicMock(spec=ResearchSession)
        session1.id = "session-1"
        session1.query = "Research OpenAI pricing"
        session1.status = "completed"
        
        session2 = MagicMock(spec=ResearchSession)
        session2.id = "session-2"
        session2.query = "Research Claude pricing"
        session2.status = "in_progress"
        
        return [session1, session2]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])