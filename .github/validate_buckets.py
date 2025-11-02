#!/usr/bin/env python3
"""
Validate S3 buckets in buckets.json files.
This script checks if buckets are still accessible (HTTP 200) and updates timestamps.
Dead buckets (non-200 responses) are removed from the files.
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


# Configuration
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
REQUEST_TIMEOUT = 10  # seconds
MAX_WORKERS = 30  # concurrent validation threads


def find_bucket_files(results_path):
    """Find all bucket files (buckets.json, buckets_1.json, etc.)."""
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


def validate_bucket(bucket):
    """
    Validate a single bucket by checking its URL.
    Returns (bucket_with_updated_timestamp, is_valid) tuple.
    """
    url = bucket.get('url', '')
    
    if not url:
        return bucket, False
    
    try:
        response = requests.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        
        # Bucket is considered alive if status is 200
        if response.status_code == 200:
            # Update timestamp and status
            bucket['timestamp'] = datetime.now().astimezone().isoformat()
            bucket['status'] = response.status_code
            return bucket, True
        else:
            # Bucket is dead (not accessible)
            return bucket, False
            
    except requests.exceptions.Timeout:
        # Timeout means bucket is not responding - consider it dead
        return bucket, False
    except requests.exceptions.RequestException:
        # Any other network error - consider bucket dead
        return bucket, False


def validate_buckets_parallel(buckets, max_workers=MAX_WORKERS):
    """
    Validate buckets in parallel and return only the alive ones.
    Returns (alive_buckets, stats).
    """
    alive_buckets = []
    stats = {
        'total': len(buckets),
        'alive': 0,
        'dead': 0,
        'errors': 0
    }
    
    print(f"Validating {len(buckets)} buckets with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all validation tasks
        future_to_bucket = {
            executor.submit(validate_bucket, bucket): bucket 
            for bucket in buckets
        }
        
        # Process completed validations
        completed = 0
        for future in as_completed(future_to_bucket):
            completed += 1
            
            # Print progress every 50 buckets
            if completed % 50 == 0 or completed == len(buckets):
                print(f"  Progress: {completed}/{len(buckets)} buckets validated")
            
            try:
                updated_bucket, is_valid = future.result()
                
                if is_valid:
                    alive_buckets.append(updated_bucket)
                    stats['alive'] += 1
                else:
                    stats['dead'] += 1
                    
            except Exception as e:
                stats['errors'] += 1
                print(f"  Error validating bucket: {e}")
    
    return alive_buckets, stats


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
    AVERAGE_BUCKET_SIZE_BYTES = 250
    check_interval = max(50, max_size // (AVERAGE_BUCKET_SIZE_BYTES * 50))
    SIZE_THRESHOLD = max_size * 0.95
    
    def check_and_rotate_if_needed():
        """Check current file size and rotate if approaching limit."""
        current_size = estimate_json_size(current_file_data)
        if current_size > SIZE_THRESHOLD:
            # Save current file data
            if current_file_data["buckets"]["public"] or current_file_data["buckets"]["private"]:
                files_data.append(current_file_data)
            
            # Start new file
            return {
                "buckets": {
                    "public": [],
                    "private": []
                }
            }
        return current_file_data
    
    bucket_count = 0
    
    # Add public buckets
    for bucket in public_buckets:
        current_file_data["buckets"]["public"].append(bucket)
        bucket_count += 1
        
        if bucket_count % check_interval == 0:
            current_file_data = check_and_rotate_if_needed()
    
    # Add private buckets
    for bucket in private_buckets:
        current_file_data["buckets"]["private"].append(bucket)
        bucket_count += 1
        
        if bucket_count % check_interval == 0:
            current_file_data = check_and_rotate_if_needed()
    
    # Add the last file if it has data
    if current_file_data["buckets"]["public"] or current_file_data["buckets"]["private"]:
        files_data.append(current_file_data)
    
    return files_data


def validate_and_update_buckets(results_dir):
    """
    Main function to validate all buckets and update the bucket files.
    
    Args:
        results_dir: Directory containing bucket files
    """
    results_path = Path(results_dir)
    
    if not results_path.exists():
        print(f"Error: Results directory '{results_dir}' does not exist")
        sys.exit(1)
    
    # Find all bucket files
    bucket_files = find_bucket_files(results_path)
    
    if not bucket_files:
        print("No bucket files found to validate")
        sys.exit(0)
    
    print(f"Found {len(bucket_files)} bucket file(s) to validate")
    
    # Load all buckets from all files
    print("\nLoading buckets from all files...")
    all_public_buckets = []
    all_private_buckets = []
    
    for bucket_file in bucket_files:
        try:
            print(f"  Loading: {bucket_file.name}")
            with open(bucket_file, 'r') as f:
                data = json.load(f)
                
                if 'buckets' in data:
                    if 'public' in data['buckets']:
                        all_public_buckets.extend(data['buckets']['public'])
                    if 'private' in data['buckets']:
                        all_private_buckets.extend(data['buckets']['private'])
                        
        except Exception as e:
            print(f"  Error loading {bucket_file.name}: {e}")
            continue
    
    print(f"\nLoaded {len(all_public_buckets)} public buckets")
    print(f"Loaded {len(all_private_buckets)} private buckets")
    
    # Validate public buckets
    print("\n=== Validating Public Buckets ===")
    alive_public_buckets, public_stats = validate_buckets_parallel(all_public_buckets)
    
    # Validate private buckets
    print("\n=== Validating Private Buckets ===")
    alive_private_buckets, private_stats = validate_buckets_parallel(all_private_buckets)
    
    # Sort buckets by timestamp
    alive_public_buckets.sort(key=lambda x: x.get('timestamp', ''))
    alive_private_buckets.sort(key=lambda x: x.get('timestamp', ''))
    
    # Split into files respecting size limit
    print("\nSplitting validated data into files (max 20MB each)...")
    files_data = split_buckets_by_size(alive_public_buckets, alive_private_buckets)
    
    # If no buckets remain, create an empty file
    if not files_data:
        files_data = [{
            "buckets": {
                "public": [],
                "private": []
            }
        }]
        print("  No alive buckets found, will create empty buckets.json")
    
    print(f"  Data will be split into {len(files_data)} file(s)")
    
    # Delete old bucket files first
    for old_file in bucket_files:
        try:
            old_file.unlink()
            print(f"  Removed old file: {old_file.name}")
        except Exception as e:
            print(f"  Warning: Failed to delete {old_file.name}: {e}")
    
    # Write new bucket files
    print("\nWriting validated bucket files...")
    for idx, file_data in enumerate(files_data):
        # Determine filename
        if idx == 0:
            filename = "buckets.json"
        else:
            filename = f"buckets_{idx}.json"
        
        output_path = results_path / filename
        
        # Add metadata
        file_data["generated_at"] = datetime.now().astimezone().isoformat()
        file_data["validated_at"] = datetime.now().astimezone().isoformat()
        file_data["file_index"] = idx
        file_data["total_files"] = len(files_data)
        file_data["stats"] = {
            "public_buckets_in_file": len(file_data["buckets"]["public"]),
            "private_buckets_in_file": len(file_data["buckets"]["private"]),
            "total_buckets_in_file": len(file_data["buckets"]["public"]) + len(file_data["buckets"]["private"]),
            "total_public_buckets": len(alive_public_buckets),
            "total_private_buckets": len(alive_private_buckets),
            "total_buckets": len(alive_public_buckets) + len(alive_private_buckets)
        }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(file_data, f, indent=2)
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  Written: {filename} ({file_size:.2f} MB)")
    
    # Print summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"\nPublic Buckets:")
    print(f"  Total validated: {public_stats['total']}")
    print(f"  Alive (kept): {public_stats['alive']}")
    print(f"  Dead (removed): {public_stats['dead']}")
    print(f"  Errors: {public_stats['errors']}")
    
    print(f"\nPrivate Buckets:")
    print(f"  Total validated: {private_stats['total']}")
    print(f"  Alive (kept): {private_stats['alive']}")
    print(f"  Dead (removed): {private_stats['dead']}")
    print(f"  Errors: {private_stats['errors']}")
    
    total_removed = public_stats['dead'] + private_stats['dead']
    total_kept = public_stats['alive'] + private_stats['alive']
    
    print(f"\nOverall:")
    print(f"  Total buckets processed: {public_stats['total'] + private_stats['total']}")
    print(f"  Total kept: {total_kept}")
    print(f"  Total removed: {total_removed}")
    print(f"  Output files: {len(files_data)}")
    print("="*60)


if __name__ == "__main__":
    # Default path
    results_dir = "results"
    
    # Allow command line argument
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    
    validate_and_update_buckets(results_dir)
