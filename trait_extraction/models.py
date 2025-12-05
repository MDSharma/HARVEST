#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data models for Trait Extraction Module
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class JobStatus(str, Enum):
    """Status of an extraction job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExtractionMode(str, Enum):
    """Mode of extraction"""
    NO_TRAINING = "no_training"
    TRAINING_ASSISTED = "training_assisted"
    WARM_START = "warm_start"


class TripleStatus(str, Enum):
    """Status of an extracted triple"""
    RAW = "raw"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


@dataclass
class Document:
    """Represents a document for trait extraction"""
    id: Optional[int] = None
    project_id: Optional[int] = None
    file_path: str = ""
    text_content: str = ""
    doi: Optional[str] = None
    doi_hash: Optional[str] = None
    status: str = "pending"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "text_content": self.text_content,
            "doi": self.doi,
            "doi_hash": self.doi_hash,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class ExtractionJob:
    """Represents a trait extraction job"""
    id: Optional[int] = None
    project_id: Optional[int] = None
    document_ids: List[int] = field(default_factory=list)
    model_profile: str = "lasuie"
    mode: str = ExtractionMode.NO_TRAINING.value
    status: str = JobStatus.PENDING.value
    progress: int = 0
    total: int = 0
    error_message: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "document_ids": self.document_ids,
            "model_profile": self.model_profile,
            "mode": self.mode,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "error_message": self.error_message,
            "results": self.results,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


@dataclass
class ExtractedTriple:
    """Represents an extracted triple from text"""
    id: Optional[int] = None
    document_id: Optional[int] = None
    job_id: Optional[int] = None
    sentence_id: Optional[int] = None
    
    # Triple components (following HARVEST schema)
    source_entity_name: str = ""
    source_entity_attr: str = ""
    relation_type: str = ""
    sink_entity_name: str = ""
    sink_entity_attr: str = ""
    
    # Extraction metadata
    model_profile: str = ""
    confidence: float = 0.0
    status: str = TripleStatus.RAW.value
    
    # Additional trait-specific fields
    trait_name: Optional[str] = None
    trait_value: Optional[str] = None
    unit: Optional[str] = None
    
    # Provenance
    project_id: Optional[int] = None
    contributor_email: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "job_id": self.job_id,
            "sentence_id": self.sentence_id,
            "source_entity_name": self.source_entity_name,
            "source_entity_attr": self.source_entity_attr,
            "relation_type": self.relation_type,
            "sink_entity_name": self.sink_entity_name,
            "sink_entity_attr": self.sink_entity_attr,
            "model_profile": self.model_profile,
            "confidence": self.confidence,
            "status": self.status,
            "trait_name": self.trait_name,
            "trait_value": self.trait_value,
            "unit": self.unit,
            "project_id": self.project_id,
            "contributor_email": self.contributor_email,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedTriple":
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
