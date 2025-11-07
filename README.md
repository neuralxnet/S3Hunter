# S3 Bucket Mass Reconnaissance Tool

Enhanced S3 bucket discovery tool with intelligent permutation engine for comprehensive reconnaissance.

## Features

- **Enhanced Permutation Engine**: Generate intelligent bucket name variations with 4 levels of sophistication
- **Continuous Research Mode**: Automatically continues with higher permutation levels after base scan completes
- **Memory-Safe Chunked Processing**: Process large wordlists efficiently without memory issues
- **Stateful Resume**: Resume from interruptions with automatic state management
- **Multi-Region Support**: Scan across all AWS regions simultaneously
- **Rate Limiting**: Control scan rate with domain-per-hour limits

## Quick Start

```bash
# Basic scan with default Level 2 permutations (recommended)
python3 .github/s3_recon_chunked.py base_wordlist.txt

# Comprehensive scan with Level 3 permutations
python3 .github/s3_recon_chunked.py base_wordlist.txt --permutation-level 3

# Custom environment keywords
python3 .github/s3_recon_chunked.py base_wordlist.txt --env-file list.txt
```

## Permutation Levels

- **Level 0**: Base words only (1x)
- **Level 1**: Basic environments (~133x expansion)
- **Level 2**: Enhanced with years/numbers/regions (~307x expansion) ⭐ **Default**
- **Level 3**: Comprehensive with prefixes/suffixes/combos (~441x expansion)

**Example**: With 100 base domains, Level 2 generates ~30,700 bucket names to check.

## Key Improvements

The enhanced permutation system generates significantly more variations:

- **3-4x more comprehensive** than the previous version
- **Intelligent patterns** based on real-world naming conventions
- **Automatic continuation** to higher permutation levels
- **Years, regions, numbers, and common patterns** intelligently combined

See [PERMUTATION_GUIDE.md](PERMUTATION_GUIDE.md) for detailed documentation.

## Usage

```bash
python3 .github/s3_recon_chunked.py [-h] [-p] [-t TIMEOUT] [-w WORKERS] 
                                    [-e ENV_FILE] [-v] [-c CHUNK_SIZE]
                                    [--state-dir STATE_DIR] 
                                    [--output-dir OUTPUT_DIR] 
                                    [--no-resume]
                                    [--domains-per-hour DOMAINS_PER_HOUR]
                                    [--permutation-level {0,1,2,3}]
                                    wordlist [wordlist ...]
```

### Key Options

- `--permutation-level {0,1,2,3}`: Set permutation sophistication (default: 2)
- `--env-file ENV_FILE`: Custom environment keywords file
- `--chunk-size CHUNK_SIZE`: Words per processing chunk (default: 50)
- `--workers WORKERS`: Concurrent workers (default: 30)
- `--domains-per-hour N`: Rate limit domains processed per hour
- `-v, --verbose`: Verbose output showing all attempts

## Output

Results are saved to the `results/` directory in JSON format:
- Organized by date and domain
- Includes discovered bucket URLs, regions, and access status
- Public and private buckets tracked separately

## Examples

### Standard Reconnaissance
```bash
python3 .github/s3_recon_chunked.py base_wordlist.txt --permutation-level 2
```

### Aggressive Scan
```bash
python3 .github/s3_recon_chunked.py base_wordlist.txt \
  --permutation-level 3 \
  --workers 50 \
  --chunk-size 25
```

### Rate-Limited Scan
```bash
python3 .github/s3_recon_chunked.py base_wordlist.txt \
  --permutation-level 2 \
  --domains-per-hour 100
```

## Requirements

- Python 3.7+
- requests library

## Documentation

- [PERMUTATION_GUIDE.md](PERMUTATION_GUIDE.md) - Detailed permutation system documentation
- [base_wordlist.txt](base_wordlist.txt) - Base company/organization names
- [list.txt](list.txt) - Environment and keyword variations

## Contributing

Contributions are welcome! Please ensure:
- New permutation patterns are based on real-world observations
- Performance impact is considered
- Documentation is updated

## License

See repository license.