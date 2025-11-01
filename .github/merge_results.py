#!/usr/bin/env python3
"""
Merge all JSON result files into a single buckets.json file.
This script combines all individual scan results into one consolidated file.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


def merge_json_files(results_dir, output_file):
    """
    Merge all JSON files from results directory into a single buckets.json file.
    
    Args:
        results_dir: Directory containing JSON result files
        output_file: Output file path for merged results
    """
    results_path = Path(results_dir)
    
    if not results_path.exists():
        print(f"Error: Results directory '{results_dir}' does not exist")
        sys.exit(1)
    
    # Find all JSON files in results directory
    json_files = list(results_path.glob("*.json"))
    
    # Exclude the buckets.json file itself if it exists
    json_files = [f for f in json_files if f.name != "buckets.json"]
    
    if not json_files:
        print("No JSON files found to merge")
        sys.exit(0)
    
    print(f"Found {len(json_files)} JSON files to merge")
    
    # Collect all buckets
    all_public_buckets = []
    all_private_buckets = []
    
    # Statistics
    total_domains = set()
    total_chunks = 0
    
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
                # Track metadata
                total_domains.add(data.get('domain', 'unknown'))
                total_chunks += 1
                
                # Extract public buckets
                if 'results' in data and 'public' in data['results']:
                    all_public_buckets.extend(data['results']['public'])
                
                # Extract private buckets
                if 'results' in data and 'private' in data['results']:
                    all_private_buckets.extend(data['results']['private'])
                    
        except Exception as e:
            print(f"Warning: Failed to process {json_file.name}: {e}")
            continue
    
    # Remove duplicates based on bucket URL
    # Use a dictionary with URL as key to keep only unique buckets (last occurrence)
    unique_public = {}
    for bucket in all_public_buckets:
        url = bucket.get('url', '')
        if url:
            unique_public[url] = bucket
    
    unique_private = {}
    for bucket in all_private_buckets:
        url = bucket.get('url', '')
        if url:
            unique_private[url] = bucket
    
    # Create merged output
    merged_data = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_files": len(json_files),
        "domains_scanned": len(total_domains),
        "total_chunks": total_chunks,
        "stats": {
            "total_public_buckets": len(unique_public),
            "total_private_buckets": len(unique_private),
            "total_buckets": len(unique_public) + len(unique_private)
        },
        "buckets": {
            "public": sorted(list(unique_public.values()), key=lambda x: x.get('timestamp', '')),
            "private": sorted(list(unique_private.values()), key=lambda x: x.get('timestamp', ''))
        }
    }
    
    # Write merged data to output file
    output_path = results_path / output_file
    with open(output_path, 'w') as f:
        json.dump(merged_data, f, indent=2)
    
    print(f"\nMerge Summary:")
    print(f"  Source files: {len(json_files)}")
    print(f"  Domains scanned: {len(total_domains)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Public buckets: {len(unique_public)}")
    print(f"  Private buckets: {len(unique_private)}")
    print(f"  Total unique buckets: {len(unique_public) + len(unique_private)}")
    print(f"\nOutput written to: {output_path}")


if __name__ == "__main__":
    # Default paths
    results_dir = "results"
    output_file = "buckets.json"
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    merge_json_files(results_dir, output_file)
