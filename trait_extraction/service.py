#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service layer for trait extraction

Handles extraction logic and switches between local/remote execution.
"""

import logging
import requests
from typing import List, Dict, Any, Optional
from .config import TraitExtractionConfig
from .adapters.factory import AdapterManager
from .store import (
    create_extraction_job,
    get_extraction_job,
    update_extraction_job,
    get_document,
    insert_extracted_triples
)

logger = logging.getLogger(__name__)


class TraitExtractionService:
    """Service for trait extraction operations"""
    
    def __init__(self, db_path: str, config: Optional[TraitExtractionConfig] = None):
        self.db_path = db_path
        self.config = config or TraitExtractionConfig()
        self.adapter_manager = AdapterManager()
    
    def extract_triples_from_documents(
        self,
        document_ids: List[int],
        model_profile: str,
        project_id: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract triples from documents
        
        Args:
            document_ids: List of document IDs to process
            model_profile: Model profile to use
            project_id: Optional project ID
            created_by: Optional user email
        
        Returns:
            Dictionary with job information
        """
        # Create extraction job
        job_id = create_extraction_job(
            self.db_path,
            project_id,
            document_ids,
            model_profile,
            "no_training",
            created_by
        )
        
        logger.info(f"Created extraction job {job_id} for {len(document_ids)} documents")
        
        # Execute extraction based on mode
        if self.config.local_mode:
            result = self._extract_local(job_id, document_ids, model_profile)
        else:
            result = self._extract_remote(job_id, document_ids, model_profile)
        
        return result
    
    def _extract_local(self, job_id: int, document_ids: List[int], 
                      model_profile: str) -> Dict[str, Any]:
        """Execute extraction locally"""
        try:
            # Update job status
            update_extraction_job(self.db_path, job_id, {
                "status": "running",
                "started_at": self._now()
            })
            
            # Get model configuration
            profile_config = self.config.get_model_profile(model_profile)
            if not profile_config:
                raise ValueError(f"Unknown model profile: {model_profile}")
            
            # Get adapter
            adapter = self.adapter_manager.get_adapter(model_profile, profile_config)
            
            # Load model if not loaded
            if not adapter.is_loaded:
                adapter.load_model()
            
            # Process documents
            total_triples = 0
            all_triples_to_insert = []  # Collect all triples for batch insert
            
            for i, doc_id in enumerate(document_ids):
                # Get document
                doc = get_document(self.db_path, doc_id)
                if not doc:
                    logger.warning(f"Document {doc_id} not found, skipping")
                    continue
                
                # Extract triples
                text = doc.get("text_content", "")
                if not text:
                    logger.warning(f"Document {doc_id} has no text content, skipping")
                    continue
                
                logger.info(f"Extracting from document {doc_id} ({i+1}/{len(document_ids)})")
                
                # Run extraction
                results = adapter.extract_triples([text])
                
                # Normalize and collect triples for batch insert
                if results and len(results) > 0:
                    raw_triples = results[0]  # First document's results
                    
                    for raw_triple in raw_triples:
                        normalized = adapter.normalize_triple(raw_triple)
                        # Add metadata
                        normalized.update({
                            "job_id": job_id,
                            "document_id": doc_id,
                            "project_id": doc.get("project_id"),
                            "model_profile": model_profile,
                            "sentence": raw_triple.get("sentence", text[:200]),
                            "doi_hash": doc.get("doi_hash")
                        })
                        
                        all_triples_to_insert.append(normalized)
                        total_triples += 1
                
                # Update progress
                progress = i + 1
                update_extraction_job(self.db_path, job_id, {
                    "progress": progress
                })
            
            # Batch insert all triples at once for efficiency
            if all_triples_to_insert:
                insert_extracted_triples(self.db_path, all_triples_to_insert)
            
            # Mark as completed
            update_extraction_job(self.db_path, job_id, {
                "status": "completed",
                "completed_at": self._now(),
                "results": {"total_triples": total_triples}
            })
            
            logger.info(f"Job {job_id} completed: extracted {total_triples} triples")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "total_triples": total_triples
            }
            
        except Exception as e:
            logger.error(f"Local extraction failed for job {job_id}: {e}", exc_info=True)
            update_extraction_job(self.db_path, job_id, {
                "status": "failed",
                "error_message": str(e),
                "completed_at": self._now()
            })
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            }
    
    def _extract_remote(self, job_id: int, document_ids: List[int], 
                       model_profile: str) -> Dict[str, Any]:
        """Execute extraction on remote server"""
        try:
            # Update job status
            update_extraction_job(self.db_path, job_id, {
                "status": "running",
                "started_at": self._now()
            })
            
            # Prepare request data
            documents = []
            for doc_id in document_ids:
                doc = get_document(self.db_path, doc_id)
                if doc:
                    documents.append({
                        "id": doc_id,
                        "text": doc.get("text_content", ""),
                        "metadata": {
                            "project_id": doc.get("project_id"),
                            "doi": doc.get("doi")
                        }
                    })
            
            # Call remote API
            url = f"{self.config.remote_url}/extract_triples"
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            payload = {
                "documents": documents,
                "model_profile": model_profile,
                "job_id": job_id
            }
            
            logger.info(f"Sending extraction request to {url} for job {job_id}")
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=(self.config.connection_timeout, self.config.request_timeout)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Process results
            total_triples = 0
            if result.get("triples"):
                for triple_data in result["triples"]:
                    triple_data["job_id"] = job_id
                    insert_extracted_triples(self.db_path, [triple_data])
                    total_triples += 1
            
            # Update job
            update_extraction_job(self.db_path, job_id, {
                "status": "completed",
                "completed_at": self._now(),
                "progress": len(document_ids),
                "results": {"total_triples": total_triples}
            })
            
            logger.info(f"Remote job {job_id} completed: extracted {total_triples} triples")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "total_triples": total_triples
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Remote extraction failed for job {job_id}: {e}")
            update_extraction_job(self.db_path, job_id, {
                "status": "failed",
                "error_message": f"Remote server error: {str(e)}",
                "completed_at": self._now()
            })
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in remote extraction for job {job_id}: {e}", exc_info=True)
            update_extraction_job(self.db_path, job_id, {
                "status": "failed",
                "error_message": str(e),
                "completed_at": self._now()
            })
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            }
    
    def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get the status of an extraction job"""
        return get_extraction_job(self.db_path, job_id)
    
    def list_model_profiles(self) -> List[Dict[str, Any]]:
        """List available model profiles"""
        return self.config.list_model_profiles()
    
    @staticmethod
    def _now() -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
