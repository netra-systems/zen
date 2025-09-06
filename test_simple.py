#!/usr/bin/env python
"""Simple test to verify basic functionality."""

def test_basic():
    """Test that basic assertion works."""
    assert 1 + 1 == 2

def test_imports():
    """Test that we can import basic modules."""
    import sys
    import os
    assert sys.version_info.major >= 3
    assert os.path.exists(".")

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])