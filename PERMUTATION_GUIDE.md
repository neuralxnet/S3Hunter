# S3 Bucket Name Permutation Guide

## Overview

The S3 reconnaissance tool now features an **enhanced intelligent permutation engine** that generates comprehensive bucket name variations with precision and intelligence. This guide explains the new permutation capabilities and how to use them effectively.

## What's New

### Enhanced Permutation System

The tool now supports **4 levels of permutation** (0-3), each progressively adding more intelligent variations:

- **Level 0**: Base words only (minimal)
- **Level 1**: Basic environment combinations
- **Level 2**: Enhanced with years, numbers, and regions (default, recommended)
- **Level 3**: Comprehensive with prefixes, suffixes, and combined patterns

### Key Improvements

1. **Significantly Larger Wordlists**: Generate 3-4x more variations than before
2. **Intelligent Permutations**: Smart combinations based on real-world naming patterns
3. **Continuous Research**: Automatically continues with higher permutation levels when base domains are exhausted
4. **Precision Targeting**: Each level targets specific naming conventions used in production

## Permutation Levels Explained

### Level 0: Base Only
```
Input:  acme
Output: acme (1 variation)
```

Use when you only want to test exact domain names without permutations.

### Level 1: Basic Environments
```
Input:  acme
Output: acme, acme-dev, acme-prod, acme-staging, dev-acme, prod-acme, etc.
        (~133x expansion factor)
```

Generates combinations with:
- All environment keywords (dev, prod, test, staging, qa, uat, etc.)
- All separators (-, _, ., and no separator)
- Prefix and suffix variations

### Level 2: Enhanced (Default) ⭐
```
Input:  acme
Output: acme, acme-dev, acme-2024, acme-us, acme-prod-2024, etc.
        (~307x expansion factor)
```

**This is the recommended level** that adds:
- **Years**: 2020-2025 (full and short format: 20-25)
- **Numbers**: Common version patterns (1, 2, 3, 01, 02, 03, v1, v2, v3)
- **Regions**: Geographic identifiers (us, eu, asia, ap, ca, uk, au, br, de, fr, jp)

**Example patterns generated:**
- `acme-2024`, `acme-prod-2024`
- `acme-us`, `us-acme`
- `acme-v1`, `acme-v2`
- `2024-acme-prod`

### Level 3: Comprehensive
```
Input:  acme
Output: acme, my-acme, acme-bucket, acme-storage, acme-dev-2024-us, etc.
        (~441x expansion factor)
```

Adds extensive patterns:
- **Common Prefixes**: my-, company-, project-, app-, service-, cloud-
- **Common Suffixes**: -bucket, -storage, -store, -media, -content, -static, -assets, -archive
- **Combined Patterns**: Environment + Year, Environment + Region combinations

**Example patterns generated:**
- `my-acme`, `company-acme`, `app-acme`
- `acme-bucket`, `acme-storage`, `acme-media`
- `acme-dev-2024`, `acme-prod-us`
- `acme-staging-eu`, `acme-test-asia`

## Usage

### Basic Usage

```bash
# Use default Level 2 (recommended)
python3 .github/s3_recon_chunked.py base_wordlist.txt

# Specify permutation level explicitly
python3 .github/s3_recon_chunked.py base_wordlist.txt --permutation-level 2
```

### Different Permutation Levels

```bash
# Level 0: Minimal (base words only)
python3 .github/s3_recon_chunked.py base_wordlist.txt --permutation-level 0

# Level 1: Basic environments only
python3 .github/s3_recon_chunked.py base_wordlist.txt --permutation-level 1

# Level 2: Enhanced (default) - Recommended
python3 .github/s3_recon_chunked.py base_wordlist.txt --permutation-level 2

# Level 3: Comprehensive (most thorough)
python3 .github/s3_recon_chunked.py base_wordlist.txt --permutation-level 3
```

### Advanced Options

```bash
# Combine with other options
python3 .github/s3_recon_chunked.py base_wordlist.txt \
  --permutation-level 3 \
  --env-file list.txt \
  --chunk-size 25 \
  --workers 50 \
  --public
```

## Continuous Research Mode

One of the key features is that **the tool doesn't stop when the domain list is finished**. Instead:

1. When all base domains have been scanned at the current permutation level
2. The tool automatically increases the permutation level by 1
3. It re-scans all domains with the enhanced permutation patterns
4. This continues until permutation level 3 is reached

**Example:**
```
Run 1: Scan 100 domains at Level 2 → Complete
Run 2: Automatically rescan same 100 domains at Level 3 with new patterns
```

This ensures maximum coverage without requiring manual intervention.

## Performance Considerations

### Expansion Factors
- Level 0: 1x (base only)
- Level 1: ~133x 
- Level 2: ~307x (default)
- Level 3: ~441x

### Recommendations

| Use Case | Recommended Level | Reason |
|----------|------------------|---------|
| Quick scan | Level 1 | Fast, covers basic patterns |
| General reconnaissance | Level 2 | Balanced coverage and speed |
| Thorough audit | Level 3 | Maximum coverage |
| Exact names only | Level 0 | No permutations |

### Memory and Time

With Level 2 (default):
- 100 domains → ~30,700 bucket names to check
- 1,000 domains → ~307,000 bucket names to check

The chunked processing system handles this efficiently:
- Processes in manageable chunks (default: 50 words)
- Saves state after each chunk
- Can resume from interruptions

## Real-World Examples

### Example 1: Company Names
```bash
# Input: apple, google, amazon
# Level 2 generates:
apple, apple-dev, apple-prod, apple-2024, apple-us, apple-backup
google-staging, google-2023, google-eu, 2024-google-prod
amazon-data, amazon-v1, amazon-ap, us-amazon-dev
# ... and many more
```

### Example 2: Project Names
```bash
# Input: myapp, webapp
# Level 3 generates:
myapp, my-myapp, myapp-bucket, myapp-storage
myapp-dev-2024, myapp-prod-us, company-myapp
webapp-media, app-webapp, webapp-staging-eu
# ... and many more
```

## Best Practices

1. **Start with Level 2**: It provides the best balance of coverage and efficiency
2. **Use Level 3 for critical targets**: When you need maximum assurance
3. **Combine with good wordlists**: Quality input = quality permutations
4. **Monitor progress**: Check the generated counts to ensure reasonable scope
5. **Use chunking**: Keep chunk sizes manageable (25-100) for better state management

## Technical Details

### Permutation Components

**Level 1 Components:**
- Environments: '', 'dev', 'prod', 'test', 'staging', 'stage', 'qa', 'uat', 'backup', 'backups', 'data', 'files', 'assets', 'public', 'private', 'internal', 'external', 'www', 'api', 'app', 'web', 'mobile', 'admin'
- Separators: '', '-', '_', '.'

**Level 2 Additional Components:**
- Years: 2020, 2021, 2022, 2023, 2024, 2025
- Short Years: 20, 21, 22, 23, 24, 25
- Numbers: 1, 2, 3, 01, 02, 03, v1, v2, v3
- Regions: us, eu, asia, ap, ca, uk, au, br, de, fr, jp

**Level 3 Additional Components:**
- Prefixes: my, company, project, app, service, cloud
- Suffixes: bucket, storage, store, media, content, static, assets, archive
- Combined patterns: env+year, env+region

### Pattern Generation Logic

Each permutation level builds on the previous:
```python
Level 0: word
Level 1: word, word-env, env-word (all combinations)
Level 2: Level 1 + word-year, word-number, word-region
Level 3: Level 2 + prefix-word, word-suffix, word-env-year
```

## Troubleshooting

### Too Many Combinations
If Level 2 or 3 generates too many combinations:
- Reduce chunk size: `--chunk-size 25`
- Use `--domains-per-hour` to limit scope
- Start with Level 1 and upgrade later

### Not Enough Coverage
If you're not finding buckets:
- Increase permutation level: `--permutation-level 3`
- Provide better base wordlist
- Use custom environment file: `--env-file custom_keywords.txt`

## Conclusion

The enhanced permutation system provides **intelligent, comprehensive bucket name generation** that significantly improves reconnaissance success rates while maintaining precision and control. The default Level 2 is recommended for most use cases, with Level 3 available for thorough audits.
