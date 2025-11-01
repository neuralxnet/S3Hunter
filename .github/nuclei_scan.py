#!/usr/bin/env python3

import sys
import json
import os
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict, Set

STATE_FILE = 'state/nuclei_state.json'
RESULTS_DIR = 'results_n'

def load_state() -> Dict:
    """Load the state of scanned programs"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'scanned_programs': [], 'last_scan': {}}

def save_state(state: Dict):
    """Save the state of scanned programs"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def is_wildcard_domain(domain: str) -> bool:
    """Check if domain is a wildcard"""
    return domain.startswith('*.')

def normalize_domain(domain: str) -> str:
    """Normalize domain by removing wildcard prefix"""
    if domain.startswith('*.'):
        return domain[2:]
    return domain

def has_protocol(domain: str) -> bool:
    """Check if domain has http or https protocol"""
    return domain.startswith('http://') or domain.startswith('https://')

def run_subfinder(domain: str, output_file: str) -> List[str]:
    """Run subfinder to enumerate subdomains and save to file"""
    print(f'[*] Running subfinder for {domain}...')
    
    try:
        # Run subfinder with output to file
        result = subprocess.run(
            ['subfinder', '-d', domain, '-silent', '-o', output_file],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and os.path.exists(output_file):
            with open(output_file, 'r') as f:
                subdomains = [line.strip() for line in f if line.strip()]
            print(f'[+] Found {len(subdomains)} subdomains')
            return subdomains
        else:
            print(f'[!] Subfinder returned no results')
            return []
            
    except Exception as e:
        print(f'[!] Error running subfinder: {e}')
        return []

def run_httpx(input_file: str, output_file: str) -> List[str]:
    """Run httpx to probe domains from input file and save to output file"""
    if not os.path.exists(input_file):
        return []
    
    # Count domains
    with open(input_file, 'r') as f:
        domain_count = len([line for line in f if line.strip()])
    
    print(f'[*] Running httpx to probe {domain_count} domains...')
    
    try:
        result = subprocess.run(
            ['httpx', '-l', input_file, '-silent', '-no-color', '-o', output_file],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0 and os.path.exists(output_file):
            with open(output_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            print(f'[+] Found {len(urls)} live URLs')
            return urls
        else:
            print(f'[!] Httpx returned no results')
            return []
            
    except Exception as e:
        print(f'[!] Error running httpx: {e}')
        return []

def update_nuclei_templates():
    """Update nuclei templates"""
    print('[*] Updating nuclei templates...')
    
    try:
        result = subprocess.run(
            ['nuclei', '-ut'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print('[+] Nuclei templates updated successfully')
            return True
        else:
            print(f'[!] Failed to update nuclei templates: {result.stderr}')
            return False
            
    except Exception as e:
        print(f'[!] Error updating nuclei templates: {e}')
        return False

def run_nuclei(input_file: str, output_file: str) -> List[Dict]:
    """Run nuclei scan on URLs from input file and save findings to output file"""
    if not os.path.exists(input_file):
        return []
    
    # Count URLs
    with open(input_file, 'r') as f:
        url_count = len([line for line in f if line.strip()])
    
    if url_count == 0:
        return []
    
    # Update templates before scanning
    update_nuclei_templates()
    
    print(f'[*] Running nuclei on {url_count} URLs...')
    
    try:
        # Run nuclei with text output (one finding per line)
        result = subprocess.run(
            ['nuclei', '-l', input_file, '-s', 'high,medium,critical', 
             '-jsonl', '-o', output_file, '-silent'],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes
        )
        
        findings = []
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            finding = json.loads(line)
                            findings.append(finding)
                        except json.JSONDecodeError:
                            # Skip lines that aren't valid JSON
                            pass
            
            print(f'[+] Found {len(findings)} vulnerabilities')
        else:
            print(f'[+] No vulnerabilities found')
        
        return findings
            
    except Exception as e:
        print(f'[!] Error running nuclei: {e}')
        return []

def process_program(program: Dict) -> Dict:
    """Process a single program"""
    print(f'\n[*] Processing program: {program["name"]} ({program["platform"]})')
    print(f'[*] Found {len(program["domains"])} domains')
    
    # Create temporary directory for this scan
    scan_dir = tempfile.mkdtemp(prefix='nuclei_scan_')
    
    try:
        all_urls = []
        
        # Separate wildcard and non-wildcard domains
        wildcard_domains = []
        regular_domains = []
        direct_urls = []
        
        for domain in program['domains']:
            if is_wildcard_domain(domain):
                wildcard_domains.append(normalize_domain(domain))
            elif has_protocol(domain):
                direct_urls.append(domain)
            else:
                regular_domains.append(domain)
        
        # Process wildcard domains
        if wildcard_domains:
            print(f'\n[*] Processing {len(wildcard_domains)} wildcard domains')
            for domain in wildcard_domains:
                print(f'[*] Processing wildcard domain: *.{domain}')
                
                # Run subfinder and save to file
                subdomains_file = os.path.join(scan_dir, f'subdomains_{domain.replace(".", "_")}.txt')
                subdomains = run_subfinder(domain, subdomains_file)
                
                if subdomains:
                    # Run httpx on subdomains
                    httpx_output = os.path.join(scan_dir, f'live_{domain.replace(".", "_")}.txt')
                    urls = run_httpx(subdomains_file, httpx_output)
                    all_urls.extend(urls)
        
        # Process regular domains (non-wildcard, no protocol)
        if regular_domains:
            print(f'\n[*] Processing {len(regular_domains)} regular domains')
            # Save regular domains to file
            domains_file = os.path.join(scan_dir, 'domains.txt')
            with open(domains_file, 'w') as f:
                for domain in regular_domains:
                    f.write(domain + '\n')
            
            # Run httpx on regular domains
            httpx_output = os.path.join(scan_dir, 'live_domains.txt')
            urls = run_httpx(domains_file, httpx_output)
            all_urls.extend(urls)
        
        # Add direct URLs
        if direct_urls:
            print(f'\n[*] Adding {len(direct_urls)} direct URLs')
            all_urls.extend(direct_urls)
        
        print(f'\n[*] Total URLs to scan: {len(all_urls)}')
        
        if all_urls:
            # Save all URLs to a file for nuclei
            urls_file = os.path.join(scan_dir, 'all_urls.txt')
            with open(urls_file, 'w') as f:
                for url in all_urls:
                    f.write(url + '\n')
            
            # Run nuclei on all collected URLs
            findings_file = os.path.join(scan_dir, 'domain_findings.txt')
            findings = run_nuclei(urls_file, findings_file)
        else:
            findings = []
        
        result = {
            'program': program['name'],
            'platform': program['platform'],
            'url': program.get('url', ''),
            'domains_count': len(program['domains']),
            'urls_scanned': len(all_urls),
            'findings_count': len(findings),
            'findings': findings,
            'scan_date': datetime.utcnow().isoformat()
        }
        
        return result
        
    finally:
        # Cleanup temporary directory
        try:
            import shutil
            shutil.rmtree(scan_dir)
        except:
            pass

def save_results(program_name: str, platform: str, result: Dict):
    """Save scan results to file"""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # Create safe filename
    safe_name = ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in program_name)
    filename = f'{platform}_{safe_name}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
    filepath = os.path.join(RESULTS_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f'[+] Results saved to {filepath}')

def main():
    if len(sys.argv) < 2:
        print('Usage: nuclei_scan.py <programs_file>')
        sys.exit(1)
    
    programs_file = sys.argv[1]
    
    # Load programs
    with open(programs_file, 'r') as f:
        programs = json.load(f)
    
    print(f'[*] Loaded {len(programs)} programs')
    
    # Load state
    state = load_state()
    scanned = set(state.get('scanned_programs', []))
    
    print(f'[*] Already scanned {len(scanned)} programs')
    
    # Find next program to scan
    program_to_scan = None
    for program in programs:
        program_id = f"{program['platform']}:{program['name']}"
        if program_id not in scanned:
            program_to_scan = program
            break
    
    if not program_to_scan:
        print('[*] All programs have been scanned. Resetting state...')
        state = {'scanned_programs': [], 'last_scan': {}}
        if programs:
            program_to_scan = programs[0]
    
    if not program_to_scan:
        print('[!] No programs to scan')
        sys.exit(0)
    
    # Process the program
    result = process_program(program_to_scan)
    
    # Save results
    save_results(program_to_scan['name'], program_to_scan['platform'], result)
    
    # Update state
    program_id = f"{program_to_scan['platform']}:{program_to_scan['name']}"
    if program_id not in scanned:
        scanned.add(program_id)
    
    state['scanned_programs'] = list(scanned)
    state['last_scan'][program_id] = datetime.utcnow().isoformat()
    save_state(state)
    
    print(f'\n[+] Scan completed successfully')
    print(f'[+] Programs scanned: {len(scanned)} / {len(programs)}')

if __name__ == '__main__':
    main()
