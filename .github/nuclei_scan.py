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

def run_subfinder(domain: str) -> List[str]:
    """Run subfinder to enumerate subdomains"""
    print(f'[*] Running subfinder for {domain}...')
    
    try:
        result = subprocess.run(
            ['subfinder', '-d', domain, '-silent'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and result.stdout:
            subdomains = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            print(f'[+] Found {len(subdomains)} subdomains')
            return subdomains
        else:
            print(f'[!] Subfinder returned no results')
            return []
            
    except Exception as e:
        print(f'[!] Error running subfinder: {e}')
        return []

def run_httpx(domains: List[str]) -> List[str]:
    """Run httpx to probe domains"""
    if not domains:
        return []
    
    print(f'[*] Running httpx to probe {len(domains)} domains...')
    
    try:
        # Create temporary file with domains
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for domain in domains:
                f.write(domain + '\n')
            temp_file = f.name
        
        result = subprocess.run(
            ['httpx', '-l', temp_file, '-silent', '-no-color'],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        os.unlink(temp_file)
        
        if result.returncode == 0 and result.stdout:
            urls = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            print(f'[+] Found {len(urls)} live URLs')
            return urls
        else:
            print(f'[!] Httpx returned no results')
            return []
            
    except Exception as e:
        print(f'[!] Error running httpx: {e}')
        if 'temp_file' in locals():
            try:
                os.unlink(temp_file)
            except:
                pass
        return []

def run_nuclei(urls: List[str]) -> List[Dict]:
    """Run nuclei scan on URLs"""
    if not urls:
        return []
    
    print(f'[*] Running nuclei on {len(urls)} URLs...')
    
    try:
        # Create temporary file with URLs
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for url in urls:
                f.write(url + '\n')
            temp_file = f.name
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name
        
        # Run nuclei with json output
        result = subprocess.run(
            ['nuclei', '-l', temp_file, '-s', 'high,medium,critical', 
             '-json', '-o', output_file, '-silent'],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes
        )
        
        os.unlink(temp_file)
        
        findings = []
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            finding = json.loads(line)
                            findings.append(finding)
                        except:
                            pass
            
            os.unlink(output_file)
            print(f'[+] Found {len(findings)} vulnerabilities')
        else:
            if os.path.exists(output_file):
                os.unlink(output_file)
            print(f'[+] No vulnerabilities found')
        
        return findings
            
    except Exception as e:
        print(f'[!] Error running nuclei: {e}')
        if 'temp_file' in locals():
            try:
                os.unlink(temp_file)
            except:
                pass
        if 'output_file' in locals():
            try:
                os.unlink(output_file)
            except:
                pass
        return []

def process_program(program: Dict) -> Dict:
    """Process a single program"""
    print(f'\n[*] Processing program: {program["name"]} ({program["platform"]})')
    print(f'[*] Found {len(program["domains"])} domains')
    
    all_urls = []
    
    for domain in program['domains']:
        print(f'\n[*] Processing domain: {domain}')
        
        if is_wildcard_domain(domain):
            # Run subfinder for wildcard domains
            normalized = normalize_domain(domain)
            subdomains = run_subfinder(normalized)
            
            if subdomains:
                # Probe subdomains with httpx
                urls = run_httpx(subdomains)
                all_urls.extend(urls)
        else:
            # Check if domain has protocol
            if has_protocol(domain):
                # No need to probe, use directly
                all_urls.append(domain)
            else:
                # Need to probe with httpx
                urls = run_httpx([domain])
                all_urls.extend(urls)
    
    print(f'\n[*] Total URLs to scan: {len(all_urls)}')
    
    # Run nuclei on all collected URLs
    findings = run_nuclei(all_urls)
    
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
