#!/usr/bin/env python3
"""
Network Resilience Issue Diagnostic

This script tests the exact URL normalization issue in NetworkResilientClient._check_postgresql
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_asyncpg_url_handling():
    """Test how asyncpg handles different URL formats."""
    logger.info("=== TESTING ASYNCPG URL HANDLING ===")
    
    test_urls = [
        "postgresql://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev",
        "postgresql+asyncpg://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev",
    ]
    
    for url in test_urls:
        logger.info(f"\nTesting URL: {url}")
        try:
            import asyncpg
            
            conn = await asyncio.wait_for(
                asyncpg.connect(url),
                timeout=5.0
            )
            
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            
            logger.info(f"  ✅ SUCCESS: {result}")
            
        except Exception as e:
            logger.error(f"  ❌ FAILED: {e}")

async def test_network_resilience_bug():
    """Test the exact bug in NetworkResilientClient."""
    logger.info("\n=== TESTING NETWORK RESILIENCE BUG ===")
    
    from dev_launcher.network_resilience import NetworkResilientClient
    
    client = NetworkResilientClient()
    
    # This is the URL that NetworkResilientClient receives
    problematic_url = "postgresql+asyncpg://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev"
    
    logger.info(f"Testing NetworkResilientClient._check_postgresql with: {problematic_url}")
    
    try:
        success, error = await client._check_postgresql(problematic_url, timeout=5.0)
        if success:
            logger.info("✅ NetworkResilientClient SUCCESS")
        else:
            logger.error(f"❌ NetworkResilientClient FAILED: {error}")
    except Exception as e:
        logger.error(f"❌ NetworkResilientClient EXCEPTION: {e}")

async def test_fixed_network_resilience():
    """Test the fixed NetworkResilientClient behavior."""
    logger.info("\n=== TESTING FIXED NETWORK RESILIENCE ===")
    
    problematic_url = "postgresql+asyncpg://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev"
    
    # This is what the fix should do
    logger.info("Testing URL normalization for asyncpg:")
    
    # Remove the driver prefix for asyncpg
    clean_url = problematic_url.replace("postgresql+asyncpg://", "postgresql://")
    logger.info(f"  Original URL: {problematic_url}")
    logger.info(f"  Cleaned URL:  {clean_url}")
    
    try:
        import asyncpg
        
        conn = await asyncio.wait_for(
            asyncpg.connect(clean_url),
            timeout=5.0
        )
        
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        logger.info(f"  ✅ FIXED VERSION SUCCESS: {result}")
        
    except Exception as e:
        logger.error(f"  ❌ FIXED VERSION FAILED: {e}")

async def main():
    """Run all diagnostic tests."""
    logger.info("🔍 STARTING NETWORK RESILIENCE ISSUE DIAGNOSTIC")
    logger.info("=" * 80)
    
    await test_asyncpg_url_handling()
    await test_network_resilience_bug()
    await test_fixed_network_resilience()
    
    logger.info("\n" + "=" * 80)
    logger.info("🧠 CONCLUSION")
    logger.info("=" * 80)
    logger.info("The NetworkResilientClient._check_postgresql method is passing")
    logger.info("postgresql+asyncpg:// URLs directly to asyncpg.connect(),")
    logger.info("but asyncpg only accepts postgresql:// URLs.")
    logger.info("")
    logger.info("FIX: Strip driver prefixes in NetworkResilientClient._check_postgresql")

if __name__ == "__main__":
    asyncio.run(main())