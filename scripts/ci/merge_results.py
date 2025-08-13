#!/usr/bin/env python3
"""Merge test results from multiple shards for GitHub Actions."""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Any


def merge_json_results(input_dir: Path, output_json: Path, output_coverage: Path) -> None:
    """Merge multiple JSON test result files into a single report."""
    merged_results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "duration": 0.0,
        "shards": [],
        "failures": [],
        "errors_list": []
    }
    
    # Find all JSON result files
    json_files = list(input_dir.glob("test-results-*.json"))
    
    if not json_files:
        print(f"No test result files found in {input_dir}")
        # Create empty result file
        with open(output_json, "w") as f:
            json.dump(merged_results, f, indent=2)
        return
    
    print(f"Found {len(json_files)} result files to merge")
    
    for json_file in json_files:
        print(f"  - Processing {json_file.name}")
        try:
            with open(json_file, "r") as f:
                shard_results = json.load(f)
            
            # Extract shard name from filename
            shard_name = json_file.stem.replace("test-results-", "")
            shard_results["shard"] = shard_name
            merged_results["shards"].append(shard_results)
            
            # Aggregate statistics
            merged_results["total_tests"] += shard_results.get("total_tests", 0)
            merged_results["passed"] += shard_results.get("passed", 0)
            merged_results["failed"] += shard_results.get("failed", 0)
            merged_results["skipped"] += shard_results.get("skipped", 0)
            merged_results["errors"] += shard_results.get("errors", 0)
            merged_results["duration"] += shard_results.get("duration", 0.0)
            
            # Collect failures and errors
            if "failures" in shard_results:
                for failure in shard_results["failures"]:
                    failure["shard"] = shard_name
                    merged_results["failures"].append(failure)
            
            if "errors_list" in shard_results:
                for error in shard_results["errors_list"]:
                    error["shard"] = shard_name
                    merged_results["errors_list"].append(error)
                    
        except Exception as e:
            print(f"    Error processing {json_file}: {e}")
    
    # Calculate success rate
    if merged_results["total_tests"] > 0:
        merged_results["success_rate"] = (
            merged_results["passed"] / merged_results["total_tests"] * 100
        )
    else:
        merged_results["success_rate"] = 0.0
    
    # Save merged results
    with open(output_json, "w") as f:
        json.dump(merged_results, f, indent=2)
    
    print(f"\nMerged results saved to: {output_json}")
    print(f"Total tests: {merged_results['total_tests']}")
    print(f"Passed: {merged_results['passed']}")
    print(f"Failed: {merged_results['failed']}")
    print(f"Success rate: {merged_results['success_rate']:.1f}%")
    
    # Merge coverage files if they exist
    coverage_files = list(input_dir.glob("coverage-*.xml"))
    if coverage_files:
        print(f"\nFound {len(coverage_files)} coverage files")
        # For now, just copy the first one as a placeholder
        # In production, you'd use coverage.py's combine feature
        import shutil
        shutil.copy(coverage_files[0], output_coverage)
        print(f"Coverage report saved to: {output_coverage}")


def main():
    parser = argparse.ArgumentParser(description="Merge test results from multiple shards")
    parser.add_argument("--input-dir", required=True, help="Directory containing test result files")
    parser.add_argument("--output-json", required=True, help="Output JSON file path")
    parser.add_argument("--output-coverage", required=True, help="Output coverage XML file path")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_json = Path(args.output_json)
    output_coverage = Path(args.output_coverage)
    
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return 1
    
    merge_json_results(input_dir, output_json, output_coverage)
    return 0


if __name__ == "__main__":
    exit(main())