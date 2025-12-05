#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LasUIE adapter for trait extraction

Wrapper for LasUIE (Universal Information Extraction) model.
LasUIE uses generative language models for IE tasks.

Note: Requires LasUIE repository to be cloned and configured.
"""

import logging
import os
import json
import subprocess
from typing import List, Dict, Any, Optional
from .base import BaseAdapter

logger = logging.getLogger(__name__)


class LasUIEAdapter(BaseAdapter):
    """LasUIE-based trait extraction adapter"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lasuie_path = os.getenv("LASUIE_PATH", "./LasUIE")
        self.config_name = config.get("params", {}).get("config_name", "default")
        self.device = config.get("params", {}).get("device", "cpu")
    
    def load_model(self) -> None:
        """Load LasUIE model (lazy loading on first inference)"""
        # Check if LasUIE repo exists
        if not os.path.exists(self.lasuie_path):
            logger.warning(f"LasUIE repository not found at {self.lasuie_path}")
            logger.info("Please clone LasUIE: git clone https://github.com/ChocoWu/LasUIE.git")
            raise FileNotFoundError(f"LasUIE not found at {self.lasuie_path}")
        
        # Check for required scripts
        inference_script = os.path.join(self.lasuie_path, "run_inference.py")
        if not os.path.exists(inference_script):
            raise FileNotFoundError(f"LasUIE inference script not found: {inference_script}")
        
        self.is_loaded = True
        logger.info("LasUIE adapter initialized (model will be loaded on first inference)")
    
    def extract_triples(self, texts: List[str], **kwargs) -> List[List[Dict[str, Any]]]:
        """
        Extract triples using LasUIE
        
        Args:
            texts: List of text strings to process
            **kwargs: Additional parameters
        
        Returns:
            List of lists of triples, one per input text
        """
        if not self.is_loaded:
            self.load_model()
        
        # Prepare input data in LasUIE format
        input_data = []
        for idx, text in enumerate(texts):
            input_data.append({
                "id": f"doc_{idx}",
                "text": text,
                "entities": [],
                "relations": []
            })
        
        # Write to temporary JSON file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(input_data, f)
            input_file = f.name
        
        # Run LasUIE inference
        try:
            output_file = input_file.replace('.json', '_output.json')
            
            # Construct command
            cmd = [
                "python",
                os.path.join(self.lasuie_path, "run_inference.py"),
                "--input", input_file,
                "--output", output_file,
                "--device", self.device,
                "--config", self.config_name
            ]
            
            # Run inference
            result = subprocess.run(
                cmd,
                cwd=self.lasuie_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"LasUIE inference failed: {result.stderr}")
                return [[] for _ in texts]
            
            # Parse output
            with open(output_file, 'r') as f:
                outputs = json.load(f)
            
            # Convert to triples format
            all_triples = []
            for output in outputs:
                text_triples = self._parse_lasuie_output(output)
                all_triples.append(text_triples)
            
            # Cleanup temp files
            os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
            
            return all_triples
            
        except subprocess.TimeoutExpired:
            logger.error("LasUIE inference timed out")
            return [[] for _ in texts]
        except Exception as e:
            logger.error(f"LasUIE inference error: {e}")
            return [[] for _ in texts]
    
    def _parse_lasuie_output(self, output: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse LasUIE output format to triples"""
        triples = []
        
        # LasUIE outputs linearized sequences - parse them
        entities = output.get("entities", [])
        relations = output.get("relations", [])
        
        for relation in relations:
            # Extract relation components
            triple = {
                "subject": relation.get("head", {}).get("text", ""),
                "subject_type": relation.get("head", {}).get("type", ""),
                "predicate": relation.get("type", "is_related_to"),
                "object": relation.get("tail", {}).get("text", ""),
                "object_type": relation.get("tail", {}).get("type", ""),
                "confidence": relation.get("score", 0.8),
                "sentence": output.get("text", "")
            }
            triples.append(triple)
        
        return triples
    
    def train(self, training_data: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Fine-tune LasUIE model
        
        Args:
            training_data: List of training examples in LasUIE format
            **kwargs: Training parameters
        
        Returns:
            Training results
        """
        if not self.is_loaded:
            self.load_model()
        
        # Write training data to JSON
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='_train.json', delete=False) as f:
            json.dump(training_data, f)
            train_file = f.name
        
        try:
            # Construct training command
            cmd = [
                "python",
                os.path.join(self.lasuie_path, "run_finetune.py"),
                "--train_file", train_file,
                "--output_dir", kwargs.get("output_dir", "./tmp/lasuie_finetuned"),
                "--num_epochs", str(kwargs.get("num_epochs", 3)),
                "--batch_size", str(kwargs.get("batch_size", 4)),
                "--device", self.device
            ]
            
            # Run training
            result = subprocess.run(
                cmd,
                cwd=self.lasuie_path,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout for training
            )
            
            if result.returncode != 0:
                logger.error(f"LasUIE training failed: {result.stderr}")
                return {"status": "failed", "error": result.stderr}
            
            # Cleanup
            os.unlink(train_file)
            
            return {
                "status": "completed",
                "output_dir": kwargs.get("output_dir", "./tmp/lasuie_finetuned"),
                "stdout": result.stdout
            }
            
        except subprocess.TimeoutExpired:
            logger.error("LasUIE training timed out")
            return {"status": "failed", "error": "Training timeout"}
        except Exception as e:
            logger.error(f"LasUIE training error: {e}")
            return {"status": "failed", "error": str(e)}
    
    def normalize_triple(self, raw_triple: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LasUIE triple to HARVEST format"""
        return {
            "source_entity_name": raw_triple.get("subject", ""),
            "source_entity_attr": self._normalize_entity_type(raw_triple.get("subject_type", "")),
            "relation_type": self._normalize_relation_type(raw_triple.get("predicate", "")),
            "sink_entity_name": raw_triple.get("object", ""),
            "sink_entity_attr": self._normalize_entity_type(raw_triple.get("object_type", "")),
            "confidence": raw_triple.get("confidence", 0.0),
            "trait_name": None,
            "trait_value": None,
            "unit": None
        }
    
    def _normalize_entity_type(self, lasuie_type: str) -> str:
        """Map LasUIE entity types to HARVEST types"""
        mapping = {
            "gene": "Gene",
            "protein": "Protein",
            "trait": "Trait",
            "phenotype": "Trait",
            "metabolite": "Metabolite",
            "enzyme": "Enzyme",
        }
        return mapping.get(lasuie_type.lower(), "Factor")
    
    def _normalize_relation_type(self, lasuie_relation: str) -> str:
        """Map LasUIE relation types to HARVEST types"""
        mapping = {
            "encode": "encodes",
            "regulate": "regulates",
            "increase": "increases",
            "decrease": "decreases",
        }
        return mapping.get(lasuie_relation.lower(), lasuie_relation)
