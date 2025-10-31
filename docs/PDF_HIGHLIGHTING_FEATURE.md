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
