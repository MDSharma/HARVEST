#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Directory Initialization for HARVEST
Creates required directories at application startup with proper error handling.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


def ensure_directory_exists(dir_path: str, description: str = "") -> Tuple[bool, str]:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dir_path: Path to the directory to create
        description: Human-readable description of the directory
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(dir_path)
        
        # Check if it already exists
        if os.path.exists(abs_path):
            if os.path.isdir(abs_path):
                logger.debug(f"Directory already exists: {abs_path}")
                return True, f"Directory already exists: {abs_path}"
            else:
                # Path exists but is not a directory
                error_msg = f"Path exists but is not a directory: {abs_path}"
                logger.error(error_msg)
                return False, error_msg
        
        # Create the directory with parents
        Path(abs_path).mkdir(parents=True, exist_ok=True)
        
        # Verify creation
        if os.path.isdir(abs_path):
            desc = f" ({description})" if description else ""
            success_msg = f"Created directory: {abs_path}{desc}"
            logger.info(success_msg)
            return True, success_msg
        else:
            error_msg = f"Failed to create directory: {abs_path}"
            logger.error(error_msg)
            return False, error_msg
            
    except PermissionError as e:
        error_msg = f"Permission denied creating directory {dir_path}: {e}"
        logger.error(error_msg)
        return False, error_msg
    except OSError as e:
        error_msg = f"OS error creating directory {dir_path}: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error creating directory {dir_path}: {e}"
        logger.error(error_msg)
        return False, error_msg


def init_harvest_directories(base_dir: str = None) -> Tuple[bool, List[str]]:
    """
    Initialize all required directories for HARVEST at application startup.
    
    This function creates:
    - .cache/huggingface: For HuggingFace model caching (literature search)
    - project_pdfs: Base directory for PDF storage
    
    Args:
        base_dir: Base directory for HARVEST (defaults to current directory)
        
    Returns:
        Tuple of (all_success: bool, messages: List[str])
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Import configuration
    try:
        from config import PDF_STORAGE_DIR
    except ImportError:
        PDF_STORAGE_DIR = "project_pdfs"
    
    messages = []
    all_success = True
    
    # Define required directories
    required_dirs = [
        (
            os.path.join(base_dir, ".cache", "huggingface"),
            "HuggingFace model cache for literature search"
        ),
        (
            os.path.join(base_dir, PDF_STORAGE_DIR),
            "PDF storage for projects"
        ),
    ]
    
    logger.info("Initializing HARVEST directories...")
    
    for dir_path, description in required_dirs:
        success, message = ensure_directory_exists(dir_path, description)
        messages.append(message)
        
        if not success:
            all_success = False
            # Log error but continue with other directories
            logger.warning(f"Failed to create {description}: {message}")
    
    if all_success:
        logger.info("All HARVEST directories initialized successfully")
    else:
        logger.warning("Some HARVEST directories could not be created")
    
    return all_success, messages


def check_directory_permissions(dir_path: str) -> Tuple[bool, str]:
    """
    Check if a directory exists and is writable.
    
    Args:
        dir_path: Path to check
        
    Returns:
        Tuple of (is_writable: bool, message: str)
    """
    try:
        abs_path = os.path.abspath(dir_path)
        
        if not os.path.exists(abs_path):
            return False, f"Directory does not exist: {abs_path}"
        
        if not os.path.isdir(abs_path):
            return False, f"Path is not a directory: {abs_path}"
        
        # Test write permission by creating a temporary file
        test_file = os.path.join(abs_path, ".harvest_write_test")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return True, f"Directory is writable: {abs_path}"
        except (PermissionError, OSError) as e:
            return False, f"Directory is not writable: {abs_path} ({e})"
            
    except Exception as e:
        return False, f"Error checking directory permissions: {e}"


if __name__ == "__main__":
    # Test directory initialization
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Testing HARVEST directory initialization...")
    success, messages = init_harvest_directories()
    
    print("\nResults:")
    for msg in messages:
        print(f"  {msg}")
    
    if success:
        print("\n✓ All directories initialized successfully")
        sys.exit(0)
    else:
        print("\n✗ Some directories could not be initialized")
        sys.exit(1)
