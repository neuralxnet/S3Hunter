#!/usr/bin/env python3

import sys
import json
import argparse
import requests
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
import os
from datetime import datetime
import hashlib

AWS_REGIONS = [
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ca-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3',
    'eu-central-1', 'eu-north-1', 'ap-south-1', 'ap-northeast-1',
    'ap-northeast-2', 'ap-northeast-3', 'ap-southeast-1', 'ap-southeast-2',
    'sa-east-1', 'af-south-1', 'me-south-1'
]

SEPARATORS = ['', '-', '_', '.']

DEFAULT_ENVIRONMENTS = [
    '', 'dev', 'prod', 'test', 'staging', 'stage', 'qa', 'uat',
    'backup', 'backups', 'data', 'files', 'assets',
    'public', 'private', 'internal', 'external',
    'www', 'api', 'app', 'web', 'mobile', 'admin'
]

class S3ReconChunked:
    def __init__(self, wordlist, timeout=10, max_workers=30, public_only=False, 
                 env_file=None, verbose=False, chunk_size=50, state_dir='state', 
                 output_dir='results', resume=True):
        self.wordlist = wordlist
        self.timeout = timeout
        self.max_workers = max_workers
        self.public_only = public_only
        self.env_file = env_file
        self.verbose = verbose
        self.chunk_size = chunk_size
        self.state_dir = state_dir
        self.output_dir = output_dir
        self.resume = resume
        self.environments = self.load_environments()
        self.results = {'public': [], 'private': []}
        self.total_checked = 0
        self.lock = threading.Lock()
        self.scanned_buckets = set()
        
        os.makedirs(state_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
    
    def load_environments(self):
        if self.env_file and os.path.exists(self.env_file):
            try:
                with open(self.env_file, 'r', encoding='utf-8', errors='ignore') as f:
                    envs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    print(f"[*] Loaded {len(envs)} environments from {self.env_file}")
                    return envs
            except Exception as e:
                print(f"[!] Error loading environment file: {e}")
                print(f"[*] Using default environments")
                return DEFAULT_ENVIRONMENTS
        return DEFAULT_ENVIRONMENTS
        
    def load_wordlist(self, filepath):
        words = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):
                        words.append(word)
        except Exception as e:
            print(f"[!] Error loading wordlist: {e}")
            sys.exit(1)
        return words
    
    def generate_bucket_names(self, words):
        buckets = set()
        
        for word in words:
            word = word.lower().replace(' ', '-').replace('*', '').replace('.', '-')
            
            if not word:
                continue
            
            buckets.add(word)
            
            for env in self.environments[:30]:
                if env:
                    for sep in SEPARATORS[:2]:
                        if sep:
                            buckets.add(f"{word}{sep}{env}")
                            buckets.add(f"{env}{sep}{word}")
        
        return list(buckets)
    
    def get_bucket_hash(self, bucket_name, region):
        return hashlib.md5(f"{bucket_name}:{region}".encode()).hexdigest()
    
    def load_state(self, chunk_id):
        state_file = os.path.join(self.state_dir, f"chunk_{chunk_id}_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    return set(state.get('scanned', []))
            except:
                return set()
        return set()
    
    def save_state(self, chunk_id, scanned_hashes):
        state_file = os.path.join(self.state_dir, f"chunk_{chunk_id}_state.json")
        try:
            with open(state_file, 'w') as f:
                json.dump({'scanned': list(scanned_hashes), 'updated': datetime.now().isoformat()}, f)
        except Exception as e:
            print(f"[!] Error saving state: {e}")
    
    def check_bucket(self, bucket_name, region):
        urls = [
            f"https://{bucket_name}.s3.{region}.amazonaws.com",
            f"https://s3.{region}.amazonaws.com/{bucket_name}"
        ]
        
        for url in urls:
            if self.verbose:
                print(f"[~] Checking: {url}")
            
            try:
                response = requests.head(url, timeout=self.timeout, allow_redirects=True)
                
                if self.verbose:
                    print(f"[>] Response: {url} -> Status: {response.status_code}")
                
                if response.status_code in [200, 301, 302, 307]:
                    access_type = self.determine_access(url)
                    return {
                        'url': url,
                        'bucket': bucket_name,
                        'region': region,
                        'status': response.status_code,
                        'access': access_type,
                        'timestamp': datetime.now().isoformat()
                    }
                    
            except requests.exceptions.Timeout:
                if self.verbose:
                    print(f"[!] Timeout: {url}")
                continue
            except requests.exceptions.RequestException as e:
                if self.verbose:
                    print(f"[!] Error: {url} -> {type(e).__name__}")
                continue
        
        return None
    
    def determine_access(self, url):
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                if '<?xml' in response.text or 'ListBucketResult' in response.text:
                    return 'public'
                return 'accessible'
            elif response.status_code == 403:
                return 'private'
            elif response.status_code in [301, 302, 307]:
                return 'exists'
            else:
                return 'unknown'
                
        except requests.exceptions.RequestException:
            return 'private'
    
    def scan_bucket(self, bucket_name, region, scanned_hashes):
        bucket_hash = self.get_bucket_hash(bucket_name, region)
        
        if bucket_hash in scanned_hashes:
            if self.verbose:
                print(f"[*] Skipping already scanned: {bucket_name} in {region}")
            return None
        
        with self.lock:
            self.total_checked += 1
            checked = self.total_checked
        
        if self.verbose:
            print(f"[*] [{checked}] Scanning: {bucket_name} in {region}")
        
        result = self.check_bucket(bucket_name, region)
        
        with self.lock:
            scanned_hashes.add(bucket_hash)
        
        if result:
            access = result['access']
            url = result['url']
            
            if access in ['public', 'accessible']:
                print(f"[+] PUBLIC  {url} | Bucket: {bucket_name} | Region: {region}")
                with self.lock:
                    self.results['public'].append(result)
                return result
            elif not self.public_only:
                print(f"[-] PRIVATE {url} | Bucket: {bucket_name} | Region: {region}")
                with self.lock:
                    self.results['private'].append(result)
                return result
        else:
            if self.verbose:
                print(f"[x] [{checked}] Not found: {bucket_name} in {region}")
        
        return None
    
    def save_chunk_results(self, chunk_id, domain):
        date_str = datetime.now().strftime('%Y-%m-%d')
        domain_clean = domain.replace('/', '_').replace(':', '_')
        
        output_file = os.path.join(self.output_dir, f"{date_str}_{domain_clean}_chunk_{chunk_id}.json")
        
        try:
            with open(output_file, 'w') as f:
                json.dump({
                    'chunk_id': chunk_id,
                    'domain': domain,
                    'date': date_str,
                    'timestamp': datetime.now().isoformat(),
                    'results': self.results,
                    'stats': {
                        'total_checked': self.total_checked,
                        'public_found': len(self.results['public']),
                        'private_found': len(self.results['private'])
                    }
                }, f, indent=2)
            print(f"[*] Results saved to {output_file}")
        except Exception as e:
            print(f"[!] Error saving results: {e}")
    
    def run_chunk(self, bucket_names, chunk_id, domain):
        print(f"\n{'='*60}")
        print(f"[*] Processing Chunk {chunk_id}")
        print(f"[*] Domain: {domain}")
        print(f"[*] Bucket names in chunk: {len(bucket_names)}")
        
        scanned_hashes = set()
        if self.resume:
            scanned_hashes = self.load_state(chunk_id)
            print(f"[*] Loaded {len(scanned_hashes)} previously scanned buckets")
        
        combinations = list(itertools.product(bucket_names, AWS_REGIONS))
        print(f"[*] Total combinations to check: {len(combinations)}")
        print(f"[*] Using {self.max_workers} concurrent workers")
        print(f"[*] Timeout per request: {self.timeout} seconds")
        print(f"[*] Starting chunk scan...\n")
        
        start_time = time.time()
        found_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.scan_bucket, bucket, region, scanned_hashes): (bucket, region)
                for bucket, region in combinations
            }
            
            completed = 0
            total = len(futures)
            
            for future in as_completed(futures):
                completed += 1
                result = future.result()
                if result:
                    found_count += 1
                
                if not self.verbose and completed % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    print(f"[*] Progress: {completed}/{total} ({(completed/total*100):.1f}%) | Rate: {rate:.1f} req/s | Found: {found_count}")
                    self.save_state(chunk_id, scanned_hashes)
        
        self.save_state(chunk_id, scanned_hashes)
        
        elapsed_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"[*] Chunk {chunk_id} completed in {elapsed_time:.2f} seconds")
        print(f"[*] Total requests made: {self.total_checked}")
        print(f"[*] Average rate: {self.total_checked/elapsed_time:.1f} requests/second")
        print(f"[*] Found {len(self.results['public'])} public buckets")
        print(f"[*] Found {len(self.results['private'])} private buckets")
        print(f"{'='*60}")
        
        self.save_chunk_results(chunk_id, domain)
        
        return self.results
    
    def run(self):
        all_words = []
        for wordlist_file in self.wordlist:
            print(f"[*] Loading wordlist: {wordlist_file}")
            words = self.load_wordlist(wordlist_file)
            all_words.extend(words)
        
        print(f"[*] Loaded {len(all_words)} words from {len(self.wordlist)} wordlist(s)")
        
        chunks = [all_words[i:i + self.chunk_size] for i in range(0, len(all_words), self.chunk_size)]
        print(f"[*] Split into {len(chunks)} chunks of {self.chunk_size} words each")
        
        for idx, chunk in enumerate(chunks):
            print(f"\n[*] Starting chunk {idx + 1}/{len(chunks)}")
            
            domain = chunk[0] if chunk else "unknown"
            
            bucket_names = self.generate_bucket_names(chunk)
            
            self.results = {'public': [], 'private': []}
            self.total_checked = 0
            
            self.run_chunk(bucket_names, idx + 1, domain)
            
            time.sleep(2)
        
        print(f"\n[*] All chunks completed!")

def main():
    parser = argparse.ArgumentParser(description='S3 Bucket Mass Reconnaissance Tool - Chunked Version')
    parser.add_argument('wordlist', nargs='+', help='Wordlist file(s) to use')
    parser.add_argument('-p', '--public', action='store_true', help='Only show public buckets')
    parser.add_argument('-t', '--timeout', type=int, default=8, help='Request timeout (default: 8)')
    parser.add_argument('-w', '--workers', type=int, default=30, help='Concurrent workers (default: 30)')
    parser.add_argument('-e', '--env-file', help='Environment/keywords file (default: list.txt)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode - show all attempts')
    parser.add_argument('-c', '--chunk-size', type=int, default=50, help='Words per chunk (default: 50)')
    parser.add_argument('--state-dir', default='state', help='State directory (default: state)')
    parser.add_argument('--output-dir', default='results', help='Output directory (default: results)')
    parser.add_argument('--no-resume', action='store_true', help='Disable resume from previous state')
    
    args = parser.parse_args()
    
    env_file = args.env_file if args.env_file else 'list.txt'
    
    print("""
╔═══════════════════════════════════════════════════╗
║   S3 Bucket Mass Recon Scanner - Chunked         ║
║   Memory-Safe Chunked Processing                 ║
╚═══════════════════════════════════════════════════╝
    """)
    
    recon = S3ReconChunked(
        wordlist=args.wordlist,
        timeout=args.timeout,
        max_workers=args.workers,
        public_only=args.public,
        env_file=env_file,
        verbose=args.verbose,
        chunk_size=args.chunk_size,
        state_dir=args.state_dir,
        output_dir=args.output_dir,
        resume=not args.no_resume
    )
    
    recon.run()

if __name__ == '__main__':
    main()
