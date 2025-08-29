"""
Test suite for symbol extraction and Go to Symbol functionality
"""

import pytest
from typing import List, Dict

from netra_backend.app.services.corpus.symbol_extractor import (
    SymbolExtractor,
    Symbol,
    SymbolType,
    PythonSymbolExtractor,
    JavaScriptSymbolExtractor
)


class TestSymbolExtractor:
    """Test main symbol extractor functionality"""
    
    @pytest.fixture
    def extractor(self):
        return SymbolExtractor()
    
    def test_extract_python_class(self, extractor):
        """Test extracting Python class definitions"""
        code = '''
class MyClass:
    def __init__(self):
        self.value = 0
    
    def method1(self):
        return self.value
        '''
        
        symbols = extractor.extract_symbols(code, "test.py")
        
        assert len(symbols) == 3
        assert symbols[0].name == "MyClass"
        assert symbols[0].type == SymbolType.CLASS
        assert symbols[1].name == "__init__"
        assert symbols[1].type == SymbolType.METHOD
        assert symbols[1].parent == "MyClass"
        assert symbols[2].name == "method1"
        assert symbols[2].type == SymbolType.METHOD
    
    def test_extract_python_functions(self, extractor):
        """Test extracting Python function definitions"""
        code = '''
def function1(arg1, arg2):
    return arg1 + arg2

async def async_function():
    pass

value = 42
        '''
        
        symbols = extractor.extract_symbols(code, "test.py")
        
        assert len(symbols) == 3
        assert symbols[0].name == "function1"
        assert symbols[0].type == SymbolType.FUNCTION
        assert symbols[0].signature == "(arg1, arg2)"
        assert symbols[1].name == "async_function"
        assert symbols[1].type == SymbolType.FUNCTION
        assert symbols[2].name == "value"
        assert symbols[2].type == SymbolType.VARIABLE
    
    def test_extract_javascript_classes(self, extractor):
        """Test extracting JavaScript class definitions"""
        code = '''
export class MyComponent {
    constructor(props) {
        this.props = props;
    }
    
    render() {
        return "<div>Hello</div>";
    }
    
    handleClick() {
        console.log("clicked");
    }
}
        '''
        
        symbols = extractor.extract_symbols(code, "component.js")
        
        # Find class and methods
        class_symbols = [s for s in symbols if s.type == SymbolType.CLASS]
        method_symbols = [s for s in symbols if s.type == SymbolType.METHOD]
        
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "MyComponent"
        
        assert len(method_symbols) >= 2
        method_names = [m.name for m in method_symbols]
        assert "render" in method_names
        assert "handleClick" in method_names
    
    def test_extract_typescript_interfaces(self, extractor):
        """Test extracting TypeScript interfaces and types"""
        code = '''
interface User {
    id: number;
    name: string;
}

type Status = "active" | "inactive";

export function getUser(id: number): User {
    return { id, name: "Test" };
}

const API_KEY = "secret123";
        '''
        
        symbols = extractor.extract_symbols(code, "types.ts")
        
        # Check for different symbol types
        interfaces = [s for s in symbols if s.type == SymbolType.INTERFACE]
        types = [s for s in symbols if s.type == SymbolType.TYPE]
        functions = [s for s in symbols if s.type == SymbolType.FUNCTION]
        consts = [s for s in symbols if s.type == SymbolType.CONST]
        
        assert len(interfaces) == 1
        assert interfaces[0].name == "User"
        
        assert len(types) == 1
        assert types[0].name == "Status"
        
        assert len(functions) == 1
        assert functions[0].name == "getUser"
        
        assert len(consts) == 1
        assert consts[0].name == "API_KEY"
    
    def test_extract_arrow_functions(self, extractor):
        """Test extracting arrow function definitions"""
        code = '''
const myFunction = (a, b) => a + b;

export const asyncArrow = async () => {
    return await fetch("/api");
};
        '''
        
        symbols = extractor.extract_symbols(code, "arrows.js")
        
        consts = [s for s in symbols if s.type == SymbolType.CONST]
        assert len(consts) == 2
        assert consts[0].name == "myFunction"
        assert consts[1].name == "asyncArrow"
    
    def test_extract_nested_classes(self, extractor):
        """Test extracting nested class structures"""
        code = '''
class OuterClass:
    class InnerClass:
        def inner_method(self):
            pass
    
    def outer_method(self):
        pass
        '''
        
        symbols = extractor.extract_symbols(code, "nested.py")
        
        # Check we have both classes and methods
        classes = [s for s in symbols if s.type == SymbolType.CLASS]
        methods = [s for s in symbols if s.type == SymbolType.METHOD]
        
        assert len(classes) >= 1
        assert "OuterClass" in [c.name for c in classes]
        assert len(methods) >= 1
    
    def test_invalid_syntax_handling(self, extractor):
        """Test handling of invalid syntax"""
        code = '''
        this is not valid python or javascript code {{{
        '''
        
        # Should return empty list instead of raising error
        symbols = extractor.extract_symbols(code, "invalid.py")
        assert symbols == []
    
    def test_extract_symbols_from_dict(self, extractor):
        """Test extracting symbols from dictionary format"""
        document = {
            "filename": "test.py",
            "content": '''
def my_function():
    return 42

class MyClass:
    pass
            '''
        }
        
        symbols = extractor.extract_symbols_from_dict(document)
        
        assert len(symbols) == 2
        assert symbols[0]["name"] == "my_function"
        assert symbols[0]["type"] == SymbolType.FUNCTION
        assert symbols[1]["name"] == "MyClass"
        assert symbols[1]["type"] == SymbolType.CLASS


class TestPythonSymbolExtractor:
    """Test Python-specific symbol extraction"""
    
    @pytest.fixture
    def extractor(self):
        return PythonSymbolExtractor()
    
    def test_extract_decorators(self, extractor):
        """Test extracting decorated functions"""
        code = '''
@decorator
def decorated_func():
    pass

@property
def my_property(self):
    return self._value
        '''
        
        symbols = extractor.extract(code, "decorators.py")
        
        functions = [s for s in symbols if s.type == SymbolType.FUNCTION]
        assert len(functions) >= 1
        assert functions[0].name == "decorated_func"
    
    def test_extract_async_functions(self, extractor):
        """Test extracting async functions"""
        code = '''
async def async_func():
    await something()
    
class AsyncClass:
    async def async_method(self):
        pass
        '''
        
        symbols = extractor.extract(code, "async.py")
        
        assert len(symbols) == 3
        assert symbols[0].name == "async_func"
        assert symbols[1].name == "AsyncClass"
        assert symbols[2].name == "async_method"
        assert symbols[2].parent == "AsyncClass"


class TestJavaScriptSymbolExtractor:
    """Test JavaScript/TypeScript-specific symbol extraction"""
    
    @pytest.fixture
    def extractor(self):
        return JavaScriptSymbolExtractor()
    
    def test_extract_exports(self, extractor):
        """Test extracting exported symbols"""
        code = '''
export function exportedFunc() {}
export class ExportedClass {}
export const exportedConst = 42;
export interface ExportedInterface {}
export type ExportedType = string;
export enum ExportedEnum { A, B }
        '''
        
        symbols = extractor.extract(code, "exports.js")
        
        names = [s.name for s in symbols]
        assert "exportedFunc" in names
        assert "ExportedClass" in names
        assert "exportedConst" in names
        assert "ExportedInterface" in names
        assert "ExportedType" in names
        assert "ExportedEnum" in names
    
    def test_extract_react_components(self, extractor):
        """Test extracting React component patterns"""
        code = '''
const MyComponent = () => {
    return <div>Hello</div>;
};

export const FunctionalComponent = (props) => {
    const handleClick = () => {
        console.log("clicked");
    };
    
    return <button onClick={handleClick}>Click</button>;
};

class ClassComponent extends React.Component {
    render() {
        return <div>Class Component</div>;
    }
}
        '''
        
        symbols = extractor.extract(code, "components.jsx")
        
        # Check for component symbols
        consts = [s for s in symbols if s.type == SymbolType.CONST]
        classes = [s for s in symbols if s.type == SymbolType.CLASS]
        
        assert len(consts) >= 2
        assert "MyComponent" in [c.name for c in consts]
        assert "FunctionalComponent" in [c.name for c in consts]
        
        assert len(classes) >= 1
        assert classes[0].name == "ClassComponent"
    
    def test_class_method_detection(self, extractor):
        """Test detecting methods inside classes"""
        code = '''
class TestClass {
    constructor() {
        this.value = 0;
    }
    
    getValue() {
        return this.value;
    }
    
    async asyncMethod() {
        await this.doSomething();
    }
    
    static staticMethod() {
        return 42;
    }
}
        '''
        
        symbols = extractor.extract(code, "class.js")
        
        methods = [s for s in symbols if s.type == SymbolType.METHOD]
        method_names = [m.name for m in methods]
        
        assert "getValue" in method_names
        assert "asyncMethod" in method_names
        assert "staticMethod" in method_names
        
        # All methods should have TestClass as parent
        for method in methods:
            if method.name != "constructor":
                assert method.parent == "TestClass"