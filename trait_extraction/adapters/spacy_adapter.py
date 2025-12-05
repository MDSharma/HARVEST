#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spaCy adapter for trait extraction

Uses spaCy for fast, production-ready NER and relation extraction.
Supports custom entity rules for biological domain.
"""

import logging
from typing import List, Dict, Any, Optional
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class SpacyAdapter(BaseAdapter):
    """spaCy-based trait extraction adapter"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.nlp = None
        self.custom_rules = config.get("params", {}).get("custom_rules", False)
        self.confidence_threshold = config.get("params", {}).get("confidence_threshold", 0.7)
    
    def load_model(self) -> None:
        """Load spaCy model"""
        try:
            import spacy
            from spacy.matcher import Matcher
            
            model_name = self.config.get("params", {}).get("model_name", "en_core_web_sm")
            logger.info(f"Loading spaCy model: {model_name}")
            
            try:
                self.nlp = spacy.load(model_name)
            except OSError:
                # Model not found, try to download it
                logger.warning(f"Model {model_name} not found, attempting download...")
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", model_name], check=True)
                self.nlp = spacy.load(model_name)
            
            # Add custom components if requested
            if self.custom_rules:
                self._add_custom_rules()
            
            self.is_loaded = True
            logger.info("spaCy model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise
    
    def _add_custom_rules(self) -> None:
        """Add custom pattern matching rules for biological entities"""
        from spacy.matcher import Matcher
        
        # Add custom entity ruler for biological terms
        if "entity_ruler" not in self.nlp.pipe_names:
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            
            # Biological entity patterns
            patterns = [
                {"label": "GENE", "pattern": [{"TEXT": {"REGEX": r"^[A-Z][A-Z0-9]+[a-z]?$"}}]},
                {"label": "PROTEIN", "pattern": [{"TEXT": {"REGEX": r"^[A-Z][A-Za-z0-9\-]+$"}}]},
                {"label": "TRAIT", "pattern": [{"LOWER": {"IN": ["yield", "height", "weight", "resistance", "tolerance"]}}]},
                {"label": "METABOLITE", "pattern": [{"LOWER": {"IN": ["glucose", "sucrose", "starch", "cellulose", "lignin"]}}]},
            ]
            ruler.add_patterns(patterns)
            logger.info("Added custom entity patterns")
    
    def extract_triples(self, texts: List[str], **kwargs) -> List[List[Dict[str, Any]]]:
        """
        Extract entity triples from texts using spaCy NER and dependency parsing
        
        Args:
            texts: List of text strings to process
            **kwargs: Additional parameters (unused)
        
        Returns:
            List of lists of triples, one per input text
        """
        if not self.is_loaded:
            self.load_model()
        
        all_triples = []
        
        for text in texts:
            doc = self.nlp(text)
            text_triples = []
            
            # Extract entity pairs from sentences
            for sent in doc.sents:
                # Get all entities in sentence
                entities = [
                    {
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char
                    }
                    for ent in sent.ents
                ]
                
                # Simple heuristic: create relations between consecutive entities
                for i in range(len(entities) - 1):
                    source_ent = entities[i]
                    target_ent = entities[i + 1]
                    
                    # Infer relation type from dependency parse
                    relation = self._infer_relation(sent, source_ent, target_ent)
                    
                    if relation:
                        triple = {
                            "subject": source_ent["text"],
                            "subject_type": self._normalize_entity_type(source_ent["label"]),
                            "predicate": relation,
                            "object": target_ent["text"],
                            "object_type": self._normalize_entity_type(target_ent["label"]),
                            "confidence": self.confidence_threshold,
                            "sentence": sent.text
                        }
                        text_triples.append(triple)
            
            all_triples.append(text_triples)
        
        return all_triples
    
    def _infer_relation(self, sent, source_ent: Dict, target_ent: Dict) -> Optional[str]:
        """Infer relation type from sentence structure"""
        # Look for verbs between entities
        for token in sent:
            if token.pos_ == "VERB":
                # Map verb lemmas to biological relations
                lemma = token.lemma_.lower()
                if lemma in ["encode", "encodes"]:
                    return "encodes"
                elif lemma in ["regulate", "regulates", "control", "controls"]:
                    return "regulates"
                elif lemma in ["increase", "increases", "enhance", "enhances"]:
                    return "increases"
                elif lemma in ["decrease", "decreases", "reduce", "reduces"]:
                    return "decreases"
                elif lemma in ["affect", "affects", "influence", "influences"]:
                    return "influences"
                elif lemma in ["associate", "associates", "correlate", "correlates"]:
                    return "associated_with"
        
        # Default relation
        return "is_related_to"
    
    def _normalize_entity_type(self, spacy_label: str) -> str:
        """Map spaCy entity labels to HARVEST entity types"""
        mapping = {
            "GENE": "Gene",
            "PROTEIN": "Protein",
            "TRAIT": "Trait",
            "METABOLITE": "Metabolite",
            "ORG": "Factor",  # Organizations as factors
            "PERSON": "Factor",
            "GPE": "Factor",  # Geo-political entities as environmental factors
            "NORP": "Factor",
            "FAC": "Factor",
        }
        return mapping.get(spacy_label, "Factor")
    
    def train(self, training_data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Train spaCy model on custom data
        
        Args:
            training_data: List of training examples with format:
                {"text": "...", "entities": [(start, end, label), ...]}
            **kwargs: Training parameters
        
        Returns:
            Training results
        """
        if not self.is_loaded:
            self.load_model()
        
        import spacy
        from spacy.training import Example
        import random
        
        # Convert training data to spaCy format
        train_examples = []
        for item in training_data:
            doc = self.nlp.make_doc(item["text"])
            entities = item.get("entities", [])
            example = Example.from_dict(doc, {"entities": entities})
            train_examples.append(example)
        
        # Train NER component
        ner = self.nlp.get_pipe("ner")
        
        # Add labels
        for example in train_examples:
            for ent in example.reference.ents:
                ner.add_label(ent.label_)
        
        # Training loop
        n_iter = kwargs.get("n_iter", 10)
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "ner"]
        
        with self.nlp.disable_pipes(*other_pipes):
            optimizer = self.nlp.create_optimizer()
            
            for iteration in range(n_iter):
                random.shuffle(train_examples)
                losses = {}
                
                for batch in spacy.util.minibatch(train_examples, size=8):
                    self.nlp.update(batch, sgd=optimizer, losses=losses, drop=0.5)
                
                logger.info(f"Iteration {iteration + 1}/{n_iter}, Loss: {losses.get('ner', 0.0):.4f}")
        
        return {
            "status": "completed",
            "iterations": n_iter,
            "final_loss": losses.get("ner", 0.0)
        }
    
    def normalize_triple(self, raw_triple: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize spaCy triple to HARVEST format"""
        return {
            "source_entity_name": raw_triple.get("subject", ""),
            "source_entity_attr": raw_triple.get("subject_type", ""),
            "relation_type": raw_triple.get("predicate", ""),
            "sink_entity_name": raw_triple.get("object", ""),
            "sink_entity_attr": raw_triple.get("object_type", ""),
            "confidence": raw_triple.get("confidence", 0.0),
            "trait_name": None,
            "trait_value": None,
            "unit": None
        }
