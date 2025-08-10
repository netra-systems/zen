"""Simple standalone tests that don't require app imports"""

def test_addition():
    """Test addition"""
    assert 1 + 1 == 2

def test_subtraction():
    """Test subtraction"""
    assert 5 - 3 == 2

def test_multiplication():
    """Test multiplication"""
    assert 3 * 4 == 12

def test_division():
    """Test division"""
    assert 10 / 2 == 5

def test_string_concat():
    """Test string concatenation"""
    assert "Hello" + " " + "World" == "Hello World"

def test_list_append():
    """Test list append"""
    lst = [1, 2, 3]
    lst.append(4)
    assert lst == [1, 2, 3, 4]

def test_dict_update():
    """Test dictionary update"""
    d = {"a": 1}
    d["b"] = 2
    assert d == {"a": 1, "b": 2}

def test_boolean_logic():
    """Test boolean logic"""
    assert True and True
    assert not (True and False)
    assert True or False
    assert not (False or False)