#!/usr/bin/env python3
"""
Test script to verify issue #942 DataAnalysisResponse SSOT migration fix.
"""

def test_dataanalysisresponse_ssot_migration():
    """Test that DataAnalysisResponse SSOT migration works correctly."""
    print("🔍 Testing DataAnalysisResponse SSOT migration for issue #942...")
    print("=" * 60)
    
    # Test 1: SSOT location should work
    try:
        from netra_backend.app.schemas.shared_types import DataAnalysisResponse
        print("✅ SUCCESS: DataAnalysisResponse imports correctly from SSOT location")
        print(f"   Class: {DataAnalysisResponse}")
        
        # Create an instance to test it works (using SSOT model structure)
        from netra_backend.app.schemas.shared_types import PerformanceMetrics
        import time

        response = DataAnalysisResponse(
            analysis_id="test_analysis_001",
            status="completed",
            results={"insights": ["Finding 1", "Finding 2"], "recommendations": ["Recommendation 1"]},
            metrics=PerformanceMetrics(duration_ms=100.0),
            created_at=time.time()
        )
        print(f"✅ SUCCESS: DataAnalysisResponse instance created successfully")
        print(f"   Analysis ID: {response.analysis_id}")
        print(f"   Status: {response.status}")
        print(f"   Results: {len(response.results)} items")
        
    except ImportError as e:
        print(f"❌ FAILED: Cannot import DataAnalysisResponse from SSOT location: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Error creating DataAnalysisResponse instance: {e}")
        return False

    # Test 2: Legacy location should no longer export it
    try:
        from netra_backend.app.agents.data_sub_agent.models import DataAnalysisResponse
        print("❌ FAILED: DataAnalysisResponse still available from legacy location (should be removed)")
        return False
    except ImportError:
        print("✅ SUCCESS: DataAnalysisResponse correctly removed from legacy location")
    except Exception as e:
        print(f"❌ UNEXPECTED: {e}")
        return False

    # Test 3: Check that other legacy models still work
    try:
        from netra_backend.app.agents.data_sub_agent.models import AnomalyDetectionResponse
        anomaly = AnomalyDetectionResponse(anomalies_found=True, anomaly_count=5)
        print(f"✅ SUCCESS: Other legacy models still work (AnomalyDetectionResponse)")
    except Exception as e:
        print(f"❌ FAILED: Other legacy models broken: {e}")
        return False
    
    print("=" * 60)
    print("🎉 All tests passed! Issue #942 fix is working correctly.")
    return True

if __name__ == "__main__":
    success = test_dataanalysisresponse_ssot_migration()
    exit(0 if success else 1)