# PDF Download Test Script

## Purpose

This script tests the PDF download workflow for the t2t_training application. It helps diagnose which PDF sources (Unpaywall, Metapub, Habanero) are working correctly for different DOIs.

## Usage

### Basic usage (with default test DOIs):
```bash
python3 test_pdf_download.py
```

### Test specific DOIs:
```bash
python3 test_pdf_download.py "10.1371/journal.pone.0000000" "10.1038/s41586-020-2649-2"
```

### Test from a file:
```bash
python3 test_pdf_download.py $(cat dois.txt)
```

## What it tests

For each DOI, the script tests:

1. **Unpaywall (REST API + Library)**
   - Checks if DOI is open access using REST API
   - Reports if a direct PDF URL is available or just a page URL
   - If `is_oa=True` but `url_for_pdf` is null, automatically tries unpywall library's `get_pdf_link()` method as fallback
   - Shows detailed diagnostics when fallback is used

2. **Metapub (PubMed Central, arXiv, Publisher-Specific Access)**
   - Checks if DOI is available via PubMed Central
   - Uses correct PMC domain: `pmc.ncbi.nlm.nih.gov` (not `www.ncbi.nlm.nih.gov`)
   - Constructs proper PDF URLs with filenames for PLOS journals
   - For PLOS journals (e.g., `10.1371/journal.pone.0229615`), generates full URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC{id}/pdf/pone.0229615.pdf`
   - Checks for arXiv papers
   - Uses **FindIt** module for publisher-specific PDF access when PMC is not available
   - FindIt can discover PDFs from various publishers (Wiley, Elsevier, etc.) using intelligent scraping
   - Reports the source URL if found

3. **Habanero (Crossref)**
   - Checks if Habanero library is installed
   - Used in multi-source download for institutional access

4. **Multi-source download**
   - Attempts to download PDF using all available sources
   - Reports which source succeeded
   - Saves PDFs to `/tmp/pdf_test/`

## Output

The script provides:

1. **Real-time progress** for each DOI
2. **Summary statistics** showing success rates
3. **Detailed breakdown** of what worked/failed for each DOI
4. **List of downloaded files** with sizes

## Example Output

```
================================================================================
Testing DOI: 10.1371/journal.pone.0000000
================================================================================

  Testing Unpaywall...
  Testing Metapub...
  Testing multi-source download...

================================================================================
SUMMARY
================================================================================

Total DOIs tested: 6
Unpaywall found: 4/6 (66%)
Metapub found: 2/6 (33%)
Successfully downloaded: 5/6 (83%)

--------------------------------------------------------------------------------
Details by DOI:
--------------------------------------------------------------------------------

10.1371/journal.pone.0000000:
  ✓ Unpaywall: Open Access (PDF URL)
  ✗ Metapub: Not found
  ✓ Habanero: Available
  ✓ Download: SUCCESS via unpaywall
```

## Troubleshooting

### "An email address is required" error from Unpywall
Make sure `UNPAYWALL_EMAIL` is set to a valid email address in `config.py` (not the default "your-email@example.com"). The unpywall library is configured using `UnpywallCredentials(email)` on import.

Alternatively, you can set the environment variable:
```bash
export UNPAYWALL_EMAIL="your-email@example.com"
```

### "NCBI_API_KEY was not set" warning from Metapub
This warning appears when using Metapub without an NCBI API key. The key improves rate limits for PubMed/PMC queries. To fix:

**Option 1 (Recommended): Set in config.py**
1. Register for a free NCBI API key at https://www.ncbi.nlm.nih.gov/account/settings/
2. Add your key to `config.py`: `NCBI_API_KEY = "your_key_here"`
3. The key will be automatically set as an environment variable when pdf_manager is imported

**Option 2: Set as environment variable**
```bash
export NCBI_API_KEY="your_key_here"
```

**Option 3: Disable Metapub**
Set `ENABLE_METAPUB_FALLBACK = False` in `config.py` to disable Metapub

Note: Metapub will still work without a key but with lower rate limits (3 requests/second vs 10 requests/second with a key).

### If Unpaywall shows "is_oa=True but no direct PDF URL"
This means the article is open access but Unpaywall REST API only provides a landing page URL, not a direct PDF link. The system will automatically try the unpywall library's `get_pdf_link()` method as a fallback, which often succeeds in finding the PDF link even when the REST API doesn't provide `url_for_pdf`.

### If Unpywall library is not available
Install with: `pip install unpywall>=0.2.0`

The unpywall library provides better PDF link detection for cases where the REST API returns `is_oa=True` but `url_for_pdf` is null.

### If Metapub is not available
Install with: `pip install metapub>=0.6.4`

Metapub includes the **FindIt** module which provides publisher-specific PDF access for articles not in PubMed Central. FindIt can discover PDFs from various publishers including Wiley, Elsevier, Nature, and others through intelligent web scraping.

Note: Metapub is now disabled by default (`ENABLE_METAPUB_FALLBACK = False` in config.py) to avoid NCBI_API_KEY warnings.

### If Habanero is not available
Install with: `pip install habanero>=1.2.6`

Habanero is enabled by default and works within institutional networks without special configuration.

## Configuration

The script uses the configuration from `config.py`:
- `UNPAYWALL_EMAIL`: Email for Unpaywall API (required - must be a valid email, not "your-email@example.com")
- `ENABLE_METAPUB_FALLBACK`: Enable/disable Metapub (default: False, requires NCBI_API_KEY)
- `ENABLE_HABANERO_DOWNLOAD`: Enable/disable Habanero (default: True, works in institutional networks)

## Notes

- PDFs are downloaded to `/tmp/pdf_test/` by default
- The script respects rate limits (1 second delay between DOIs)
- Some DOIs may fail if they require institutional access or subscriptions
- arXiv papers should work well with Metapub
- PLOS and other open access publishers work well with Unpaywall
