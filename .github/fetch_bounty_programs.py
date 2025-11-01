#!/usr/bin/env python3

import sys
import json
import requests
from typing import List, Dict, Set

def fetch_bugcrowd_programs() -> List[Dict]:
    """Fetch programs from BugCrowd"""
    url = 'https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/refs/heads/main/data/bugcrowd_data.json'
    
    print('[*] Fetching BugCrowd programs...')
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = json.loads(response.text)
        
        programs = []
        for program in data:
            program_data = {
                'platform': 'bugcrowd',
                'name': program.get('name', ''),
                'url': program.get('url', ''),
                'domains': []
            }
            
            targets = program.get('targets', {})
            in_scope = targets.get('in_scope', [])
            
            for target in in_scope:
                target_type = target.get('type', '')
                target_url = target.get('target', '')
                
                # Only process website, api, and other web targets
                if target_type in ['website', 'api', 'other'] and target_url:
                    # Extract domain from URL
                    domain = target_url.replace('http://', '').replace('https://', '').split('/')[0]
                    if domain and domain not in program_data['domains']:
                        program_data['domains'].append(domain)
            
            if program_data['domains']:
                programs.append(program_data)
        
        print(f'[+] Found {len(programs)} BugCrowd programs with domains')
        return programs
        
    except Exception as e:
        print(f'[!] Error fetching BugCrowd: {e}')
        return []

def fetch_hackerone_programs() -> List[Dict]:
    """Fetch programs from HackerOne"""
    url = 'https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/refs/heads/main/data/hackerone_data.json'
    
    print('[*] Fetching HackerOne programs...')
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = json.loads(response.text)
        
        programs = []
        for program in data:
            if not program.get('offers_bounties', False):
                continue
                
            program_data = {
                'platform': 'hackerone',
                'name': program.get('name', ''),
                'url': program.get('url', ''),
                'domains': []
            }
            
            targets = program.get('targets', {})
            in_scope = targets.get('in_scope', [])
            
            for target in in_scope:
                asset_type = target.get('asset_type', '')
                asset_identifier = target.get('asset_identifier', '')
                
                # Only process URL type assets
                if asset_type == 'URL' and asset_identifier:
                    # Remove protocol if present
                    domain = asset_identifier.replace('http://', '').replace('https://', '').split('/')[0]
                    if domain and domain not in program_data['domains']:
                        program_data['domains'].append(domain)
            
            if program_data['domains']:
                programs.append(program_data)
        
        print(f'[+] Found {len(programs)} HackerOne programs with domains')
        return programs
        
    except Exception as e:
        print(f'[!] Error fetching HackerOne: {e}')
        return []

def fetch_intigriti_programs() -> List[Dict]:
    """Fetch programs from Intigriti"""
    url = 'https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/refs/heads/main/data/intigriti_data.json'
    
    print('[*] Fetching Intigriti programs...')
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = json.loads(response.text)
        
        programs = []
        for program in data:
            if program.get('status', '') != 'open':
                continue
                
            program_data = {
                'platform': 'intigriti',
                'name': program.get('name', ''),
                'url': program.get('url', ''),
                'domains': []
            }
            
            targets = program.get('targets', {})
            in_scope = targets.get('in_scope', [])
            
            for target in in_scope:
                target_type = target.get('type', '')
                endpoint = target.get('endpoint', '')
                
                # Process url and wildcard types
                if target_type in ['url', 'wildcard'] and endpoint:
                    # Remove protocol if present
                    domain = endpoint.replace('http://', '').replace('https://', '').split('/')[0]
                    if domain and domain not in program_data['domains']:
                        program_data['domains'].append(domain)
            
            if program_data['domains']:
                programs.append(program_data)
        
        print(f'[+] Found {len(programs)} Intigriti programs with domains')
        return programs
        
    except Exception as e:
        print(f'[!] Error fetching Intigriti: {e}')
        return []

def fetch_yeswehack_programs() -> List[Dict]:
    """Fetch programs from YesWeHack"""
    url = 'https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/refs/heads/main/data/yeswehack_data.json'
    
    print('[*] Fetching YesWeHack programs...')
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = json.loads(response.text)
        
        programs = []
        for program in data:
            if program.get('disabled', False):
                continue
                
            program_data = {
                'platform': 'yeswehack',
                'name': program.get('name', ''),
                'id': program.get('id', ''),
                'domains': []
            }
            
            targets = program.get('targets', {})
            in_scope = targets.get('in_scope', [])
            
            for target in in_scope:
                target_type = target.get('type', '')
                target_url = target.get('target', '')
                
                # Only process web-application and api types
                if target_type in ['web-application', 'api'] and target_url:
                    # Remove protocol if present
                    domain = target_url.replace('http://', '').replace('https://', '').split('/')[0]
                    if domain and domain not in program_data['domains']:
                        program_data['domains'].append(domain)
            
            if program_data['domains']:
                programs.append(program_data)
        
        print(f'[+] Found {len(programs)} YesWeHack programs with domains')
        return programs
        
    except Exception as e:
        print(f'[!] Error fetching YesWeHack: {e}')
        return []

def main():
    if len(sys.argv) < 2:
        print('Usage: fetch_bounty_programs.py <output_file>')
        sys.exit(1)
    
    output_file = sys.argv[1]
    
    all_programs = []
    
    # Fetch from all platforms
    all_programs.extend(fetch_bugcrowd_programs())
    all_programs.extend(fetch_hackerone_programs())
    all_programs.extend(fetch_intigriti_programs())
    all_programs.extend(fetch_yeswehack_programs())
    
    print(f'\n[*] Total programs collected: {len(all_programs)}')
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(all_programs, f, indent=2)
    
    print(f'[+] Programs saved to {output_file}')

if __name__ == '__main__':
    main()
