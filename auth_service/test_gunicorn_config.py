#!/usr/bin/env python3
"""
Test script to verify Gunicorn configuration
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_gunicorn_config():
    """Test that Gunicorn configuration is valid"""
    try:
        import gunicorn_config
        
        # Verify essential configuration values
        assert hasattr(gunicorn_config, 'bind')
        assert hasattr(gunicorn_config, 'workers')
        assert hasattr(gunicorn_config, 'worker_class')
        assert gunicorn_config.worker_class == 'uvicorn.workers.UvicornWorker'
        assert gunicorn_config.graceful_timeout == 30
        assert gunicorn_config.preload_app == True
        assert gunicorn_config.reuse_port == True
        
        # Verify signal handlers are set
        assert callable(gunicorn_config.handle_term)
        assert callable(gunicorn_config.handle_int)
        
        # Verify lifecycle hooks
        assert callable(gunicorn_config.worker_int)
        assert callable(gunicorn_config.pre_fork)
        assert callable(gunicorn_config.post_fork)
        assert callable(gunicorn_config.child_exit)
        assert callable(gunicorn_config.on_exit)
        
        print("[OK] Gunicorn configuration is valid")
        print(f"  - Bind: {gunicorn_config.bind}")
        print(f"  - Workers: {gunicorn_config.workers}")
        print(f"  - Worker class: {gunicorn_config.worker_class}")
        print(f"  - Graceful timeout: {gunicorn_config.graceful_timeout}s")
        print(f"  - Max requests: {gunicorn_config.max_requests}")
        print(f"  - Preload app: {gunicorn_config.preload_app}")
        print(f"  - Reuse port: {gunicorn_config.reuse_port}")
        print("[OK] All lifecycle hooks configured")
        print("[OK] Signal handlers configured for graceful shutdown")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Gunicorn configuration error: {e}")
        return False


if __name__ == "__main__":
    success = test_gunicorn_config()
    sys.exit(0 if success else 1)