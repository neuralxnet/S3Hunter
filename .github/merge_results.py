#!/usr/bin/env python3
"""
Merge all JSON result files into bucket files with automatic rotation.
This script combines all individual scan results and rotates files when they exceed 20MB.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


# Maximum file size in bytes (20 MB)
MAX_FILE_SIZE = 20 * 1024 * 1024


def get_file_size(filepath):
    """Get file size in bytes, return 0 if file doesn't exist."""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def find_existing_bucket_files(results_path):
    """Find all existing bucket files (buckets.json, buckets_1.json, etc.)."""
    bucket_files = []
    
    # Check for buckets.json
    base_file = results_path / "buckets.json"
    if base_file.exists():
        bucket_files.append(base_file)
    
    # Check for buckets_N.json files
    index = 1
    while True:
        numbered_file = results_path / f"buckets_{index}.json"
        if numbered_file.exists():
            bucket_files.append(numbered_file)
            index += 1
        else:
            break
    
    return bucket_files


def load_existing_buckets(results_path):
    """Load all existing buckets from all bucket files."""
    bucket_files = find_existing_bucket_files(results_path)
    
    all_public_buckets = []
    all_private_buckets = []
    
    for bucket_file in bucket_files:
        try:
            print(f"Loading existing data from: {bucket_file.name}")
            with open(bucket_file, 'r') as f:
                data = json.load(f)
                
                # Extract public buckets
                if 'buckets' in data and 'public' in data['buckets']:
                    all_public_buckets.extend(data['buckets']['public'])
                
                # Extract private buckets
                if 'buckets' in data and 'private' in data['buckets']:
                    all_private_buckets.extend(data['buckets']['private'])
                    
        except Exception as e:
            print(f"Warning: Failed to load {bucket_file.name}: {e}")
            continue
    
    return all_public_buckets, all_private_buckets


def estimate_json_size(data):
    """Estimate the size of JSON data when serialized."""
    return len(json.dumps(data, indent=2).encode('utf-8'))


def split_buckets_by_size(public_buckets, private_buckets, max_size=MAX_FILE_SIZE):
    """Split buckets into multiple files to respect size limit."""
    files_data = []
    current_file_data = {
        "buckets": {
            "public": [],
            "private": []
        }
    }
    
    # Constants for performance optimization
    # Average bucket entry is about 200-300 bytes based on typical S3 bucket data
    AVERAGE_BUCKET_SIZE_BYTES = 250
    SIZE_CHECK_FREQUENCY = 100  # Check size every N buckets for performance
    
    # Calculate how often to check size based on file size limit
    check_interval = max(1, max_size // (AVERAGE_BUCKET_SIZE_BYTES * SIZE_CHECK_FREQUENCY))
    
    bucket_count = 0
    
    # Add public buckets
    for bucket in public_buckets:
        current_file_data["buckets"]["public"].append(bucket)
        bucket_count += 1
        
        # Only check size periodically for efficiency
        if bucket_count % check_interval == 0:
            current_size = estimate_json_size(current_file_data)
            
            # If we're approaching the limit, save current file
            if current_size > max_size * 0.95:  # 95% threshold
                # Save current file data
                if current_file_data["buckets"]["public"] or current_file_data["buckets"]["private"]:
                    files_data.append(current_file_data)
                
                # Start new file
                current_file_data = {
                    "buckets": {
                        "public": [],
                        "private": []
                    }
                }
    
    # Add private buckets
    bucket_count = 0
    for bucket in private_buckets:
        current_file_data["buckets"]["private"].append(bucket)
        bucket_count += 1
        
        # Only check size periodically for efficiency
        if bucket_count % check_interval == 0:
            current_size = estimate_json_size(current_file_data)
            
            # If we're approaching the limit, save current file
            if current_size > max_size * 0.95:  # 95% threshold
                # Save current file data
                if current_file_data["buckets"]["public"] or current_file_data["buckets"]["private"]:
                    files_data.append(current_file_data)
                
                # Start new file
                current_file_data = {
                    "buckets": {
                        "public": [],
                        "private": []
                    }
                }
    
    # Add the last file if it has data
    if current_file_data["buckets"]["public"] or current_file_data["buckets"]["private"]:
        files_data.append(current_file_data)
    
    return files_data


def merge_json_files(results_dir, output_file):
    """
    Merge all JSON files from results directory, appending to existing buckets.json.
    Automatically rotates files when they exceed 20MB.
    
    Args:
        results_dir: Directory containing JSON result files
        output_file: Base output file name (e.g., "buckets.json")
    """
    results_path = Path(results_dir)
    
    if not results_path.exists():
        print(f"Error: Results directory '{results_dir}' does not exist")
        sys.exit(1)
    
    # Find all JSON files in results directory (exclude bucket files)
    json_files = list(results_path.glob("*.json"))
    
    # Exclude all bucket files (buckets.json, buckets_1.json, etc.)
    json_files = [f for f in json_files if not (f.name == "buckets.json" or f.name.startswith("buckets_"))]
    
    if not json_files:
        print("No new JSON files found to merge")
        sys.exit(0)
    
    print(f"Found {len(json_files)} new JSON files to merge")
    
    # Load existing buckets from all bucket files
    print("\nLoading existing bucket data...")
    existing_public, existing_private = load_existing_buckets(results_path)
    print(f"  Loaded {len(existing_public)} existing public buckets")
    print(f"  Loaded {len(existing_private)} existing private buckets")
    
    # Collect all buckets from new files
    new_public_buckets = []
    new_private_buckets = []
    
    # Statistics
    total_domains = set()
    total_chunks = 0
    
    print("\nProcessing new result files...")
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
                # Track metadata
                total_domains.add(data.get('domain', 'unknown'))
                total_chunks += 1
                
                # Extract public buckets
                if 'results' in data and 'public' in data['results']:
                    new_public_buckets.extend(data['results']['public'])
                
                # Extract private buckets
                if 'results' in data and 'private' in data['results']:
                    new_private_buckets.extend(data['results']['private'])
                    
        except Exception as e:
            print(f"Warning: Failed to process {json_file.name}: {e}")
            continue
    
    print(f"  Found {len(new_public_buckets)} new public buckets")
    print(f"  Found {len(new_private_buckets)} new private buckets")
    
    # Combine existing and new buckets
    all_public_buckets = existing_public + new_public_buckets
    all_private_buckets = existing_private + new_private_buckets
    
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
    
    print(f"\nAfter deduplication:")
    print(f"  Total unique public buckets: {len(unique_public)}")
    print(f"  Total unique private buckets: {len(unique_private)}")
    
    # Sort buckets
    sorted_public = sorted(list(unique_public.values()), key=lambda x: x.get('timestamp', ''))
    sorted_private = sorted(list(unique_private.values()), key=lambda x: x.get('timestamp', ''))
    
    # Split buckets into multiple files if needed
    print("\nSplitting data into files (max 20MB each)...")
    files_data = split_buckets_by_size(sorted_public, sorted_private)
    
    print(f"  Data will be split into {len(files_data)} file(s)")
    
    # First, get list of old bucket files to delete later
    old_bucket_files = find_existing_bucket_files(results_path)
    
    # Write data to NEW files first (to avoid data loss if write fails)
    new_files_written = []
    for idx, file_data in enumerate(files_data):
        # Determine filename
        if idx == 0:
            filename = output_file
        else:
            filename = f"buckets_{idx}.json"
        
        output_path = results_path / filename
        
        # Add metadata
        file_data["generated_at"] = datetime.now().astimezone().isoformat()
        file_data["source_files"] = len(json_files)
        file_data["domains_scanned"] = len(total_domains)
        file_data["total_chunks"] = total_chunks
        file_data["file_index"] = idx
        file_data["total_files"] = len(files_data)
        file_data["stats"] = {
            "public_buckets_in_file": len(file_data["buckets"]["public"]),
            "private_buckets_in_file": len(file_data["buckets"]["private"]),
            "total_buckets_in_file": len(file_data["buckets"]["public"]) + len(file_data["buckets"]["private"]),
            "total_public_buckets": len(unique_public),
            "total_private_buckets": len(unique_private),
            "total_buckets": len(unique_public) + len(unique_private)
        }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(file_data, f, indent=2)
        
        new_files_written.append(output_path)
        
        file_size = get_file_size(output_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"  Written: {filename} ({file_size_mb:.2f} MB)")
    
    # Only delete old bucket files AFTER successfully writing all new files
    # This prevents data loss if the write operation fails
    for old_file in old_bucket_files:
        # Don't delete files we just wrote
        if old_file not in new_files_written:
            try:
                old_file.unlink()
                print(f"  Cleaned up old file: {old_file.name}")
            except Exception as e:
                print(f"  Warning: Failed to delete old file {old_file.name}: {e}")
    
    print(f"\nMerge Summary:")
    print(f"  New source files: {len(json_files)}")
    print(f"  Domains scanned: {len(total_domains)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Total unique public buckets: {len(unique_public)}")
    print(f"  Total unique private buckets: {len(unique_private)}")
    print(f"  Total unique buckets: {len(unique_public) + len(unique_private)}")
    print(f"  Output files created: {len(files_data)}")
    
    # Delete the individual JSON files after successful merge
    print(f"\nDeleting {len(json_files)} merged source files...")
    deleted_count = 0
    failed_deletes = []
    
    for json_file in json_files:
        try:
            json_file.unlink()
            deleted_count += 1
        except Exception as e:
            failed_deletes.append((json_file.name, str(e)))
    
    print(f"  Successfully deleted: {deleted_count} files")
    
    if failed_deletes:
        print(f"  Failed to delete {len(failed_deletes)} files:")
        for filename, error in failed_deletes:
            print(f"    - {filename}: {error}")


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
