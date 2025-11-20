# Test Scripts

This directory contains test scripts for the HARVEST application. These scripts help validate functionality and can be used for manual testing and verification.

## Available Tests

### Configuration Tests
- **test_config_overrides.py** - Tests that environment variables correctly override config.py settings
  ```bash
  python3 test_config_overrides.py
  ```

### WSGI Entry Point Tests
- **test_wsgi_be.py** - Tests the backend WSGI entry point for Gunicorn deployment
  ```bash
  python3 test_wsgi_be.py
  ```
- **test_wsgi_fe.py** - Tests the frontend WSGI entry point for Gunicorn deployment
  ```bash
  python3 test_wsgi_fe.py
  ```

### Literature Search Tests
- **test_literature_search_integration.py** - Integration tests for the complete search workflow
  ```bash
  python3 test_literature_search_integration.py
  ```
- **test_literature_search_improvements.py** - Tests for literature search improvements (per-source limits, query format detection)
  ```bash
  python3 test_literature_search_improvements.py
  ```

### PDF Feature Tests
- **test_pdf_annotation.py** - Tests the PDF annotation and highlighting functionality
  ```bash
  python3 test_pdf_annotation.py
  ```
- **test_pdf_download.py** - Tests the PDF download workflow with multiple sources (Unpaywall, Metapub, Habanero)
  ```bash
  # Test with default DOIs:
  python3 test_pdf_download.py
  
  # Test with specific DOIs:
  python3 test_pdf_download.py "10.1371/journal.pone.0000000" "10.1038/s41586-020-2649-2"
  ```
  See [test_pdf_download_README.md](test_pdf_download_README.md) for detailed documentation.

## Running Tests

Most tests can be run independently:
```bash
cd test_scripts
python3 <test_file>.py
```

Some tests require specific setup (mock services, environment variables, etc.). Check the individual test file documentation for details.

## Test Structure

These are primarily integration and functional tests rather than unit tests. They:
- Test end-to-end functionality
- Validate API integrations
- Check configuration handling
- Verify deployment scenarios

For automated testing in CI/CD, these can be integrated into your test pipeline.
