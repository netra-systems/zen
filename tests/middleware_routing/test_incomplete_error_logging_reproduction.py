"""
Tests to reproduce incomplete error logging that masks the real Starlette routing errors.

TARGET ISSUE: Incomplete stack traces that truncate at routing.py line 716
ROOT CAUSE: Exception handling middleware that wrap/mask underlying routing errors

CRITICAL PATTERN FROM STACK TRACE:
- Stack trace cuts off abruptly after starlette/_exception_handler.py line 42
- Missing the actual error that caused the routing failure
- Exception wrapping prevents root cause diagnosis
"""

import asyncio
import pytest
import logging
import traceback
import sys
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette._exception_handler import wrap_app_handling_exceptions

from shared.isolated_environment import get_env


class TestErrorLoggingReproduction:
    """Tests to reproduce incomplete error logging patterns that hide routing errors."""
    
    def setup_method(self, method=None):
        """Set up error logging reproduction tests."""
        # Initialize environment isolation
        self._env = get_env()
        
        # Capture all logging and error output
        self.captured_errors = []
        self.captured_logs = []
        self.truncated_traces = []
        self.exception_wrappers = []
        
        # Set up comprehensive logging capture
        self.log_handler = logging.Handler()
        self.log_handler.emit = self._capture_log_record
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        
        # Simple metrics tracking
        self.metrics = {}
    
    def record_metric(self, name: str, value):
        """Simple metric recording."""
        self.metrics[name] = value
    
    def _capture_log_record(self, record):
        """Capture log records for analysis."""
        self.captured_logs.append({
            "level": record.levelname,
            "message": record.getMessage(),
            "exc_info": record.exc_info,
            "stack_info": record.stack_info
        })
    
    @pytest.mark.asyncio
    async def test_starlette_exception_handler_truncation_reproduction(self):
        """
        Test 1: Reproduce the exact exception handler truncation from the stack trace.
        
        TARGET: Reproduce starlette/_exception_handler.py line 42 truncation pattern
        """
        app = FastAPI()
        
        # Create a middleware that mimics the problematic behavior
        class ExceptionTruncatingMiddleware(BaseHTTPMiddleware):
            """Middleware that truncates exceptions like in the stack trace."""
            
            async def dispatch(self, request: Request, call_next):
                try:
                    response = await call_next(request)
                    return response
                except Exception as original_exc:
                    # This mimics starlette/_exception_handler.py line 42 behavior
                    self.captured_errors.append({
                        "original_type": type(original_exc).__name__,
                        "original_message": str(original_exc),
                        "original_traceback": traceback.format_exc()
                    })
                    
                    # Re-raise in a way that truncates the trace (reproduces the issue)
                    raise HTTPException(
                        status_code=500, 
                        detail="Internal Server Error"
                    ) from None  # This 'from None' truncates the chain!
        
        app.add_middleware(ExceptionTruncatingMiddleware)
        
        @app.get("/trigger-routing-error")
        async def trigger_routing_error():
            # Simulate an error that would normally show full context
            raise RuntimeError("Simulated routing middleware_stack error")
        
        @app.get("/trigger-deep-error") 
        async def trigger_deep_error():
            # Create a nested error that should show full stack
            def level3():
                raise ValueError("Deep nested error")
            
            def level2():
                level3()
            
            def level1():
                level2()
            
            level1()
        
        client = TestClient(app)
        
        # Test truncated error handling
        truncation_tests = [
            ("/trigger-routing-error", "routing_error"),
            ("/trigger-deep-error", "deep_error")
        ]
        
        for path, error_type in truncation_tests:
            with self.subTest(error_type=error_type):
                try:
                    response = client.get(path)
                    # Should not reach here
                    self.fail(f"Expected error was not raised for {error_type}")
                except Exception as e:
                    # Analyze the exception chain
                    self.truncated_traces.append({
                        "error_type": error_type,
                        "path": path,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                        "has_cause": hasattr(e, '__cause__') and e.__cause__ is not None,
                        "has_context": hasattr(e, '__context__') and e.__context__ is not None,
                        "traceback": traceback.format_exc()
                    })
                    
                    # Check if truncation occurred (matches target pattern)
                    tb_str = traceback.format_exc()
                    if "from None" in str(e.__class__.__module__) or e.__cause__ is None:
                        self.record_metric(f"error_truncation_{error_type}_truncated", 1)
        
        # Verify we captured the original errors before truncation
        self.assertGreater(len(self.captured_errors), 0, "Should have captured original errors")
        
        # Analyze if truncation matches the target pattern
        for error in self.captured_errors:
            if "routing" in error["original_message"].lower():
                self.record_metric("error_truncation_routing_error_truncated", 1)
    
    @pytest.mark.asyncio
    async def test_middleware_exception_wrapping_chain_reproduction(self):
        """
        Test 2: Reproduce complex exception wrapping chains that hide the real error.
        
        HYPOTHESIS: Multiple middleware layers wrap exceptions, obscuring the original routing error
        """
        app = FastAPI()
        
        # Create a chain of exception-wrapping middleware
        class FirstWrapperMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    return await call_next(request)
                except Exception as e:
                    self.exception_wrappers.append({
                        "wrapper": "FirstWrapper",
                        "original_error": str(e),
                        "error_type": type(e).__name__
                    })
                    raise RuntimeError(f"FirstWrapper: {e}")
        
        class SecondWrapperMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    return await call_next(request)
                except Exception as e:
                    self.exception_wrappers.append({
                        "wrapper": "SecondWrapper", 
                        "original_error": str(e),
                        "error_type": type(e).__name__
                    })
                    raise ValueError(f"SecondWrapper: {e}")
        
        class FinalWrapperMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    return await call_next(request)
                except Exception as e:
                    self.exception_wrappers.append({
                        "wrapper": "FinalWrapper",
                        "original_error": str(e), 
                        "error_type": type(e).__name__
                    })
                    # This final wrapper completely obscures the original
                    raise HTTPException(status_code=500, detail="Server Error") from None
        
        # Add middleware in wrapping order
        app.add_middleware(FinalWrapperMiddleware)
        app.add_middleware(SecondWrapperMiddleware)  
        app.add_middleware(FirstWrapperMiddleware)
        
        @app.get("/deep-routing-error")
        async def deep_routing_error():
            # Simulate the original routing error (like middleware_stack failure)
            raise RuntimeError("Original routing middleware_stack processing error")
        
        client = TestClient(app)
        
        try:
            response = client.get("/deep-routing-error")
            self.fail("Expected wrapped exception chain")
        except Exception as final_exception:
            # Analyze the exception wrapping chain
            self.record_metric("exception_wrapping_final_exception_caught", 1)
            
            # Check if original error is still accessible
            original_error_found = False
            for wrapper_info in self.exception_wrappers:
                if "routing middleware_stack" in wrapper_info["original_error"]:
                    original_error_found = True
                    self.record_metric("exception_wrapping_original_error_preserved", 1)
                    break
            
            if not original_error_found:
                self.record_metric("exception_wrapping_original_error_obscured", 1)
            
            # Verify complete obscuration (matches production issue)
            final_error_str = str(final_exception)
            if "Server Error" in final_error_str and "routing" not in final_error_str:
                self.record_metric("exception_wrapping_complete_obscuration_reproduced", 1)
    
    @pytest.mark.asyncio
    async def test_asyncio_exception_handling_truncation(self):
        """
        Test 3: Test asyncio exception handling that might truncate stack traces.
        
        HYPOTHESIS: Asyncio event loop exception handling truncates traces at middleware level
        """
        app = FastAPI()
        
        # Middleware that interacts with asyncio exception handling
        class AsyncioExceptionMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    # Create asyncio context that might affect exception handling
                    loop = asyncio.get_event_loop()
                    
                    # Set up asyncio exception handler
                    original_handler = loop.get_exception_handler()
                    
                    def custom_exception_handler(loop, context):
                        self.captured_errors.append({
                            "source": "asyncio_handler",
                            "context": str(context),
                            "exception": context.get('exception')
                        })
                        # Call original handler if it exists
                        if original_handler:
                            original_handler(loop, context)
                    
                    loop.set_exception_handler(custom_exception_handler)
                    
                    try:
                        response = await call_next(request)
                        return response
                    finally:
                        # Restore original handler
                        loop.set_exception_handler(original_handler)
                        
                except Exception as e:
                    # Log the exception with asyncio context
                    self.captured_errors.append({
                        "source": "asyncio_middleware",
                        "error": str(e),
                        "type": type(e).__name__,
                        "in_asyncio_context": True
                    })
                    raise
        
        app.add_middleware(AsyncioExceptionMiddleware)
        
        @app.get("/asyncio-routing-error")
        async def asyncio_routing_error():
            # Simulate routing error in asyncio context
            await asyncio.sleep(0.01)  # Ensure we're in asyncio context
            raise RuntimeError("Asyncio routing middleware_stack error")
        
        @app.get("/asyncio-nested-error")
        async def asyncio_nested_error():
            async def nested_async_call():
                await asyncio.sleep(0.01)
                raise ValueError("Nested async routing error")
            
            await nested_async_call()
        
        client = TestClient(app)
        
        # Test asyncio error patterns
        asyncio_tests = [
            ("/asyncio-routing-error", "asyncio_routing"),
            ("/asyncio-nested-error", "asyncio_nested")
        ]
        
        for path, test_name in asyncio_tests:
            with self.subTest(test_name=test_name):
                try:
                    response = client.get(path)
                    self.fail(f"Expected asyncio error for {test_name}")
                except Exception as e:
                    # Check if asyncio affected the exception handling
                    asyncio_errors = [
                        err for err in self.captured_errors 
                        if err.get("in_asyncio_context") or err.get("source") == "asyncio_handler"
                    ]
                    
                    if asyncio_errors:
                        self.record_metric(f"asyncio_exceptions_{test_name}_asyncio_interaction", 1)
                    
                    # Check for truncated traces in asyncio context
                    tb_str = traceback.format_exc()
                    if len(tb_str.split('\n')) < 10:  # Suspiciously short trace
                        self.record_metric(f"asyncio_exceptions_{test_name}_short_trace", 1)
    
    @pytest.mark.asyncio
    async def test_logging_configuration_impact_on_error_visibility(self):
        """
        Test 4: Test how logging configuration affects error visibility.
        
        HYPOTHESIS: Production logging configuration suppresses detailed error traces
        """
        # Test different logging configurations
        logging_configs = [
            {"level": logging.ERROR, "name": "error_only"},
            {"level": logging.CRITICAL, "name": "critical_only"},
            {"level": logging.DEBUG, "name": "debug_verbose"}
        ]
        
        for config in logging_configs:
            with self.subTest(logging_config=config["name"]):
                # Reset captured logs for this test
                self.captured_logs.clear()
                
                # Configure logging for this test
                logger = logging.getLogger(f"test_{config['name']}")
                logger.setLevel(config["level"])
                
                app = FastAPI()
                
                # Middleware that logs errors at different levels
                class LoggingTestMiddleware(BaseHTTPMiddleware):
                    async def dispatch(self, request: Request, call_next):
                        try:
                            return await call_next(request)
                        except Exception as e:
                            # Log at different levels
                            logger.debug(f"DEBUG: Routing error: {e}")
                            logger.info(f"INFO: Routing error: {e}")
                            logger.warning(f"WARNING: Routing error: {e}")
                            logger.error(f"ERROR: Routing error: {e}")
                            logger.critical(f"CRITICAL: Routing error: {e}")
                            raise
                
                app.add_middleware(LoggingTestMiddleware)
                
                @app.get("/logging-test")
                async def logging_test():
                    raise RuntimeError("Test routing error for logging")
                
                client = TestClient(app)
                
                try:
                    response = client.get("/logging-test")
                    self.fail("Expected logging test error")
                except Exception as e:
                    # Analyze what was actually logged
                    debug_logs = [log for log in self.captured_logs if log["level"] == "DEBUG"]
                    info_logs = [log for log in self.captured_logs if log["level"] == "INFO"]
                    error_logs = [log for log in self.captured_logs if log["level"] == "ERROR"]
                    critical_logs = [log for log in self.captured_logs if log["level"] == "CRITICAL"]
                    
                    # Record what was captured at each level
                    self.record_metric(f"logging_config_{config['name']}_debug_count", len(debug_logs))
                    self.record_metric(f"logging_config_{config['name']}_error_count", len(error_logs))
                    
                    # Check if error details are lost due to logging level
                    routing_error_logged = any(
                        "routing error" in log["message"].lower()
                        for log in self.captured_logs
                    )
                    
                    if routing_error_logged:
                        self.record_metric(f"logging_config_{config['name']}_error_visible", 1)
                    else:
                        self.record_metric(f"logging_config_{config['name']}_error_hidden", 1)
    
    @pytest.mark.asyncio
    async def test_production_error_handler_exact_reproduction(self):
        """
        Test 5: Reproduce the exact production error handling configuration.
        
        MISSION CRITICAL: Test the production app's error handling that causes truncated traces
        """
        from netra_backend.app.core.app_factory import create_app
        from netra_backend.app.core.unified_error_handler import general_exception_handler
        
        # Capture stderr to catch uncaught exceptions
        stderr_capture = StringIO()
        
        with redirect_stderr(stderr_capture):
            try:
                # Create production app with exact error handling
                app = create_app()
                
                # Add test endpoint that triggers the production error pattern
                @app.get("/production-error-test")
                async def production_error_test():
                    # Simulate the error that causes routing.py line 716 failure
                    raise RuntimeError("Production routing middleware_stack processing error")
                
                client = TestClient(app)
                
                try:
                    response = client.get("/production-error-test")
                    self.fail("Expected production error")
                except Exception as e:
                    # Capture the full exception handling chain
                    production_error = {
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                        "traceback": traceback.format_exc(),
                        "stderr_output": stderr_capture.getvalue()
                    }
                    
                    self.captured_errors.append(production_error)
                    
                    # Analyze if this matches the production truncation pattern
                    tb_lines = production_error["traceback"].split('\n')
                    
                    # Look for the specific truncation pattern from the stack trace
                    routing_py_found = any("starlette/routing.py" in line for line in tb_lines)
                    exception_handler_found = any("_exception_handler.py" in line for line in tb_lines)
                    line_716_found = any("line 716" in line for line in tb_lines)
                    middleware_stack_found = any("middleware_stack" in line for line in tb_lines)
                    
                    if routing_py_found:
                        self.record_metric("production_errors_routing_py_in_trace", 1)
                    if exception_handler_found:
                        self.record_metric("production_errors_exception_handler_in_trace", 1)
                    if line_716_found:
                        self.record_metric("production_errors_line_716_in_trace", 1) 
                    if middleware_stack_found:
                        self.record_metric("production_errors_middleware_stack_in_trace", 1)
                    
                    # Check for truncation (short trace despite complex middleware stack)
                    if len(tb_lines) < 20 and len(app.user_middleware) > 5:
                        self.record_metric("production_errors_suspicious_truncation", 1)
                    
                    # Check stderr for additional error details
                    stderr_content = stderr_capture.getvalue()
                    if stderr_content and "routing" in stderr_content.lower():
                        self.record_metric("production_errors_routing_error_in_stderr", 1)
            
            except Exception as app_creation_error:
                self.captured_errors.append({
                    "source": "production_app_creation",
                    "error": str(app_creation_error),
                    "type": type(app_creation_error).__name__
                })
                raise
    
    def teardown_method(self, method=None):
        """Provide comprehensive error logging analysis."""
        # Remove our custom log handler
        logging.getLogger().removeHandler(self.log_handler)
        pass  # No parent teardown needed
        
        print("\n" + "="*80)
        print("INCOMPLETE ERROR LOGGING REPRODUCTION ANALYSIS")
        print("="*80)
        
        print(f"\n📊 SUMMARY STATISTICS:")
        print(f"   Captured errors: {len(self.captured_errors)}")
        print(f"   Truncated traces: {len(self.truncated_traces)}")
        print(f"   Exception wrappers: {len(self.exception_wrappers)}")
        print(f"   Captured logs: {len(self.captured_logs)}")
        
        # Analyze truncated traces
        if self.truncated_traces:
            print(f"\n🔍 TRUNCATED TRACE ANALYSIS:")
            for trace in self.truncated_traces:
                print(f"\n   Error Type: {trace['error_type']}")
                print(f"   Path: {trace['path']}")
                print(f"   Has Cause Chain: {trace['has_cause']}")
                print(f"   Has Context: {trace['has_context']}")
                
                # Look for the target pattern
                tb = trace['traceback']
                if "_exception_handler.py" in tb and "line 42" in tb:
                    print("   🎯 MATCHES TARGET: _exception_handler.py line 42 pattern!")
                elif "routing.py" in tb and "line 716" in tb:
                    print("   🎯 MATCHES TARGET: routing.py line 716 pattern!")
                elif len(tb.split('\n')) < 10:
                    print("   ⚠️ SUSPICIOUS: Very short traceback")
        
        # Analyze exception wrapping
        if self.exception_wrappers:
            print(f"\n🔗 EXCEPTION WRAPPING CHAIN ANALYSIS:")
            for i, wrapper in enumerate(self.exception_wrappers):
                print(f"   {i+1}. {wrapper['wrapper']}: {wrapper['error_type']}")
                if "routing" in wrapper['original_error'].lower():
                    print(f"      🎯 ORIGINAL ROUTING ERROR: {wrapper['original_error']}")
        
        # Analyze captured errors for patterns
        routing_errors = [e for e in self.captured_errors if "routing" in str(e).lower()]
        middleware_errors = [e for e in self.captured_errors if "middleware" in str(e).lower()]
        
        print(f"\n📈 ERROR PATTERN ANALYSIS:")
        print(f"   Routing-related errors: {len(routing_errors)}")
        print(f"   Middleware-related errors: {len(middleware_errors)}")
        
        if routing_errors and len(self.truncated_traces) > 0:
            print("\n🎯 HIGH CORRELATION: Routing errors + truncated traces detected!")
            print("   This strongly suggests the target incomplete logging issue is reproducible.")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=long", "--capture=no"])