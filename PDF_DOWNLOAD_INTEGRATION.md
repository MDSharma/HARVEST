# Enhanced PDF Download System - Integration Guide

## Quick Start

This guide shows how to integrate the enhanced PDF download system into the existing T2T Training application.

## Overview

The enhanced system has been designed to work alongside the existing PDF download system without breaking changes. You can enable it with a single configuration flag.

## Installation Steps

### 1. Install Dependencies

Choose your installation level:

**Minimal (Recommended for testing):**
```bash
pip install -r requirements-minimal.txt
```

**Standard (Recommended for production):**
```bash
pip install -r requirements-standard.txt
```

**Full (Maximum functionality):**
```bash
pip install -r requirements-full.txt
```

### 2. Configure the System

Edit `config.py`:

```python
# Enable the enhanced system
ENABLE_ENHANCED_PDF_DOWNLOAD = True

# Configure sources (all True for maximum coverage)
ENABLE_EUROPE_PMC = True
ENABLE_CORE = True
ENABLE_SEMANTIC_SCHOLAR = True
ENABLE_PUBLISHER_DIRECT = True

# Optional: Add API keys for better results
CORE_API_KEY = ""  # Get free at https://core.ac.uk/services/api
NCBI_API_KEY = ""  # Get free at https://www.ncbi.nlm.nih.gov/account/
```

### 3. Initialize the Database

The database will be automatically initialized on first use, but you can do it manually:

```bash
python pdf_download_db.py
```

This creates `pdf_downloads.db` with all required tables.

### 4. Integrate Analytics Endpoints (Optional)

Edit `t2t_training_be.py` to add analytics endpoints:

```python
# Add at the top with other imports
from pdf_analytics_endpoints import init_pdf_analytics_routes

# Add after creating the Flask app
init_pdf_analytics_routes(app, verify_admin_password, is_admin_user)
```

This adds all the analytics endpoints documented in `PDF_DOWNLOAD_ENHANCED.md`.

### 5. Update Download Function (Optional)

To use the enhanced system, update the download function in `t2t_training_be.py`:

Find the `_run_pdf_download_task` function and replace:

```python
# OLD:
from pdf_manager import process_project_dois_with_progress

# NEW:
from config import ENABLE_ENHANCED_PDF_DOWNLOAD

if ENABLE_ENHANCED_PDF_DOWNLOAD:
    from pdf_manager_enhanced import process_dois_smart as process_function
else:
    from pdf_manager import process_project_dois_with_progress as process_function
```

Then use `process_function` instead of calling the old function directly.

## Backward Compatibility

The enhanced system is fully backward compatible:

1. **Existing code continues to work** - The old `pdf_manager.py` is unchanged
2. **Separate database** - Uses `pdf_downloads.db`, doesn't touch `t2t_training.db`
3. **Configuration flag** - Easy to enable/disable via `config.py`
4. **Optional analytics** - Analytics endpoints are optional, system works without them

## Testing the Integration

### 1. Test Database Initialization

```bash
python pdf_download_db.py
```

Expected output:
```
[PDF DB] Initialized PDF download tracking database: pdf_downloads.db
✓ Database initialized successfully
✓ Logged download attempt: 1
✓ Retrieved 9 source rankings
✓ Statistics: 1 attempts, 100.0% success
```

### 2. Test Source Implementations

```bash
python pdf_sources.py
```

Expected output shows results for each source tested.

### 3. Test Smart Download

```bash
python pdf_manager_enhanced.py
```

This tests the complete smart download system with a known open access DOI.

### 4. Test via API

Start the backend and test the download endpoint:

```bash
curl -X POST http://localhost:5001/api/admin/projects/1/download-pdfs \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "your_password"}'
```

### 5. Test Analytics Endpoints

```bash
# Get statistics
curl http://localhost:5001/api/admin/pdf-analytics/statistics

# Get source rankings
curl http://localhost:5001/api/admin/pdf-analytics/sources
```

## Migration from Old System

If you have an existing installation:

1. **No data migration needed** - Old and new systems are independent
2. **Old downloads still work** - Existing PDFs are recognized and not re-downloaded
3. **Gradual transition** - Enable enhanced system only for new downloads
4. **Performance comparison** - Run both systems in parallel to compare

## Monitoring

### Check System Status

```python
from pdf_download_db import get_source_rankings, get_download_statistics

# View source performance
rankings = get_source_rankings()
for source in rankings[:5]:
    print(f"{source['name']}: {source['success_rate']:.1f}% success")

# View overall statistics
stats = get_download_statistics(days=7)
print(f"Last 7 days: {stats['successful']}/{stats['total_attempts']} successful")
```

### View Recent Attempts

```python
from pdf_download_db import get_pdf_db_connection

conn = get_pdf_db_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT doi, source_name, success, failure_reason, timestamp
    FROM download_attempts
    ORDER BY timestamp DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(row)

conn.close()
```

## Common Integration Patterns

### Pattern 1: Full Integration (Recommended)

Replace old system completely:

```python
from config import ENABLE_ENHANCED_PDF_DOWNLOAD

if ENABLE_ENHANCED_PDF_DOWNLOAD:
    from pdf_manager_enhanced import process_dois_smart
    results = process_dois_smart(doi_list, project_id, project_dir)
else:
    from pdf_manager import process_project_dois
    results = process_project_dois(doi_list, project_dir)
```

### Pattern 2: Parallel Comparison

Run both systems and compare:

```python
from pdf_manager import process_project_dois as old_process
from pdf_manager_enhanced import process_dois_smart as new_process

# Try enhanced first
results_new = new_process(doi_list, project_id, project_dir)

# Fallback to old for failures
failed_dois = [doi for doi, _, _ in results_new['needs_upload']]
if failed_dois:
    results_old = old_process(failed_dois, project_dir)
```

### Pattern 3: Gradual Rollout

Enable for specific projects:

```python
ENHANCED_PROJECT_IDS = [1, 2, 3]  # Projects using enhanced system

if project_id in ENHANCED_PROJECT_IDS:
    from pdf_manager_enhanced import process_dois_smart
    results = process_dois_smart(doi_list, project_id, project_dir)
else:
    from pdf_manager import process_project_dois
    results = process_project_dois(doi_list, project_dir)
```

## Rollback Plan

If you need to roll back:

1. Set `ENABLE_ENHANCED_PDF_DOWNLOAD = False` in config.py
2. Restart the application
3. Old system takes over immediately
4. Enhanced database remains intact for future use

No data is lost, and you can re-enable at any time.

## Performance Tuning

### Adjust Rate Limiting

If you're getting rate limited:

```python
PDF_RATE_LIMIT_DELAY_SECONDS = 2  # Increase delay between requests
```

### Adjust Retry Strategy

```python
PDF_SMART_RETRY_MAX_ATTEMPTS = 5        # More retry attempts
PDF_SMART_RETRY_BASE_DELAY_MINUTES = 30  # Shorter base delay
```

### Disable Slow Sources

Use analytics to identify slow sources and disable them:

```python
ENABLE_CORE = False  # If CORE is consistently slow
```

Or use the API:

```bash
curl -X POST http://localhost:5001/api/admin/pdf-analytics/sources/core/toggle \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "secret", "enabled": false}'
```

## Troubleshooting Integration

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'pdf_sources'`

**Solution**: Ensure all new files are in the same directory as the application:
- pdf_download_db.py
- pdf_sources.py
- pdf_manager_enhanced.py
- pdf_analytics_endpoints.py

### Database Errors

**Problem**: `sqlite3.OperationalError: no such table: sources`

**Solution**: Initialize the database:
```bash
python pdf_download_db.py
```

### Configuration Errors

**Problem**: `AttributeError: module 'config' has no attribute 'ENABLE_ENHANCED_PDF_DOWNLOAD'`

**Solution**: Update config.py with new configuration options from the integration guide.

### No Improvements Seen

**Problem**: Success rate is the same as old system

**Possible causes**:
1. Enhanced system not actually enabled - check configuration
2. Only tried one source so far - needs time to learn patterns
3. All papers are behind paywalls - check failure reasons in analytics
4. Rate limits preventing source attempts - check logs

**Solution**: Check analytics to see which sources are being tried:
```python
from pdf_download_db import get_download_statistics
stats = get_download_statistics(days=1)
print(stats['by_source'])
```

## Getting Help

If you encounter issues:

1. Check logs for error messages
2. Run test scripts to isolate the problem
3. Check analytics for patterns
4. Verify configuration matches this guide
5. Try minimal installation first before adding dependencies

## Next Steps

After successful integration:

1. Monitor performance for first week
2. Adjust configuration based on results
3. Enable additional sources as needed
4. Set up periodic cleanup of old data
5. Use analytics to optimize source selection
6. Consider getting API keys for better results

## Additional Resources

- **Full Documentation**: See `PDF_DOWNLOAD_ENHANCED.md`
- **Configuration Reference**: See `config.py`
- **API Reference**: See `PDF_DOWNLOAD_ENHANCED.md` (Analytics API Endpoints section)
- **Source Code**: All files are well-commented and can be reviewed for details
