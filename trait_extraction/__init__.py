#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trait Extraction Module for HARVEST

This module provides NLP-based trait extraction capabilities using multiple backends:
- LasUIE: Universal information extraction
- Hugging Face Transformers: Custom NER/RE models
- spaCy: Fast production-ready pipelines
- AllenNLP: Advanced semantic analysis

Supports both local and remote execution modes for GPU-intensive operations.
"""

__version__ = "1.0.0"
__author__ = "HARVEST Team"

from .config import TraitExtractionConfig
from .models import ExtractionJob, Document, ExtractedTriple

__all__ = [
    "TraitExtractionConfig",
    "ExtractionJob", 
    "Document",
    "ExtractedTriple"
]
