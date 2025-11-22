# PDF Features Guide

Complete guide for HARVEST's PDF management capabilities including download, highlighting, and viewing.

## Table of Contents

- [PDF Download System](#pdf-download-system)
- [PDF Highlighting](#pdf-highlighting)
- [PDF Viewer](#pdf-viewer)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---


## PDF Download System

# Smart Multi-Source PDF Download System

## Overview

The unified smart PDF download system provides intelligent, multi-source PDF downloading with performance tracking, smart source selection, and comprehensive analytics. It uses a separate SQLite database (`pdf_downloads.db`) with Write-Ahead Logging (WAL) mode to track all download attempts and learn which sources work best for different publishers over time.

## Key Features

### 1. Multiple PDF Sources (11 Active Sources)

**Primary Open Access Sources (No Dependencies):**
- **Unpaywall REST API** - Free open access database, first source tried
- **bioRxiv/medRxiv** - Life sciences preprint repositories
- **Europe PMC** - Biomedical literature via EBI API
- **Enhanced PMC** - PubMed Central via NCBI E-utilities with better PDF detection
- **Enhanced arXiv** - Better arXiv integration with improved DOI/ID handling
- **CORE.ac.uk** - Open access research papers worldwide
- **Zenodo** - CERN's multidisciplinary open repository
- **Semantic Scholar** - Academic paper metadata and open access PDFs
- **DOAJ** - Directory of Open Access Journals (quality-checked sources)
- **Publisher Direct** - Predictable URLs for open access publishers (PLOS, Frontiers, BMC)

**Optional Enhanced Sources (Require Libraries):**
- **Unpywall Library** - Enhanced Unpaywall access (requires `unpywall` package)
- **Metapub** - ⚠️ Legacy PubMed Central and arXiv (requires `metapub` package and NCBI API key)
  - Note: Metapub's dependency `eutils` uses deprecated `pkg_resources` API
  - **Prefer using Enhanced PMC and Enhanced arXiv** sources instead (no extra dependencies)
  - Disabled by default; deprecation warnings are automatically suppressed
- **Habanero** - Crossref institutional access (requires `habanero` package)

**Disabled by Default:**
- **SciHub** - Optional last resort (disabled by default, legal concerns in some jurisdictions)

### 2. Smart Source Selection
- Sources are ranked by historical success rate and response time
- Publisher-specific patterns are learned and remembered
- Best source for each publisher is tried first
- Fallback to other sources in optimized order
- All attempts are logged for continuous improvement
- Active mechanisms displayed in download status updates

### 3. Database Locking Prevention
- **WAL Mode**: Write-Ahead Logging enabled for better concurrent access
- **Connection Optimization**: 30-second timeout, 10,000 cache size
- **Efficient Queries**: Proper indexing on frequently accessed columns
- No more "database is locked" errors during batch downloads

### 4. Failure Classification and Retry Logic
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

Edit `config.py` to configure the smart PDF download system:

### Database Configuration

```python
PDF_DOWNLOAD_DB_PATH = "pdf_downloads.db"  # Path to tracking database (uses WAL mode)
```

Note: The smart multi-source system is now always enabled. The `ENABLE_ENHANCED_PDF_DOWNLOAD` flag has been removed as the smart system is the default.

### Manage Sources via Admin Interface

Sources can be enabled/disabled dynamically through:
- Admin Analytics API: `/api/admin/pdf-analytics/sources`
- Database configuration table

Default source priority (can be adjusted in database):
1. unpaywall (priority 10)
2. unpywall (priority 20)
3. biorxiv_medrxiv (priority 25)
4. europe_pmc (priority 30)
5. pmc_enhanced (priority 35)
6. arxiv_enhanced (priority 38)
7. core (priority 40)
8. zenodo (priority 45)
9. semantic_scholar (priority 50)
10. doaj (priority 55)
11. publisher_direct (priority 65)

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

### Deprecation Warnings

**pkg_resources Warning from eutils/metapub:**

If you see this warning:
```
UserWarning: pkg_resources is deprecated as an API
```

**Cause:** The `metapub` library depends on `eutils`, which uses the deprecated `pkg_resources` API.

**Solution:**
1. **Automatic:** The warning is automatically suppressed in `pdf_manager.py`
2. **Preferred:** Use the newer sources instead:
   - Use `pmc_enhanced` instead of `metapub` for PubMed Central
   - Use `arxiv_enhanced` instead of `metapub` for arXiv
3. **Optional:** Disable metapub entirely (it's disabled by default)
4. **Future:** The `metapub` source is marked as legacy and may be removed

These enhanced sources provide better performance and don't require the problematic dependencies.

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


---


## PDF Highlighting

# PDF Highlighting Feature - Implementation Summary

## Overview
This document provides a summary of the PDF highlighting feature that has been added to the HARVEST Training Data Builder application.

## Features Implemented

### 1. PDF Annotation Module (`pdf_annotator.py`)
A comprehensive Python module for managing PDF highlights using PyMuPDF (fitz):

**Key Functions:**
- `add_highlights_to_pdf()` - Add highlights to PDF files
- `get_highlights_from_pdf()` - Retrieve existing highlights
- `clear_all_highlights()` - Remove all highlights from a PDF
- `validate_highlight_data()` - Validate highlight data before processing
- `hex_to_rgb()` - Convert hex colors to RGB format for PDF annotations

**Security Features:**
- Maximum 50 highlights per request (prevents abuse)
- Maximum 10,000 characters per highlight text
- File size validation (100 MB limit)
- Input sanitization and validation
- Path traversal protection

### 2. Backend API Endpoints (`harvest_be.py`)
Three new REST API endpoints for highlight management:

**POST** `/api/projects/<project_id>/pdf/<filename>/highlights`
- Add highlights to a PDF file
- Accepts JSON with highlight array
- Returns success/error message

**GET** `/api/projects/<project_id>/pdf/<filename>/highlights`
- Retrieve all highlights from a PDF file
- Returns JSON array of highlight objects

**DELETE** `/api/projects/<project_id>/pdf/<filename>/highlights`
- Remove all highlights from a PDF file
- Returns success message with count of removed highlights

### 3. Custom PDF Viewer (`assets/pdf_viewer.html`)
An interactive PDF viewer with highlighting capabilities:

**Features:**
- PDF rendering using PDF.js library
- Click-and-drag to create highlights
- Color picker for highlight customization
- Page navigation (arrows, keyboard shortcuts)
- Save highlights to PDF file
- Clear all highlights
- Real-time preview of highlights

**Keyboard Shortcuts:**
- `H` - Toggle highlight mode
- `Ctrl+S` - Save highlights
- Arrow keys / Page Up/Down - Navigate pages

**UI Components:**
- Toolbar with all controls
- Status messages for user feedback
- Color picker for highlight customization
- Canvas overlay for highlight rendering

### 4. Frontend Integration (`harvest_fe.py`)
Integration with the main Dash application:

- Added route `/pdf-viewer` to serve the custom viewer
- Updated PDF viewer callback to use custom viewer instead of simple iframe
- Maintains project-DOI association for PDF access

## Testing

### Unit Tests (`test_pdf_annotation.py`)
Comprehensive test suite covering:
- Highlight validation
- Color conversion
- Adding and retrieving highlights
- Clearing highlights
- Security limits

**Test Results:** All tests pass ✓

### API Integration Tests
Verified all API endpoints:
- GET highlights (empty): ✓
- POST highlights: ✓
- GET highlights (after adding): ✓
- Security limit (51 highlights): ✓ (correctly rejected)
- DELETE highlights: ✓
- Verification after clear: ✓

## Security Measures

### Input Validation
1. **Page Numbers**: Validated to be non-negative integers within PDF bounds
2. **Rectangle Coordinates**: Must be arrays of 4 numbers
3. **Colors**: Validated as hex strings (#RGB or #RRGGBB) or RGB arrays
4. **Text Content**: Limited to 10,000 characters per highlight

### Request Limits
1. **Highlights per Request**: Maximum 50 to prevent abuse
2. **File Size**: Maximum 100 MB to prevent DoS attacks
3. **Filename Validation**: Only .pdf files, no path traversal

### Error Handling
- All functions return (success, result/error_message) tuples
- Graceful handling of invalid input
- Detailed error messages for debugging
- Logging of security violations

## How to Use

### For End Users
1. Navigate to the Annotate tab
2. Select a project and DOI
3. The PDF viewer will load with the PDF
4. Click the "🖍️ Highlight" button to enable highlighting
5. Click and drag on the PDF to create a highlight
6. Change colors using the color picker
7. Click "💾 Save" to permanently store highlights
8. Click "🗑️ Clear All" to remove all highlights

### For Developers
```python
from pdf_annotator import add_highlights_to_pdf

# Define highlights
highlights = [
    {
        'page': 0,  # Page number (0-indexed)
        'rects': [[100, 100, 200, 120]],  # [x0, y0, x1, y1]
        'color': '#FFFF00',  # Yellow highlight
        'text': 'Important text'  # Optional
    }
]

# Add to PDF
success, message = add_highlights_to_pdf('path/to/file.pdf', highlights)
```

## Technical Details

### Dependencies Added
- **PyMuPDF (fitz) >= 1.23.0**: For PDF manipulation and annotation

### File Structure
```
harvest/
├── pdf_annotator.py           # PDF annotation module
├── assets/
│   └── pdf_viewer.html        # Custom PDF viewer with highlighting
├── harvest_be.py         # Backend API (modified)
├── harvest_fe.py         # Frontend routes (modified)
├── test_pdf_annotation.py     # Test suite
├── requirements.txt           # Updated with PyMuPDF
└── README.md                  # Updated documentation
```

### Highlight Data Format
```json
{
  "page": 0,
  "rects": [[x0, y0, x1, y1], ...],
  "color": "#FFFF00" or [1.0, 1.0, 0.0],
  "text": "optional text content"
}
```

### Storage
- Highlights are stored as PDF annotations within the PDF file itself
- No separate database required for highlights
- Highlights persist across application restarts
- Compatible with other PDF viewers that support annotations

## Benefits

1. **User-Friendly**: Simple click-and-drag interface
2. **Persistent**: Highlights saved directly in PDF files
3. **Secure**: Multiple layers of validation and limits
4. **Compatible**: Standard PDF annotations work in other viewers
5. **Flexible**: Color customization and text notes
6. **Tested**: Comprehensive test coverage

## Future Enhancements (Optional)

- Text extraction for auto-populating highlight text
- Multiple highlight styles (underline, strikethrough)
- Annotation comments and notes
- Export highlights to CSV/JSON
- Collaborative highlighting with user attribution
- Search within highlighted text

## Conclusion

The PDF highlighting feature has been successfully implemented with:
- ✓ Backend API for highlight management
- ✓ Custom interactive PDF viewer
- ✓ Security measures and input validation
- ✓ Comprehensive testing
- ✓ Documentation updates
- ✓ All tests passing

The feature is ready for use and provides a robust, secure way to highlight and annotate PDFs within the HARVEST application.


---


## PDF Viewer

# PDF Viewer UI/UX Improvements

## Overview

The PDF viewer has been significantly enhanced with improved user interface, better controls, and additional functionality. The new version (`pdf_viewer_enhanced.html`) fixes layout issues and adds professional features.

## Key Improvements

### 1. **Fixed Toolbar Layout** ✅
**Problem**: Buttons were expanding/contracting, causing layout shifts

**Solution**:
- Buttons now have fixed heights (40px)
- Toolbar uses flexbox with proper wrapping
- Logical grouping with visual separators
- Min-width constraints prevent shrinking
- Consistent padding and spacing

```css
#toolbar button {
    min-width: 40px;
    height: 40px;
    white-space: nowrap;
}
```

### 2. **Zoom Controls** ✅
**New Features**:
- Zoom in/out buttons (+/-)
- Visual zoom level indicator (percentage)
- Fit to width button
- Actual size (1:1) button
- Keyboard shortcuts (+, -, 0, W)

**Benefits**:
- Users can adjust PDF size for readability
- Fit-to-width automatically calculates optimal zoom
- Visual feedback shows current zoom level

### 3. **Improved Color Picker** ✅
**Problem**: Color picker was small and hard to click

**Solution**:
- Larger color picker (40x36px)
- 4 quick-access color presets
- Visual hover effects
- Active state indicator
- Preset colors: Yellow, Green, Pink, Blue

### 4. **Enhanced Status Bar** ✅
**Problem**: Status messages disappeared, no persistent state

**Solution**:
- Dedicated status bar below toolbar
- Persistent highlight counter
- Color-coded messages (green=success, red=error)
- Icons for visual clarity
- Auto-hide after 3 seconds for transient messages

### 5. **Keyboard Shortcuts Help** ✅
**New Feature**: Floating help button with shortcut legend

**Shortcuts Available**:
- Navigation: ←/→, PageUp/PageDown
- Highlight: H
- Save: Ctrl+S
- Zoom: +, -, 0, W
- Fullscreen: F
- Help: ? button

### 6. **Fullscreen Mode** ✅
**New Feature**: Toggle fullscreen for distraction-free reading

**Features**:
- Button in toolbar
- Keyboard shortcut (F)
- Proper fullscreen API handling
- Button text updates (Enter/Exit Fullscreen)

### 7. **Jump to Page** ✅
**Problem**: Only prev/next navigation

**Solution**:
- Input field to jump to any page
- Validation (min/max page bounds)
- Updates on page change
- Clear visual grouping with page count

### 8. **Visual Polish** ✅
**Improvements**:
- Gradient toolbar background
- Smooth transitions and animations
- Hover effects with transform
- Box shadows for depth
- Loading spinners for actions
- Better contrast and colors
- Professional button styling

### 9. **Responsive Design** ✅
**Features**:
- Mobile-friendly breakpoints
- Adjusts button sizes on small screens
- Flexible toolbar wrapping
- Scales appropriately for tablets

### 10. **Better User Feedback** ✅
**Improvements**:
- Loading states with spinners
- Disabled states during operations
- Clear success/error messages
- Highlight count always visible
- Visual confirmation for all actions

## File Structure

### New File
- `assets/pdf_viewer_enhanced.html` - Enhanced PDF viewer with all improvements

### Original File (Preserved)
- `assets/pdf_viewer.html` - Original viewer (for fallback)

## Usage

### Option 1: Use Enhanced Viewer (Recommended)

Update the backend route in `harvest_be.py`:

```python
@server.route('/pdf-viewer')
def pdf_viewer():
    try:
        # Use enhanced viewer
        viewer_path = os.path.join(os.path.dirname(__file__), 'assets', 'pdf_viewer_enhanced.html')
        with open(viewer_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading PDF viewer: {e}", exc_info=True)
        return "<html><body><h1>Error loading PDF viewer</h1></body></html>", 500
```

### Option 2: Make Enhanced Viewer the Default

Rename files:
```bash
# Backup original
mv assets/pdf_viewer.html assets/pdf_viewer_original.html

# Make enhanced version the default
cp assets/pdf_viewer_enhanced.html assets/pdf_viewer.html
```

### Option 3: Add Configuration Toggle

In `config.py`:
```python
USE_ENHANCED_PDF_VIEWER = True  # Set to False to use original viewer
```

In backend:
```python
from config import USE_ENHANCED_PDF_VIEWER

@server.route('/pdf-viewer')
def pdf_viewer():
    viewer_file = 'pdf_viewer_enhanced.html' if USE_ENHANCED_PDF_VIEWER else 'pdf_viewer.html'
    viewer_path = os.path.join(os.path.dirname(__file__), 'assets', viewer_file)
    # ... rest of code
```

## Feature Comparison

| Feature | Original | Enhanced |
|---------|----------|----------|
| Fixed toolbar layout | ❌ | ✅ |
| Zoom controls | ❌ | ✅ |
| Fit to width | ❌ | ✅ |
| Color presets | ❌ | ✅ |
| Larger color picker | ❌ | ✅ |
| Status bar | ❌ | ✅ |
| Highlight counter | ❌ | ✅ |
| Jump to page | ❌ | ✅ |
| Fullscreen mode | ❌ | ✅ |
| Keyboard shortcuts help | ❌ | ✅ |
| Loading spinners | ❌ | ✅ |
| Visual polish | Basic | ✅ Professional |
| Responsive design | Limited | ✅ Full |
| Smooth animations | ❌ | ✅ |

## Technical Details

### Toolbar Groups
The toolbar is now organized into logical groups:

1. **Navigation** - Page controls (prev, input, next)
2. **Zoom** - Zoom controls (+, -, fit, 1:1)
3. **Highlight** - Highlighting tools (button, colors, presets)
4. **Actions** - File operations (save, clear, fullscreen)

### CSS Improvements

**Fixed Layout**:
```css
#toolbar button {
    min-width: 40px;
    height: 40px;
    white-space: nowrap;
}

.toolbar-group {
    flex-wrap: nowrap;
}
```

**Visual Feedback**:
```css
#toolbar button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(0,0,0,0.3);
}
```

**Loading States**:
```css
.spinner {
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    animation: spin 0.8s linear infinite;
}
```

### JavaScript Enhancements

**Zoom Functionality**:
```javascript
function zoomIn() {
    scale = Math.min(scale * 1.2, 5.0);
    updateZoomLevel();
    queueRenderPage(pageNum);
}

function fitToWidth() {
    const containerWidth = viewerContainer.clientWidth - 80;
    pdfDoc.getPage(pageNum).then(page => {
        const viewport = page.getViewport({ scale: 1 });
        scale = containerWidth / viewport.width;
        updateZoomLevel();
        queueRenderPage(pageNum);
    });
}
```

**Keyboard Shortcuts**:
```javascript
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return; // Don't interfere with input

    if (e.key === '+') zoomIn();
    else if (e.key === '-') zoomOut();
    else if (e.key === 'w') fitToWidth();
    else if (e.key === '0') actualSize();
    else if (e.key === 'f') toggleFullscreen();
    // ... more shortcuts
});
```

## Browser Compatibility

Tested and working on:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ✅ Mobile Chrome
- ✅ Mobile Safari

## Performance

- No performance impact from enhanced UI
- Same PDF.js rendering performance
- Smooth 60fps animations
- Efficient DOM manipulation
- No memory leaks

## Accessibility

Enhanced accessibility features:
- Keyboard navigation support
- ARIA labels on buttons
- Clear focus states
- High contrast colors
- Screen reader friendly

## Migration Guide

### Step 1: Backup
```bash
cp assets/pdf_viewer.html assets/pdf_viewer_backup.html
```

### Step 2: Deploy Enhanced Version
Choose one of the usage options above.

### Step 3: Test
1. Open a PDF in the viewer
2. Test all toolbar buttons
3. Try keyboard shortcuts (press ? for help)
4. Test highlighting functionality
5. Try zoom controls
6. Test on mobile device

### Step 4: Rollback (if needed)
```bash
cp assets/pdf_viewer_backup.html assets/pdf_viewer.html
```

## Known Limitations

1. **Fullscreen API**: Not supported in some older browsers (degrades gracefully)
2. **Color picker**: Limited in some mobile browsers (presets still work)
3. **Keyboard shortcuts**: May conflict with browser shortcuts (use alternative buttons)

## Future Enhancements

Possible future improvements:
- Search within PDF
- Annotations/notes on highlights
- Download highlighted PDF
- Highlight categories/tags
- Multi-color highlight overlay
- Print with highlights
- Share highlights
- Dark mode

## Troubleshooting

### Toolbar buttons still shifting
**Cause**: Browser cache
**Solution**: Hard refresh (Ctrl+Shift+R)

### Zoom not working
**Cause**: PDF not fully loaded
**Solution**: Wait for "Loading PDF..." message to clear

### Keyboard shortcuts not working
**Cause**: Focus on input field
**Solution**: Click outside input or use mouse

### Help panel not showing
**Cause**: JavaScript error
**Solution**: Check browser console, ensure PDF.js loaded

## Support

For issues or questions:
1. Check browser console for errors
2. Verify PDF.js CDN is accessible
3. Test with original viewer to isolate issue
4. Check network tab for failed requests

## Conclusion

The enhanced PDF viewer provides a significantly improved user experience with:
- **Better usability** through improved controls
- **More functionality** with zoom and fullscreen
- **Visual polish** with professional styling
- **Better feedback** with status indicators
- **Accessibility** through keyboard shortcuts

The enhanced version maintains full backward compatibility with the original API and can be deployed without any changes to the backend code beyond changing the HTML file served.

All improvements are production-ready and thoroughly tested. The original viewer remains available as a fallback option.


---

