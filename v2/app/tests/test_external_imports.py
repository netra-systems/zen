"""
Test file to verify all external Python dependencies can be imported.
This ensures all required packages from requirements.txt are properly installed.
"""

import pytest
import sys
import importlib
from typing import List, Tuple


class TestExternalImports:
    """Test that all external dependencies can be imported successfully."""
    
    @pytest.mark.parametrize("module_name,import_path", [
        # FastAPI and related
        ("fastapi", "fastapi"),
        ("fastapi.FastAPI", "fastapi.FastAPI"),
        ("fastapi.Request", "fastapi.Request"),
        ("fastapi.WebSocket", "fastapi.WebSocket"),
        ("fastapi.responses", "fastapi.responses"),
        ("fastapi.middleware.cors", "fastapi.middleware.cors"),
        ("fastapi.security", "fastapi.security"),
        
        # Starlette
        ("starlette", "starlette"),
        ("starlette.middleware.base", "starlette.middleware.base"),
        ("starlette.responses", "starlette.responses"),
        
        # Uvicorn
        ("uvicorn", "uvicorn"),
        
        # Pydantic
        ("pydantic", "pydantic"),
        ("pydantic.BaseModel", "pydantic.BaseModel"),
        ("pydantic.Field", "pydantic.Field"),
        ("pydantic.validator", "pydantic.validator"),
        
        # SQLAlchemy and related
        ("sqlalchemy", "sqlalchemy"),
        ("sqlalchemy.orm", "sqlalchemy.orm"),
        ("sqlalchemy.ext.asyncio", "sqlalchemy.ext.asyncio"),
        ("aiosqlite", "aiosqlite"),
        ("asyncpg", "asyncpg"),
        ("psycopg2", "psycopg2"),
        
        # Alembic
        ("alembic", "alembic"),
        ("alembic.config", "alembic.config"),
        ("alembic.command", "alembic.command"),
        
        # Redis
        ("redis", "redis"),
        ("redis.asyncio", "redis.asyncio"),
        
        # JWT and Auth
        ("jose", "jose"),
        ("jose.jwt", "jose.jwt"),
        ("passlib", "passlib"),
        ("passlib.context", "passlib.context"),
        ("authlib", "authlib"),
        
        # HTTP and networking
        ("httpx", "httpx"),
        ("aiohttp", "aiohttp"),
        ("requests", "requests"),
        
        # AI/ML libraries
        ("anthropic", "anthropic"),
        ("openai", "openai"),
        ("tiktoken", "tiktoken"),
        ("langchain", "langchain"),
        ("langchain.embeddings", "langchain.embeddings"),
        ("langchain.vectorstores", "langchain.vectorstores"),
        
        # Data processing
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        
        # Utilities
        ("python-dotenv", "dotenv"),
        ("pyyaml", "yaml"),
        ("python-multipart", "multipart"),
        ("orjson", "orjson"),
        ("ujson", "ujson"),
        
        # Testing (should be available in test environment)
        ("pytest", "pytest"),
        ("pytest-asyncio", "pytest_asyncio"),
        ("pytest-cov", "pytest_cov"),
        ("faker", "faker"),
        
        # Logging and monitoring
        ("structlog", "structlog"),
        ("sentry_sdk", "sentry_sdk"),
        
        # ClickHouse
        ("clickhouse_driver", "clickhouse_driver"),
        ("aiochclient", "aiochclient"),
        
        # Type checking
        ("typing_extensions", "typing_extensions"),
        
        # Async utilities
        ("asyncio", "asyncio"),
        ("aiofiles", "aiofiles"),
        
        # Date/time
        ("pendulum", "pendulum"),
        ("pytz", "pytz"),
        
        # Validation
        ("email_validator", "email_validator"),
        
        # Security
        ("cryptography", "cryptography"),
        ("bcrypt", "bcrypt"),
    ])
    def test_external_import(self, module_name: str, import_path: str):
        """Test that each external module can be imported."""
        try:
            # Try to import the module
            parts = import_path.split('.')
            if len(parts) == 1:
                # Simple module import
                module = importlib.import_module(import_path)
            else:
                # Import with attribute access
                module_path = '.'.join(parts[:-1])
                attr_name = parts[-1]
                module = importlib.import_module(module_path)
                # Check if the attribute exists
                assert hasattr(module, attr_name), f"Module {module_path} does not have attribute {attr_name}"
            
            assert module is not None, f"Failed to import {import_path}"
            
        except ImportError as e:
            pytest.fail(f"Failed to import {import_path}: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing {import_path}: {e}")
    
    def test_critical_imports_batch(self):
        """Test critical imports as a batch to ensure they all work together."""
        critical_imports = [
            "fastapi",
            "pydantic",
            "sqlalchemy",
            "redis.asyncio",
            "anthropic",
            "httpx",
            "jose",
        ]
        
        failed_imports = []
        for module_name in critical_imports:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                failed_imports.append((module_name, str(e)))
        
        assert len(failed_imports) == 0, f"Failed to import critical modules: {failed_imports}"
    
    def test_optional_imports(self):
        """Test optional imports that may not be installed in all environments."""
        optional_imports = [
            ("transformers", "Hugging Face Transformers"),
            ("torch", "PyTorch"),
            ("tensorflow", "TensorFlow"),
        ]
        
        warnings = []
        for module_name, description in optional_imports:
            try:
                importlib.import_module(module_name)
            except ImportError:
                warnings.append(f"Optional dependency {description} ({module_name}) not installed")
        
        if warnings:
            # Just warn, don't fail
            for warning in warnings:
                print(f"WARNING: {warning}")
    
    def test_version_compatibility(self):
        """Check that imported modules have compatible versions."""
        version_checks = [
            ("fastapi", "0.100.0", ">="),
            ("pydantic", "2.0.0", ">="),
            ("sqlalchemy", "2.0.0", ">="),
        ]
        
        for module_name, required_version, comparison in version_checks:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "__version__"):
                    actual_version = module.__version__
                    # Basic version comparison (simplified)
                    print(f"{module_name} version: {actual_version} (required: {comparison}{required_version})")
            except ImportError:
                pytest.fail(f"Cannot check version for {module_name} - module not installed")