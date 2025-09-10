#!/usr/bin/env python3
"""
Debug script to check JWT validation logging behavior.
"""
import asyncio
import logging
from fastapi import FastAPI
from unittest.mock import AsyncMock

from netra_backend.app.core.service_dependencies.golden_path_validator import GoldenPathValidator
from netra_backend.app.core.service_dependencies.models import ServiceType, EnvironmentType

async def main():
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create app without key_manager
    app = FastAPI()
    app.state.db_session_factory = AsyncMock()
    app.state.redis_manager = AsyncMock()
    
    # Create validator
    validator = GoldenPathValidator(environment=EnvironmentType.DEVELOPMENT)
    
    print("Testing direct JWT validation method...")
    result = await validator._validate_jwt_capabilities(app)
    print(f"Direct validation result: {result}")
    
    print("\nTesting full golden path validation...")
    services_to_validate = [ServiceType.AUTH_SERVICE]
    full_result = await validator.validate_golden_path_services(app, services_to_validate)
    
    print(f"Full validation overall_success: {full_result.overall_success}")
    print(f"Business impact failures: {full_result.business_impact_failures}")
    print(f"Critical failures: {full_result.critical_failures}")
    print(f"Warnings: {full_result.warnings}")

if __name__ == "__main__":
    asyncio.run(main())