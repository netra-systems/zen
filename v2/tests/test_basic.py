"""Basic tests to verify test infrastructure"""

import pytest
import sys
import os

# Ensure proper path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_environment_setup():
    """Test that environment variables are set correctly"""
    assert os.environ.get("TESTING") == "1"
    assert os.environ.get("REDIS_HOST") == "localhost"
    assert os.environ.get("CLICKHOUSE_HOST") == "localhost"

def test_imports():
    """Test that core modules can be imported"""
    try:
        from app.config import settings
        assert settings is not None
    except ImportError as e:
        pytest.fail(f"Failed to import settings: {e}")
    
    try:
        from app.schemas import User
        assert User is not None
    except ImportError as e:
        pytest.fail(f"Failed to import schemas: {e}")

def test_basic_math():
    """Simple test to verify pytest is working"""
    assert 2 + 2 == 4
    assert 10 * 10 == 100

def test_string_operations():
    """Test basic string operations"""
    test_string = "Netra AI"
    assert test_string.lower() == "netra ai"
    assert test_string.upper() == "NETRA AI"
    assert len(test_string) == 8

@pytest.mark.asyncio
async def test_async_function():
    """Test that async tests work"""
    import asyncio
    await asyncio.sleep(0.01)
    assert True

def test_list_operations():
    """Test list operations"""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert sum(test_list) == 15
    assert max(test_list) == 5
    assert min(test_list) == 1

def test_dictionary_operations():
    """Test dictionary operations"""
    test_dict = {"key1": "value1", "key2": "value2"}
    assert len(test_dict) == 2
    assert test_dict.get("key1") == "value1"
    assert test_dict.get("key3", "default") == "default"

def test_exception_handling():
    """Test exception handling"""
    with pytest.raises(ValueError):
        raise ValueError("Test exception")
    
    with pytest.raises(ZeroDivisionError):
        result = 10 / 0

def test_type_checking():
    """Test type checking"""
    assert isinstance(42, int)
    assert isinstance(3.14, float)
    assert isinstance("test", str)
    assert isinstance([1, 2, 3], list)
    assert isinstance({"key": "value"}, dict)

class TestClassBasedTests:
    """Class-based test organization"""
    
    def test_class_method_1(self):
        """Test method 1 in class"""
        assert True
    
    def test_class_method_2(self):
        """Test method 2 in class"""
        result = "test".upper()
        assert result == "TEST"