# Security Scanning Automation

This repository contains automated workflows for security reconnaissance and vulnerability scanning.

## Workflows

### S3 Bucket Reconnaissance
- **File**: `.github/workflows/s3-recon.yml`
- **Schedule**: Runs every hour
- **Purpose**: Scans for publicly accessible S3 buckets

### Nuclei Security Scanning
- **File**: `.github/workflows/nuclei-scan.yml`
- **Schedule**: Runs every 3 hours
- **Purpose**: Performs vulnerability scanning on bug bounty program targets

#### Features:
- Fetches targets from multiple bug bounty platforms:
  - BugCrowd
  - HackerOne
  - Intigriti
  - YesWeHack
- Processes different domain types with file-based workflow:
  - Wildcard domains (*.example.com):
    - Runs Subfinder for subdomain enumeration → saves to file
    - Runs Httpx to probe live subdomains → saves to file
  - Plain domains (example.com):
    - Saves to file → runs Httpx for probing → saves live URLs to file
  - URLs with protocols (https://example.com):
    - Uses directly in scan
- Aggregates all live URLs and runs Nuclei scan with:
  - High, medium, and critical severity templates
  - JSONL output format for proper parsing
  - Results saved with detailed findings
- Stores results in `results_n/` directory
- Tracks scanned programs to avoid duplicates
- Scans one program per run for efficient resource usage

#### Results Format:
Results are stored as JSON files in `results_n/` with the following structure:
```json
{
  "program": "Program Name",
  "platform": "bugcrowd|hackerone|intigriti|yeswehack",
  "url": "Program URL",
  "domains_count": 5,
  "urls_scanned": 10,
  "findings_count": 2,
  "findings": [...],
  "scan_date": "2025-01-01T00:00:00"
}
```

### Results Merging
- **File**: `.github/workflows/merge-results.yml`
- **Schedule**: Runs every 12 hours
- **Purpose**: Merges S3 scan results into consolidated files

### Bucket Validation
- **File**: `.github/workflows/bucket-validation.yml`
- **Schedule**: Runs every 24 hours
- **Purpose**: Validates buckets in buckets.json and removes dead ones

#### Features:
- Validates all buckets by checking their HTTP status
- Removes dead buckets (non-200 responses)
- Updates timestamps for alive buckets
- Maintains file rotation for large datasets (20MB per file)
- Concurrent validation with configurable workers (default: 30)

## State Management

The workflows maintain state in the `state/` directory to track progress and avoid redundant scans.
