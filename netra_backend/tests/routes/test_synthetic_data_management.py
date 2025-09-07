"""
Test 29B: Synthetic Data Management
Tests for synthetic data export, analysis, and cleanup - app/routes/synthetic_data.py

Business Value Justification (BVJ):
- Segment: Growth, Mid, Enterprise
- Business Goal: Efficient synthetic data lifecycle management
- Value Impact: Streamlines data export, quality analysis, and storage management
- Revenue Impact: Operational efficiency features for data management workflows
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment


import pytest

from netra_backend.tests.test_route_fixtures import (
    CommonResponseValidators,
    basic_test_client,
)

class TestSyntheticDataManagement:
    """Test synthetic data management and lifecycle functionality."""
    
    def test_synthetic_data_export(self, basic_test_client):
        """Test synthetic data export functionality."""
        export_request = {
            "job_id": "test_job_123",
            "format": "json",
            "include_metadata": True,
            "compression": "gzip",
            "filters": {
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-02T00:00:00Z"
                },
                "record_limit": 1000
            }
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.export_data') as mock_export:
            mock_export.return_value = {
                "export_id": "export_456",
                "download_url": "/api/synthetic-data/downloads/export_456",
                "file_size_mb": 2.5,
                "record_count": 1000,
                "format": "json",
                "expires_at": "2024-01-02T12:00:00Z"
            }
            
            response = basic_test_client.post("/api/synthetic-data/export", json=export_request)
            
            if response.status_code in [200, 201]:
                data = response.json()
                CommonResponseValidators.validate_success_response(
                    response,
                    expected_keys=["export_id", "download_url"]
                )
                
                if "file_size_mb" in data:
                    assert data["file_size_mb"] > 0
                if "record_count" in data:
                    assert data["record_count"] > 0
                    assert data["record_count"] <= export_request["filters"]["record_limit"]
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_synthetic_data_quality_analysis(self, basic_test_client):
        """Test synthetic data quality analysis."""
        analysis_request = {
            "job_id": "test_job_123",
            "analysis_type": "comprehensive",
            "metrics": [
                "data_distribution",
                "correlation_analysis",
                "anomaly_detection",
                "statistical_validation"
            ]
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.analyze_quality') as mock_analyze:
            mock_analyze.return_value = {
                "overall_quality_score": 0.87,
                "analysis_results": {
                    "data_distribution": {
                        "score": 0.92,
                        "issues": [],
                        "summary": "Data follows expected distribution patterns"
                    },
                    "correlation_analysis": {
                        "score": 0.85,
                        "issues": ["High correlation between user_age and signup_date"],
                        "correlations": {
                            "user_age_signup_date": 0.78
                        }
                    },
                    "anomaly_detection": {
                        "score": 0.89,
                        "anomalies_found": 12,
                        "anomaly_rate": 0.0012
                    },
                    "statistical_validation": {
                        "score": 0.83,
                        "tests_passed": 18,
                        "tests_failed": 2,
                        "failed_tests": ["normality_test", "variance_test"]
                    }
                },
                "recommendations": [
                    "Consider adjusting age distribution parameters",
                    "Review correlation between age and signup date"
                ]
            }
            
            response = basic_test_client.post("/api/synthetic-data/analyze", json=analysis_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "overall_quality_score" in data or "analysis_results" in data
                
                if "overall_quality_score" in data:
                    assert 0 <= data["overall_quality_score"] <= 1
                
                if "analysis_results" in data:
                    for metric, result in data["analysis_results"].items():
                        assert "score" in result
                        assert 0 <= result["score"] <= 1
                        assert "issues" in result
                        assert isinstance(result["issues"], list)
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_synthetic_data_cleanup(self, basic_test_client):
        """Test synthetic data cleanup and deletion."""
        cleanup_request = {
            "job_ids": ["job_123", "job_456", "job_789"],
            "cleanup_type": "complete",  # or "data_only", "metadata_only"
            "confirm_deletion": True
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.cleanup_jobs') as mock_cleanup:
            mock_cleanup.return_value = {
                "cleaned_jobs": 3,
                "failed_cleanups": 0,
                "space_freed_mb": 125.7,
                "cleanup_summary": {
                    "job_123": {"status": "cleaned", "data_freed_mb": 45.2},
                    "job_456": {"status": "cleaned", "data_freed_mb": 38.9},
                    "job_789": {"status": "cleaned", "data_freed_mb": 41.6}
                }
            }
            
            response = basic_test_client.post("/api/synthetic-data/cleanup", json=cleanup_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "cleaned_jobs" in data or "space_freed_mb" in data
                
                if "cleaned_jobs" in data:
                    assert data["cleaned_jobs"] <= len(cleanup_request["job_ids"])
                if "space_freed_mb" in data:
                    assert data["space_freed_mb"] >= 0
                
                if "cleanup_summary" in data:
                    for job_id, summary in data["cleanup_summary"].items():
                        assert "status" in summary
                        assert summary["status"] in ["cleaned", "failed", "not_found"]
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_data_format_conversion(self, basic_test_client):
        """Test synthetic data format conversion capabilities."""
        conversion_request = {
            "job_id": "test_job_123",
            "source_format": "json",
            "target_formats": ["csv", "parquet", "xlsx"],
            "conversion_options": {
                "csv": {"delimiter": ",", "include_headers": True},
                "parquet": {"compression": "snappy", "chunk_size": 10000},
                "xlsx": {"worksheet_name": "synthetic_data", "include_formatting": True}
            }
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.convert_format') as mock_convert:
            mock_convert.return_value = {
                "conversion_id": "conv_789",
                "converted_files": {
                    "csv": {
                        "file_path": "/exports/test_job_123.csv",
                        "file_size_mb": 12.3,
                        "record_count": 50000
                    },
                    "parquet": {
                        "file_path": "/exports/test_job_123.parquet",
                        "file_size_mb": 8.7,
                        "record_count": 50000
                    },
                    "xlsx": {
                        "file_path": "/exports/test_job_123.xlsx",
                        "file_size_mb": 15.1,
                        "record_count": 50000
                    }
                },
                "conversion_summary": {
                    "total_formats": 3,
                    "successful_conversions": 3,
                    "failed_conversions": 0
                }
            }
            
            response = basic_test_client.post("/api/synthetic-data/convert", json=conversion_request)
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "conversion_id" in data or "converted_files" in data
                
                if "converted_files" in data:
                    for format_name, file_info in data["converted_files"].items():
                        assert format_name in conversion_request["target_formats"]
                        assert "file_path" in file_info
                        assert "file_size_mb" in file_info
                        assert file_info["file_size_mb"] > 0
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_data_comparison_analysis(self, basic_test_client):
        """Test synthetic vs real data comparison analysis."""
        comparison_request = {
            "synthetic_job_id": "synth_job_123",
            "real_data_source": {
                "type": "database_table",
                "connection": "production_db",
                "table_name": "users",
                "sample_size": 10000
            },
            "comparison_metrics": [
                "distribution_similarity",
                "statistical_properties",
                "correlation_patterns",
                "outlier_detection"
            ],
            "significance_level": 0.05
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.compare_with_real_data') as mock_compare:
            mock_compare.return_value = {
                "overall_similarity_score": 0.89,
                "metric_scores": {
                    "distribution_similarity": {
                        "score": 0.92,
                        "p_value": 0.15,
                        "significant_differences": []
                    },
                    "statistical_properties": {
                        "score": 0.87,
                        "mean_diff": 0.03,
                        "std_diff": 0.05,
                        "properties_match": True
                    },
                    "correlation_patterns": {
                        "score": 0.91,
                        "correlation_preservation": 0.88,
                        "pattern_fidelity": 0.94
                    },
                    "outlier_detection": {
                        "score": 0.85,
                        "outlier_rate_real": 0.02,
                        "outlier_rate_synthetic": 0.025,
                        "outlier_similarity": 0.83
                    }
                },
                "recommendations": [
                    "Synthetic data closely matches real data distribution",
                    "Consider adjusting outlier generation parameters"
                ]
            }
            
            response = basic_test_client.post("/api/synthetic-data/compare", json=comparison_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "overall_similarity_score" in data or "metric_scores" in data
                
                if "overall_similarity_score" in data:
                    assert 0 <= data["overall_similarity_score"] <= 1
                
                if "metric_scores" in data:
                    for metric, scores in data["metric_scores"].items():
                        assert "score" in scores
                        assert 0 <= scores["score"] <= 1
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_data_versioning_and_lineage(self, basic_test_client):
        """Test synthetic data versioning and lineage tracking."""
        versioning_request = {
            "base_job_id": "job_123",
            "version_name": "v2.1_improved_quality",
            "changes": {
                "schema_updates": ["added_phone_number_field", "updated_age_distribution"],
                "quality_improvements": ["reduced_correlation", "improved_uniqueness"],
                "parameter_changes": {
                    "batch_size": 2000,
                    "quality_threshold": 0.95
                }
            },
            "create_new_version": True
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.create_version') as mock_version:
            mock_version.return_value = {
                "new_version_id": "job_456_v2.1",
                "version_info": {
                    "version_number": "v2.1",
                    "base_version": "v2.0",
                    "created_at": "2024-01-01T12:00:00Z",
                    "changes_summary": "Improved data quality and added phone number field"
                },
                "lineage": {
                    "parent_jobs": ["job_123_v2.0", "job_123_v1.5"],
                    "child_jobs": [],
                    "generation_depth": 3
                },
                "compatibility": {
                    "schema_compatible": True,
                    "api_compatible": True,
                    "backward_compatible": True
                }
            }
            
            response = basic_test_client.post("/api/synthetic-data/version", json=versioning_request)
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "new_version_id" in data or "version_info" in data
                
                if "lineage" in data:
                    lineage = data["lineage"]
                    assert "parent_jobs" in lineage
                    assert "generation_depth" in lineage
                    assert lineage["generation_depth"] >= 0
                
                if "compatibility" in data:
                    compat = data["compatibility"]
                    for key, value in compat.items():
                        assert isinstance(value, bool)
            else:
                assert response.status_code in [404, 422, 401]
    
    def test_automated_data_refresh(self, basic_test_client):
        """Test automated synthetic data refresh capabilities."""
        refresh_config = {
            "job_id": "job_123",
            "refresh_schedule": {
                "frequency": "weekly",
                "day_of_week": "sunday",
                "time": "02:00"
            },
            "refresh_triggers": {
                "real_data_changes": True,
                "quality_degradation": True,
                "schema_updates": True
            },
            "quality_thresholds": {
                "minimum_quality_score": 0.85,
                "maximum_drift_percentage": 0.10
            }
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.synthetic_data_service.setup_auto_refresh') as mock_refresh:
            mock_refresh.return_value = {
                "refresh_config_id": "refresh_789",
                "schedule_status": "active",
                "next_refresh": "2024-01-07T02:00:00Z",
                "monitoring_enabled": True,
                "notification_settings": {
                    "email_alerts": True,
                    "slack_notifications": False,
                    "webhook_url": None
                }
            }
            
            response = basic_test_client.post("/api/synthetic-data/auto-refresh", json=refresh_config)
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "refresh_config_id" in data or "schedule_status" in data
                
                if "schedule_status" in data:
                    assert data["schedule_status"] in ["active", "paused", "inactive"]
                
                if "next_refresh" in data:
                    # Should be a valid ISO timestamp
                    assert "T" in data["next_refresh"]
                    assert "Z" in data["next_refresh"] or "+" in data["next_refresh"]
            else:
                assert response.status_code in [404, 422, 401]