# S3Hunter

A powerful S3 bucket reconnaissance tool with intelligent domain tracking and rate limiting capabilities.

## Features

- **Domain-Level Tracking**: Automatically tracks which domains have been scanned to prevent duplicate scanning
- **Hourly Rate Limiting**: Configure specific number of domains to scan per hour
- **Resume Capability**: Automatically resumes from where it stopped in previous runs
- **State Management**: Persistent state tracking across runs
- **Chunked Processing**: Memory-safe processing of large wordlists
- **Public/Private Detection**: Identifies both public and private S3 buckets
- **Multi-Region Support**: Scans across all AWS regions

## Usage

### Basic Usage

```bash
python3 .github/s3_recon_chunked.py wordlist.txt
```

### With Hourly Rate Limiting

Scan only 100 domains per hour:

```bash
python3 .github/s3_recon_chunked.py base_wordlist.txt --domains-per-hour 100
```

### Common Options

```bash
python3 .github/s3_recon_chunked.py base_wordlist.txt \
  --domains-per-hour 100 \       # Limit to 100 domains per hour
  -c 50 \                         # Process 50 words per chunk
  -w 30 \                         # Use 30 concurrent workers
  -t 8 \                          # 8 second timeout per request
  -e list.txt \                   # Use custom environment keywords
  --state-dir state \             # State directory
  --output-dir results \          # Output directory
  -p                              # Show only public buckets
```

### Automated Scanning with GitHub Actions

The tool includes two GitHub Actions workflows:

#### S3 Reconnaissance Workflow (`s3-recon.yml`)
- Runs automatically every hour
- Fetches and updates bug bounty program domains
- Scans a configurable number of domains per run
- Maintains state across runs to avoid duplicate scanning
- Commits results back to the repository
- Configure the workflow by setting the `domains_per_hour` parameter

#### Results Merge Workflow (`merge-results.yml`)
- Runs automatically every 12 hours
- Merges all individual JSON result files into a single `buckets.json`
- Removes duplicate bucket entries
- Deletes the individual split files after successful merge
- Provides comprehensive statistics on discovered buckets
- Can be manually triggered via workflow_dispatch

## How It Works

### Domain Tracking

The tool maintains a global state file (`state/domain_state.json`) that tracks:
- All domains that have been scanned
- Last scan timestamp
- Total progress through the wordlist

Each domain is hashed and stored in the state file. On subsequent runs, the tool:
1. Loads the existing state
2. Filters out already-scanned domains
3. Processes only the remaining domains (up to the hourly limit)
4. Updates the state after each chunk completes

### Hourly Rate Limiting

When `--domains-per-hour` is specified:
- The tool calculates how many domains remain to be scanned
- Processes only up to the specified limit
- Stops when the limit is reached
- Next run continues from where it stopped

This ensures:
- Predictable resource usage
- Gradual coverage of large domain lists
- No duplicate scanning
- Easy monitoring of progress

## State Files

### Domain State (`state/domain_state.json`)

```json
{
  "scanned_domains": ["hash1", "hash2", ...],
  "last_scan_time": "2024-10-31T10:00:00",
  "updated": "2024-10-31T10:00:00"
}
```

### Chunk State (`state/chunk_N_state.json`)

Tracks which specific bucket/region combinations have been checked within each chunk.

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `wordlist` | Wordlist file(s) to use | Required |
| `-p, --public` | Only show public buckets | False |
| `-t, --timeout` | Request timeout in seconds | 8 |
| `-w, --workers` | Concurrent workers | 30 |
| `-e, --env-file` | Environment/keywords file | list.txt |
| `-v, --verbose` | Verbose mode | False |
| `-c, --chunk-size` | Words per chunk | 50 |
| `--state-dir` | State directory | state |
| `--output-dir` | Output directory | results |
| `--no-resume` | Disable resume | False |
| `--domains-per-hour` | Domains to scan per hour | All remaining |

## Output

### Individual Scan Results

Individual scan results are saved in JSON format in the `results` directory:

```json
{
  "chunk_id": 1,
  "domain": "example",
  "date": "2024-10-31",
  "timestamp": "2024-10-31T10:00:00",
  "results": {
    "public": [...],
    "private": [...]
  },
  "stats": {
    "total_checked": 1000,
    "public_found": 5,
    "private_found": 50
  }
}
```

### Merged Results (buckets.json)

Every 12 hours, all individual result files are merged into a single `buckets.json` file:

```json
{
  "generated_at": "2024-10-31T10:00:00Z",
  "source_files": 22,
  "domains_scanned": 22,
  "total_chunks": 22,
  "stats": {
    "total_public_buckets": 138,
    "total_private_buckets": 0,
    "total_buckets": 138
  },
  "buckets": {
    "public": [
      {
        "url": "https://example-bucket.s3.amazonaws.com",
        "bucket": "example-bucket",
        "region": "us-east-1",
        "status": 200,
        "access": "public",
        "timestamp": "2024-10-31T10:00:00"
      }
    ],
    "private": [...]
  }
}
```

**Note:** After the merge, individual JSON files are automatically deleted to save space, and only `buckets.json` remains.

## Example Workflow

### Scenario: Scan 2000 domains at 100 per hour

1. **Hour 1**: Scans domains 1-100, state saved
2. **Hour 2**: Scans domains 101-200, state saved
3. **Hour 3**: Scans domains 201-300, state saved
4. ... continues until all domains scanned
5. **Hour 21**: Scans remaining domains, completes

If interrupted at any point, the next run automatically resumes from where it stopped.

## Requirements

- Python 3.7+
- requests library

```bash
pip install requests
```

## License

See LICENSE file for details.
