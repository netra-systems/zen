#!/usr/bin/env python3
"""
Simple standalone unit test to verify our setup.
"""
import pytest

def test_basic_python():
    """Test that basic Python works."""
    assert 1 + 1 == 2
    assert "hello" == "hello"
    assert True is True

def test_pytest_raises():
    """Test that pytest.raises works."""
    with pytest.raises(ValueError) as ctx:
        raise ValueError("test error")
    assert "test error" in str(ctx.value)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])