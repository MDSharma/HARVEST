#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllenNLP adapter for trait extraction

Uses AllenNLP for advanced NLP tasks like SRL and coreference resolution.
"""

import logging
from typing import List, Dict, Any, Optional
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class AllenNLPAdapter(BaseAdapter):
    """AllenNLP-based trait extraction adapter"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.predictor = None
        self.model_name = config.get("params", {}).get("model_name", "structured-prediction-srl-bert")
    
    def load_model(self) -> None:
        """Load AllenNLP model"""
        try:
            from allennlp.predictors.predictor import Predictor
            import allennlp_models.tagging
            
            logger.info(f"Loading AllenNLP model: {self.model_name}")
            
            # Load pre-trained model
            self.predictor = Predictor.from_path(
                f"https://storage.googleapis.com/allennlp-public-models/{self.model_name}.tar.gz"
            )
            
            self.is_loaded = True
            logger.info("AllenNLP model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load AllenNLP model: {e}")
            raise
    
    def extract_triples(self, texts: List[str], **kwargs) -> List[List[Dict[str, Any]]]:
        """
        Extract triples using AllenNLP SRL
        
        Args:
            texts: List of text strings to process
            **kwargs: Additional parameters
        
        Returns:
            List of lists of triples, one per input text
        """
        if not self.is_loaded:
            self.load_model()
        
        all_triples = []
        
        for text in texts:
            # Run SRL prediction
            result = self.predictor.predict(sentence=text)
            
            text_triples = []
            
            # Extract semantic roles as triples
            for verb_frame in result.get("verbs", []):
                verb = verb_frame["verb"]
                description = verb_frame["description"]
                
                # Parse SRL output
                triple = self._parse_srl_frame(verb_frame, text)
                if triple:
                    text_triples.append(triple)
            
            all_triples.append(text_triples)
        
        return all_triples
    
    def _parse_srl_frame(self, frame: Dict[str, Any], text: str) -> Optional[Dict[str, Any]]:
        """Parse SRL frame into triple format"""
        tags = frame.get("tags", [])
        words = text.split()
        
        # Extract arguments
        arg0 = []  # Agent
        arg1 = []  # Patient
        verb = frame.get("verb", "")
        
        current_arg = None
        for i, tag in enumerate(tags):
            if i < len(words):
                if tag.startswith("B-ARG0"):
                    current_arg = "arg0"
                    arg0.append(words[i])
                elif tag.startswith("I-ARG0"):
                    if current_arg == "arg0":
                        arg0.append(words[i])
                elif tag.startswith("B-ARG1"):
                    current_arg = "arg1"
                    arg1.append(words[i])
                elif tag.startswith("I-ARG1"):
                    if current_arg == "arg1":
                        arg1.append(words[i])
                elif tag == "O":
                    current_arg = None
        
        if arg0 and arg1 and verb:
            return {
                "subject": " ".join(arg0),
                "subject_type": "Factor",
                "predicate": self._verb_to_relation(verb),
                "object": " ".join(arg1),
                "object_type": "Factor",
                "confidence": 0.8,
                "sentence": text
            }
        
        return None
    
    def _verb_to_relation(self, verb: str) -> str:
        """Map verb to biological relation type"""
        verb_map = {
            "encode": "encodes",
            "encodes": "encodes",
            "regulate": "regulates",
            "regulates": "regulates",
            "activate": "activates",
            "activates": "activates",
            "inhibit": "inhibits",
            "inhibits": "inhibits",
            "increase": "increases",
            "increases": "increases",
            "decrease": "decreases",
            "decreases": "decreases",
            "affect": "influences",
            "affects": "influences",
            "influence": "influences",
            "influences": "influences",
        }
        return verb_map.get(verb.lower(), "is_related_to")
    
    def train(self, training_data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Training not implemented for AllenNLP adapter
        
        Note: AllenNLP training requires more complex setup with config files
        """
        logger.warning("Training not implemented for AllenNLP adapter")
        return {
            "status": "not_implemented",
            "message": "AllenNLP training requires custom configuration files"
        }
    
    def normalize_triple(self, raw_triple: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize AllenNLP triple to HARVEST format"""
        return {
            "source_entity_name": raw_triple.get("subject", ""),
            "source_entity_attr": raw_triple.get("subject_type", "Factor"),
            "relation_type": raw_triple.get("predicate", ""),
            "sink_entity_name": raw_triple.get("object", ""),
            "sink_entity_attr": raw_triple.get("object_type", "Factor"),
            "confidence": raw_triple.get("confidence", 0.0),
            "trait_name": None,
            "trait_value": None,
            "unit": None
        }
