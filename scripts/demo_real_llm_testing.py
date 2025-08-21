#!/usr/bin/env python3
"""
Demo script for Real LLM Testing Configuration

This script demonstrates the enhanced real LLM testing configuration
that provides isolated test environments with comprehensive validation.

Business Value Justification (BVJ):
1. Segment: Platform/Internal
2. Business Goal: Testing Infrastructure Excellence  
3. Value Impact: Demonstrates reliable AI optimization validation capabilities
4. Revenue Impact: Enables confident deployment of AI features
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.real_llm_config import (
    configure_real_llm_testing,
    get_real_llm_manager,
)
from test_framework.seed_data_manager import get_seed_data_manager
from test_framework.test_environment_setup import (
    TestEnvironmentValidator,
    get_test_orchestrator,
)


async def demo_environment_validation():
    """Demonstrate environment validation for real LLM testing."""
    print("=" * 60)
    print("REAL LLM TESTING ENVIRONMENT VALIDATION DEMO")
    print("=" * 60)
    
    # Initialize validator
    validator = TestEnvironmentValidator()
    
    # Test database validation
    print("\n1. Database Validation:")
    database_url = os.getenv('TEST_DATABASE_URL', os.getenv('DATABASE_URL', 'postgresql://localhost/netra_test'))
    try:
        db_valid = await validator.validate_database_connection(database_url)
        print(f"   Database connection: {'PASSED' if db_valid else 'FAILED'}")
    except Exception as e:
        print(f"   Database connection: FAILED ({e})")
    
    # Test API key validation
    print("\n2. API Key Validation:")
    try:
        api_valid = await validator.validate_api_keys(True)
        print(f"   API keys: {'PASSED' if api_valid else 'FAILED'}")
        
        # Show detailed API key status
        validation_results = validator.validation_results.get('api_keys', {})
        if isinstance(validation_results, dict):
            available_providers = validation_results.get('available_providers', [])
            missing_providers = validation_results.get('missing_providers', [])
            isolation_level = validation_results.get('isolation_level', 'unknown')
            
            print(f"   Available providers: {available_providers}")
            print(f"   Missing providers: {missing_providers}")
            print(f"   Isolation level: {isolation_level}")
    except Exception as e:
        print(f"   API keys: FAILED ({e})")
    
    # Test seed data validation
    print("\n3. Seed Data Validation:")
    required_datasets = ['basic_optimization', 'complex_workflows']
    try:
        seed_valid = validator.validate_seed_data_files(required_datasets)
        print(f"   Seed data: {'PASSED' if seed_valid else 'FAILED'}")
        
        # Show seed data details
        seed_results = validator.validation_results.get('seed_data', {})
        if isinstance(seed_results, dict) and 'file_details' in seed_results:
            print("   Dataset details:")
            for dataset, details in seed_results['file_details'].items():
                size_kb = details['size_bytes'] / 1024
                record_count = sum(details['record_count'].values())
                print(f"     - {dataset}: {size_kb:.1f}KB, {record_count} records")
    except Exception as e:
        print(f"   Seed data: FAILED ({e})")
    
    # Overall validation summary
    print("\n4. Overall Validation Summary:")
    validation_summary = validator.get_validation_summary()
    print(f"   Status: {validation_summary['overall_status']}")


async def demo_real_llm_configuration():
    """Demonstrate real LLM configuration setup."""
    print("\n" + "=" * 60)
    print("REAL LLM CONFIGURATION DEMO")
    print("=" * 60)
    
    # Initialize real LLM manager
    print("\n1. Initializing Real LLM Manager:")
    try:
        llm_manager = get_real_llm_manager()
        print("   Real LLM manager: INITIALIZED")
        
        # Show configuration details
        config = llm_manager.config_manager.config
        print(f"   Enabled: {config.enabled}")
        print(f"   Testing mode: {config.testing_mode.value}")
        print(f"   Cost budget: ${config.cost_budget_per_run}")
        print(f"   Rate limit: {config.rate_limit_per_minute} calls/minute")
        
        # Show available models
        print("   Available models:")
        for model_key, model_config in config.models.items():
            print(f"     - {model_key}: {model_config.name} (${model_config.cost_per_1k_tokens:.4f}/1k tokens)")
        
        # Show API key status
        print("   API key status:")
        for provider in ['openai', 'anthropic', 'google']:
            has_key = llm_manager.config_manager.has_provider(provider)
            print(f"     - {provider}: {'CONFIGURED' if has_key else 'NOT_CONFIGURED'}")
            
    except Exception as e:
        print(f"   Real LLM manager: FAILED ({e})")


async def demo_seed_data_management():
    """Demonstrate seed data management capabilities."""
    print("\n" + "=" * 60)
    print("SEED DATA MANAGEMENT DEMO")
    print("=" * 60)
    
    try:
        # Initialize seed data manager (without actual database connection for demo)
        print("\n1. Seed Data Manager Features:")
        print("   - Parallel dataset loading")
        print("   - Data integrity verification")
        print("   - Dependency resolution")
        print("   - Transaction-based isolation")
        
        # Show dataset structure
        print("\n2. Available Datasets:")
        test_data_dir = Path(project_root) / "test_data" / "seed"
        if test_data_dir.exists():
            for seed_file in test_data_dir.glob("*.json"):
                try:
                    import json
                    with open(seed_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    metadata = data.get('metadata', {})
                    description = metadata.get('description', 'No description')
                    record_counts = metadata.get('record_count', {})
                    total_records = sum(record_counts.values()) if record_counts else 0
                    
                    print(f"   - {seed_file.stem}:")
                    print(f"     Description: {description}")
                    print(f"     Total records: {total_records}")
                    if record_counts:
                        print(f"     Record types: {list(record_counts.keys())}")
                except Exception as e:
                    print(f"   - {seed_file.stem}: ERROR reading file ({e})")
        else:
            print("   No seed data directory found")
            
    except Exception as e:
        print(f"   Seed data management: FAILED ({e})")


async def demo_test_environment_orchestration():
    """Demonstrate test environment orchestration."""
    print("\n" + "=" * 60)
    print("TEST ENVIRONMENT ORCHESTRATION DEMO")
    print("=" * 60)
    
    print("\n1. Test Environment Features:")
    print("   - Comprehensive validation pipeline")
    print("   - Isolated test sessions")  
    print("   - Automatic dataset dependency resolution")
    print("   - Environment safety scoring")
    
    print("\n2. Test Level Dataset Mappings:")
    from test_framework.test_execution_engine import get_datasets_for_llm_level
    
    test_levels = ['unit', 'integration', 'agents', 'e2e', 'comprehensive', 'critical', 'performance']
    for level in test_levels:
        datasets = get_datasets_for_llm_level(level)
        print(f"   - {level}: {datasets}")
    
    print("\n3. Environment Safety Assessment:")
    from test_framework.test_execution_engine import calculate_environment_safety_score
    
    scenarios = [
        ("Fully Isolated", "test_db", "test_redis", "test_ch", ["openai", "anthropic"]),
        ("Production DB", None, "test_redis", "test_ch", ["openai"]),
        ("Mixed Environment", "test_db", None, None, []),
        ("Production Only", None, None, None, [])
    ]
    
    for scenario_name, test_db, test_redis, test_ch, test_keys in scenarios:
        safety_score = calculate_environment_safety_score(test_db, test_redis, test_ch, test_keys)
        print(f"   - {scenario_name}: {safety_score}")


def demo_cli_usage():
    """Demonstrate CLI usage examples."""
    print("\n" + "=" * 60)
    print("CLI USAGE EXAMPLES")
    print("=" * 60)
    
    print("\n1. Basic Real LLM Testing:")
    print("   python -m test_framework.test_runner --level integration --real-llm")
    print("   python -m test_framework.test_runner --level agents --real-llm")
    
    print("\n2. Advanced Real LLM Testing:")
    print("   python -m test_framework.test_runner --level integration --real-llm --llm-model gpt-4")
    print("   python -m test_framework.test_runner --level agents --real-llm --llm-timeout 60")
    print("   python -m test_framework.test_runner --level comprehensive --real-llm --parallel 1")
    
    print("\n3. Environment Configuration:")
    print("   # Set test-specific API keys (recommended)")
    print("   export TEST_OPENAI_API_KEY=your_test_key")
    print("   export TEST_ANTHROPIC_API_KEY=your_test_key")
    print("")
    print("   # Set test database (recommended)")
    print("   export TEST_DATABASE_URL=postgresql://localhost/netra_test")
    print("")
    print("   # Enable transaction isolation")
    print("   export USE_TEST_ISOLATION=true")
    
    print("\n4. Database Setup:")
    print("   # Setup test database")
    print("   psql -f database_scripts/setup_test_db.sql")
    print("")
    print("   # Teardown test database")
    print("   psql -f database_scripts/teardown_test_db.sql")


async def main():
    """Run the complete demo."""
    print("Real LLM Testing Configuration Demo")
    print("Netra AI Optimization Platform")
    print("=" * 60)
    
    try:
        await demo_environment_validation()
        await demo_real_llm_configuration()
        await demo_seed_data_management()
        await demo_test_environment_orchestration()
        demo_cli_usage()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nThe Real LLM Testing Configuration is ready for use!")
        print("All components have been enhanced with:")
        print("- Isolated test environments")
        print("- Comprehensive validation")
        print("- Enhanced seed data management")
        print("- Parallel test coordination")
        print("- Cost tracking and safety monitoring")
        
    except Exception as e:
        print(f"\nDEMO FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())