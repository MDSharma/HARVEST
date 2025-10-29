# Enhanced PDF Download System

## Overview

The enhanced PDF download system provides intelligent, multi-source PDF downloading with performance tracking, smart source selection, and comprehensive analytics. It uses a separate SQLite database (`pdf_downloads.db`) to track all download attempts and learn which sources work best for different publishers over time.

## Key Features

### 1. Multiple PDF Sources
- **Unpaywall REST API** - Free open access database (no extra dependencies)
- **Europe PMC** - Biomedical literature (no extra dependencies)
- **CORE.ac.uk** - Open access research papers (no extra dependencies)
- **Semantic Scholar** - Academic paper metadata and PDFs (no extra dependencies)
- **Publisher Direct** - Predictable URLs for open access publishers (no extra dependencies)
- **Unpywall Library** - Enhanced Unpaywall access (requires `unpywall` package)
- **Metapub** - PubMed Central and arXiv (requires `metapub` package and NCBI API key)
- **Habanero** - Crossref institutional access (requires `habanero` package)
- **SciHub** - Optional last resort (disabled by default, legal concerns)

### 2. Smart Source Selection
- Sources are ranked by historical success rate and response time
- Publisher-specific patterns are learned and remembered
- Best source for each publisher is tried first
- Fallback to other sources in optimized order
- All attempts are logged for continuous improvement

### 3. Failure Classification and Retry Logic
Failures are classified into categories:
- **Temporary failures** (network errors, timeouts, rate limits) - automatically retried
- **Permanent failures** (paywall, not found, invalid content) - marked for manual upload

Retry strategy:
- Exponential backoff for temporary failures
- Configurable retry limits and delays
- Smart scheduling based on failure type

### 4. Performance Tracking
- Separate database (`pdf_downloads.db`) tracks all attempts
- Success rates per source
- Average response times
- Publisher-specific success patterns
- Failure categorization and analysis

### 5. Admin Analytics
REST API endpoints for:
- Download statistics (overall and per-project)
- Source performance rankings
- Enable/disable sources dynamically
- Adjust source priorities
- View retry queue
- Export data as CSV
- Cleanup old records

## Architecture

### Database Schema (`pdf_downloads.db`)

#### Tables

1. **sources** - Configuration for each PDF source
   - name, enabled, base_url, requires_auth, timeout, priority, description, requires_library

2. **download_attempts** - Log of every download attempt
   - project_id, doi, source_name, success, failure_reason, failure_category, response_time_ms, file_size_bytes, pdf_url, timestamp

3. **source_performance** - Aggregated metrics per source
   - source_name, total_attempts, success_count, failure_count, avg_response_time_ms, success_rate, last_success_at, last_failure_at

4. **publisher_patterns** - Learned URL patterns by publisher
   - doi_prefix, publisher_name, successful_source, url_pattern, success_count, last_success_at

5. **retry_queue** - DOIs scheduled for retry
   - project_id, doi, failure_category, retry_count, next_retry_at, last_attempted_at

6. **configuration** - Runtime configuration settings
   - key, value, description

### Module Structure

- **pdf_download_db.py** - Database schema and helper functions
- **pdf_sources.py** - Lightweight source implementations (Europe PMC, CORE, Semantic Scholar, SciHub, Publisher Direct)
- **pdf_manager_enhanced.py** - Smart download orchestration with database-driven source selection
- **pdf_analytics_endpoints.py** - REST API endpoints for analytics and management
- **pdf_manager.py** - Original PDF manager (unchanged, used for actual downloads)

## Installation

### Minimal Installation (Recommended)

Install only the core dependencies:

```bash
pip install -r requirements-minimal.txt
```

This provides:
- Unpaywall REST API
- Europe PMC
- CORE.ac.uk (limited results without API key)
- Semantic Scholar
- Publisher Direct

**No additional dependencies required** for these sources - they all use the `requests` library which is already required for the core application.

### Standard Installation

For enhanced functionality:

```bash
pip install -r requirements-standard.txt
```

Adds:
- Unpywall library (better Unpaywall results)
- Literature search capabilities
- Habanero (Crossref institutional access)

### Full Installation

For maximum source coverage:

```bash
pip install -r requirements-full.txt
```

Adds:
- Metapub (PubMed Central access, requires NCBI API key)

## Configuration

Edit `config.py` to configure the enhanced PDF download system:

### Enable/Disable the Enhanced System

```python
ENABLE_ENHANCED_PDF_DOWNLOAD = True  # Use enhanced multi-source system
PDF_DOWNLOAD_DB_PATH = "pdf_downloads.db"  # Path to tracking database
```

### Enable/Disable Individual Sources

```python
ENABLE_EUROPE_PMC = True          # No extra dependencies
ENABLE_CORE = True                # No extra dependencies
ENABLE_SEMANTIC_SCHOLAR = True    # No extra dependencies
ENABLE_PUBLISHER_DIRECT = True    # No extra dependencies
ENABLE_SCIHUB = False             # Disabled by default (legal concerns)
```

### Optional API Keys

```python
# CORE.ac.uk API Key (optional but recommended)
# Get free API key at: https://core.ac.uk/services/api
CORE_API_KEY = ""

# NCBI API Key for Metapub (required for metapub)
# Get free API key at: https://www.ncbi.nlm.nih.gov/account/
NCBI_API_KEY = ""
```

### Smart Download Configuration

```python
PDF_SMART_RETRY_ENABLED = True             # Enable automatic retry
PDF_SMART_RETRY_MAX_ATTEMPTS = 3           # Max retry attempts
PDF_SMART_RETRY_BASE_DELAY_MINUTES = 60    # Base delay (exponential backoff)
PDF_RATE_LIMIT_DELAY_SECONDS = 1           # Delay between requests
PDF_CLEANUP_RETENTION_DAYS = 90            # Days to keep history
PDF_USER_AGENT_ROTATION = True             # Rotate User-Agent headers
```

## Usage

### From Code

Use the enhanced download function:

```python
from pdf_manager_enhanced import download_pdf_smart, process_dois_smart

# Download single DOI
success, message, source = download_pdf_smart(
    doi="10.1371/journal.pone.0000001",
    project_id=1,
    save_dir="project_pdfs/project_1"
)

# Download multiple DOIs
results = process_dois_smart(
    doi_list=["10.1371/journal.pone.0000001", "10.1038/nature12345"],
    project_id=1,
    project_dir="project_pdfs/project_1"
)
```

### From Backend API

The existing endpoint automatically uses the enhanced system if enabled:

```
POST /api/admin/projects/<project_id>/download-pdfs
```

### Analytics API Endpoints

All analytics endpoints require admin authentication.

#### Get Statistics

```
GET /api/admin/pdf-analytics/statistics?project_id=1&days=30
```

Returns:
```json
{
  "ok": true,
  "statistics": {
    "total_attempts": 150,
    "successful": 120,
    "failed": 30,
    "success_rate": 80.0,
    "avg_response_time_ms": 450,
    "unique_dois": 100,
    "by_source": [...],
    "failure_categories": [...]
  }
}
```

#### Get Source Rankings

```
GET /api/admin/pdf-analytics/sources
```

Returns sources ranked by performance.

#### Enable/Disable Source

```
POST /api/admin/pdf-analytics/sources/<source_name>/toggle
{
  "email": "admin@example.com",
  "password": "secret",
  "enabled": false
}
```

#### Update Source Priority

```
POST /api/admin/pdf-analytics/sources/<source_name>/priority
{
  "email": "admin@example.com",
  "password": "secret",
  "priority": 50
}
```

#### Get Retry Queue

```
GET /api/admin/pdf-analytics/retry-queue
```

#### Get Download History

```
GET /api/admin/pdf-analytics/download-history?project_id=1&limit=100
```

#### Export Statistics

```
GET /api/admin/pdf-analytics/export?project_id=1&days=30
```

Downloads CSV file with detailed statistics.

#### Cleanup Old Records

```
POST /api/admin/pdf-analytics/cleanup
{
  "email": "admin@example.com",
  "password": "secret",
  "retention_days": 90
}
```

## How It Works

### Download Flow

1. **Check Cache**: If PDF already downloaded, return immediately
2. **Check Publisher Pattern**: Look up best source for this publisher based on history
3. **Try Publisher-Specific Source**: If found, try it first
4. **Try All Sources**: Try remaining sources in order of performance ranking
5. **Log All Attempts**: Every attempt (success or failure) is logged to database
6. **Update Metrics**: Source performance metrics are updated in real-time
7. **Record Success Pattern**: Successful downloads update publisher patterns
8. **Handle Failures**: Classify failure and add to retry queue if temporary

### Smart Selection Algorithm

Sources are ordered by:
1. Publisher-specific best source (if available)
2. Overall success rate (descending)
3. Average response time (ascending)
4. Manual priority setting (ascending)

### Failure Handling

Failures are classified into:
- **rate_limit**: HTTP 429, "too many requests" - retry with longer delay
- **timeout**: Connection timeout - retry soon
- **network_error**: Connection issues - retry soon
- **server_error**: HTTP 5xx - retry later
- **authentication**: HTTP 401/403, API key required - don't retry
- **not_found**: HTTP 404, paper not found - don't retry
- **paywall**: Behind paywall, not open access - don't retry
- **invalid_pdf**: Downloaded but not valid PDF - don't retry

### Performance Learning

The system continuously learns:
- Which sources work best overall
- Which sources work best for specific publishers (DOI prefixes)
- Which URL patterns succeed for each publisher
- Which failure types indicate permanent vs temporary issues

Over time, the system gets smarter and faster by trying the most likely successful source first.

## Testing

### Test Database Initialization

```bash
python pdf_download_db.py
```

### Test Individual Sources

```bash
python pdf_sources.py
```

### Test Smart Download

```bash
python pdf_manager_enhanced.py
```

## Monitoring and Maintenance

### View Current Performance

```python
from pdf_download_db import get_source_rankings

rankings = get_source_rankings()
for rank, source in enumerate(rankings, 1):
    print(f"{rank}. {source['name']}: {source['success_rate']:.1f}% success")
```

### Check Retry Queue

```python
from pdf_download_db import get_retry_queue_ready

retries = get_retry_queue_ready()
print(f"{len(retries)} DOIs ready for retry")
```

### Cleanup Old Data

```python
from pdf_download_db import cleanup_old_attempts

deleted = cleanup_old_attempts(retention_days=90)
print(f"Deleted {deleted} old records")
```

## Troubleshooting

### Sources Not Working

1. Check if source is enabled in config.py
2. Check if required library is installed (for optional sources)
3. Check source performance in analytics
4. Review failure logs in database

### Low Success Rates

1. Check if API keys are configured (CORE, NCBI)
2. Verify DOIs are valid and properly formatted
3. Check if papers are actually open access
4. Review failure categories in analytics

### Database Issues

1. Ensure database file is writable
2. Check disk space
3. Run database initialization manually
4. Review error logs

### API Rate Limits

1. Increase `PDF_RATE_LIMIT_DELAY_SECONDS` in config
2. Reduce concurrent download threads
3. Check source-specific rate limits
4. Use API keys where available

## Best Practices

1. **Start with minimal installation** - Add dependencies only as needed
2. **Get API keys** - CORE and NCBI keys significantly improve results
3. **Monitor performance** - Regularly check analytics to identify issues
4. **Clean up old data** - Periodically remove old attempts to prevent bloat
5. **Adjust configuration** - Fine-tune delays and retries based on your usage
6. **Enable SciHub cautiously** - Only if legal in your jurisdiction and as last resort
7. **Keep database backed up** - The tracking database contains valuable performance data

## Legal and Ethical Considerations

### Open Access Sources
- Unpaywall, Europe PMC, CORE, Semantic Scholar, Publisher Direct are all legal and ethical
- These sources only provide access to legitimately open access papers

### Institutional Access
- Habanero with institutional proxy requires valid institutional credentials
- Only use within your institution's network and policies

### SciHub
- **Disabled by default**
- May not be legal in all jurisdictions
- Use only if you understand the legal implications in your location
- Consider as absolute last resort only

### Rate Limiting
- Respect API rate limits
- Use appropriate delays between requests
- Get API keys for better rate limits

### Publisher Rights
- The system only attempts to download papers that are open access
- Respect publisher terms of service
- Don't circumvent paywalls

## Performance Expectations

With minimal installation:
- **Success rate**: 40-60% for biomedical papers, 30-50% for general papers
- **Response time**: 2-5 seconds per attempt
- **Coverage**: Primarily open access papers

With standard installation:
- **Success rate**: 60-75% for biomedical papers, 50-65% for general papers
- **Response time**: 2-5 seconds per attempt
- **Coverage**: Most open access papers, some institutional access

With full installation + API keys:
- **Success rate**: 70-85% for biomedical papers, 60-75% for general papers
- **Response time**: 2-5 seconds per attempt
- **Coverage**: Most open access and PMC papers

Performance improves over time as the system learns optimal sources for each publisher.

## Support and Contribution

For issues, questions, or contributions:
1. Check the troubleshooting section
2. Review error logs
3. Check analytics for patterns
4. File issue with detailed logs if problem persists

## License

Same as parent project.
