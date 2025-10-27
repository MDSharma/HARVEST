#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Annotation Manager
Handles adding and retrieving highlights from PDF files using PyMuPDF (fitz)
"""

import os
import fitz  # PyMuPDF
import json
import hashlib
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Security limits to prevent abuse
MAX_HIGHLIGHTS_PER_REQUEST = 50  # Maximum highlights per request
MAX_HIGHLIGHT_TEXT_LENGTH = 10000  # Maximum text length for a single highlight
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB max file size


def validate_highlight_data(highlight: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a single highlight object.
    
    Args:
        highlight: Dictionary with highlight data
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['page', 'rects', 'color']
    
    # Check required fields
    for field in required_fields:
        if field not in highlight:
            return False, f"Missing required field: {field}"
    
    # Validate page number
    if not isinstance(highlight['page'], int) or highlight['page'] < 0:
        return False, "Invalid page number"
    
    # Validate rects
    if not isinstance(highlight['rects'], list) or len(highlight['rects']) == 0:
        return False, "Rects must be a non-empty list"
    
    # Validate each rect has 4 coordinates
    for rect in highlight['rects']:
        if not isinstance(rect, list) or len(rect) != 4:
            return False, "Each rect must have exactly 4 coordinates [x0, y0, x1, y1]"
        if not all(isinstance(x, (int, float)) for x in rect):
            return False, "All rect coordinates must be numbers"
    
    # Validate color (should be a hex color or RGB array)
    color = highlight['color']
    if isinstance(color, str):
        # Validate hex color
        if not color.startswith('#') or len(color) not in [4, 7]:
            return False, "Invalid color format (use #RGB or #RRGGBB)"
    elif isinstance(color, list):
        if len(color) != 3 or not all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in color):
            return False, "Color as array must be [r, g, b] with values 0-1"
    else:
        return False, "Color must be a hex string or RGB array"
    
    # Validate optional text field length
    if 'text' in highlight:
        if not isinstance(highlight['text'], str):
            return False, "Text must be a string"
        if len(highlight['text']) > MAX_HIGHLIGHT_TEXT_LENGTH:
            return False, f"Highlight text exceeds maximum length of {MAX_HIGHLIGHT_TEXT_LENGTH}"
    
    return True, None


def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    """
    Convert hex color to RGB tuple (0-1 range).
    
    Args:
        hex_color: Hex color string like "#FFFF00" or "#FF0"
        
    Returns:
        Tuple of (r, g, b) in 0-1 range
    """
    hex_color = hex_color.lstrip('#')
    
    # Handle shorthand hex (#RGB -> #RRGGBB)
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    # Convert to RGB (0-1 range)
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    
    return (r, g, b)


def add_highlights_to_pdf(pdf_path: str, highlights: List[Dict]) -> Tuple[bool, str]:
    """
    Add highlights to a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        highlights: List of highlight dictionaries with structure:
            {
                'page': int,  # Page number (0-indexed)
                'rects': [[x0, y0, x1, y1], ...],  # Rectangle coordinates
                'color': '#FFFF00' or [1.0, 1.0, 0.0],  # Highlight color
                'text': 'highlighted text'  # Optional: the text being highlighted
            }
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Security: Check file size
        if not os.path.exists(pdf_path):
            return False, "PDF file not found"
        
        file_size = os.path.getsize(pdf_path)
        if file_size > MAX_FILE_SIZE:
            return False, f"PDF file too large (max {MAX_FILE_SIZE/1024/1024}MB)"
        
        # Security: Check number of highlights
        if len(highlights) > MAX_HIGHLIGHTS_PER_REQUEST:
            return False, f"Too many highlights (max {MAX_HIGHLIGHTS_PER_REQUEST} per request)"
        
        # Validate all highlights first
        for i, highlight in enumerate(highlights):
            is_valid, error = validate_highlight_data(highlight)
            if not is_valid:
                return False, f"Invalid highlight at index {i}: {error}"
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        try:
            # Add each highlight
            for highlight in highlights:
                page_num = highlight['page']
                
                # Security: Check page number is valid
                if page_num < 0 or page_num >= len(doc):
                    logger.warning(f"Invalid page number {page_num}, skipping")
                    continue
                
                page = doc[page_num]
                
                # Convert color to RGB tuple if it's a hex string
                color = highlight['color']
                if isinstance(color, str):
                    color = hex_to_rgb(color)
                
                # Add highlight annotation for each rectangle
                for rect in highlight['rects']:
                    # Create a fitz.Rect from coordinates
                    fitz_rect = fitz.Rect(rect[0], rect[1], rect[2], rect[3])
                    
                    # Add highlight annotation
                    annot = page.add_highlight_annot(fitz_rect)
                    annot.set_colors(stroke=color)
                    
                    # Add optional text as annotation content
                    if 'text' in highlight and highlight['text']:
                        annot.set_info(content=highlight['text'][:1000])  # Limit to 1000 chars
                    
                    annot.update()
            
            # Save the modified PDF with incremental save to preserve existing annotations
            doc.saveIncr()
            doc.close()
            
            return True, f"Successfully added {len(highlights)} highlight(s)"
        
        except Exception as e:
            doc.close()
            raise e
    
    except Exception as e:
        logger.error(f"Error adding highlights to PDF: {e}", exc_info=True)
        return False, f"Error adding highlights: {str(e)}"


def get_highlights_from_pdf(pdf_path: str) -> Tuple[bool, List[Dict], str]:
    """
    Extract existing highlights from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Tuple of (success: bool, highlights: List[Dict], message: str)
    """
    try:
        if not os.path.exists(pdf_path):
            return False, [], "PDF file not found"
        
        # Security: Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size > MAX_FILE_SIZE:
            return False, [], f"PDF file too large (max {MAX_FILE_SIZE/1024/1024}MB)"
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        highlights = []
        
        try:
            # Iterate through all pages
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get all annotations on this page
                for annot in page.annots():
                    # We're only interested in highlight annotations
                    if annot.type[0] == 8:  # 8 is the type code for highlight
                        # Get the highlight rectangles
                        rects = annot.vertices
                        if rects:
                            # Convert vertices to coordinate lists
                            rect_list = []
                            # Vertices come in groups of 4 points (quadrilaterals)
                            for i in range(0, len(rects), 4):
                                if i + 3 < len(rects):
                                    quad = rects[i:i+4]
                                    # Each vertex is a tuple (x, y) or a Point object
                                    # Convert to [x0, y0, x1, y1] format (bounding box)
                                    if hasattr(quad[0], 'x'):
                                        # It's a Point object
                                        x_coords = [p.x for p in quad]
                                        y_coords = [p.y for p in quad]
                                    else:
                                        # It's a tuple (x, y)
                                        x_coords = [p[0] for p in quad]
                                        y_coords = [p[1] for p in quad]
                                    
                                    rect_list.append([
                                        min(x_coords), min(y_coords),
                                        max(x_coords), max(y_coords)
                                    ])
                            
                            # Get color
                            color_rgb = annot.colors.get("stroke", [1.0, 1.0, 0.0])
                            
                            # Get annotation content (text)
                            text = annot.info.get("content", "")
                            
                            highlight_data = {
                                'page': page_num,
                                'rects': rect_list,
                                'color': color_rgb,
                            }
                            
                            if text:
                                highlight_data['text'] = text
                            
                            highlights.append(highlight_data)
            
            doc.close()
            return True, highlights, f"Found {len(highlights)} highlight(s)"
        
        except Exception as e:
            doc.close()
            raise e
    
    except Exception as e:
        logger.error(f"Error reading highlights from PDF: {e}", exc_info=True)
        return False, [], f"Error reading highlights: {str(e)}"


def clear_all_highlights(pdf_path: str) -> Tuple[bool, str]:
    """
    Remove all highlight annotations from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if not os.path.exists(pdf_path):
            return False, "PDF file not found"
        
        # Security: Check file size
        file_size = os.path.getsize(pdf_path)
        if file_size > MAX_FILE_SIZE:
            return False, f"PDF file too large (max {MAX_FILE_SIZE/1024/1024}MB)"
        
        doc = fitz.open(pdf_path)
        count = 0
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Delete all highlight annotations
                for annot in list(page.annots()):
                    if annot.type[0] == 8:  # Highlight annotation
                        page.delete_annot(annot)
                        count += 1
            
            # Save changes
            if count > 0:
                doc.saveIncr()
            
            doc.close()
            return True, f"Removed {count} highlight(s)"
        
        except Exception as e:
            doc.close()
            raise e
    
    except Exception as e:
        logger.error(f"Error clearing highlights from PDF: {e}", exc_info=True)
        return False, f"Error clearing highlights: {str(e)}"
