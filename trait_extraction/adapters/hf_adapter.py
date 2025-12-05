#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hugging Face Transformers adapter for trait extraction

Uses pre-trained or fine-tuned transformer models for NER and RE.
"""

import logging
from typing import List, Dict, Any, Optional
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class HuggingFaceAdapter(BaseAdapter):
    """Hugging Face Transformers-based trait extraction adapter"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pipeline = None
        self.tokenizer = None
        self.device = config.get("params", {}).get("device", "cpu")
    
    def load_model(self) -> None:
        """Load Hugging Face model"""
        try:
            from transformers import pipeline, AutoTokenizer
            
            model_name = self.config.get("params", {}).get("model_name", "dbmdz/bert-large-cased-finetuned-conll03-english")
            task = self.config.get("params", {}).get("task", "ner")
            
            logger.info(f"Loading Hugging Face model: {model_name} for task: {task}")
            
            # Load pipeline
            device_id = 0 if self.device == "cuda" else -1
            self.pipeline = pipeline(task, model=model_name, device=device_id, aggregation_strategy="simple")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            self.is_loaded = True
            logger.info("Hugging Face model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Hugging Face model: {e}")
            raise
    
    def extract_triples(self, texts: List[str], **kwargs) -> List[List[Dict[str, Any]]]:
        """
        Extract entities and relations from texts using Hugging Face models
        
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
            # Extract named entities
            entities = self.pipeline(text)
            
            text_triples = []
            
            # Create triples from consecutive entity pairs (simple heuristic)
            for i in range(len(entities) - 1):
                source = entities[i]
                target = entities[i + 1]
                
                # Infer relation based on entity types
                relation = self._infer_relation(source["entity_group"], target["entity_group"])
                
                triple = {
                    "subject": source["word"],
                    "subject_type": self._normalize_entity_type(source["entity_group"]),
                    "predicate": relation,
                    "object": target["word"],
                    "object_type": self._normalize_entity_type(target["entity_group"]),
                    "confidence": (source["score"] + target["score"]) / 2.0,
                    "sentence": text[max(0, source["start"] - 50):min(len(text), target["end"] + 50)]
                }
                text_triples.append(triple)
            
            all_triples.append(text_triples)
        
        return all_triples
    
    def _infer_relation(self, source_type: str, target_type: str) -> str:
        """Infer relation type from entity types"""
        # Simple rule-based relation inference
        type_pairs = {
            ("PER", "ORG"): "associated_with",
            ("ORG", "LOC"): "localizes_to",
            ("MISC", "MISC"): "is_related_to",
        }
        
        return type_pairs.get((source_type, target_type), "is_related_to")
    
    def _normalize_entity_type(self, hf_label: str) -> str:
        """Map Hugging Face entity labels to HARVEST entity types"""
        mapping = {
            "PER": "Factor",
            "ORG": "Factor",
            "LOC": "Factor",
            "MISC": "Factor",
        }
        return mapping.get(hf_label, "Factor")
    
    def train(self, training_data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Fine-tune Hugging Face model on custom data
        
        Args:
            training_data: List of training examples
            **kwargs: Training parameters
        
        Returns:
            Training results
        """
        try:
            from transformers import (
                AutoModelForTokenClassification,
                TrainingArguments,
                Trainer,
                DataCollatorForTokenClassification
            )
            from datasets import Dataset
            import torch
            
            if not self.is_loaded:
                self.load_model()
            
            model_name = self.config.get("params", {}).get("model_name")
            model = AutoModelForTokenClassification.from_pretrained(model_name)
            
            # Convert training data to Hugging Face dataset format
            # This is a simplified example - real implementation would need proper data formatting
            dataset = Dataset.from_dict({
                "text": [item["text"] for item in training_data],
                "labels": [item.get("labels", []) for item in training_data]
            })
            
            # Training arguments
            training_args = TrainingArguments(
                output_dir="./tmp/trait_extraction_training",
                num_train_epochs=kwargs.get("num_epochs", 3),
                per_device_train_batch_size=kwargs.get("batch_size", 4),
                warmup_steps=kwargs.get("warmup_steps", 500),
                weight_decay=kwargs.get("weight_decay", 0.01),
                logging_dir="./tmp/logs",
                logging_steps=10,
            )
            
            # Data collator
            data_collator = DataCollatorForTokenClassification(self.tokenizer)
            
            # Trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=dataset,
                data_collator=data_collator,
            )
            
            # Train
            train_result = trainer.train()
            
            # Save model
            output_dir = kwargs.get("output_dir", "./tmp/fine_tuned_model")
            trainer.save_model(output_dir)
            
            return {
                "status": "completed",
                "model_path": output_dir,
                "train_loss": train_result.training_loss,
                "metrics": train_result.metrics
            }
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def normalize_triple(self, raw_triple: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Hugging Face triple to HARVEST format"""
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
