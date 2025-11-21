# frontend/server_routes.py
"""
Flask server routes for HARVEST frontend.
Includes PDF proxy, ASReview proxy, highlights storage, and PDF viewer.
"""
import os
import json
import logging
import requests
from functools import lru_cache
from flask import Response, request as flask_request, render_template_string

# Import from parent frontend package  
from frontend import server, API_BASE, ASREVIEW_PROXY_FILTERED_HEADERS

logger = logging.getLogger(__name__)

# Get ASREVIEW_SERVICE_URL from environment
ASREVIEW_SERVICE_URL = os.getenv("ASREVIEW_SERVICE_URL", "")



# -----------------------
# Proxy Routes for PDF Streaming
# -----------------------
# These routes proxy PDF requests from the frontend to the internal backend (127.0.0.1:5001)
# This keeps the backend private and unexposed to remote clients
# Note: These routes are only active in "internal" deployment mode
# In "nginx" mode, the frontend makes direct requests to the backend

@lru_cache(maxsize=100)
def _validate_pdf_params(project_id: int, filename: str) -> bool:
    """
    Validate PDF request parameters with caching.
    Returns True if parameters are valid, False otherwise.
    """
    # Validate project_id is a positive integer
    if not isinstance(project_id, int) or project_id <= 0:
        return False
    
    # Validate filename: must be .pdf and no path traversal
    if not filename:
        return False
    if not filename.endswith('.pdf'):
        return False
    if '/' in filename or '\\' in filename or '..' in filename:
        return False
    
    # Filename should be a valid hash format (alphanumeric + .pdf)
    if not all(c.isalnum() or c == '.' for c in filename):
        return False
    
    return True

@server.route('/proxy/pdf/<int:project_id>/<filename>')
def proxy_pdf(project_id: int, filename: str):
    """
    Proxy route to fetch PDFs from internal backend and stream to client.
    - Validates input parameters
    - Fetches PDF from internal backend (127.0.0.1:5001)
    - Streams response with proper error handling
    - Returns 400 for invalid input, 502 for backend errors, 404 for not found

    Note: Works in all deployment modes to avoid CORS issues.
    In nginx mode, the browser requests /harvest/proxy/pdf/..., nginx strips the prefix,
    and Flask receives the request at /proxy/pdf/... which proxies to the backend.
    """
    try:
        # Validate parameters
        if not _validate_pdf_params(project_id, filename):
            return Response(
                json.dumps({"error": "Invalid project_id or filename"}),
                status=400,
                mimetype='application/json'
            )
        
        # Construct internal backend URL
        backend_url = f"{API_BASE}/api/projects/{project_id}/pdf/{filename}"
        
        # Fetch PDF from internal backend
        try:
            response = requests.get(backend_url, timeout=10, stream=True)
            
            if response.status_code == 404:
                return Response(
                    json.dumps({"error": "PDF not found"}),
                    status=404,
                    mimetype='application/json'
                )
            
            if not response.ok:
                return Response(
                    json.dumps({"error": f"Backend returned status {response.status_code}"}),
                    status=502,
                    mimetype='application/json'
                )
            
            # Stream PDF response to client
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            
            return Response(
                generate(),
                status=200,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'inline; filename="{filename}"',
                    'Cache-Control': 'public, max-age=3600'  # Cache for 1 hour
                }
            )
        
        except requests.exceptions.Timeout:
            return Response(
                json.dumps({"error": "Backend request timeout"}),
                status=502,
                mimetype='application/json'
            )
        except requests.exceptions.ConnectionError:
            return Response(
                json.dumps({"error": "Cannot connect to backend"}),
                status=502,
                mimetype='application/json'
            )
        except requests.exceptions.RequestException:
            return Response(
                json.dumps({"error": "Backend request failed"}),
                status=502,
                mimetype='application/json'
            )
    
    except Exception:
        # Catch-all for unexpected errors
        return Response(
            json.dumps({"error": "Internal server error"}),
            status=500,
            mimetype='application/json'
        )

@server.route('/pdf-viewer')
def pdf_viewer():
    """
    Serve the custom PDF viewer HTML page with highlighting capabilities.
    """
    try:
        viewer_path = os.path.join(os.path.dirname(__file__), 'assets', 'pdf_viewer.html')
        with open(viewer_path, 'r') as f:
            html_content = f.read()
        return Response(html_content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error loading PDF viewer: {e}", exc_info=True)
        return Response(
            "<html><body><h1>Error loading PDF viewer</h1><p>Please try again later.</p></body></html>",
            status=500,
            mimetype='text/html'
        )

@server.route('/proxy/highlights/<int:project_id>/<filename>', methods=['GET', 'POST', 'DELETE'])
def proxy_highlights(project_id: int, filename: str):
    """
    Proxy route for PDF highlights API to avoid CORS issues.
    Forwards GET/POST/DELETE requests to the backend API.

    Note: Works in all deployment modes to avoid CORS issues.
    In nginx mode, the browser requests /harvest/proxy/highlights/..., nginx strips the prefix,
    and Flask receives the request at /proxy/highlights/... which proxies to the backend.
    """
    try:
        # Validate parameters
        if not _validate_pdf_params(project_id, filename):
            return Response(
                json.dumps({"error": "Invalid project_id or filename"}),
                status=400,
                mimetype='application/json'
            )
        
        # Construct backend URL
        backend_url = f"{API_BASE}/api/projects/{project_id}/pdf/{filename}/highlights"
        
        # Forward the request to backend
        try:
            if flask_request.method == 'GET':
                response = requests.get(backend_url, timeout=10)
            elif flask_request.method == 'POST':
                # Get the JSON data from request
                json_data = flask_request.get_json(silent=True)
                if json_data is None:
                    return Response(
                        json.dumps({"error": "Invalid JSON in request"}),
                        status=400,
                        mimetype='application/json'
                    )
                response = requests.post(
                    backend_url,
                    json=json_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
            elif flask_request.method == 'DELETE':
                response = requests.delete(backend_url, timeout=10)
            else:
                return Response(
                    json.dumps({"error": "Method not allowed"}),
                    status=405,
                    mimetype='application/json'
                )
            
            # Return backend response
            return Response(
                response.content,
                status=response.status_code,
                mimetype='application/json'
            )
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout connecting to backend: {backend_url}")
            return Response(
                json.dumps({"error": "Backend request timeout"}),
                status=502,
                mimetype='application/json'
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to backend for highlights: {e}", exc_info=True)
            logger.error(f"Backend URL: {backend_url}, API_BASE: {API_BASE}")
            return Response(
                json.dumps({"error": "Cannot connect to backend"}),
                status=502,
                mimetype='application/json'
            )
        except Exception as e:
            logger.error(f"Error proxying highlights request: {e}", exc_info=True)
            logger.error(f"Backend URL was: {backend_url}")
            logger.error(f"Request method: {flask_request.method}")
            return Response(
                json.dumps({"error": "Backend request failed"}),
                status=502,
                mimetype='application/json'
            )
    
    except Exception as e:
        logger.error(f"Error in proxy_highlights: {e}", exc_info=True)
        return Response(
            json.dumps({"error": "Internal server error"}),
            status=500,
            mimetype='application/json'
        )


@server.route('/proxy/asreview/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_asreview(path: str):
    """
    Proxy route to forward requests to ASReview service.
    - Forwards all HTTP methods (GET, POST, PUT, DELETE)
    - Preserves request headers, body, and query parameters
    - Returns ASReview response or appropriate error
    
    This allows the frontend to access ASReview service without CORS issues,
    similar to how PDF proxy works.
    """
    try:
        # Get ASReview service URL from config
        try:
            from config import ASREVIEW_SERVICE_URL
            if not ASREVIEW_SERVICE_URL:
                return Response(
                    json.dumps({"error": "ASReview service URL not configured"}),
                    status=503,
                    mimetype='application/json'
                )
        except ImportError:
            return Response(
                json.dumps({"error": "ASReview service URL not configured"}),
                status=503,
                mimetype='application/json'
            )
        
        # Construct ASReview service URL
        asreview_url = f"{ASREVIEW_SERVICE_URL.rstrip('/')}/{path}"
        
        # Preserve query parameters
        if flask_request.query_string:
            asreview_url += f"?{flask_request.query_string.decode('utf-8')}"
        
        # Prepare headers (filter out hop-by-hop headers)
        headers = {
            key: value for key, value in flask_request.headers.items()
            if key.lower() not in ['host', 'connection', 'content-length']
        }
        
        # Forward request to ASReview service
        try:
            if flask_request.method == 'GET':
                response = requests.get(
                    asreview_url,
                    headers=headers,
                    timeout=30
                )
            elif flask_request.method == 'POST':
                response = requests.post(
                    asreview_url,
                    headers=headers,
                    data=flask_request.get_data(),
                    timeout=30
                )
            elif flask_request.method == 'PUT':
                response = requests.put(
                    asreview_url,
                    headers=headers,
                    data=flask_request.get_data(),
                    timeout=30
                )
            elif flask_request.method == 'DELETE':
                response = requests.delete(
                    asreview_url,
                    headers=headers,
                    timeout=30
                )
            else:
                return Response(
                    json.dumps({"error": "Method not allowed"}),
                    status=405,
                    mimetype='application/json'
                )
            
            # Return ASReview response with filtered headers
            # Filter out headers that can cause iframe issues or redirects
            # Keep only safe headers for proxying
            safe_headers = {}
            for key, value in response.headers.items():
                if key.lower() not in ASREVIEW_PROXY_FILTERED_HEADERS:
                    safe_headers[key] = value
            
            return Response(
                response.content,
                status=response.status_code,
                headers=safe_headers
            )
        
        except requests.exceptions.Timeout:
            logger.error(f"ASReview service timeout: {asreview_url}")
            return Response(
                json.dumps({"error": "ASReview service timeout"}),
                status=504,
                mimetype='application/json'
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to ASReview service at {asreview_url}: {e}")
            return Response(
                json.dumps({"error": f"Cannot connect to ASReview service at {ASREVIEW_SERVICE_URL}"}),
                status=502,
                mimetype='application/json'
            )
        except Exception as e:
            logger.error(f"Error forwarding request to ASReview: {e}", exc_info=True)
            return Response(
                json.dumps({"error": "ASReview proxy failed"}),
                status=502,
                mimetype='application/json'
            )
    
    except Exception as e:
        logger.error(f"Error in proxy_asreview: {e}", exc_info=True)
        return Response(
            json.dumps({"error": "Internal server error"}),
            status=500,
            mimetype='application/json'
        )


