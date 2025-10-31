#!/usr/bin/env python3

import sys
import json
import requests

def fetch_bugbounty_programs(output_file='base_wordlist.txt'):
    url = 'https://raw.githubusercontent.com/projectdiscovery/public-bugbounty-programs/main/chaos-bugbounty-list.json'
    
    print('[*] Fetching bug bounty programs from ProjectDiscovery...')
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = json.loads(response.text)
        
        wordlist = set()
        program_count = 0
        
        for program in data.get('programs', []):
            if program.get('bounty') == True:
                program_count += 1
                
                name = program.get('name', '')
                if name:
                    wordlist.add(name)
                
                domains = program.get('domains', [])
                for domain in domains:
                    if domain:
                        wordlist.add(domain)
                        
                        parts = domain.replace('*.', '').split('.')
                        for part in parts:
                            if part and len(part) > 2:
                                wordlist.add(part)
        
        print(f'[*] Found {program_count} bug bounty programs')
        print(f'[*] Generated {len(wordlist)} unique words')
        
        with open(output_file, 'w') as f:
            for word in sorted(wordlist):
                f.write(word + '\n')
        
        print(f'[+] Wordlist saved to {output_file}')
        
    except Exception as e:
        print(f'[!] Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    output = sys.argv[1] if len(sys.argv) > 1 else 'base_wordlist.txt'
    fetch_bugbounty_programs(output)
