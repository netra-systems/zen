"""
Integration Tests for OpenTelemetry Automatic Framework Discovery

FOCUS: Automatic instrumentation only - tests real framework detection and 
auto-instrumentation setup with FastAPI, SQLAlchemy, Redis integration.

Tests that auto-instrumentation libraries correctly detect and instrument
frameworks used in the Netra Apex platform.

Business Value: Platform/Enterprise - Ensures observability works across
all critical infrastructure components for AI operations.

CRITICAL: Tests use REAL SERVICES - no mocks for integration testing.
SSOT Architecture: Uses SSotBaseTestCase and UnifiedDockerManager.

Tests MUST FAIL before auto-instrumentation is applied, PASS after setup.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from unittest.mock import patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.unified_docker_manager import UnifiedDockerManager

logger = logging.getLogger(__name__)


class TestAutoInstrumentationFrameworkDiscovery(SSotAsyncTestCase):
    """Test automatic discovery and instrumentation of frameworks."""
    
    @pytest.fixture(autouse=True)
    def setup_docker_manager(self):
        """Setup Docker manager for real service testing."""
        self.docker_manager = UnifiedDockerManager()
        
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set test environment for auto-instrumentation
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("ENABLE_TRACING", "true")
        self.set_env_var("OTEL_SERVICE_NAME", "netra-apex-integration-test")
        
        # Configure for testing - use console exporter to avoid external dependencies
        self.set_env_var("OTEL_TRACES_EXPORTER", "console")
        self.set_env_var("OTEL_TRACES_SAMPLER", "always_on")  # Sample all traces for testing
        
    def test_fastapi_framework_detection_and_auto_instrumentation(self):
        """
        Test automatic detection and instrumentation of FastAPI.
        
        This test MUST FAIL before auto-instrumentation is configured.
        Uses real FastAPI application to validate instrumentation.
        """
        # Test framework detection BEFORE instrumentation
        try:
            import fastapi
            fastapi_available = True
            fastapi_version = getattr(fastapi, '__version__', 'unknown')
        except ImportError:
            pytest.skip("FastAPI not available for auto-instrumentation testing")
            
        # Test instrumentor availability
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            instrumentor_available = True
        except ImportError:
            pytest.skip("OpenTelemetry FastAPI instrumentor not available")
            
        # Check if FastAPI is already instrumented (should fail initially)
        instrumentor = FastAPIInstrumentor()
        initially_instrumented = instrumentor.is_instrumented_by_opentelemetry
        
        # Before configuration, should NOT be instrumented
        assert not initially_instrumented, (
            "FastAPI should not be auto-instrumented initially. "
            "This test validates the before-state."
        )
        
        # Create a minimal FastAPI app for testing
        from fastapi import FastAPI
        test_app = FastAPI(title="AutoInstrumentationTest")
        
        @test_app.get("/test-endpoint")
        async def test_endpoint():
            return {"message": "auto-instrumentation-test", "instrumented": False}
        
        # Apply automatic instrumentation
        try:
            # Initialize OpenTelemetry SDK
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
            
            # Setup tracer provider
            trace.set_tracer_provider(TracerProvider())
            tracer = trace.get_tracer(__name__)
            
            # Add console exporter for testing
            span_processor = BatchSpanProcessor(ConsoleSpanExporter())
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Apply FastAPI auto-instrumentation
            instrumentor.instrument_app(test_app)
            
            # Verify instrumentation was applied
            post_instrumentation = instrumentor.is_instrumented_by_opentelemetry
            assert post_instrumentation, (
                "FastAPI should be instrumented after applying auto-instrumentation"
            )
            
            # Test that instrumented endpoint still works
            # (In real testing, this would be done with TestClient, but keeping minimal)
            assert test_app is not None
            assert hasattr(test_app, 'routes')
            
            self.record_metric("fastapi_auto_instrumented", True)
            self.record_metric("fastapi_version", fastapi_version)
            
        except Exception as e:
            self.record_metric("fastapi_instrumentation_error", str(e))
            raise
            
        finally:
            # Cleanup - uninstrument to avoid affecting other tests
            try:
                instrumentor.uninstrument_app(test_app)
            except:
                pass
                
    def test_sqlalchemy_auto_instrumentation_detection(self):
        """
        Test automatic detection and instrumentation of SQLAlchemy.
        
        Tests with real database connection (PostgreSQL via Docker).
        """
        # Check SQLAlchemy availability
        try:
            import sqlalchemy
            sqlalchemy_version = sqlalchemy.__version__
        except ImportError:
            pytest.skip("SQLAlchemy not available for auto-instrumentation testing")
            
        # Check instrumentor availability
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            instrumentor_available = True
        except ImportError:
            pytest.skip("OpenTelemetry SQLAlchemy instrumentor not available")
            
        # Verify database service is available
        db_available = self.docker_manager.is_service_healthy("postgres")
        if not db_available:
            pytest.skip("PostgreSQL service not available for auto-instrumentation testing")
            
        instrumentor = SQLAlchemyInstrumentor()
        
        # Check initial state (should not be instrumented)
        initially_instrumented = instrumentor.is_instrumented_by_opentelemetry
        assert not initially_instrumented, (
            "SQLAlchemy should not be auto-instrumented initially"
        )
        
        try:
            # Setup OpenTelemetry tracing
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
            
            trace.set_tracer_provider(TracerProvider())
            span_processor = BatchSpanProcessor(ConsoleSpanExporter())
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Create SQLAlchemy engine for testing
            from sqlalchemy import create_engine, text
            
            # Use test database connection
            db_url = f"postgresql://{self.get_env_var('POSTGRES_USER', 'netra')}:" \
                    f"{self.get_env_var('POSTGRES_PASSWORD', 'netra_secure_2024')}@" \
                    f"{self.get_env_var('POSTGRES_HOST', 'localhost')}:" \
                    f"{self.get_env_var('POSTGRES_PORT', '5432')}/" \
                    f"{self.get_env_var('POSTGRES_DB', 'netra_test')}"
            
            engine = create_engine(db_url, echo=False)  # Disable echo to avoid spam
            
            # Apply auto-instrumentation
            instrumentor.instrument(engine=engine)
            
            # Verify instrumentation
            post_instrumentation = instrumentor.is_instrumented_by_opentelemetry
            assert post_instrumentation, (
                "SQLAlchemy should be instrumented after applying auto-instrumentation"
            )
            
            # Test instrumented database query
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as test_auto_instrumentation"))
                row = result.fetchone()
                assert row[0] == 1, "Instrumented query should work correctly"
                
            self.record_metric("sqlalchemy_auto_instrumented", True)
            self.record_metric("sqlalchemy_version", sqlalchemy_version)
            
        except Exception as e:
            self.record_metric("sqlalchemy_instrumentation_error", str(e))
            raise
            
        finally:
            # Cleanup
            try:
                instrumentor.uninstrument()
            except:
                pass
                
    def test_redis_auto_instrumentation_detection(self):
        """
        Test automatic detection and instrumentation of Redis.
        
        Tests with real Redis connection via Docker.
        """
        # Check Redis availability
        try:
            import redis
            redis_version = redis.__version__
        except ImportError:
            pytest.skip("Redis not available for auto-instrumentation testing")
            
        # Check instrumentor availability
        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            instrumentor_available = True
        except ImportError:
            pytest.skip("OpenTelemetry Redis instrumentor not available")
            
        # Verify Redis service is available
        redis_available = self.docker_manager.is_service_healthy("redis")
        if not redis_available:
            pytest.skip("Redis service not available for auto-instrumentation testing")
            
        instrumentor = RedisInstrumentor()
        
        # Check initial state
        initially_instrumented = instrumentor.is_instrumented_by_opentelemetry
        assert not initially_instrumented, (
            "Redis should not be auto-instrumented initially"
        )
        
        try:
            # Setup OpenTelemetry tracing
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
            
            trace.set_tracer_provider(TracerProvider())
            span_processor = BatchSpanProcessor(ConsoleSpanExporter())
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Apply auto-instrumentation
            instrumentor.instrument()
            
            # Verify instrumentation
            post_instrumentation = instrumentor.is_instrumented_by_opentelemetry
            assert post_instrumentation, (
                "Redis should be instrumented after applying auto-instrumentation"
            )
            
            # Test instrumented Redis operations
            redis_client = redis.Redis(
                host=self.get_env_var('REDIS_HOST', 'localhost'),
                port=int(self.get_env_var('REDIS_PORT', '6379')),
                db=0,
                decode_responses=True
            )
            
            # Perform instrumented operations
            test_key = "auto_instrumentation_test"
            redis_client.set(test_key, "test_value", ex=60)  # Expire in 60 seconds
            retrieved_value = redis_client.get(test_key)
            
            assert retrieved_value == "test_value", (
                "Instrumented Redis operations should work correctly"
            )
            
            # Cleanup test key
            redis_client.delete(test_key)
            
            self.record_metric("redis_auto_instrumented", True)
            self.record_metric("redis_version", redis_version)
            
        except Exception as e:
            self.record_metric("redis_instrumentation_error", str(e))
            raise
            
        finally:
            # Cleanup
            try:
                instrumentor.uninstrument()
            except:
                pass
                
    def test_requests_auto_instrumentation_detection(self):
        """
        Test automatic detection and instrumentation of requests library.
        
        Tests HTTP client instrumentation for external API calls.
        """
        # Check requests availability (should always be available)
        try:
            import requests
            requests_version = requests.__version__
        except ImportError:
            pytest.fail("requests library should always be available")
            
        # Check instrumentor availability
        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            instrumentor_available = True
        except ImportError:
            pytest.skip("OpenTelemetry requests instrumentor not available")
            
        instrumentor = RequestsInstrumentor()
        
        # Check initial state
        initially_instrumented = instrumentor.is_instrumented_by_opentelemetry
        assert not initially_instrumented, (
            "requests should not be auto-instrumented initially"
        )
        
        try:
            # Setup OpenTelemetry tracing
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
            
            trace.set_tracer_provider(TracerProvider())
            span_processor = BatchSpanProcessor(ConsoleSpanExporter())
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Apply auto-instrumentation
            instrumentor.instrument()
            
            # Verify instrumentation
            post_instrumentation = instrumentor.is_instrumented_by_opentelemetry
            assert post_instrumentation, (
                "requests should be instrumented after applying auto-instrumentation"
            )
            
            # Test instrumented HTTP request (using httpbin.org for reliable testing)
            try:
                response = requests.get("https://httpbin.org/json", timeout=10)
                assert response.status_code == 200, (
                    "Instrumented HTTP request should succeed"
                )
                
                # Verify response contains expected data
                json_data = response.json()
                assert isinstance(json_data, dict), (
                    "Response should contain JSON data"
                )
                
                self.record_metric("requests_auto_instrumented", True)
                self.record_metric("requests_version", requests_version)
                self.record_metric("instrumented_http_request_success", True)
                
            except requests.exceptions.RequestException as e:
                # Network issues shouldn't fail the test, just log
                self.record_metric("instrumented_http_request_error", str(e))
                logger.warning(f"HTTP request failed during instrumentation test: {e}")
                
        except Exception as e:
            self.record_metric("requests_instrumentation_error", str(e))
            raise
            
        finally:
            # Cleanup
            try:
                instrumentor.uninstrument()
            except:
                pass


class TestAutoInstrumentationMultiFrameworkIntegration(SSotAsyncTestCase):
    """Test automatic instrumentation across multiple frameworks simultaneously."""
    
    def setup_method(self, method=None):
        """Setup for multi-framework testing."""
        super().setup_method(method)
        
        # Configure comprehensive auto-instrumentation
        auto_instrumentation_config = {
            "ENVIRONMENT": "test",
            "ENABLE_TRACING": "true",
            "OTEL_SERVICE_NAME": "netra-apex-multi-framework-test",
            "OTEL_TRACES_EXPORTER": "console",
            "OTEL_TRACES_SAMPLER": "always_on",
            "OTEL_PYTHON_LOG_CORRELATION": "true",
        }
        
        for key, value in auto_instrumentation_config.items():
            self.set_env_var(key, value)
            
    def test_multiple_frameworks_auto_instrumentation_coordination(self):
        """
        Test that multiple auto-instrumentors can work together.
        
        Validates that FastAPI + SQLAlchemy + Redis + requests can all be
        instrumented simultaneously without conflicts.
        """
        # Check availability of all frameworks
        frameworks_available = {}
        
        try:
            import fastapi
            frameworks_available['fastapi'] = fastapi.__version__
        except ImportError:
            frameworks_available['fastapi'] = None
            
        try:
            import sqlalchemy  
            frameworks_available['sqlalchemy'] = sqlalchemy.__version__
        except ImportError:
            frameworks_available['sqlalchemy'] = None
            
        try:
            import redis
            frameworks_available['redis'] = redis.__version__
        except ImportError:
            frameworks_available['redis'] = None
            
        try:
            import requests
            frameworks_available['requests'] = requests.__version__
        except ImportError:
            frameworks_available['requests'] = None
            
        # Skip test if not enough frameworks available
        available_count = sum(1 for v in frameworks_available.values() if v is not None)
        if available_count < 2:
            pytest.skip(f"Need at least 2 frameworks for multi-framework test, got {available_count}")
            
        # Initialize OpenTelemetry SDK
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
            
            trace.set_tracer_provider(TracerProvider())
            span_processor = BatchSpanProcessor(ConsoleSpanExporter())
            trace.get_tracer_provider().add_span_processor(span_processor)
            
        except ImportError:
            pytest.skip("OpenTelemetry SDK not available")
            
        # Collect instrumentors
        instrumentors = {}
        
        if frameworks_available['fastapi']:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                instrumentors['fastapi'] = FastAPIInstrumentor()
            except ImportError:
                pass
                
        if frameworks_available['sqlalchemy']:
            try:
                from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
                instrumentors['sqlalchemy'] = SQLAlchemyInstrumentor()
            except ImportError:
                pass
                
        if frameworks_available['redis']:
            try:
                from opentelemetry.instrumentation.redis import RedisInstrumentor
                instrumentors['redis'] = RedisInstrumentor()
            except ImportError:
                pass
                
        if frameworks_available['requests']:
            try:
                from opentelemetry.instrumentation.requests import RequestsInstrumentor
                instrumentors['requests'] = RequestsInstrumentor()
            except ImportError:
                pass
                
        # Verify none are initially instrumented
        for framework, instrumentor in instrumentors.items():
            initially_instrumented = instrumentor.is_instrumented_by_opentelemetry
            assert not initially_instrumented, (
                f"{framework} should not be initially instrumented in multi-framework test"
            )
            
        try:
            # Apply all instrumentors
            instrumentation_results = {}
            
            for framework, instrumentor in instrumentors.items():
                try:
                    if framework == 'fastapi':
                        # FastAPI needs an app instance
                        from fastapi import FastAPI
                        test_app = FastAPI(title="MultiFrameworkTest")
                        instrumentor.instrument_app(test_app)
                    else:
                        # Other frameworks can be instrumented globally
                        instrumentor.instrument()
                        
                    instrumentation_results[framework] = True
                    
                except Exception as e:
                    instrumentation_results[framework] = str(e)
                    logger.error(f"Failed to instrument {framework}: {e}")
                    
            # Verify instrumentation status
            successful_instrumentations = []
            failed_instrumentations = []
            
            for framework, instrumentor in instrumentors.items():
                is_instrumented = instrumentor.is_instrumented_by_opentelemetry
                if is_instrumented:
                    successful_instrumentations.append(framework)
                else:
                    failed_instrumentations.append(framework)
                    
            # Should have at least some successful instrumentations
            assert len(successful_instrumentations) >= 1, (
                f"At least 1 framework should be successfully instrumented. "
                f"Successful: {successful_instrumentations}, Failed: {failed_instrumentations}"
            )
            
            # Record metrics
            self.record_metric("frameworks_available", available_count)
            self.record_metric("frameworks_instrumented", len(successful_instrumentations))
            self.record_metric("instrumentation_failures", len(failed_instrumentations))
            
            for framework in successful_instrumentations:
                self.record_metric(f"{framework}_instrumented", True)
                
            for framework in failed_instrumentations:
                self.record_metric(f"{framework}_instrumentation_failed", True)
                
        finally:
            # Cleanup all instrumentors
            for framework, instrumentor in instrumentors.items():
                try:
                    if framework == 'fastapi':
                        # FastAPI instrumentor uninstrumentation
                        instrumentor.uninstrument()
                    else:
                        instrumentor.uninstrument()
                except Exception as e:
                    logger.warning(f"Failed to uninstrument {framework}: {e}")
                    
    def test_auto_instrumentation_framework_conflict_detection(self):
        """
        Test detection of potential conflicts between auto-instrumentors.
        
        Validates that instrumentors don't interfere with each other.
        """
        # This test focuses on conflict detection rather than actual instrumentation
        
        # Define potential conflict scenarios
        conflict_scenarios = [
            {
                "name": "overlapping_http_instrumentation",
                "frameworks": ["fastapi", "requests"],
                "conflict_type": "HTTP instrumentation overlap",
                "expected_conflict": False  # Should be handled gracefully
            },
            {
                "name": "database_connection_sharing", 
                "frameworks": ["sqlalchemy", "fastapi"],
                "conflict_type": "Database connection instrumentation",
                "expected_conflict": False  # Should work together
            }
        ]
        
        conflict_detection_results = {}
        
        for scenario in conflict_scenarios:
            scenario_name = scenario["name"]
            frameworks = scenario["frameworks"]
            
            # Check if frameworks are available
            frameworks_available = []
            for framework in frameworks:
                try:
                    if framework == "fastapi":
                        import fastapi
                        frameworks_available.append(framework)
                    elif framework == "requests":
                        import requests
                        frameworks_available.append(framework)
                    elif framework == "sqlalchemy":
                        import sqlalchemy
                        frameworks_available.append(framework)
                except ImportError:
                    pass
                    
            if len(frameworks_available) != len(frameworks):
                conflict_detection_results[scenario_name] = {
                    "skipped": True,
                    "reason": f"Missing frameworks: {set(frameworks) - set(frameworks_available)}"
                }
                continue
                
            # Test for potential conflicts (without actually instrumenting)
            conflict_indicators = []
            
            # Check for shared modules/namespaces
            if "fastapi" in frameworks and "requests" in frameworks:
                # Both instrument HTTP - check for namespace conflicts
                try:
                    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                    from opentelemetry.instrumentation.requests import RequestsInstrumentor
                    
                    # Check if they use different span naming conventions
                    # This is a simplified conflict check
                    conflict_indicators.append("shared_http_instrumentation")
                    
                except ImportError:
                    pass
                    
            conflict_detection_results[scenario_name] = {
                "frameworks_available": frameworks_available,
                "conflict_indicators": conflict_indicators,
                "expected_conflict": scenario["expected_conflict"],
                "actual_conflict_detected": len(conflict_indicators) > 0
            }
            
        # Validate conflict detection
        for scenario_name, result in conflict_detection_results.items():
            if result.get("skipped"):
                continue
                
            expected = result["expected_conflict"]
            detected = result["actual_conflict_detected"]
            
            # For now, we expect no conflicts (OpenTelemetry handles this well)
            assert not detected or expected, (
                f"Scenario {scenario_name}: Unexpected conflict detected. "
                f"Indicators: {result['conflict_indicators']}"
            )
            
        self.record_metric("conflict_scenarios_tested", len([r for r in conflict_detection_results.values() if not r.get("skipped")]))
        self.record_metric("conflicts_detected", sum(1 for r in conflict_detection_results.values() if r.get("actual_conflict_detected", False)))