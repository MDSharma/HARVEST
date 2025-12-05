#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base adapter interface for trait extraction backends
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models import ExtractedTriple


class BaseAdapter(ABC):
    """Base class for all trait extraction adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration
        
        Args:
            config: Dictionary containing adapter-specific configuration
        """
        self.config = config
        self.model = None
        self.is_loaded = False
    
    @abstractmethod
    def load_model(self) -> None:
        """Load the model into memory"""
        pass
    
    @abstractmethod
    def extract_triples(self, texts: List[str], **kwargs) -> List[List[Dict[str, Any]]]:
        """
        Extract triples from a list of text documents
        
        Args:
            texts: List of text strings to process
            **kwargs: Additional extraction parameters
        
        Returns:
            List of lists of dictionaries, one list per input text.
            Each dictionary contains triple information that can be converted to ExtractedTriple
        """
        pass
    
    @abstractmethod
    def train(self, training_data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Train or fine-tune the model
        
        Args:
            training_data: List of training examples
            **kwargs: Training parameters
        
        Returns:
            Dictionary with training results (metrics, model path, etc.)
        """
        pass
    
    def normalize_triple(self, raw_triple: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a raw triple from backend-specific format to HARVEST format
        
        Args:
            raw_triple: Backend-specific triple representation
        
        Returns:
            Dictionary with HARVEST-compatible fields
        """
        # Default implementation - subclasses should override for specific formats
        return {
            "source_entity_name": raw_triple.get("subject", raw_triple.get("source", "")),
            "source_entity_attr": raw_triple.get("subject_type", raw_triple.get("source_type", "")),
            "relation_type": raw_triple.get("predicate", raw_triple.get("relation", "")),
            "sink_entity_name": raw_triple.get("object", raw_triple.get("target", "")),
            "sink_entity_attr": raw_triple.get("object_type", raw_triple.get("target_type", "")),
            "confidence": raw_triple.get("confidence", raw_triple.get("score", 0.0)),
            "trait_name": raw_triple.get("trait_name"),
            "trait_value": raw_triple.get("trait_value"),
            "unit": raw_triple.get("unit")
        }
    
    def unload_model(self) -> None:
        """Unload model from memory to free resources"""
        self.model = None
        self.is_loaded = False
    
    def validate_config(self) -> bool:
        """Validate adapter configuration"""
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "backend": self.__class__.__name__,
            "is_loaded": self.is_loaded,
            "config": self.config
        }
