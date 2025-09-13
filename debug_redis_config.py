#!/usr/bin/env python3
"""
Debug script to understand Redis configuration loading.
"""

import os
from unittest.mock import patch

# Test environment variables
test_env = {
    'REDIS_HOST': '10.107.0.3',
    'REDIS_PORT': '6379',
    'REDIS_PASSWORD': 'test-password-debug',
    'REDIS_DB': '5',
    'REDIS_SSL': 'true'
}

print("Environment variables being set:")
for k, v in test_env.items():
    print(f"  {k} = {v}")

# Patch environment variables
with patch.dict(os.environ, test_env, clear=False):
    print("\nActual environment variables:")
    for k in test_env.keys():
        print(f"  {k} = {os.environ.get(k)}")

    # Test isolated environment
    from shared.isolated_environment import get_env
    env = get_env()
    print("\nIsolated environment variables:")
    for k in test_env.keys():
        print(f"  {k} = {env.get(k)}")

    # Test RedisConfig
    from netra_backend.app.schemas.config import RedisConfig
    print("\nRedisConfig initialization:")
    redis_config = RedisConfig()
    print(f"  host: {redis_config.host}")
    print(f"  port: {redis_config.port}")
    print(f"  password: {redis_config.password}")
    print(f"  db: {redis_config.db}")
    print(f"  ssl: {redis_config.ssl}")