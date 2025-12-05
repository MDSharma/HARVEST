#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration for Trait Extraction Module
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TraitExtractionConfig:
    """Configuration for trait extraction system"""
    
    # Execution mode
    local_mode: bool = field(default_factory=lambda: os.getenv("TRAIT_EXTRACTION_LOCAL_MODE", "true").lower() in ("true", "1", "yes"))
    
    # Remote server configuration (used when local_mode=False)
    remote_url: str = field(default_factory=lambda: os.getenv("TRAIT_EXTRACTION_URL", "http://localhost:8000"))
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("TRAIT_EXTRACTION_API_KEY"))
    
    # Timeout settings for remote calls
    request_timeout: int = field(default_factory=lambda: int(os.getenv("TRAIT_EXTRACTION_TIMEOUT", "300")))
    connection_timeout: int = field(default_factory=lambda: int(os.getenv("TRAIT_EXTRACTION_CONNECTION_TIMEOUT", "30")))
    
    # Model profiles
    model_profiles: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "lasuie": {
            "name": "LasUIE",
            "description": "Universal Information Extraction using generative LMs",
            "backend": "lasuie",
            "params": {
                "config_name": "default",
                "device": "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu",
                "batch_size": 8,
                "max_length": 512
            }
        },
        "huggingface_ner": {
            "name": "Hugging Face NER",
            "description": "BERT-based Named Entity Recognition",
            "backend": "huggingface",
            "params": {
                "model_name": "dbmdz/bert-large-cased-finetuned-conll03-english",
                "task": "ner",
                "device": "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu",
                "batch_size": 16
            }
        },
        "spacy_bio": {
            "name": "spaCy Biological NER",
            "description": "Fast spaCy pipeline with custom biological entity recognition",
            "backend": "spacy",
            "params": {
                "model_name": "en_core_web_sm",
                "custom_rules": True,
                "confidence_threshold": 0.7
            }
        },
        "allennlp_srl": {
            "name": "AllenNLP SRL",
            "description": "Semantic Role Labeling for relation extraction",
            "backend": "allennlp",
            "params": {
                "model_name": "structured-prediction-srl-bert",
                "device": "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"
            }
        }
    })
    
    # Storage paths
    models_cache_dir: str = field(default_factory=lambda: os.getenv("TRAIT_EXTRACTION_MODELS_CACHE", "trait_extraction/models_cache"))
    documents_dir: str = field(default_factory=lambda: os.getenv("TRAIT_EXTRACTION_DOCUMENTS", "trait_extraction/documents"))
    
    # Training settings
    enable_training: bool = field(default_factory=lambda: os.getenv("TRAIT_EXTRACTION_ENABLE_TRAINING", "true").lower() in ("true", "1", "yes"))
    training_batch_size: int = field(default_factory=lambda: int(os.getenv("TRAIT_EXTRACTION_TRAINING_BATCH_SIZE", "4")))
    training_epochs: int = field(default_factory=lambda: int(os.getenv("TRAIT_EXTRACTION_TRAINING_EPOCHS", "3")))
    
    # Confidence thresholds
    min_confidence: float = field(default_factory=lambda: float(os.getenv("TRAIT_EXTRACTION_MIN_CONFIDENCE", "0.5")))
    
    @classmethod
    def from_config_file(cls, config_path: Optional[str] = None) -> "TraitExtractionConfig":
        """Load configuration from config.py if available"""
        try:
            from config import (
                TRAIT_EXTRACTION_LOCAL_MODE,
                TRAIT_EXTRACTION_URL,
                TRAIT_EXTRACTION_API_KEY
            )
            return cls(
                local_mode=TRAIT_EXTRACTION_LOCAL_MODE,
                remote_url=TRAIT_EXTRACTION_URL,
                api_key=TRAIT_EXTRACTION_API_KEY
            )
        except ImportError:
            # Use environment variables / defaults
            return cls()
    
    def get_model_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific model profile by name"""
        return self.model_profiles.get(profile_name)
    
    def list_model_profiles(self) -> list:
        """List all available model profiles"""
        return [
            {
                "id": key,
                "name": profile["name"],
                "description": profile["description"],
                "backend": profile["backend"]
            }
            for key, profile in self.model_profiles.items()
        ]


# Global configuration instance
config = TraitExtractionConfig()
