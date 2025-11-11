"""
ASReview Client Module for HARVEST
Provides integration with remote ASReview service for AI-powered literature review.

ASReview (https://asreview.ai) is an active learning tool for systematic reviews.
It uses machine learning to help researchers efficiently screen papers by:
1. Learning from user decisions (relevant/irrelevant)
2. Prioritizing papers by predicted relevance
3. Reducing manual screening workload by 95%+

This module provides a client interface to communicate with a remote ASReview
service deployed on a GPU-enabled host for optimal ML performance.
"""

import logging
import requests
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ASReviewClient:
    """
    Client for interacting with remote ASReview service.
    
    The ASReview service should be deployed separately on a GPU-enabled host
    for optimal machine learning performance. This client communicates via
    REST API to create projects, upload papers, record decisions, and get
    relevance predictions.
    """
    
    def __init__(
        self, 
        service_url: Optional[str] = None,
        api_key: Optional[str] = None,
        connection_timeout: int = 10,
        request_timeout: int = 300
    ):
        """
        Initialize ASReview client.
        
        Args:
            service_url: Base URL of ASReview service (e.g., "http://asreview-host:5000")
            api_key: Optional API key for authentication
            connection_timeout: Connection timeout in seconds
            request_timeout: Request timeout in seconds for long-running operations
        """
        # Get configuration from config.py or environment
        if service_url is None:
            try:
                from config import ASREVIEW_SERVICE_URL
                service_url = ASREVIEW_SERVICE_URL
            except ImportError:
                service_url = os.getenv('ASREVIEW_SERVICE_URL', '')
        
        if api_key is None:
            try:
                from config import ASREVIEW_API_KEY
                api_key = ASREVIEW_API_KEY
            except ImportError:
                api_key = os.getenv('ASREVIEW_API_KEY', '')
        
        self.service_url = service_url.rstrip('/') if service_url else None
        self.api_key = api_key if api_key else None
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
        
        # Setup headers
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'HARVEST-ASReview-Client/1.0'
        }
        
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def is_configured(self) -> bool:
        """Check if ASReview service is properly configured."""
        return bool(self.service_url)
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check if ASReview service is available and responsive.
        
        Returns:
            Dictionary with health status information.
        """
        if not self.is_configured():
            return {
                'available': False,
                'error': 'ASReview service URL not configured'
            }
        
        try:
            response = requests.get(
                f'{self.service_url}/api/health',
                headers=self.headers,
                timeout=self.connection_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'available': True,
                    'version': data.get('version', 'unknown'),
                    'status': data.get('status', 'ok')
                }
            else:
                return {
                    'available': False,
                    'error': f'Service returned status {response.status_code}'
                }
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to ASReview service at {self.service_url}: {e}")
            return {
                'available': False,
                'error': f'Connection failed: {str(e)}'
            }
        except requests.exceptions.Timeout as e:
            logger.error(f"ASReview service health check timeout: {e}")
            return {
                'available': False,
                'error': 'Connection timeout'
            }
        except Exception as e:
            logger.error(f"ASReview health check failed: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def create_project(
        self, 
        project_name: str,
        description: str = "",
        model_type: str = "nb"
    ) -> Dict[str, Any]:
        """
        Create a new ASReview project for screening papers.
        
        Args:
            project_name: Name of the project
            description: Optional project description
            model_type: ML model type ('nb' for Naive Bayes, 'svm' for SVM, 'rf' for Random Forest)
        
        Returns:
            Dictionary with project information including project_id.
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ASReview service not configured'
            }
        
        try:
            payload = {
                'project_name': project_name,
                'description': description,
                'model_type': model_type
            }
            
            response = requests.post(
                f'{self.service_url}/api/projects',
                json=payload,
                headers=self.headers,
                timeout=self.request_timeout
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Created ASReview project: {project_name}")
                return {
                    'success': True,
                    'project_id': data.get('project_id'),
                    'project_name': project_name
                }
            else:
                error_msg = f"Failed to create project (status {response.status_code})"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"Error creating ASReview project: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_papers(
        self, 
        project_id: str,
        papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Upload papers to an ASReview project for screening.
        
        Args:
            project_id: ASReview project ID
            papers: List of paper dictionaries with title, abstract, authors, doi, etc.
        
        Returns:
            Dictionary with upload status.
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ASReview service not configured'
            }
        
        try:
            # Convert papers to ASReview format
            formatted_papers = []
            for paper in papers:
                formatted_papers.append({
                    'title': paper.get('title', ''),
                    'abstract': paper.get('abstract', ''),
                    'authors': ', '.join(paper.get('authors', [])),
                    'doi': paper.get('doi', ''),
                    'year': paper.get('year'),
                    'keywords': paper.get('keywords', ''),
                    'notes': paper.get('notes', '')
                })
            
            payload = {
                'papers': formatted_papers
            }
            
            response = requests.post(
                f'{self.service_url}/api/projects/{project_id}/data',
                json=payload,
                headers=self.headers,
                timeout=self.request_timeout
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Uploaded {len(papers)} papers to ASReview project {project_id}")
                return {
                    'success': True,
                    'uploaded_count': len(papers),
                    'message': data.get('message', 'Papers uploaded successfully')
                }
            else:
                error_msg = f"Failed to upload papers (status {response.status_code})"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"Error uploading papers to ASReview: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def start_review(
        self, 
        project_id: str,
        prior_relevant: Optional[List[str]] = None,
        prior_irrelevant: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Start the active learning review process.
        
        Args:
            project_id: ASReview project ID
            prior_relevant: Optional list of DOIs known to be relevant (for initial training)
            prior_irrelevant: Optional list of DOIs known to be irrelevant (for initial training)
        
        Returns:
            Dictionary with status of review initialization.
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ASReview service not configured'
            }
        
        try:
            payload = {
                'prior_relevant': prior_relevant or [],
                'prior_irrelevant': prior_irrelevant or []
            }
            
            response = requests.post(
                f'{self.service_url}/api/projects/{project_id}/start',
                json=payload,
                headers=self.headers,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Started ASReview for project {project_id}")
                return {
                    'success': True,
                    'message': data.get('message', 'Review started successfully')
                }
            else:
                error_msg = f"Failed to start review (status {response.status_code})"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"Error starting ASReview: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_next_paper(self, project_id: str) -> Dict[str, Any]:
        """
        Get the next paper to review based on active learning predictions.
        
        Args:
            project_id: ASReview project ID
        
        Returns:
            Dictionary with next paper information.
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ASReview service not configured'
            }
        
        try:
            response = requests.get(
                f'{self.service_url}/api/projects/{project_id}/next',
                headers=self.headers,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'paper': data.get('paper'),
                    'relevance_score': data.get('relevance_score'),
                    'progress': data.get('progress')
                }
            elif response.status_code == 404:
                # No more papers to review
                return {
                    'success': True,
                    'paper': None,
                    'message': 'Review complete - no more papers to screen'
                }
            else:
                error_msg = f"Failed to get next paper (status {response.status_code})"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"Error getting next paper from ASReview: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def record_decision(
        self, 
        project_id: str,
        paper_id: str,
        relevant: bool,
        note: str = ""
    ) -> Dict[str, Any]:
        """
        Record a screening decision for a paper.
        
        This trains the active learning model and updates predictions.
        
        Args:
            project_id: ASReview project ID
            paper_id: Paper identifier (DOI or internal ID)
            relevant: True if paper is relevant, False if irrelevant
            note: Optional note about the decision
        
        Returns:
            Dictionary with status of recorded decision.
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ASReview service not configured'
            }
        
        try:
            payload = {
                'paper_id': paper_id,
                'relevant': relevant,
                'note': note
            }
            
            response = requests.post(
                f'{self.service_url}/api/projects/{project_id}/record',
                json=payload,
                headers=self.headers,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Recorded decision for paper {paper_id}: relevant={relevant}")
                return {
                    'success': True,
                    'message': data.get('message', 'Decision recorded'),
                    'model_updated': data.get('model_updated', True)
                }
            else:
                error_msg = f"Failed to record decision (status {response.status_code})"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"Error recording decision in ASReview: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_progress(self, project_id: str) -> Dict[str, Any]:
        """
        Get review progress statistics.
        
        Args:
            project_id: ASReview project ID
        
        Returns:
            Dictionary with progress information.
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ASReview service not configured'
            }
        
        try:
            response = requests.get(
                f'{self.service_url}/api/projects/{project_id}/progress',
                headers=self.headers,
                timeout=self.connection_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'total_papers': data.get('total_papers', 0),
                    'reviewed_papers': data.get('reviewed_papers', 0),
                    'relevant_papers': data.get('relevant_papers', 0),
                    'irrelevant_papers': data.get('irrelevant_papers', 0),
                    'progress_percent': data.get('progress_percent', 0),
                    'estimated_remaining': data.get('estimated_remaining', 0)
                }
            else:
                error_msg = f"Failed to get progress (status {response.status_code})"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"Error getting progress from ASReview: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_results(self, project_id: str) -> Dict[str, Any]:
        """
        Export review results (relevant papers).
        
        Args:
            project_id: ASReview project ID
        
        Returns:
            Dictionary with list of relevant papers.
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'ASReview service not configured'
            }
        
        try:
            response = requests.get(
                f'{self.service_url}/api/projects/{project_id}/export',
                headers=self.headers,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Exported results from ASReview project {project_id}")
                return {
                    'success': True,
                    'relevant_papers': data.get('relevant_papers', []),
                    'irrelevant_papers': data.get('irrelevant_papers', []),
                    'export_format': data.get('format', 'json')
                }
            else:
                error_msg = f"Failed to export results (status {response.status_code})"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"Error exporting results from ASReview: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
_asreview_client = None


def get_asreview_client() -> ASReviewClient:
    """
    Get or create singleton ASReview client instance.
    
    Returns:
        ASReviewClient instance
    """
    global _asreview_client
    if _asreview_client is None:
        _asreview_client = ASReviewClient()
    return _asreview_client
