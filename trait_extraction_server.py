#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trait Extraction Remote Server

FastAPI server for running trait extraction on a remote GPU server.
This service handles compute-intensive NLP model inference and training.

Usage:
    uvicorn trait_extraction_server:app --host 0.0.0.0 --port 8000

With authentication:
    export TRAIT_EXTRACTION_API_KEY="your-secret-key"
    uvicorn trait_extraction_server:app --host 0.0.0.0 --port 8000
"""

import os
import logging
from typing import List, Dict, Any, Optional
import secrets
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import trait extraction modules
try:
    from trait_extraction.config import TraitExtractionConfig
    from trait_extraction.adapters.factory import AdapterManager
except ImportError:
    logger.error("Failed to import trait_extraction modules. Make sure they are in PYTHONPATH")
    raise

# Initialize FastAPI app
app = FastAPI(
    title="HARVEST Trait Extraction Server",
    description="Remote server for NLP-based trait extraction",
    version="1.0.0"
)

# Security
security = HTTPBearer(auto_error=False)
API_KEY = os.getenv("TRAIT_EXTRACTION_API_KEY")

# Initialize config and adapter manager
config = TraitExtractionConfig()
adapter_manager = AdapterManager()


# Pydantic models for request/response
class DocumentInput(BaseModel):
    """Input document for extraction"""
    id: int
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractionRequest(BaseModel):
    """Request for trait extraction"""
    documents: List[DocumentInput]
    model_profile: str
    job_id: Optional[int] = None


class ExtractionResponse(BaseModel):
    """Response from trait extraction"""
    job_id: Optional[int] = None
    status: str
    total_documents: int
    total_triples: int
    triples: List[Dict[str, Any]]


class TrainingRequest(BaseModel):
    """Request for model training"""
    model_profile: str
    training_data: List[Dict[str, Any]]
    output_dir: Optional[str] = None
    num_epochs: int = 3
    batch_size: int = 4


class TrainingResponse(BaseModel):
    """Response from model training"""
    status: str
    model_path: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ModelProfile(BaseModel):
    """Model profile information"""
    id: str
    name: str
    description: str
    backend: str


# Authentication dependency
def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Verify API key if configured"""
    if API_KEY:
        if not credentials:
            raise HTTPException(status_code=401, detail="Missing authentication")
        # Use secrets.compare_digest to prevent timing attacks
        if not secrets.compare_digest(credentials.credentials, API_KEY):
            raise HTTPException(status_code=403, detail="Invalid API key")
    return True


# Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "HARVEST Trait Extraction Server",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "loaded_adapters": adapter_manager.list_loaded()
    }


@app.get("/models", response_model=List[ModelProfile])
async def list_models(authenticated: bool = Depends(verify_api_key)):
    """List available model profiles"""
    try:
        profiles = config.list_model_profiles()
        return profiles
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract_triples", response_model=ExtractionResponse)
async def extract_triples(
    request: ExtractionRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Extract triples from documents using specified model
    
    This endpoint processes documents through the selected NLP model
    and returns extracted entity-relation triples.
    """
    try:
        logger.info(f"Extraction request for {len(request.documents)} documents using {request.model_profile}")
        
        # Get model configuration
        profile_config = config.get_model_profile(request.model_profile)
        if not profile_config:
            raise HTTPException(status_code=400, detail=f"Unknown model profile: {request.model_profile}")
        
        # Get or create adapter
        adapter = adapter_manager.get_adapter(request.model_profile, profile_config)
        
        # Load model if not loaded
        if not adapter.is_loaded:
            logger.info(f"Loading model for profile: {request.model_profile}")
            adapter.load_model()
        
        # Extract texts
        texts = [doc.text for doc in request.documents]
        
        # Run extraction
        logger.info("Running extraction...")
        results = adapter.extract_triples(texts)
        
        # Normalize and collect triples
        all_triples = []
        for doc_idx, doc_triples in enumerate(results):
            doc = request.documents[doc_idx]
            
            for raw_triple in doc_triples:
                normalized = adapter.normalize_triple(raw_triple)
                
                # Add document metadata
                normalized.update({
                    "document_id": doc.id,
                    "model_profile": request.model_profile,
                    "job_id": request.job_id,
                    "project_id": doc.metadata.get("project_id"),
                    "doi": doc.metadata.get("doi"),
                    "sentence": raw_triple.get("sentence", "")
                })
                
                all_triples.append(normalized)
        
        logger.info(f"Extraction complete: {len(all_triples)} triples extracted")
        
        return ExtractionResponse(
            job_id=request.job_id,
            status="completed",
            total_documents=len(request.documents),
            total_triples=len(all_triples),
            triples=all_triples
        )
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/train_model", response_model=TrainingResponse)
async def train_model(
    request: TrainingRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Train or fine-tune a model
    
    This endpoint trains/fine-tunes the specified model on provided data.
    """
    try:
        logger.info(f"Training request for {request.model_profile}")
        
        # Check if training is enabled
        if not config.enable_training:
            raise HTTPException(status_code=400, detail="Training is disabled")
        
        # Get model configuration
        profile_config = config.get_model_profile(request.model_profile)
        if not profile_config:
            raise HTTPException(status_code=400, detail=f"Unknown model profile: {request.model_profile}")
        
        # Get or create adapter
        adapter = adapter_manager.get_adapter(request.model_profile, profile_config)
        
        # Load model if not loaded
        if not adapter.is_loaded:
            adapter.load_model()
        
        # Run training
        logger.info("Starting training...")
        result = adapter.train(
            request.training_data,
            output_dir=request.output_dir,
            num_epochs=request.num_epochs,
            batch_size=request.batch_size
        )
        
        logger.info(f"Training complete: {result.get('status')}")
        
        return TrainingResponse(
            status=result.get("status", "unknown"),
            model_path=result.get("model_path"),
            metrics=result.get("metrics", {}),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return TrainingResponse(
            status="failed",
            error=str(e)
        )


@app.post("/unload_model")
async def unload_model(
    model_profile: str,
    authenticated: bool = Depends(verify_api_key)
):
    """Unload a model from memory"""
    try:
        adapter_manager.unload_adapter(model_profile)
        return {"status": "success", "message": f"Model {model_profile} unloaded"}
    except Exception as e:
        logger.error(f"Failed to unload model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/unload_all")
async def unload_all_models(authenticated: bool = Depends(verify_api_key)):
    """Unload all models from memory"""
    try:
        adapter_manager.unload_all()
        return {"status": "success", "message": "All models unloaded"}
    except Exception as e:
        logger.error(f"Failed to unload models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc)
    }


if __name__ == "__main__":
    # Run server
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting trait extraction server on {host}:{port}")
    if API_KEY:
        logger.info("API key authentication enabled")
    else:
        logger.warning("API key authentication disabled - set TRAIT_EXTRACTION_API_KEY to enable")
    
    uvicorn.run(app, host=host, port=port)
