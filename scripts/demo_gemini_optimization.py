#!/usr/bin/env python3
"""Demonstration script for Gemini 2.5 Flash circuit breaker optimization.

This script demonstrates the performance improvements achieved through
Gemini-specific circuit breaker tuning compared to generic LLM configurations.

Run this script to see:
1. Gemini-specific vs default configuration comparison
2. Health checker configuration
3. Fallback chain optimization
4. Performance characteristics summary
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.llm.llm_defaults import LLMModel
from netra_backend.app.llm.gemini_config import (
    get_gemini_config,
    create_gemini_circuit_config,
    create_gemini_health_config,
    get_gemini_fallback_chain,
    is_gemini_model
)
from netra_backend.app.core.resilience.domain_circuit_breakers import (
    LLMCircuitBreakerConfig,
    LLMCircuitBreaker
)
from netra_backend.app.core.health.gemini_health import create_gemini_health_checker


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-' * 40}")
    print(f"  {title}")
    print(f"{'-' * 40}")


def compare_configurations():
    """Compare Gemini-optimized vs default LLM configurations."""
    print_section("CONFIGURATION COMPARISON")
    
    # Get configurations
    default_config = LLMCircuitBreakerConfig()
    flash_config = create_gemini_circuit_config(LLMModel.GEMINI_2_5_FLASH)
    pro_config = create_gemini_circuit_config(LLMModel.GEMINI_2_5_PRO)
    
    print_subsection("Timeout Settings (seconds)")
    print(f"Default LLM timeout:       {default_config.request_timeout_seconds:>8.1f}")
    print(f"Gemini Flash timeout:      {flash_config['timeout_seconds']:>8.1f}")
    print(f"Gemini Pro timeout:        {pro_config['timeout_seconds']:>8.1f}")
    print(f"")
    print(f"Flash improvement:         {((default_config.request_timeout_seconds - flash_config['timeout_seconds']) / default_config.request_timeout_seconds * 100):>7.1f}% faster")
    
    print_subsection("Recovery Settings")
    print(f"Default recovery timeout:  {default_config.recovery_timeout_seconds:>8.1f}s")
    print(f"Flash recovery timeout:    {flash_config['recovery_timeout']:>8.1f}s")
    print(f"Pro recovery timeout:      {pro_config['recovery_timeout']:>8.1f}s")
    print(f"")
    print(f"Flash recovery improvement: {((default_config.recovery_timeout_seconds - flash_config['recovery_timeout']) / default_config.recovery_timeout_seconds * 100):>6.1f}% faster")
    
    print_subsection("Circuit Breaker Settings")
    print(f"Default failure threshold: {default_config.failure_threshold:>8}")
    print(f"Flash failure threshold:   {flash_config['failure_threshold']:>8}")
    print(f"Pro failure threshold:     {pro_config['failure_threshold']:>8}")
    print(f"")
    print("Higher thresholds = more tolerance for transient errors")


def show_model_characteristics():
    """Show Gemini model performance characteristics."""
    print_section("GEMINI MODEL CHARACTERISTICS")
    
    flash_model = get_gemini_config(LLMModel.GEMINI_2_5_FLASH)
    pro_model = get_gemini_config(LLMModel.GEMINI_2_5_PRO)
    
    print_subsection("Performance Metrics")
    print(f"{'Metric':<25} {'Flash':<12} {'Pro':<12}")
    print(f"{'-' * 25} {'-' * 12} {'-' * 12}")
    print(f"{'Avg Response Time':<25} {flash_model.avg_response_time_seconds:<12.1f} {pro_model.avg_response_time_seconds:<12.1f}")
    print(f"{'Max Response Time':<25} {flash_model.max_response_time_seconds:<12.1f} {pro_model.max_response_time_seconds:<12.1f}")
    print(f"{'Requests/Minute':<25} {flash_model.requests_per_minute:<12} {pro_model.requests_per_minute:<12}")
    print(f"{'Tokens/Minute':<25} {flash_model.tokens_per_minute:<12} {pro_model.tokens_per_minute:<12}")
    
    print_subsection("Cost Optimization (per 1K tokens)")
    print(f"{'Model':<12} {'Input Cost':<12} {'Output Cost':<12} {'Total Est.':<12}")
    print(f"{'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12}")
    flash_total = flash_model.input_cost_per_1k_tokens + flash_model.output_cost_per_1k_tokens
    pro_total = pro_model.input_cost_per_1k_tokens + pro_model.output_cost_per_1k_tokens
    print(f"{'Flash':<12} ${flash_model.input_cost_per_1k_tokens:<11.6f} ${flash_model.output_cost_per_1k_tokens:<11.6f} ${flash_total:<11.6f}")
    print(f"{'Pro':<12} ${pro_model.input_cost_per_1k_tokens:<11.6f} ${pro_model.output_cost_per_1k_tokens:<11.6f} ${pro_total:<11.6f}")
    
    cost_savings = ((pro_total - flash_total) / pro_total) * 100
    print(f"\nFlash cost savings vs Pro: {cost_savings:.1f}%")


def show_fallback_chains():
    """Show optimized fallback chains for Gemini models."""
    print_section("FALLBACK CHAIN OPTIMIZATION")
    
    print_subsection("Gemini 2.5 Flash Fallback Chain")
    flash_chain = get_gemini_fallback_chain(LLMModel.GEMINI_2_5_FLASH)
    for i, model in enumerate(flash_chain, 1):
        provider = model.get_provider()
        print(f"  {i}. {model.value} ({provider})")
    
    print_subsection("Gemini 2.5 Pro Fallback Chain")
    pro_chain = get_gemini_fallback_chain(LLMModel.GEMINI_2_5_PRO)
    for i, model in enumerate(pro_chain, 1):
        provider = model.get_provider()
        print(f"  {i}. {model.value} ({provider})")
    
    print("\nFallback Strategy:")
    print("- Primary: Use specified Gemini model")
    print("- Secondary: Fallback to other Gemini model (same provider)")
    print("- Tertiary: Fallback to external providers as needed")


async def demonstrate_health_monitoring():
    """Demonstrate health monitoring capabilities."""
    print_section("HEALTH MONITORING")
    
    try:
        # Create health checker
        health_checker = create_gemini_health_checker(LLMModel.GEMINI_2_5_FLASH)
        
        print_subsection("Health Configuration")
        health_config = create_gemini_health_config(LLMModel.GEMINI_2_5_FLASH)
        
        print(f"Check interval:           {health_config['check_interval_seconds']}s")
        print(f"Timeout:                  {health_config['timeout_seconds']}s")
        print(f"Min success rate:         {health_config['min_success_rate'] * 100:.1f}%")
        print(f"Max avg latency:          {health_config['max_avg_latency_ms']}ms")
        print(f"Validate API key:         {health_config['validate_api_key']}")
        print(f"Check quota usage:        {health_config['check_quota_usage']}")
        
        print_subsection("Health Checker Status")
        status = health_checker.get_detailed_status()
        print(f"Service:                  {status['service']}")
        print(f"Model:                    {status['model']}")
        print(f"Status:                   {status['status']}")
        print(f"Check interval:           {status['check_interval']}s")
        
        # Clean up
        await health_checker.cleanup()
        
    except Exception as e:
        print(f"Health monitoring demo failed: {e}")
        print("This is expected if GOOGLE_API_KEY is not configured")


def show_optimization_summary():
    """Show summary of optimization benefits."""
    print_section("OPTIMIZATION SUMMARY")
    
    benefits = [
        "[+] 91.7% faster timeout for Flash model (5s vs 60s)",
        "[+] 50% faster recovery time (5s vs 10s)", 
        "[+] Higher failure threshold (10 vs 3) for stable models",
        "[+] Provider-aware fallback chains",
        "[+] Model-specific health monitoring",
        "[+] Cost optimization through efficient model selection",
        "[+] Adaptive thresholds based on model characteristics",
        "[+] Burst capacity handling for high-throughput scenarios"
    ]
    
    print("Key Performance Improvements:")
    for benefit in benefits:
        print(f"  {benefit}")
    
    print(f"\nBusiness Impact:")
    print(f"  * Reduced response times improve user experience")
    print(f"  * Faster recovery reduces downtime")
    print(f"  * Cost savings through optimal model selection")
    print(f"  * Improved reliability through provider-specific tuning")


def main():
    """Run the Gemini optimization demonstration."""
    print("Gemini 2.5 Flash Circuit Breaker Optimization Demo")
    print("=" * 60)
    
    # Verify Gemini model detection
    models_to_check = ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4", "claude-3-opus"]
    print(f"\nModel Detection:")
    for model in models_to_check:
        is_gemini = is_gemini_model(model)
        print(f"  {model:<20} {'[+] Gemini' if is_gemini else '[-] Not Gemini'}")
    
    # Run demonstrations
    compare_configurations()
    show_model_characteristics()
    show_fallback_chains()
    
    # Run async health monitoring demo
    asyncio.run(demonstrate_health_monitoring())
    
    show_optimization_summary()
    
    print(f"\n{'=' * 60}")
    print("Demo completed successfully!")
    print("Run tests with: python -m pytest netra_backend/tests/integration/test_gemini_optimization.py")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()