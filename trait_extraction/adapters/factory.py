#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adapter factory and manager for trait extraction
"""

import logging
from typing import Dict, Any, Optional
from .base import BaseAdapter
from .spacy_adapter import SpacyAdapter
from .hf_adapter import HuggingFaceAdapter
from .lasuie_adapter import LasUIEAdapter
from .allennlp_adapter import AllenNLPAdapter

logger = logging.getLogger(__name__)


class AdapterFactory:
    """Factory for creating adapter instances"""
    
    _adapters = {
        "spacy": SpacyAdapter,
        "huggingface": HuggingFaceAdapter,
        "lasuie": LasUIEAdapter,
        "allennlp": AllenNLPAdapter,
    }
    
    @classmethod
    def create_adapter(cls, backend: str, config: Dict[str, Any]) -> BaseAdapter:
        """
        Create an adapter instance
        
        Args:
            backend: Backend type (spacy, huggingface, lasuie, allennlp)
            config: Configuration dictionary for the adapter
        
        Returns:
            Adapter instance
        
        Raises:
            ValueError: If backend is not supported
        """
        adapter_class = cls._adapters.get(backend.lower())
        
        if adapter_class is None:
            raise ValueError(f"Unsupported backend: {backend}. Supported: {list(cls._adapters.keys())}")
        
        logger.info(f"Creating {backend} adapter")
        return adapter_class(config)
    
    @classmethod
    def list_backends(cls) -> list:
        """List all available backends"""
        return list(cls._adapters.keys())


class AdapterManager:
    """Manager for loaded adapters (singleton pattern)"""
    
    _instance = None
    _loaded_adapters: Dict[str, BaseAdapter] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_adapter(self, profile_name: str, config: Dict[str, Any]) -> BaseAdapter:
        """
        Get or create an adapter instance
        
        Args:
            profile_name: Profile identifier
            config: Adapter configuration
        
        Returns:
            Adapter instance (reused if already loaded)
        """
        # Check if adapter already loaded
        if profile_name in self._loaded_adapters:
            logger.debug(f"Reusing loaded adapter: {profile_name}")
            return self._loaded_adapters[profile_name]
        
        # Create new adapter
        backend = config.get("backend")
        adapter = AdapterFactory.create_adapter(backend, config)
        
        # Cache it
        self._loaded_adapters[profile_name] = adapter
        logger.info(f"Cached new adapter: {profile_name}")
        
        return adapter
    
    def unload_adapter(self, profile_name: str) -> None:
        """Unload an adapter to free resources"""
        if profile_name in self._loaded_adapters:
            adapter = self._loaded_adapters[profile_name]
            adapter.unload_model()
            del self._loaded_adapters[profile_name]
            logger.info(f"Unloaded adapter: {profile_name}")
    
    def unload_all(self) -> None:
        """Unload all adapters"""
        for profile_name in list(self._loaded_adapters.keys()):
            self.unload_adapter(profile_name)
        logger.info("Unloaded all adapters")
    
    def list_loaded(self) -> list:
        """List currently loaded adapters"""
        return list(self._loaded_adapters.keys())
