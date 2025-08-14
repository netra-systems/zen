#!/usr/bin/env python3
"""
Autonomous Test Review System - Main Entry Point
Command-line interface for the autonomous test review system
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .types import ReviewMode
from .test_reviewer import AutonomousTestReviewer


async def main():
    """Main entry point for autonomous test review"""
    parser = argparse.ArgumentParser(
        description="Autonomous Test Review System - Ultra-thinking powered test improvement"
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=[mode.value for mode in ReviewMode],
        default="auto",
        help="Review execution mode"
    )
    
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in fully autonomous mode with auto-fixes"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test refresh (< 5 minutes)"
    )
    
    parser.add_argument(
        "--full-analysis",
        action="store_true",
        help="Complete test suite analysis with ultra-thinking"
    )
    
    parser.add_argument(
        "--smart-generate",
        action="store_true",
        help="Intelligently generate missing tests"
    )
    
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous background review"
    )
    
    parser.add_argument(
        "--ultra-think",
        action="store_true",
        help="Enable ultra-thinking deep analysis"
    )
    
    parser.add_argument(
        "--target-coverage",
        type=float,
        default=97.0,
        help="Target coverage percentage (default: 97)"
    )
    
    args = parser.parse_args()
    
    # Determine mode from arguments
    if args.auto:
        mode = ReviewMode.AUTO
    elif args.quick:
        mode = ReviewMode.QUICK
    elif args.full_analysis:
        mode = ReviewMode.FULL_ANALYSIS
    elif args.smart_generate:
        mode = ReviewMode.SMART_GENERATE
    elif args.continuous:
        mode = ReviewMode.CONTINUOUS
    elif args.ultra_think:
        mode = ReviewMode.ULTRA_THINK
    else:
        mode = ReviewMode(args.mode)
    
    # Run review
    reviewer = AutonomousTestReviewer()
    reviewer.coverage_goal = args.target_coverage
    
    if mode == ReviewMode.CONTINUOUS:
        # Run continuous review loop
        print("[CONTINUOUS] Starting continuous test review...")
        while True:
            try:
                analysis = await reviewer.run_review(ReviewMode.AUTO)
                print(f"\n[STATUS] Coverage: {analysis.coverage_percentage:.1f}% | Quality: {analysis.quality_score:.0f}/100")
                print("[WAITING] Next review in 1 hour...")
                await asyncio.sleep(3600)  # Wait 1 hour
            except KeyboardInterrupt:
                print("\n[STOPPED] Continuous review stopped")
                break
    else:
        # Run single review
        analysis = await reviewer.run_review(mode)
        
        # Print summary
        print("\n" + "=" * 60)
        print("REVIEW COMPLETE")
        print("=" * 60)
        print(f"Coverage: {analysis.coverage_percentage:.1f}% (Target: {reviewer.coverage_goal}%)")
        print(f"Quality Score: {analysis.quality_score:.0f}/100")
        print(f"Critical Gaps: {len(analysis.critical_gaps)}")
        print(f"Missing Tests: {len(analysis.missing_tests)}")
        print(f"Test Debt: {analysis.test_debt} issues")
        
        if analysis.recommendations:
            print("\nTop Recommendations:")
            for i, rec in enumerate(analysis.recommendations[:3], 1):
                print(f"  {i}. {rec}")


if __name__ == "__main__":
    asyncio.run(main())