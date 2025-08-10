import pytest

def test_simple_addition():
    """Simple test to verify pytest is working"""
    assert 1 + 1 == 2

def test_simple_string():
    """Test string operations"""
    assert "hello" + " world" == "hello world"

@pytest.mark.asyncio
async def test_simple_async():
    """Test async function"""
    result = await simple_async_function()
    assert result == "async result"

async def simple_async_function():
    return "async result"

class TestBasicFunctionality:
    def test_class_method(self):
        """Test method in a class"""
        assert True
    
    def test_list_operations(self):
        """Test list operations"""
        test_list = [1, 2, 3]
        test_list.append(4)
        assert len(test_list) == 4
        assert test_list[-1] == 4