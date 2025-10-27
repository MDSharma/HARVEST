# Installation Guide

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation Steps

### 1. Install Python Dependencies

Install all required packages from requirements.txt:

```bash
pip install -r requirements.txt
```

**Important**: This includes PyMuPDF (fitz), which is required for the PDF highlighting feature.

### 2. Verify PyMuPDF Installation

Verify that PyMuPDF is installed correctly:

```bash
python -c "import fitz; print('PyMuPDF version:', fitz.__version__)"
```

If this fails with `ModuleNotFoundError: No module named 'fitz'`, install it manually:

```bash
pip install PyMuPDF>=1.23.0
```

### 3. Start the Backend Server

The backend server must be running for PDF highlighting to work:

```bash
python t2t_training_be.py
```

By default, the backend runs on port 5001. Check the console output to verify.

### 4. Start the Frontend Server

In a separate terminal, start the frontend:

```bash
python t2t_training_fe.py
```

By default, the frontend runs on port 8050.

## Configuration

### Enable/Disable PDF Highlighting

Edit `config.py` and set:

```python
ENABLE_PDF_HIGHLIGHTING = True  # Enable highlighting feature
# or
ENABLE_PDF_HIGHLIGHTING = False  # Disable highlighting feature
```

## Troubleshooting

### 500 Internal Server Error when saving highlights

**Symptom**: Getting HTTP 500 errors when trying to save PDF highlights.

**Cause**: PyMuPDF (fitz) is not installed.

**Solution**:
```bash
pip install PyMuPDF>=1.23.0
```

Then restart the backend server.

### 502 Bad Gateway Error

**Symptom**: Getting HTTP 502 errors when accessing PDF viewer or saving highlights.

**Cause**: Backend server is not running or not accessible.

**Solution**:
1. Start the backend server: `python t2t_training_be.py`
2. Verify it's running on port 5001
3. Check backend logs for errors

### Text Selection Not Working

**Symptom**: Cannot select text in PDF viewer.

**Cause**: PDF.js text layer not rendering properly.

**Solution**: 
- Clear browser cache and refresh
- Check browser console for JavaScript errors
- Verify PDF.js CDN is accessible

### CORS Errors

**Symptom**: Cross-Origin Request Blocked errors in browser console.

**Cause**: Outdated code or incorrect proxy routes.

**Solution**: 
- Ensure you're using the latest code with proxy routes
- All API calls should go through `/proxy/pdf/` and `/proxy/highlights/` routes
- Never call backend API directly from frontend JavaScript

## Testing

Run the test suite to verify installation:

```bash
python -m pytest test_pdf_annotation.py -v
```

All tests should pass if PyMuPDF is installed correctly.
