# frontend/callbacks.py
"""
All Dash callbacks for HARVEST frontend.
This module registers all interactive callbacks for the application.
TODO: Split into domain-specific modules (dashboard, annotation, admin, literature, etc.)
"""
import os
import json
import hashlib
import requests
import base64
import time
import logging
import threading
import re
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict

from dash import Input, Output, State, MATCH, ALL, ctx, no_update, dcc, html, dash_table
import dash_bootstrap_components as dbc

# Import from parent frontend package
from frontend import (
    app, server, markdown_cache,
    API_BASE, API_CHOICES, API_SAVE, API_RECENT,
    API_VALIDATE_DOI, API_ADMIN_AUTH, API_PROJECTS, API_ADMIN_PROJECTS,
    API_ADMIN_TRIPLE, API_BROWSE_FIELDS, API_ADMIN_BROWSE_FIELDS,
    SCHEMA_JSON, OTHER_SENTINEL, EMAIL_HASH_SALT,
    ENABLE_LITERATURE_SEARCH, ENABLE_PDF_HIGHLIGHTING, ENABLE_LITERATURE_REVIEW,
    DASH_REQUESTS_PATHNAME_PREFIX, PORT, ASREVIEW_SERVICE_URL,
    ENABLE_DEBUG_LOGGING
)

# Import layout utilities
from frontend.layout import (
    create_execution_log_display,
    triple_row,
    build_entity_options,
    build_relation_options
)

# Import literature search module
import literature_search

# Import PDF storage configuration and utilities
try:
    from config import PDF_STORAGE_DIR
except ImportError:
    PDF_STORAGE_DIR = "project_pdfs"

# Import PDF manager utilities for DOI hash generation
try:
    from pdf_manager import generate_doi_hash, get_project_pdf_dir
except ImportError:
    # Fallback implementations if pdf_manager is not available
    def generate_doi_hash(doi: str) -> str:
        """Generate a hash from DOI for file naming"""
        return hashlib.sha256(doi.encode('utf-8')).hexdigest()[:16]
    
    def get_project_pdf_dir(project_id: int, base_dir: str = "project_pdfs") -> str:
        """Get the directory path for a project's PDFs"""
        return os.path.join(base_dir, f"project_{project_id}")

logger = logging.getLogger(__name__)

# Configure logging level based on debug setting
if ENABLE_DEBUG_LOGGING:
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.debug("DEBUG LOGGING ENABLED - This will generate verbose logs!")

DEFAULT_BROWSE_FIELDS = [
    "project_id",
    "sentence_id",
    "sentence",
    "source_entity_name",
    "source_entity_attr",
    "relation_type",
    "sink_entity_name",
    "sink_entity_attr",
    "triple_id",
]
ALLOWED_BROWSE_FIELDS = {
    "sentence_id",
    "triple_id",
    "project_id",
    "doi",
    "doi_hash",
    "literature_link",
    "relation_type",
    "source_entity_name",
    "source_entity_attr",
    "sink_entity_name",
    "sink_entity_attr",
    "sentence",
    "triple_contributor",
}

# Rate limiting state for data fetches
_last_fetch_times = {
    "recent_data": 0,
}
_fetch_lock = threading.Lock()
FETCH_COOLDOWN_SECONDS = 2

# Helper constant
NO_UPDATE_15 = tuple([no_update] * 15)


# -----------------------
# Helper Functions
# -----------------------

def _create_paper_card(paper: Dict, index: int) -> dbc.Card:
    """
    Create a paper card component with badges, metadata, and abstract displayed side-by-side.
    
    Args:
        paper: Paper dictionary with title, authors, year, doi, citations, etc.
        index: Display index for the paper (1-based)
    
    Returns:
        dbc.Card component for the paper
    """
    # Format authors
    authors_text = ", ".join(paper.get('authors', [])[:3])
    if len(paper.get('authors', [])) > 3:
        authors_text += " et al."

    # Format year
    year_text = str(paper.get('year', 'N/A'))
    
    # Get citation count
    citations = paper.get('citations', 0)

    # Format DOI link
    doi = paper.get('doi', '')
    if doi:
        if doi.startswith('arXiv:'):
            arxiv_id = doi.replace('arXiv:', '')
            doi_link = html.A(
                doi,
                href=f"https://arxiv.org/abs/{arxiv_id}",
                target="_blank",
                className="text-decoration-none"
            )
        elif doi.startswith('WOS:'):
            doi_link = html.Span(doi, className="text-muted font-monospace", style={"fontSize": "0.85rem"})
        elif doi.startswith('OpenAlex:'):
            doi_link = html.Span(doi, className="text-muted font-monospace", style={"fontSize": "0.85rem"})
        else:
            doi_link = html.A(
                doi,
                href=f"https://doi.org/{doi}",
                target="_blank",
                className="text-decoration-none"
            )
    else:
        doi_link = html.Span("N/A", className="text-muted")
    
    # Source badge with color coding
    source = paper.get('source', 'N/A')
    source_colors = {
        'Semantic Scholar': 'primary',
        'arXiv': 'success',
        'Web of Science': 'info',
        'OpenAlex': 'warning'
    }
    source_badge = dbc.Badge(
        source,
        color=source_colors.get(source, 'secondary'),
        className="me-2",
        pill=True
    )
    
    # Citation badge (only if > 0)
    citation_badge = None
    if citations > 0:
        # Color code by citation count
        if citations >= 100:
            citation_color = "danger"  # High impact
        elif citations >= 50:
            citation_color = "warning"  # Medium-high impact
        elif citations >= 10:
            citation_color = "info"  # Medium impact
        else:
            citation_color = "secondary"  # Low impact
        
        citation_badge = dbc.Badge(
            f"📊 {citations} citations",
            color=citation_color,
            className="me-2",
            pill=True
        )
    
    # Year badge
    year_badge = dbc.Badge(
        f"📅 {year_text}",
        color="light",
        text_color="dark",
        className="me-2",
        pill=True
    )
    
    # Open access badge (if available)
    open_access_badge = None
    if paper.get('is_open_access'):
        open_access_badge = dbc.Badge(
            "🔓 Open Access",
            color="success",
            className="me-2",
            pill=True,
            title="This paper is freely available"
        )

    # Create paper card with two-column layout: metadata on left, abstract on right
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            # Left column: Checkbox and metadata
                            dbc.Col(
                                [
                                    # Top row with checkbox and title
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Checkbox(
                                                        id={"type": "paper-checkbox", "index": index},
                                                        className="form-check-input-lg",
                                                        value=False,
                                                    ),
                                                ],
                                                width="auto",
                                                className="d-flex align-items-start pt-1",
                                            ),
                                            dbc.Col(
                                                [
                                                    # Title with rank number
                                                    html.Div(
                                                        [
                                                            dbc.Badge(
                                                                f"#{index}",
                                                                color="secondary",
                                                                className="me-2",
                                                                pill=True
                                                            ),
                                                            html.Span(
                                                                paper.get('title', 'N/A'),
                                                                style={"fontWeight": "600", "fontSize": "1.05rem"}
                                                            )
                                                        ],
                                                        className="mb-2"
                                                    ),
                                                    # Badges row
                                                    html.Div(
                                                        [
                                                            source_badge,
                                                            year_badge,
                                                            citation_badge if citation_badge else None,
                                                            open_access_badge if open_access_badge else None,
                                                        ],
                                                        className="mb-2"
                                                    ),
                                                    # Metadata section with improved styling
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                [
                                                                    html.I(className="bi bi-people-fill me-2", style={"color": "#6c757d"}),
                                                                    html.Span(authors_text, style={"fontSize": "0.9rem"}),
                                                                ],
                                                                className="mb-1"
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.I(className="bi bi-link-45deg me-2", style={"color": "#6c757d"}),
                                                                    doi_link,
                                                                ],
                                                                className="mb-2"
                                                            ),
                                                        ],
                                                        style={"fontSize": "0.9rem", "color": "#495057"}
                                                    ),
                                                ],
                                            ),
                                        ],
                                        className="g-2",
                                    ),
                                ],
                                md=6,
                                className="border-end",
                            ),
                            # Right column: Abstract
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.I(className="bi bi-file-text me-2", style={"color": "#6c757d"}),
                                            html.Strong("Abstract", style={"fontSize": "0.95rem"})
                                        ],
                                        className="mb-2"
                                    ),
                                    html.P(
                                        paper.get('abstract_snippet', 'No abstract available'),
                                        className="mb-0",
                                        style={
                                            "fontSize": "0.85rem", 
                                            "lineHeight": "1.6",
                                            "color": "#495057",
                                            "maxHeight": "200px",
                                            "overflowY": "auto"
                                        }
                                    ),
                                ],
                                md=6,
                                className="ps-3",
                            ),
                        ],
                        className="g-0",
                    ),
                ]
            )
        ],
        className="mb-3 shadow-sm",
        style={
            "borderLeft": "4px solid #007bff",
            "transition": "box-shadow 0.2s ease-in-out"
        }
    )


# -----------------------
# Callbacks
# -----------------------

# Email validation callback
@app.callback(
    Output("email-validation", "children"),
    Output("email-validation", "style"),
    Output("email-store", "data"),
    Input("contributor-email", "value"),
)
def validate_email(email):
    if not email or not email.strip():
        return "Email is required to attribute your contributions", {"color": "red"}, None

    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email.strip()):
        return "Valid email", {"color": "green"}, email.strip()
    else:
        return "Please enter a valid email address", {"color": "red"}, None

# Note: Removed restore_email callback to prevent circular dependency
# The email-store serves as validation state, not as a persistent storage for the input field


# OTP Email Verification Callbacks
@app.callback(
    Output("otp-verification-section", "style"),
    Output("otp-verification-store", "data"),
    Output("email-validation", "children", allow_duplicate=True),
    Output("email-validation", "style", allow_duplicate=True),
    Output("contributor-email", "value", allow_duplicate=True),
    Output("contributor-email", "disabled", allow_duplicate=True),
    Input("email-store", "data"),
    State("otp-session-store", "data"),
    prevent_initial_call=True
)
def request_otp_code(email, session_data):
    """
    Request OTP code when email is validated.
    Check if OTP validation is enabled first.
    """
    # Check if OTP is enabled
    try:
        config_response = requests.get(f"{API_BASE}/api/email-verification/config")
        if not config_response.ok or not config_response.json().get("enabled"):
            # OTP not enabled, keep section hidden
            return {"display": "none"}, None, "", {}, no_update, no_update
    except:
        # API error, keep section hidden
        return {"display": "none"}, None, "", {}, no_update, no_update
    
    # Check if already verified
    if session_data and session_data.get("session_id"):
        # Check session validity
        try:
            check_response = requests.post(
                f"{API_BASE}/api/email-verification/check-session",
                json={"session_id": session_data["session_id"]}
            )
            if check_response.ok and check_response.json().get("verified"):
                # Already verified, keep section hidden and lock email field
                verified_email = check_response.json().get("email")
                return {"display": "none"}, session_data, "✓ Email verified", {"color": "green"}, verified_email, True
        except:
            pass
    
    if not email:
        return {"display": "none"}, None, "", {}, no_update, no_update
    
    # Request OTP code
    try:
        response = requests.post(
            f"{API_BASE}/api/email-verification/request-code",
            json={"email": email}
        )
        
        if response.ok:
            return (
                {"display": "block"},  # Show OTP section
                {"email": email, "code_requested": True},
                "Verification code sent to your email",
                {"color": "blue"},
                no_update,
                no_update
            )
        else:
            try:
                error = response.json().get("error", "Failed to send code")
            except json.JSONDecodeError:
                error = f"HTTP {response.status_code}: Failed to send code"
            return (
                {"display": "none"},
                None,
                f"Error: {error}",
                {"color": "red"},
                no_update,
                no_update
            )
    except Exception as e:
        return (
            {"display": "none"},
            None,
            f"Error requesting code: {str(e)}",
            {"color": "red"},
            no_update,
            no_update
        )


@app.callback(
    Output("otp-verify-button", "disabled"),
    Input("otp-code-input", "value"),
)
def enable_verify_button(code):
    """Enable verify button when code is 6 digits."""
    if code and len(code) == 6 and code.isdigit():
        return False
    return True


@app.callback(
    Output("otp-verification-feedback", "children"),
    Output("otp-session-store", "data"),
    Output("email-validation", "children", allow_duplicate=True),
    Output("email-validation", "style", allow_duplicate=True),
    Output("otp-verification-section", "style", allow_duplicate=True),
    Output("contributor-email", "value", allow_duplicate=True),
    Output("contributor-email", "disabled", allow_duplicate=True),
    Input("otp-verify-button", "n_clicks"),
    State("otp-code-input", "value"),
    State("otp-verification-store", "data"),
    prevent_initial_call=True
)
def verify_otp_code(n_clicks, code, otp_data):
    """Verify OTP code and create session."""
    if not n_clicks or not code or not otp_data:
        return "", None, "", {}, {"display": "block"}, no_update, no_update
    
    email = otp_data.get("email")
    if not email:
        return (
            dbc.Alert("Error: Email not found", color="danger", dismissable=True, duration=4000),
            None,
            "",
            {},
            {"display": "block"},
            no_update,
            no_update
        )
    
    try:
        response = requests.post(
            f"{API_BASE}/api/email-verification/verify-code",
            json={"email": email, "code": code}
        )
        
        if response.ok:
            data = response.json()
            session_id = data.get("session_id")
            
            return (
                dbc.Alert("✓ Email verified successfully!", color="success", dismissable=True, duration=3000),
                {"session_id": session_id, "email": email},
                "✓ Email verified",
                {"color": "green"},
                {"display": "none"},  # Hide OTP section
                email,  # Set the verified email in the field
                True  # Disable the email field
            )
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", "Invalid code")
                
                if error_data.get("expired"):
                    error_msg = "Code expired. Please request a new code."
                elif error_data.get("attempts_exceeded"):
                    error_msg = "Too many attempts. Please request a new code."
            except json.JSONDecodeError:
                error_msg = f"HTTP {response.status_code}: Invalid code"
            
            return (
                dbc.Alert(error_msg, color="danger", dismissable=True, duration=4000),
                None,
                "",
                {},
                {"display": "block"},
                no_update,
                no_update
            )
    except Exception as e:
        return (
            dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True, duration=4000),
            None,
            "",
            {},
            {"display": "block"},
            no_update,
            no_update
        )


@app.callback(
    Output("contributor-email", "value"),
    Output("contributor-email", "disabled"),
    Input("otp-session-store", "data"),
    prevent_initial_call=True
)
def populate_verified_email(otp_session):
    """
    Auto-populate and lock the email field when OTP is verified.
    This prevents users from changing to an unverified email address.
    """
    if otp_session and otp_session.get("session_id") and otp_session.get("email"):
        # Verify session is still valid
        try:
            check_response = requests.post(
                f"{API_BASE}/api/email-verification/check-session",
                json={"session_id": otp_session["session_id"]}
            )
            if check_response.ok and check_response.json().get("verified"):
                verified_email = check_response.json().get("email")
                return verified_email, True  # Set email and disable field
        except:
            pass
    
    # Not verified or session invalid - clear email and leave field editable
    return "", False


@app.callback(
    Output("annotator-id-display", "children"),
    Input("contributor-email", "value"),
    prevent_initial_call=False,
)
def show_annotator_id(email_value):
    """Display hashed annotator ID when email is present/verified."""
    if not email_value:
        return ""
    annotator_id = hashlib.sha256((EMAIL_HASH_SALT + email_value).encode()).hexdigest()[:16]
    return f"Annotator ID: {annotator_id}"


@app.callback(
    Output("otp-verification-feedback", "children", allow_duplicate=True),
    Input("otp-resend-button", "n_clicks"),
    State("otp-verification-store", "data"),
    prevent_initial_call=True
)
def resend_otp_code(n_clicks, otp_data):
    """Resend OTP code."""
    if not n_clicks or not otp_data:
        return ""
    
    email = otp_data.get("email")
    if not email:
        return dbc.Alert("Error: Email not found", color="danger", dismissable=True, duration=4000)
    
    try:
        response = requests.post(
            f"{API_BASE}/api/email-verification/request-code",
            json={"email": email}
        )
        
        if response.ok:
            return dbc.Alert(
                "New code sent to your email",
                color="info",
                dismissable=True,
                duration=3000
            )
        else:
            try:
                error = response.json().get("error", "Failed to send code")
            except json.JSONDecodeError:
                error = f"HTTP {response.status_code}: Failed to send code"
            return dbc.Alert(error, color="danger", dismissable=True, duration=4000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True, duration=4000)


# Literature Search Authentication check - use Admin panel auth
@app.callback(
    Output("lit-search-auth-required", "style"),
    Output("lit-search-content", "style"),
    Input("admin-auth-store", "data"),
    prevent_initial_call=False,
)
def check_lit_search_auth(auth_data):
    """Check if user is authenticated via Admin panel and show/hide Literature Search content"""
    if auth_data and ("email" in auth_data or "token" in auth_data):
        # User is authenticated, show search content and hide auth required message
        return {"display": "none"}, {"display": "block"}
    else:
        # User not authenticated, show auth required message and hide search content
        return {"display": "block"}, {"display": "none"}


# Literature Review Authentication check - use Admin panel auth
@app.callback(
    Output("lit-review-auth-required", "style"),
    Output("lit-review-auth-content", "style"),
    Input("admin-auth-store", "data"),
    prevent_initial_call=False,
)
def check_lit_review_auth(auth_data):
    """Check if user is authenticated via Admin panel and show/hide Literature Review content"""
    if auth_data and ("email" in auth_data or "token" in auth_data):
        # User is authenticated, show review content and hide auth required message
        return {"display": "none"}, {"display": "block"}
    else:
        # User not authenticated, show auth required message and hide review content
        return {"display": "block"}, {"display": "none"}


# Literature Search callback
@app.callback(
    Output("search-status", "children"),
    Output("search-results", "children"),
    Output("lit-search-selected-papers", "data"),
    Output("lit-search-export-controls", "style"),
    Output("lit-search-session-papers", "data"),
    Output("all-papers-data", "data"),
    Output("pagination-state", "data"),
    Output("pagination-controls", "style"),
    Output("pagination-info", "children"),
    Output("btn-prev-page", "disabled"),
    Output("btn-next-page", "disabled"),
    Input("btn-search-papers", "n_clicks"),
    State("lit-search-query", "value"),
    State("lit-search-sources", "value"),
    State("lit-search-pipeline-controls", "value"),
    State("lit-search-build-session", "value"),
    State("lit-search-session-papers", "data"),
    State("lit-search-top-k", "value"),
    State("limit-semantic-scholar", "value"),
    State("limit-arxiv", "value"),
    State("limit-wos", "value"),
    State("limit-openalex", "value"),
    prevent_initial_call=True,
)
def perform_literature_search(n_clicks, query, sources, pipeline_controls, build_session, session_papers, 
                              top_k, s2_limit, arxiv_limit, wos_limit, openalex_limit):
    """
    Callback to perform literature search when button is clicked.
    Displays the execution pipeline for AutoResearch, DeepResearch, and DELM.
    Supports multiple sources, session-based cumulative searching, pipeline controls,
    and per-source result limits.
    
    Note: The search runs synchronously and displays results upon completion.
    For true real-time progress updates during execution, the implementation would need:
    - Background task processing (e.g., Celery, Redis Queue)
    - WebSocket or Server-Sent Events for live updates
    - State management for in-progress searches
    Currently, users see a loading spinner during search, then full results with
    execution timing details when complete. For typical searches (5-10s), this is
    a reasonable user experience.
    """
    if not query or not query.strip():
        return (
            dbc.Alert("Please enter a search query", color="warning"),
            None,
            [],
            {"display": "none"},
            session_papers or [],
            [],
            {},  # pagination_state
            {"display": "none"},  # pagination-controls style
            None,  # pagination-info
            True,  # prev button disabled
            True   # next button disabled
        )
    
    if not sources:
        return (
            dbc.Alert("Please select at least one search source", color="warning"),
            None,
            [],
            {"display": "none"},
            session_papers or [],
            [],
            {},  # pagination_state
            {"display": "none"},  # pagination-controls style
            None,  # pagination-info
            True,  # prev button disabled
            True   # next button disabled
        )

    try:
        # Prepare previous papers for session build
        previous_papers = None
        if build_session and session_papers:
            previous_papers = session_papers
        
        # Parse pipeline controls
        pipeline_controls = pipeline_controls or []
        enable_query_expansion = "query_expansion" in pipeline_controls
        enable_deduplication = "deduplication" in pipeline_controls
        enable_reranking = "reranking" in pipeline_controls
        
        # Validate and set top_k
        if not top_k or top_k < 1:
            top_k = 20
        top_k = min(top_k, 100)  # Cap at 100
        
        # Build per-source limit dictionary
        per_source_limit = {}
        if s2_limit and s2_limit > 0:
            per_source_limit['semantic_scholar'] = min(s2_limit, 100)
        if arxiv_limit and arxiv_limit > 0:
            per_source_limit['arxiv'] = min(arxiv_limit, 100)
        if wos_limit and wos_limit > 0:
            per_source_limit['web_of_science'] = min(wos_limit, 100)
        if openalex_limit and openalex_limit > 0:
            per_source_limit['openalex'] = min(openalex_limit, 200)
        
        # Perform search with selected sources and pipeline controls
        result = literature_search.search_papers(
            query.strip(), 
            top_k=top_k,
            sources=sources,
            previous_papers=previous_papers,
            enable_query_expansion=enable_query_expansion,
            enable_deduplication=enable_deduplication,
            enable_reranking=enable_reranking,
            per_source_limit=per_source_limit if per_source_limit else None
        )

        if not result['success']:
            # Show execution log even on failure
            execution_log = result.get('execution_log', [])
            if execution_log:
                log_display = create_execution_log_display(execution_log)
                return (
                    html.Div([
                        dbc.Alert(result['message'], color="danger"),
                        log_display
                    ]),
                    None,
                    [],
                    {"display": "none"},
                    session_papers or [],
                    [],
                    {},  # pagination_state
                    {"display": "none"},  # pagination-controls style
                    None,  # pagination-info
                    True,  # prev button disabled
                    True   # next button disabled
                )
            return (
                dbc.Alert(result['message'], color="danger"),
                None,
                [],
                {"display": "none"},
                session_papers or [],
                [],
                {},  # pagination_state
                {"display": "none"},  # pagination-controls style
                None,  # pagination-info
                True,  # prev button disabled
                True   # next button disabled
            )

        papers = result['papers']

        if not papers:
            return (
                dbc.Alert("No papers found. Try a different query or different sources.", color="info"),
                None,
                [],
                {"display": "none"},
                session_papers or [],
                [],
                {},  # pagination_state
                {"display": "none"},  # pagination-controls style
                None,  # pagination-info
                True,  # prev button disabled
                True   # next button disabled
            )

        # Store all unique papers from session
        new_session_papers = result.get('all_session_papers', papers)

        # Create execution log display
        execution_log = result.get('execution_log', [])
        log_display = create_execution_log_display(execution_log)
        
        # Create sources info
        sources_used = result.get('sources_used', [])
        sources_display = ', '.join([
            {'semantic_scholar': 'Semantic Scholar', 'arxiv': 'arXiv', 'web_of_science': 'Web of Science', 'openalex': 'OpenAlex'}.get(s, s)
            for s in sources_used
        ])

        # Create status message with execution log
        status = html.Div([
            dbc.Alert(
                [
                    html.Strong(result['message']),
                    html.Br(),
                    html.Small(f"Sources: {sources_display}"),
                    html.Br(),
                    html.Small(f"Total found: {result['total_found']} | Unique: {result['total_unique']} | Displaying: {result['returned']}")
                ],
                color="success"
            ),
            log_display
        ])

        # Store paper data for later use
        papers_data = []
        
        # Create results table using helper function
        results_content = []

        for i, paper in enumerate(papers, 1):
            # Store paper data including DOI
            papers_data.append({
                'index': i,
                'doi': paper.get('doi', ''),
                'title': paper.get('title', 'N/A'),
                'authors': paper.get('authors', []),
                'year': paper.get('year', 'N/A'),
                'source': paper.get('source', 'N/A'),
                'citations': paper.get('citations', 0),
                'is_open_access': paper.get('is_open_access', False),
                'abstract_snippet': paper.get('abstract_snippet', '')
            })
            
            # Create paper card using helper function
            paper_card = _create_paper_card(paper, i)
            results_content.append(paper_card)

        # Initialize pagination state for new search
        pagination_state = {
            'current_page': {'web_of_science': 1, 'openalex': 1},
            'total_results': {},
            'last_query': query,
            'last_sources': sources
        }
        
        # Check if pagination is available
        pageable_sources = [s for s in sources if s in ['web_of_science', 'openalex']]
        has_pagination = len(pageable_sources) > 0
        
        # Pagination info - show if pagination is available
        pagination_info = None
        if has_pagination:
            pagination_info = html.Div([
                html.Small([
                    f"Showing {len(papers)} results (Page 1)",
                    html.Br(),
                    f"Click 'Load Next Page' to fetch more results from {', '.join([s.replace('_', ' ').title() for s in pageable_sources])}"
                ], className="text-muted")
            ])
        
        return (
            status,
            html.Div(results_content),
            papers_data,
            {"display": "block"},
            new_session_papers,
            papers,
            pagination_state,
            {"display": "block"} if has_pagination else {"display": "none"},
            pagination_info,
            True,  # prev button disabled on first page
            False if has_pagination else True  # next button enabled if pagination available
        )

    except Exception as e:
        logger.error(f"Literature search error: {e}")
        return (
            dbc.Alert(f"Search failed: {str(e)}", color="danger"),
            None,
            [],
            {"display": "none"},
            session_papers or [],
            [],
            {},  # pagination_state
            {"display": "none"},  # pagination-controls style
            None,  # pagination-info
            True,  # prev button disabled
            True   # next button disabled
        )


# Callback to clear search session
@app.callback(
    Output("lit-search-session-papers", "data", allow_duplicate=True),
    Output("search-status", "children", allow_duplicate=True),
    Input("btn-clear-session", "n_clicks"),
    prevent_initial_call=True,
)
def clear_search_session(n_clicks):
    """Clear the search session history"""
    return [], dbc.Alert("Search session cleared", color="info", duration=3000)


# Callback for sorting and filtering search results
@app.callback(
    Output("search-results", "children", allow_duplicate=True),
    Input("result-sort-by", "value"),
    Input("result-filter-source", "value"),
    State("all-papers-data", "data"),
    prevent_initial_call=True,
)
def sort_and_filter_results(sort_by, filter_source, all_papers):
    """
    Sort and filter the displayed search results without re-running the search.
    Provides instant client-side filtering and sorting for better UX.
    """
    if not all_papers:
        return no_update
    
    # Filter by source
    filtered_papers = all_papers
    if filter_source and filter_source != "all":
        filtered_papers = [p for p in all_papers if p.get('source') == filter_source]
    
    # Sort papers
    if sort_by == "citations_desc":
        filtered_papers = sorted(filtered_papers, key=lambda x: x.get('citations', 0), reverse=True)
    elif sort_by == "year_desc":
        # Sort by year, treating None/missing as -1 (very old) so they appear at the bottom when sorting newest first
        filtered_papers = sorted(filtered_papers, key=lambda x: x.get('year') if x.get('year') is not None else -1, reverse=True)
    elif sort_by == "year_asc":
        # Sort by year, treating None/missing as -1 (very old) so they appear at the top when sorting oldest first
        filtered_papers = sorted(filtered_papers, key=lambda x: x.get('year') if x.get('year') is not None else -1)
    # else: keep relevance order (original search order)
    
    # Re-render the paper cards with new order using helper function
    results_content = []
    for i, paper in enumerate(filtered_papers, 1):
        paper_card = _create_paper_card(paper, i)
        results_content.append(paper_card)
    
    if not results_content:
        return html.Div(
            dbc.Alert("No papers match the selected filters.", color="info", className="text-center"),
            className="mt-3"
        )
    
    return html.Div(results_content)


# Callback for pagination (load more results)
@app.callback(
    Output("search-status", "children", allow_duplicate=True),
    Output("search-results", "children", allow_duplicate=True),
    Output("all-papers-data", "data", allow_duplicate=True),
    Output("lit-search-session-papers", "data", allow_duplicate=True),
    Output("pagination-state", "data", allow_duplicate=True),
    Output("pagination-controls", "style", allow_duplicate=True),
    Output("pagination-info", "children", allow_duplicate=True),
    Output("btn-prev-page", "disabled", allow_duplicate=True),
    Output("btn-next-page", "disabled", allow_duplicate=True),
    Input("btn-next-page", "n_clicks"),
    Input("btn-prev-page", "n_clicks"),
    State("lit-search-query", "value"),
    State("lit-search-sources", "value"),
    State("lit-search-pipeline-controls", "value"),
    State("limit-wos", "value"),
    State("limit-openalex", "value"),
    State("all-papers-data", "data"),
    State("lit-search-session-papers", "data"),
    State("pagination-state", "data"),
    prevent_initial_call=True,
)
def handle_pagination(next_clicks, prev_clicks, query, sources, pipeline_controls, 
                     wos_limit, openalex_limit, all_papers, session_papers, pagination_state):
    """
    Handle pagination button clicks to load additional pages from OpenAlex and Web of Science.
    Results accumulate with deduplication applied.
    """
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Only handle pagination for sources that support it
    pageable_sources = [s for s in (sources or []) if s in ['web_of_science', 'openalex']]
    if not pageable_sources:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    try:
        # Initialize or retrieve pagination state
        if not pagination_state:
            pagination_state = {
                'current_page': {},
                'total_results': {},
                'last_query': query,
                'last_sources': sources
            }
        
        # Check if query or sources changed - if so, this is a new search, don't paginate
        if pagination_state.get('last_query') != query or pagination_state.get('last_sources') != sources:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        # Determine which source to paginate based on which sources are selected
        # For simplicity, we'll paginate the first available pageable source
        source_to_paginate = pageable_sources[0] if pageable_sources else None
        if not source_to_paginate:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        # Get current page for this source
        current_page = pagination_state.get('current_page', {}).get(source_to_paginate, 1)
        
        # Update page number based on button clicked
        if triggered_id == "btn-next-page":
            new_page = current_page + 1
        elif triggered_id == "btn-prev-page":
            new_page = max(1, current_page - 1)
        else:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        # Fetch new page of results
        new_papers = []
        if source_to_paginate == 'web_of_science':
            limit = wos_limit if wos_limit and wos_limit > 0 else 100
            result = literature_search.search_web_of_science(query, limit=min(limit, 100), page=new_page)
            if isinstance(result, dict):
                new_papers = result.get('papers', [])
                pagination_state['total_results']['web_of_science'] = result.get('total_results', 0)
        elif source_to_paginate == 'openalex':
            limit = openalex_limit if openalex_limit and openalex_limit > 0 else 200
            contact_email = literature_search._get_contact_email()
            result = literature_search.search_openalex(query, limit=min(limit, 200), page=new_page, contact_email=contact_email)
            if isinstance(result, dict):
                new_papers = result.get('papers', [])
                pagination_state['total_results']['openalex'] = result.get('total_results', 0)
        
        if not new_papers:
            # No more results available
            status_msg = dbc.Alert(f"No more results available from {source_to_paginate.replace('_', ' ').title()}.", 
                                  color="info", duration=3000)
            return status_msg, no_update, no_update, no_update, pagination_state, no_update, no_update, no_update, no_update
        
        # Combine with existing papers and deduplicate
        combined_papers = (all_papers or []) + new_papers
        
        # Parse pipeline controls
        pipeline_controls = pipeline_controls or []
        enable_deduplication = "deduplication" in pipeline_controls
        
        # Deduplicate if enabled
        if enable_deduplication:
            unique_papers = literature_search.deduplicate_papers(combined_papers)
        else:
            unique_papers = combined_papers
        
        # Update pagination state
        pagination_state['current_page'][source_to_paginate] = new_page
        
        # Calculate pagination info
        total_results = pagination_state.get('total_results', {}).get(source_to_paginate, 0)
        current_count = len(unique_papers)
        
        # Determine if there are more pages
        per_page = 100 if source_to_paginate == 'web_of_science' else 200
        has_more = current_count < total_results and new_page * per_page < total_results
        
        # Create pagination info display
        pagination_info = html.Div([
            html.Small([
                f"Showing {current_count} results from {source_to_paginate.replace('_', ' ').title()}",
                html.Br(),
                f"(Total available: {total_results}, Page {new_page})"
            ], className="text-muted")
        ])
        
        # Render results
        results_content = []
        for i, paper in enumerate(unique_papers, 1):
            paper_card = _create_paper_card(paper, i)
            results_content.append(paper_card)
        
        # Update session papers
        new_session_papers = unique_papers
        
        # Status message
        status_msg = dbc.Alert(
            f"Loaded page {new_page} from {source_to_paginate.replace('_', ' ').title()} "
            f"({len(new_papers)} new papers, {current_count} total after deduplication)",
            color="success", duration=4000
        )
        
        # Determine button states
        prev_disabled = new_page <= 1
        next_disabled = not has_more
        
        return (
            status_msg,
            html.Div(results_content),
            unique_papers,
            new_session_papers,
            pagination_state,
            {"display": "block"} if total_results > 0 else {"display": "none"},
            pagination_info,
            prev_disabled,
            next_disabled
        )
        
    except Exception as e:
        logger.error(f"Pagination error: {e}", exc_info=True)
        return (
            dbc.Alert(f"Pagination failed: {str(e)}", color="danger"),
            no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        )


# Callback to show/hide WoS syntax help modal
@app.callback(
    Output("wos-syntax-help-modal", "is_open"),
    Input("wos-syntax-help-link", "n_clicks"),
    Input("wos-syntax-help-close", "n_clicks"),
    State("wos-syntax-help-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_wos_syntax_help(link_clicks, close_clicks, is_open):
    """Toggle the WoS advanced syntax help modal"""
    return not is_open


# Callback to display source availability info
@app.callback(
    Output("lit-search-sources-info", "children"),
    Input("load-trigger", "n_intervals"),
    prevent_initial_call=False,
)
def update_source_info(n_intervals):
    """Display information about available search sources"""
    try:
        sources_info = literature_search.get_available_sources()
        
        info_parts = []
        for source_key, source_data in sources_info.items():
            if source_data['available']:
                info_parts.append(f"✓ {source_data['name']}")
            else:
                info_parts.append(f"✗ {source_data['name']} (unavailable)")
        
        info_text = " | ".join(info_parts)
        
        # Add WoS API key hint if not available
        if not sources_info['web_of_science']['available']:
            info_text += " | Set WOS_API_KEY in config.py or environment variable to enable Web of Science"
        
        return info_text
    except Exception as e:
        logger.error(f"Error getting source info: {e}")
        return "Source availability check failed"


# Callback for pipeline execution flow collapse
@app.callback(
    Output("pipeline-collapse", "is_open"),
    Output("pipeline-chevron", "className"),
    Input("pipeline-collapse-button", "n_clicks"),
    State("pipeline-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_pipeline_collapse(n_clicks, is_open):
    """Toggle the pipeline execution flow card"""
    if n_clicks:
        new_state = not is_open
        chevron_class = "bi bi-chevron-down" if new_state else "bi bi-chevron-right"
        return new_state, chevron_class + " " + "text-muted" + " " + "float-end"
    return is_open, "bi bi-chevron-right text-muted float-end"


# Callbacks for selecting/deselecting all papers
@app.callback(
    Output({"type": "paper-checkbox", "index": ALL}, "value"),
    Input("btn-select-all-papers", "n_clicks"),
    Input("btn-deselect-all-papers", "n_clicks"),
    State("lit-search-selected-papers", "data"),
    prevent_initial_call=True,
)
def select_deselect_all_papers(select_clicks, deselect_clicks, papers_data):
    """Select or deselect all paper checkboxes"""
    if not papers_data:
        return []
    
    trigger = ctx.triggered_id
    if trigger == "btn-select-all-papers":
        return [True] * len(papers_data)
    elif trigger == "btn-deselect-all-papers":
        return [False] * len(papers_data)
    return no_update


# Update selected paper count and enable/disable export button
@app.callback(
    Output("selected-papers-count", "children"),
    Output("btn-export-selected-dois", "disabled"),
    Input({"type": "paper-checkbox", "index": ALL}, "value"),
    State("lit-search-selected-papers", "data"),
    State("admin-auth-store", "data"),
    prevent_initial_call=False,
)
def update_selected_count(checkbox_values, papers_data, auth_data):
    """Update the count of selected papers and enable/disable export button"""
    if not checkbox_values or not papers_data:
        return "", True
    
    selected_count = sum(1 for v in checkbox_values if v)
    
    if selected_count == 0:
        return html.Small("No papers selected", className="text-muted"), True
    
    # Check if user is authenticated
    is_authenticated = auth_data is not None
    button_disabled = not is_authenticated
    
    count_text = f"Selected: {selected_count} paper(s)"
    if not is_authenticated:
        count_text += " - Login required to export"
    
    return html.Small(count_text, className="text-info"), button_disabled


# Open export modal and populate selected DOIs
@app.callback(
    Output("export-doi-modal", "is_open"),
    Output("export-selected-dois-list", "children"),
    Output("export-target-project", "options"),
    Input("btn-export-selected-dois", "n_clicks"),
    Input("export-doi-cancel", "n_clicks"),
    Input("export-doi-confirm", "n_clicks"),
    State("export-doi-modal", "is_open"),
    State({"type": "paper-checkbox", "index": ALL}, "value"),
    State("lit-search-selected-papers", "data"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def toggle_export_modal(export_clicks, cancel_clicks, confirm_clicks, is_open, 
                       checkbox_values, papers_data, auth_data):
    """Toggle export modal and populate with selected DOIs"""
    trigger = ctx.triggered_id
    
    if trigger == "btn-export-selected-dois":
        if not auth_data:
            return False, None, []
        
        # Get selected papers
        selected_papers = [
            paper for i, paper in enumerate(papers_data)
            if i < len(checkbox_values) and checkbox_values[i]
        ]
        
        if not selected_papers:
            return False, None, []
        
        # Create DOI list display with warnings for non-DOI identifiers
        doi_list_items = []
        valid_doi_count = 0
        invalid_identifier_count = 0
        
        for paper in selected_papers:
            doi = paper.get('doi', 'N/A')
            title = paper.get('title', 'N/A')
            
            # Check if it's a valid DOI or just an identifier
            is_valid_doi = doi and doi != 'N/A' and not doi.startswith('WOS:') and not doi.startswith('OpenAlex:')
            
            if is_valid_doi:
                valid_doi_count += 1
                doi_list_items.append(
                    html.Li([
                        html.Strong(doi),
                        html.Br(),
                        html.Small(title, className="text-muted")
                    ])
                )
            else:
                invalid_identifier_count += 1
                doi_list_items.append(
                    html.Li([
                        html.Strong(doi, style={"color": "#dc3545"}),
                        html.Span(" (not a DOI - will be skipped)", className="small text-danger"),
                        html.Br(),
                        html.Small(title, className="text-muted")
                    ])
                )
        
        # Build display with warning if needed
        display_parts = []
        
        if invalid_identifier_count > 0:
            display_parts.append(
                dbc.Alert([
                    html.I(className="bi bi-exclamation-triangle-fill me-2"),
                    html.Strong(f"Warning: {invalid_identifier_count} paper(s) without valid DOIs will be skipped"),
                    html.Br(),
                    html.Small("Only papers with real DOIs can be added to projects")
                ], color="warning", className="mb-2")
            )
        
        display_parts.extend([
            html.H6(f"Selected papers ({len(selected_papers)} total, {valid_doi_count} with valid DOIs):"),
            html.Ul(doi_list_items, style={"maxHeight": "200px", "overflowY": "auto"})
        ])
        
        doi_list_display = html.Div(display_parts)
        
        # Get projects for dropdown
        try:
            r = requests.get(API_PROJECTS, timeout=5)
            if r.ok:
                projects = r.json()
                project_options = [{"label": p["name"], "value": p["id"]} for p in projects]
            else:
                project_options = []
        except:
            project_options = []
        
        return True, doi_list_display, project_options
    
    elif trigger in ["export-doi-cancel", "export-doi-confirm"]:
        return False, None, []
    
    return is_open, None, []


# Toggle between new project and existing project fields
@app.callback(
    Output("export-new-project-fields", "style"),
    Output("export-existing-project-fields", "style"),
    Input("export-doi-action", "value"),
    prevent_initial_call=False,
)
def toggle_export_fields(action):
    """Show/hide fields based on export action"""
    if action == "new":
        return {"display": "block"}, {"display": "none"}
    elif action == "existing":
        return {"display": "none"}, {"display": "block"}
    else:  # clipboard
        return {"display": "none"}, {"display": "none"}


# Handle export confirmation
@app.callback(
    Output("export-doi-message", "children"),
    Input("export-doi-confirm", "n_clicks"),
    State("export-doi-action", "value"),
    State("export-new-project-name", "value"),
    State("export-new-project-description", "value"),
    State("export-target-project", "value"),
    State({"type": "paper-checkbox", "index": ALL}, "value"),
    State("lit-search-selected-papers", "data"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def handle_export_confirmation(n_clicks, action, new_name, new_desc, target_project_id,
                               checkbox_values, papers_data, auth_data):
    """Handle the export confirmation based on selected action"""
    if not auth_data:
        return dbc.Alert("Authentication required", color="danger")
    
    # Get selected DOIs and filter out non-DOI identifiers
    selected_dois = []
    skipped_identifiers = []
    
    for i, paper in enumerate(papers_data):
        if i < len(checkbox_values) and checkbox_values[i]:
            doi = paper.get('doi', '')
            if doi:
                # Skip WOS: and OpenAlex: identifiers - only accept real DOIs
                if doi.startswith('WOS:') or doi.startswith('OpenAlex:'):
                    skipped_identifiers.append(doi)
                else:
                    selected_dois.append(doi)
    
    if not selected_dois:
        if skipped_identifiers:
            return dbc.Alert([
                html.Strong("No valid DOIs to export"),
                html.Br(),
                html.Small(f"Skipped {len(skipped_identifiers)} identifier(s) without real DOIs: {', '.join(skipped_identifiers[:3])}{'...' if len(skipped_identifiers) > 3 else ''}")
            ], color="warning")
        return dbc.Alert("No DOIs to export", color="warning")
    
    # Normalize DOIs (lowercase, remove URL prefixes)
    normalized_dois = []
    for doi in selected_dois:
        # Remove URL prefixes
        doi_clean = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        # Convert to lowercase
        doi_clean = doi_clean.strip().lower()
        if doi_clean:
            normalized_dois.append(doi_clean)
    
    # Validate DOIs via CrossRef API before adding to project
    try:
        validation_payload = {
            "email": auth_data["email"],
            "password": auth_data["password"],
            "dois": normalized_dois
        }
        val_response = requests.post(
            f"{API_BASE}/api/admin/validate-dois", 
            json=validation_payload, 
            timeout=30
        )
        
        if val_response.ok:
            validation_result = val_response.json()
            valid_dois = validation_result.get("valid", [])
            invalid_dois = validation_result.get("invalid", [])
            
            if not valid_dois:
                invalid_msg = ", ".join([f"{inv['doi']} ({inv['reason']})" for inv in invalid_dois[:3]])
                if len(invalid_dois) > 3:
                    invalid_msg += "..."
                return dbc.Alert([
                    html.Strong("All DOIs failed validation"),
                    html.Br(),
                    html.Small(f"Invalid DOIs: {invalid_msg}")
                ], color="danger")
            
            # Use only valid DOIs
            selected_dois = valid_dois
            
            # Show warning if some DOIs were invalid
            validation_warning = None
            if invalid_dois:
                validation_warning = html.Div([
                    html.Strong(f"Note: {len(invalid_dois)} DOI(s) failed validation and were skipped"),
                    html.Br(),
                    html.Small(", ".join([f"{inv['doi']}" for inv in invalid_dois[:3]]) + ("..." if len(invalid_dois) > 3 else ""))
                ], className="text-warning small mb-2")
        else:
            # If validation endpoint fails, proceed with normalized DOIs
            # but show a warning
            logger.warning(f"DOI validation failed: {val_response.status_code}")
            validation_warning = html.Div([
                html.Strong("Warning: Could not validate DOIs via CrossRef"),
                html.Br(),
                html.Small("Proceeding with normalized DOIs without validation")
            ], className="text-warning small mb-2")
    except Exception as e:
        logger.error(f"DOI validation error: {e}")
        # Proceed with normalized DOIs but show warning
        validation_warning = html.Div([
            html.Strong("Warning: Could not validate DOIs via CrossRef"),
            html.Br(),
            html.Small(f"Error: {str(e)}")
        ], className="text-warning small mb-2")
    
    # Handle clipboard action
    if action == "clipboard":
        doi_text = "\n".join(selected_dois)
        result_parts = [html.Strong("Copy these DOIs:")]
        if validation_warning:
            result_parts.append(html.Br())
            result_parts.append(validation_warning)
        result_parts.append(html.Pre(doi_text, style={"marginTop": "10px", "padding": "10px", "backgroundColor": "#f8f9fa"}))
        return dbc.Alert(result_parts, color="info")
    
    # Handle new project creation
    if action == "new":
        if not new_name or not new_name.strip():
            return dbc.Alert("Project name is required", color="warning")
        
        try:
            payload = {
                "email": auth_data["email"],
                "password": auth_data["password"],
                "name": new_name.strip(),
                "description": new_desc.strip() if new_desc else "",
                "doi_list": selected_dois
            }
            r = requests.post(f"{API_BASE}/api/admin/projects", json=payload, timeout=10)
            if r.ok:
                result = r.json()
                if result.get("ok"):
                    result_parts = [f"Project created successfully! ID: {result.get('project_id')}"]
                    if validation_warning:
                        result_parts = [validation_warning, html.Br(), html.Span(result_parts[0])]
                    return dbc.Alert(result_parts, color="success")
                else:
                    return dbc.Alert(f"Failed: {result.get('error', 'Unknown error')}", color="danger")
            else:
                return dbc.Alert(f"Failed: {r.status_code}", color="danger")
        except Exception as e:
            return dbc.Alert(f"Error: {str(e)}", color="danger")
    
    # Handle adding to existing project
    if action == "existing":
        if not target_project_id:
            return dbc.Alert("Please select a target project", color="warning")
        
        try:
            # First, get the existing project
            r = requests.get(f"{API_BASE}/api/projects/{target_project_id}", timeout=5)
            if not r.ok:
                return dbc.Alert("Failed to fetch project", color="danger")
            
            project = r.json()
            existing_dois = set(project.get("doi_list", []))
            
            # Deduplicate: only add DOIs that don't exist
            new_dois = [doi for doi in selected_dois if doi not in existing_dois]
            duplicates = len(selected_dois) - len(new_dois)
            
            if not new_dois:
                return dbc.Alert(f"All {len(selected_dois)} DOI(s) already exist in the project", color="info")
            
            # Merge DOI lists
            merged_dois = list(existing_dois) + new_dois
            
            # Update project
            payload = {
                "email": auth_data["email"],
                "password": auth_data["password"],
                "doi_list": merged_dois
            }
            r = requests.put(f"{API_BASE}/api/admin/projects/{target_project_id}", json=payload, timeout=10)
            if r.ok:
                result = r.json()
                if result.get("ok"):
                    msg_parts = [f"Added {len(new_dois)} new DOI(s) to project"]
                    if duplicates > 0:
                        msg_parts.append(f" ({duplicates} duplicate(s) skipped)")
                    if validation_warning:
                        msg_parts = [validation_warning, html.Br(), html.Span("".join(msg_parts))]
                    return dbc.Alert(msg_parts, color="success")
                else:
                    return dbc.Alert(f"Failed: {result.get('error', 'Unknown error')}", color="danger")
            else:
                return dbc.Alert(f"Failed: {r.status_code}", color="danger")
        except Exception as e:
            return dbc.Alert(f"Error: {str(e)}", color="danger")
    
    return no_update


# Helper function to create DOI metadata card and store data
def create_doi_metadata_card_and_data(doi, metadata):
    """
    Create metadata card and data structure for a validated DOI.
    
    Args:
        doi: The validated DOI string
        metadata: Dictionary with title, authors, year
        
    Returns:
        tuple: (metadata_card, metadata_data_dict)
    """
    metadata_card = dbc.Alert(
        [
            html.H6("Article Metadata Retrieved:", className="alert-heading"),
            html.Hr(),
            html.P([html.Strong("DOI: "), doi]),
            html.P([html.Strong("Title: "), metadata.get("title", "N/A")]),
            html.P([html.Strong("Authors: "), metadata.get("authors", "N/A")]),
            html.P([html.Strong("Year: "), metadata.get("year", "N/A")], className="mb-0"),
        ],
        color="success",
        className="mb-2",
    )
    
    metadata_data = {
        "doi": doi,
        "title": metadata.get("title", ""),
        "authors": metadata.get("authors", ""),
        "year": metadata.get("year", ""),
    }
    
    return metadata_card, metadata_data


def validate_doi_internal(doi_input):
    """
    Internal helper function to validate a DOI and retrieve metadata.
    
    Args:
        doi_input: DOI string to validate
        
    Returns:
        tuple: (success, validation_message, validation_style, metadata_card, metadata_card_style, metadata_data)
        - success: boolean indicating if validation was successful
        - validation_message: string message to display
        - validation_style: dict with CSS style for validation message
        - metadata_card: Dash component with metadata display or None
        - metadata_card_style: dict with CSS style for metadata card
        - metadata_data: dict with metadata or None
    """
    if not doi_input or not doi_input.strip():
        return (
            False,
            "Please enter a DOI",
            {"color": "red"},
            None,
            {"display": "none"},
            None
        )

    try:
        r = requests.post(API_VALIDATE_DOI, json={"doi": doi_input}, timeout=15)
        if r.ok:
            result = r.json()
            if result.get("valid"):
                metadata = result.get("metadata", {})
                doi = result.get("doi", "")

                metadata_card, metadata_data = create_doi_metadata_card_and_data(doi, metadata)

                return (
                    True,
                    "Valid DOI - metadata retrieved",
                    {"color": "green"},
                    metadata_card,
                    {"display": "block"},
                    metadata_data
                )
            else:
                error_msg = result.get("error", "Invalid DOI")
                return (
                    False,
                    error_msg,
                    {"color": "red"},
                    None,
                    {"display": "none"},
                    None
                )
        else:
            return (
                False,
                f"Validation failed: {r.status_code}",
                {"color": "red"},
                None,
                {"display": "none"},
                None
            )
    except requests.exceptions.Timeout:
        # Log error type for debugging without exposing DOI
        logger.warning("DOI validation request timed out")
        return (
            False,
            "Validation request timed out",
            {"color": "red"},
            None,
            {"display": "none"},
            None
        )
    except requests.exceptions.RequestException as e:
        # Log error type for debugging without exposing DOI or internal details
        logger.warning(f"DOI validation request failed: {type(e).__name__}")
        return (
            False,
            "Validation service unavailable",
            {"color": "red"},
            None,
            {"display": "none"},
            None
        )
    except Exception as e:
        # Log error type for debugging without exposing internal details
        logger.error(f"Unexpected error during DOI validation: {type(e).__name__}")
        return (
            False,
            "An error occurred during validation",
            {"color": "red"},
            None,
            {"display": "none"},
            None
        )

# DOI validation callback
@app.callback(
    Output("doi-validation", "children"),
    Output("doi-validation", "style"),
    Output("doi-metadata-display", "children"),
    Output("doi-metadata-display", "style"),
    Output("doi-metadata-store", "data"),
    Input("btn-validate-doi", "n_clicks"),
    State("literature-link", "value"),
    prevent_initial_call=True,
)
def validate_doi(n_clicks, doi_input):
    # Use internal helper function for validation
    success, msg, style, card, card_style, data = validate_doi_internal(doi_input)
    return msg, style, card, card_style, data

# Load choices once (try backend; fallback to local schema)
@app.callback(
    Output("choices-store", "data"),
    Input("load-trigger", "n_intervals"),
    prevent_initial_call=False,
)
def load_choices(_):
    try:
        r = requests.get(API_CHOICES, timeout=5)
        if r.ok:
            data = r.json()
            entity_types = data.get("entity_types") or list(SCHEMA_JSON["span-attribute"].keys())
            relation_types = data.get("relation_types") or list(SCHEMA_JSON["relation-type"].keys())
        else:
            entity_types = list(SCHEMA_JSON["span-attribute"].keys())
            relation_types = list(SCHEMA_JSON["relation-type"].keys())
    except Exception as e:
        print(f"Failed to load choices from API: {e}")
        entity_types = list(SCHEMA_JSON["span-attribute"].keys())
        relation_types = list(SCHEMA_JSON["relation-type"].keys())

    return {
        "entity_options": [{"label": k, "value": k} for k in entity_types] + [{"label": "Other…", "value": OTHER_SENTINEL}],
        "relation_options": [{"label": k, "value": k} for k in relation_types] + [{"label": "Other…", "value": OTHER_SENTINEL}],
    }

# Populate triple editor dropdown options
@app.callback(
    Output("edit-src-attr", "options"),
    Output("edit-rel-type", "options"),
    Output("edit-sink-attr", "options"),
    Input("choices-store", "data"),
    prevent_initial_call=False,
)
def populate_triple_editor_dropdowns(choices_data):
    if not choices_data:
        entity_options = [{"label": k, "value": k} for k in SCHEMA_JSON["span-attribute"].keys()]
        relation_options = [{"label": k, "value": k} for k in SCHEMA_JSON["relation-type"].keys()]
    else:
        entity_options = choices_data["entity_options"]
        relation_options = choices_data["relation_options"]
    
    return entity_options, relation_options, entity_options

# Add/remove triple rows
@app.callback(
    Output("triple-count", "data"),
    Input("btn-add-triple", "n_clicks"),
    Input("btn-remove-triple", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    State("triple-count", "data"),
    prevent_initial_call=True,
)
def modify_triple_count(add_clicks, remove_clicks, reset_clicks, current_count):
    trigger = ctx.triggered_id
    count = current_count or 1
    if trigger == "btn-add-triple":
        return count + 1
    elif trigger == "btn-remove-triple":
        return max(1, count - 1)
    elif trigger == "btn-reset":
        return 1
    return count

# Render triple rows whenever count or choices change
@app.callback(
    Output("triples-container", "children"),
    Input("triple-count", "data"),
    Input("choices-store", "data"),
)
def render_triple_rows(count, choices_data):
    if not choices_data:
        entity_options = build_entity_options(SCHEMA_JSON)
        relation_options = build_relation_options(SCHEMA_JSON)
    else:
        entity_options = choices_data["entity_options"]
        relation_options = choices_data["relation_options"]

    rows = [triple_row(i, entity_options, relation_options) for i in range(count or 1)]
    return rows

# Show/hide "Other…" inputs for Source Attr
@app.callback(
    Output({"type": "src-attr-other-div", "index": ALL}, "style"),
    Input({"type": "src-attr", "index": ALL}, "value"),
)
def toggle_src_other(values):
    styles = []
    for v in values:
        styles.append({"display": "block"} if v == OTHER_SENTINEL else {"display": "none"})
    return styles

# Show/hide "Other…" inputs for Relation
@app.callback(
    Output({"type": "rel-type-other-div", "index": ALL}, "style"),
    Input({"type": "rel-type", "index": ALL}, "value"),
)
def toggle_rel_other(values):
    styles = []
    for v in values:
        styles.append({"display": "block"} if v == OTHER_SENTINEL else {"display": "none"})
    return styles

# Show/hide "Other…" inputs for Sink Attr
@app.callback(
    Output({"type": "sink-attr-other-div", "index": ALL}, "style"),
    Input({"type": "sink-attr", "index": ALL}, "value"),
)
def toggle_sink_other(values):
    styles = []
    for v in values:
        styles.append({"display": "block"} if v == OTHER_SENTINEL else {"display": "none"})
    return styles

# Save handler
@app.callback(
    Output("save-message", "children"),
    Input("btn-save", "n_clicks"),
    State("sentence-text", "value"),
    State("literature-link", "value"),
    State("contributor-email", "value"),
    State("email-store", "data"),
    State("otp-session-store", "data"),  # NEW: Check verified session
    State("doi-metadata-store", "data"),
    State("project-selector", "value"),  # Add project selector
    State({"type": "src-name", "index": ALL}, "value"),
    State({"type": "src-attr", "index": ALL}, "value"),
    State({"type": "src-attr-other", "index": ALL}, "value"),
    State({"type": "rel-type", "index": ALL}, "value"),
    State({"type": "rel-type-other", "index": ALL}, "value"),
    State({"type": "sink-name", "index": ALL}, "value"),
    State({"type": "sink-attr", "index": ALL}, "value"),
    State({"type": "sink-attr-other", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def save_triples(n_clicks, sentence_text, literature_link, contributor_email, email_validated,
                otp_session,  # NEW: OTP session parameter
                doi_metadata, project_id,  # Add project_id parameter
                src_names, src_attrs, src_other,
                rel_types, rel_other,
                sink_names, sink_attrs, sink_other):
    if not sentence_text or not sentence_text.strip():
        return dbc.Alert("Sentence is required.", color="danger", dismissable=True, duration=4000)

    if not email_validated:
        return dbc.Alert("Please enter a valid email address.", color="danger", dismissable=True, duration=4000)

    # NEW: Check OTP verification if enabled
    try:
        config_response = requests.get(f"{API_BASE}/api/email-verification/config")
        if config_response.ok and config_response.json().get("enabled"):
            # OTP is enabled, check verification
            if not otp_session or not otp_session.get("session_id"):
                return dbc.Alert(
                    "Please verify your email address before submitting annotations.",
                    color="warning",
                    dismissable=True,
                    duration=6000
                )
            
            # Verify session is still valid
            check_response = requests.post(
                f"{API_BASE}/api/email-verification/check-session",
                json={"session_id": otp_session["session_id"]}
            )
            
            if not check_response.ok or not check_response.json().get("verified"):
                return dbc.Alert(
                    "Your verification session has expired. Please verify your email again.",
                    color="warning",
                    dismissable=True,
                    duration=6000
                )
            
            # Use verified email from session
            email_validated = check_response.json().get("email")
    except Exception as e:
        # If OTP check fails, block submission and notify user
        logger.error(f"OTP verification check failed, blocking submission: {e}")
        return dbc.Alert(
            "Could not verify your email session. Please try again.",
            color="danger",
            dismissable=True,
            duration=6000
        )

    num_rows = max(
        len(src_names or []),
        len(src_attrs or []),
        len(rel_types or []),
        len(sink_names or []),
        len(sink_attrs or []),
    )

    triples = []
    for i in range(num_rows):
        src_name = (src_names or [""] * num_rows)[i] or ""
        src_attr_val = (src_attrs or [""] * num_rows)[i] or ""
        src_attr_final = (src_other or [""] * num_rows)[i] if src_attr_val == OTHER_SENTINEL else src_attr_val

        rel_val = (rel_types or [""] * num_rows)[i] or ""
        rel_final = (rel_other or [""] * num_rows)[i] if rel_val == OTHER_SENTINEL else rel_val

        sink_name = (sink_names or [""] * num_rows)[i] or ""
        sink_attr_val = (sink_attrs or [""] * num_rows)[i] or ""
        sink_attr_final = (sink_other or [""] * num_rows)[i] if sink_attr_val == OTHER_SENTINEL else sink_attr_val

        # Minimal validation: require src_name, relation, sink_name
        if src_name and rel_final and sink_name:
            triples.append(
                {
                    "source_entity_name": src_name,
                    "source_entity_attr": src_attr_final,
                    "relation_type": rel_final,
                    "sink_entity_name": sink_name,
                    "sink_entity_attr": sink_attr_final,
                }
            )

    if not triples:
        return dbc.Alert("At least one complete triple is required (source, relation, sink).", color="danger", dismissable=True, duration=4000)

    payload = {
        "sentence": sentence_text.strip(),
        "literature_link": (literature_link or "").strip(),
        "contributor_email": email_validated,
        "triples": triples,
    }

    if doi_metadata:
        payload["doi"] = doi_metadata.get("doi", "")
    
    # Add project_id if a project is selected
    if project_id:
        payload["project_id"] = project_id

    try:
        print(f"Saving payload: {json.dumps(payload, indent=2)}")
        r = requests.post(API_SAVE, json=payload, timeout=10)
        print(f"Response status: {r.status_code}")
        print(f"Response text: {r.text}")
        if r.ok:
            try:
                resp = r.json()
            except Exception as parse_err:
                print(f"Failed to parse response: {parse_err}")
                resp = {}
            new_id = resp.get("sentence_id") or resp.get("id") or "(unknown)"
            num_triples = len(triples)
            return dbc.Alert(
                f"Saved successfully! Sentence ID: {new_id}, Triples saved: {num_triples}",
                color="success",
                dismissable=True,
                duration=4000
            )
        else:
            error_msg = r.text[:500]
            return dbc.Alert(f"Save failed: {r.status_code} - {error_msg}", color="danger", dismissable=True, duration=8000)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Save error: {str(e)}", color="danger", dismissable=True, duration=8000)

# Populate browse project filter
@app.callback(
    Output("browse-project-filter", "options"),
    Input("load-trigger", "n_intervals"),
    Input("btn-refresh", "n_clicks"),
    Input("main-tabs", "value"),
    prevent_initial_call=False,
)
def populate_browse_project_filter(load_trigger, refresh_click, tab_value):
    try:
        r = requests.get(API_PROJECTS, timeout=5)
        if r.ok:
            projects = r.json()
            options = [{"label": "All (no filter)", "value": None}] + [{"label": p["name"], "value": p["id"]} for p in projects]
            return options
        else:
            return [{"label": "All (no filter)", "value": None}]
    except Exception:
        return [{"label": "All (no filter)", "value": None}]

# Browse recent
@app.callback(
    Output("recent-table", "children"),
    Input("btn-refresh", "n_clicks"),
    Input("load-trigger", "n_intervals"),
    Input("main-tabs", "value"),
    State("browse-project-filter", "value"),
    State("browse-contributor-filter", "value"),
    State("browse-field-config", "data"),
    State("admin-auth-store", "data"),
    prevent_initial_call=False,
)
def refresh_recent(btn_clicks, interval_trigger, tab_value, project_filter, contributor_filter, visible_fields, admin_auth):
    # Only refresh if Browse tab is active
    if tab_value != "tab-browse" and ctx.triggered_id == "main-tabs":
        return no_update
    
    # Use default fields if none configured
    if not visible_fields:
        visible_fields = DEFAULT_BROWSE_FIELDS
    else:
        visible_fields = [f for f in visible_fields if f in ALLOWED_BROWSE_FIELDS] or DEFAULT_BROWSE_FIELDS
    
    # Rate limiting: check if enough time has passed since last fetch
    # Allow manual refresh button to bypass cooldown
    # Use thread-safe lock for multi-user scenarios
    current_time = time.time()
    should_fetch = True
    
    with _fetch_lock:
        time_since_last_fetch = current_time - _last_fetch_times["recent_data"]
        
        if ctx.triggered_id != "btn-refresh" and time_since_last_fetch < FETCH_COOLDOWN_SECONDS:
            # Too soon since last fetch, skip this request
            should_fetch = False
        else:
            # Update last fetch time
            _last_fetch_times["recent_data"] = current_time
    
    if not should_fetch:
        return no_update
    
    try:
        print(f"Fetching recent data from {API_RECENT}")
        # Add project_id and contributor filters if selected
        params = []
        if project_filter:
            params.append(f"project_id={project_filter}")
        if contributor_filter:
            params.append(f"triple_contributor={contributor_filter}")
        url = API_RECENT if not params else f\"{API_RECENT}?{'&'.join(params)}\"
        
        r = requests.get(url, timeout=8)
        print(f"Response status: {r.status_code}")
        if not r.ok:
            error_text = r.text[:500]
            return dbc.Alert(f"Failed to load recent entries: {r.status_code} - {error_text}", color="danger")
        data = r.json()
        print(f"Received {len(data)} rows")

        if isinstance(data, dict):
            if "error" in data:
                return dbc.Alert(f"API Error: {data['error']}", color="danger")
            rows = data.get("items", [])
        else:
            rows = data

        if not rows:
            return dbc.Alert("No records found. Try adding some data first!", color="info")

        # Hash email addresses for privacy using installation-specific salt
        is_admin = bool(admin_auth and (admin_auth.get("email") or admin_auth.get("token")))
        for row in rows:
            if is_admin:
                continue
            # Hash the 'email' field if present (legacy field name)
            if 'email' in row and row['email']:
                row['email'] = hashlib.sha256((EMAIL_HASH_SALT + row['email']).encode()).hexdigest()[:16] + '...'
            # Hash the 'triple_contributor' field (actual field name from backend)
            if 'triple_contributor' in row and row['triple_contributor']:
                row['triple_contributor'] = hashlib.sha256((EMAIL_HASH_SALT + row['triple_contributor']).encode()).hexdigest()[:16] + '...'
        
        # Filter columns based on admin configuration
        if rows:
            # Get all available fields
            all_fields = list(rows[0].keys())
            
            # Filter to only include visible fields (preserve order from visible_fields)
            filtered_fields = [field for field in visible_fields if field in all_fields]
            
            # If no valid fields, show all
            if not filtered_fields:
                filtered_fields = all_fields
            
            # Filter row data to only include visible fields
            filtered_rows = [{field: row.get(field, '') for field in filtered_fields} for row in rows]
            columns = [{"name": k, "id": k} for k in filtered_fields]
        else:
            filtered_rows = rows
            columns = [{"name": k, "id": k} for k in rows[0].keys()]

        return dash_table.DataTable(
            data=filtered_rows,
            columns=columns,
            page_size=20,
            style_table={"overflowX": "auto"},
            style_cell={
                'textAlign': 'left',
                'padding': '8px',
                'minWidth': '100px',
                'maxWidth': '300px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            tooltip_data=[
                {
                    column: {'value': str(row[column]), 'type': 'markdown'}
                    for column in row.keys()
                } for row in rows
            ],
            tooltip_duration=None,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error loading data: {str(e)}", color="danger")

# Reset form
@app.callback(
    Output("sentence-text", "value"),
    Output("literature-link", "value"),
    Output("doi-metadata-store", "clear_data"),
    Output("doi-validation", "children", allow_duplicate=True),
    Output("doi-metadata-display", "children", allow_duplicate=True),
    Output("doi-metadata-display", "style", allow_duplicate=True),
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True,
)
def reset_form(_):
    return "", "", True, "", None, {"display": "none"}

# Load projects
@app.callback(
    Output("projects-store", "data"),
    Output("project-selector", "options"),
    Input("load-trigger", "n_intervals"),
    Input("btn-create-project", "n_clicks"),
    Input("main-tabs", "value"),
    prevent_initial_call=False,
)
def load_projects(load_trigger, create_click, tab_value):
    try:
        r = requests.get(API_PROJECTS, timeout=5)
        if r.ok:
            projects = r.json()
            options = [{"label": p["name"], "value": p["id"]} for p in projects]
            return projects, options
        else:
            return [], []
    except Exception as e:
        print(f"Failed to load projects: {e}")
        return [], []

@app.callback(
    Output("export-project-filter", "options"),
    Input("projects-store", "data"),
    prevent_initial_call=False,
)
def populate_export_project_filter(projects):
    if not projects:
        return []
    return [{"label": "All projects", "value": None}] + [
        {"label": p["name"], "value": p["id"]} for p in projects
    ]

# Show project info when selected and populate DOI list (only if no batches)
@app.callback(
    Output("project-info", "children"),
    Output("project-doi-selector", "options"),
    Output("project-doi-selector", "disabled"),
    Input("project-selector", "value"),
    State("projects-store", "data"),
    prevent_initial_call=False,
)
def show_project_info(project_id, projects):
    if not project_id or not projects:
        return "", [], True
    
    # Find selected project
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return "", [], True
    
    doi_count = len(project.get("doi_list", []))
    info_text = f"Project: {project['name']} ({doi_count} DOIs available)"
    
    # Check if project has batches
    try:
        response = requests.get(f"{API_BASE}/api/projects/{project_id}/batches", timeout=5)
        if response.ok:
            data = response.json()
            batches = data.get("batches", [])
            if batches:
                # Project has batches - batch selector will populate DOI dropdown
                return info_text, [], True
    except Exception as e:
        logger.error(f"Failed to check for batches: {e}")
    
    # No batches - populate DOI dropdown directly with PDF indicators
    try:
        # Fetch DOI list with PDF indicators
        response = requests.get(f"{API_BASE}/api/projects/{project_id}/dois-with-pdfs", timeout=5)
        if response.ok:
            data = response.json()
            dois_with_pdfs = data.get("dois", [])
            # Add 📄 emoji for DOIs that have PDFs
            doi_options = [
                {
                    "label": f"{item['doi']} 📄" if item.get("has_pdf") else item['doi'],
                    "value": item['doi']
                }
                for item in dois_with_pdfs
            ]
        else:
            # Fallback to simple list if API fails
            doi_list = project.get("doi_list", [])
            doi_options = [{"label": doi, "value": doi} for doi in doi_list]
    except Exception as e:
        logger.error(f"Failed to fetch DOI PDF indicators: {e}")
        # Fallback to simple list
        doi_list = project.get("doi_list", [])
        doi_options = [{"label": doi, "value": doi} for doi in doi_list]
    
    return info_text, doi_options, False


# ============================================================================
# DOI Batch Management Callbacks
# ============================================================================

@app.callback(
    Output("batch-selector", "options"),
    Output("batch-selector", "disabled"),
    Output("batch-selector-row", "style"),
    Input("project-selector", "value"),
    prevent_initial_call=True,
)
def load_project_batches(project_id):
    """Load batches for selected project"""
    if not project_id:
        return [], True, {"display": "none"}
    
    try:
        # Call backend API to get batches
        response = requests.get(f"{API_BASE}/api/projects/{project_id}/batches", timeout=5)
        if response.ok:
            data = response.json()
            batches = data.get("batches", [])
            
            if not batches:
                # No batches - hide batch selector
                return [], True, {"display": "none"}
            
            # Build batch options
            options = [
                {
                    "label": f"{b['batch_name']} ({b['doi_count']} papers)",
                    "value": b['batch_id']
                }
                for b in batches
            ]
            
            return options, False, {"display": "block"}
        else:
            return [], True, {"display": "none"}
    except Exception as e:
        logger.error(f"Failed to load batches: {e}")
        return [], True, {"display": "none"}


@app.callback(
    Output("project-doi-selector", "options", allow_duplicate=True),
    Output("project-doi-selector", "disabled", allow_duplicate=True),
    Output("batch-progress-indicator", "children"),
    Input("batch-selector", "value"),
    State("project-selector", "value"),
    State("email-store", "data"),
    prevent_initial_call=True,
)
def load_batch_dois(batch_id, project_id, user_email):
    """Load DOIs for selected batch with status indicators and PDF indicators"""
    if not batch_id or not project_id:
        return [], True, ""
    
    try:
        # Call backend API to get DOIs with status and PDF indicators
        response = requests.get(
            f"{API_BASE}/api/projects/{project_id}/batches/{batch_id}/dois",
            timeout=5
        )
        
        if response.ok:
            data = response.json()
            dois_data = data.get("dois", [])
            
            # Build options with status indicators and PDF indicators
            options = []
            for doi_info in dois_data:
                status = doi_info.get('status', 'unstarted')
                annotator = doi_info.get('annotator_email', '')
                doi = doi_info['doi']
                has_pdf = doi_info.get('has_pdf', False)
                
                # Choose status indicator based on annotation status
                if status == 'completed':
                    status_indicator = '🟢'
                elif status == 'in_progress':
                    if annotator == user_email:
                        status_indicator = '🔵'  # Your work
                    else:
                        status_indicator = '🟡'  # Someone else's work
                else:
                    status_indicator = '🔴'
                
                # Add PDF indicator if PDF exists
                pdf_indicator = ' 📄' if has_pdf else ''
                
                options.append({
                    "label": f"{status_indicator} {doi}{pdf_indicator}",
                    "value": doi
                })
            
            # Build progress indicator
            total = len(dois_data)
            if total > 0:
                completed = sum(1 for d in dois_data if d.get('status') == 'completed')
                in_progress = sum(1 for d in dois_data if d.get('status') == 'in_progress')
                unstarted = total - completed - in_progress
                
                progress = dbc.Stack([
                    dbc.Progress(
                        [
                            dbc.Progress(value=(completed/total)*100, color="success", bar=True),
                            dbc.Progress(value=(in_progress/total)*100, color="warning", bar=True),
                        ],
                        className="mb-1"
                    ),
                    html.Small([
                        f"✓ {completed} completed • ",
                        f"⏳ {in_progress} in progress • ",
                        f"○ {unstarted} unstarted"
                    ], className="text-muted")
                ])
            else:
                progress = ""
            
            return options, False, progress
        else:
            return [], True, ""
            
    except Exception as e:
        logger.error(f"Failed to load batch DOIs: {e}")
        return [], True, ""


@app.callback(
    Output("doi-status-indicator", "children"),
    Input("project-doi-selector", "value"),
    State("project-selector", "value"),
    State("email-store", "data"),
    prevent_initial_call=True,
)
def mark_doi_in_progress(doi, project_id, user_email):
    """Automatically mark DOI as in-progress when selected"""
    if not doi or not project_id or not user_email:
        return ""
    
    try:
        # Update status in backend
        response = requests.post(
            f"{API_BASE}/api/projects/{project_id}/dois/{doi}/status",
            json={
                "status": "in_progress",
                "annotator_email": user_email
            },
            timeout=5
        )
        
        if response.ok:
            return html.Small("📝 Status: In Progress", className="text-info")
        else:
            return ""
            
    except Exception as e:
        logger.error(f"Failed to update DOI status: {e}")
        return ""


def create_empty_form_values(num_rows):
    """
    Helper function to create empty values for clearing form fields.
    
    Args:
        num_rows: Number of triple rows to clear
        
    Returns:
        tuple: (empty_values, empty_dropdowns) for clearing form fields
    """
    empty_values = [""] * num_rows if num_rows > 0 else []
    empty_dropdowns = [None] * num_rows if num_rows > 0 else []
    return empty_values, empty_dropdowns


# Update literature link when DOI is selected from project
@app.callback(
    Output("literature-link", "value", allow_duplicate=True),
    Output("doi-metadata-store", "data", allow_duplicate=True),
    Output("doi-validation", "children", allow_duplicate=True),
    Output("doi-validation", "style", allow_duplicate=True),
    Output("doi-metadata-display", "children", allow_duplicate=True),
    Output("doi-metadata-display", "style", allow_duplicate=True),
    Output("sentence-text", "value", allow_duplicate=True),
    Output({"type": "src-name", "index": ALL}, "value", allow_duplicate=True),
    Output({"type": "src-attr", "index": ALL}, "value", allow_duplicate=True),
    Output({"type": "src-attr-other", "index": ALL}, "value", allow_duplicate=True),
    Output({"type": "rel-type", "index": ALL}, "value", allow_duplicate=True),
    Output({"type": "rel-type-other", "index": ALL}, "value", allow_duplicate=True),
    Output({"type": "sink-name", "index": ALL}, "value", allow_duplicate=True),
    Output({"type": "sink-attr", "index": ALL}, "value", allow_duplicate=True),
    Output({"type": "sink-attr-other", "index": ALL}, "value", allow_duplicate=True),
    Input("project-doi-selector", "value"),
    State({"type": "src-name", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def update_doi_from_project(selected_doi, src_names):
    if not selected_doi:
        return NO_UPDATE_15
    
    # Clear previous sentence and triple fields
    num_rows = len(src_names) if src_names else 0
    empty_values, empty_dropdowns = create_empty_form_values(num_rows)
    
    # Try to validate the DOI automatically
    success, validation_msg, validation_style, metadata_card, metadata_card_style, metadata_data = validate_doi_internal(selected_doi)
    
    if success:
        # Validation succeeded - populate with DOI and metadata
        return (
            selected_doi,
            metadata_data,
            validation_msg,
            validation_style,
            metadata_card,
            metadata_card_style,
            "",  # Clear sentence text
            empty_values,  # src-name
            empty_dropdowns,  # src-attr
            empty_values,  # src-attr-other
            empty_dropdowns,  # rel-type
            empty_values,  # rel-type-other
            empty_values,  # sink-name
            empty_dropdowns,  # sink-attr
            empty_values,  # sink-attr-other
        )
    else:
        # Validation failed - provide user feedback with error message
        return (
            selected_doi,
            None,
            validation_msg,  # Show error message instead of empty string
            {"color": "orange"},  # Use orange for warning
            None,
            {"display": "none"},
            "",  # Clear sentence text
            empty_values,  # src-name
            empty_dropdowns,  # src-attr
            empty_values,  # src-attr-other
            empty_dropdowns,  # rel-type
            empty_values,  # rel-type-other
            empty_values,  # sink-name
            empty_dropdowns,  # sink-attr
            empty_values,  # sink-attr-other
        )

# Update PDF viewer when DOI is selected from project
@app.callback(
    Output("pdf-viewer-container", "children"),
    Input("project-doi-selector", "value"),
    State("project-selector", "value"),
    prevent_initial_call=True,
)
def update_pdf_viewer(selected_doi, project_id):
    if not selected_doi or not project_id:
        return html.P(
            "Select a DOI from a project to view the PDF here.",
            className="text-muted text-center",
            style={"padding": "50px"}
        )
    
    # Get the doi_hash for the selected DOI
    try:
        # Clean the DOI
        clean_doi = selected_doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        doi_hash = hashlib.sha256(clean_doi.encode()).hexdigest()[:16]
        
        # Construct PDF path
        pdf_filename = f"{doi_hash}.pdf"
        # Use internal backend URL for server-side check
        backend_pdf_url = f"{API_BASE}/api/projects/{project_id}/pdf/{pdf_filename}"
        
        # Check if PDF exists by trying to fetch it from backend
        try:
            r = requests.head(backend_pdf_url, timeout=5)
            if r.ok:
                # PDF exists - check if highlighting is enabled
                if ENABLE_PDF_HIGHLIGHTING:
                    # Show custom viewer with highlighting capability
                    # Pass deployment mode to viewer for proper URL handling
                    # Include pathname prefix for correct routing in nginx mode
                    viewer_url = f"{DASH_REQUESTS_PATHNAME_PREFIX.rstrip('/')}/pdf-viewer?project_id={project_id}&filename={pdf_filename}&api_base={API_BASE}&deployment_mode={DEPLOYMENT_MODE}"
                    return html.Iframe(
                        src=viewer_url,
                        style={
                            "width": "100%",
                            "height": "980px",
                            "border": "none"
                        }
                    )
                else:
                    # Show simple PDF viewer without highlighting
                    # Always use proxy route to avoid direct backend connection issues
                    # and ensure compatibility with subpath deployments
                    proxy_pdf_url = f"{DASH_REQUESTS_PATHNAME_PREFIX.rstrip('/')}/proxy/pdf/{project_id}/{pdf_filename}"
                    return html.Iframe(
                        src=proxy_pdf_url,
                        style={
                            "width": "100%",
                            "height": "980px",
                            "border": "none"
                        }
                    )
            else:
                # PDF doesn't exist
                return html.Div([
                    html.P("PDF not available for this DOI.", className="text-warning text-center", style={"padding": "20px"}),
                    html.P(f"Expected file: {pdf_filename}", className="text-muted text-center small"),
                    html.P("You may need to download PDFs for this project from the Admin panel.", className="text-muted text-center small"),
                ])
        except:
            # Error checking, assume it doesn't exist
            return html.Div([
                html.P("PDF not available for this DOI.", className="text-warning text-center", style={"padding": "20px"}),
                html.P(f"Expected file: {pdf_filename}", className="text-muted text-center small"),
                html.P("You may need to download PDFs for this project from the Admin panel.", className="text-muted text-center small"),
            ])
    except Exception as e:
        return html.P(
            f"Error loading PDF: {str(e)}",
            className="text-danger text-center",
            style={"padding": "50px"}
        )

# Admin authentication
@app.callback(
    Output("admin-auth-message", "children"),
    Output("admin-panel-content", "style"),
    Output("admin-auth-store", "data"),
    Output("btn-admin-login", "style"),
    Output("btn-admin-logout", "style"),
    Input("btn-admin-login", "n_clicks"),
    State("admin-email", "value"),
    State("admin-password", "value"),
    prevent_initial_call=True,
)
def admin_login(n_clicks, email, password):
    if not email or not password:
        return (
            dbc.Alert("Please enter email and password", color="danger"), 
            {"display": "none"}, 
            None,
            {"display": "inline-block"},
            {"display": "none"}
        )
    
    try:
        r = requests.post(API_ADMIN_AUTH, json={"email": email, "password": password}, timeout=10)
        if r.ok:
            result = r.json()
            if result.get("authenticated"):
                return (
                    dbc.Alert("Logged in successfully!", color="success"),
                    {"display": "block"},
                    {"email": email, "password": password},
                    {"display": "none"},  # Hide login button
                    {"display": "inline-block"}  # Show logout button
                )
            else:
                return (
                    dbc.Alert("Invalid credentials", color="danger"), 
                    {"display": "none"}, 
                    None,
                    {"display": "inline-block"},
                    {"display": "none"}
                )
        else:
            return (
                dbc.Alert(f"Authentication failed: {r.status_code}", color="danger"), 
                {"display": "none"}, 
                None,
                {"display": "inline-block"},
                {"display": "none"}
            )
    except Exception as e:
        return (
            dbc.Alert(f"Error: {str(e)}", color="danger"), 
            {"display": "none"}, 
            None,
            {"display": "inline-block"},
            {"display": "none"}
        )


# Admin logout
@app.callback(
    Output("admin-auth-message", "children", allow_duplicate=True),
    Output("admin-panel-content", "style", allow_duplicate=True),
    Output("admin-auth-store", "data", allow_duplicate=True),
    Output("btn-admin-login", "style", allow_duplicate=True),
    Output("btn-admin-logout", "style", allow_duplicate=True),
    Input("btn-admin-logout", "n_clicks"),
    prevent_initial_call=True,
)
def admin_logout(n_clicks):
    return (
        dbc.Alert("Logged out successfully", color="info"),
        {"display": "none"},
        None,  # Clear auth data
        {"display": "inline-block"},  # Show login button
        {"display": "none"}  # Hide logout button
    )

# Create project
@app.callback(
    Output("project-message", "children"),
    Output("btn-create-project", "disabled"),
    Input("btn-create-project", "n_clicks"),
    State("new-project-name", "value"),
    State("new-project-description", "value"),
    State("new-project-doi-list", "value"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def create_project_callback(n_clicks, name, description, doi_list_text, auth_data):
    if not auth_data:
        return dbc.Alert("Please login first", color="danger"), False
    
    if not name or not doi_list_text:
        return dbc.Alert("Project name and DOI list are required", color="danger"), False
    
    # Parse DOI list
    doi_list = [doi.strip() for doi in doi_list_text.split("\n") if doi.strip()]
    
    # Count total DOIs submitted
    total_submitted = len(doi_list)
    
    try:
        payload = {
            "email": auth_data["email"],
            "password": auth_data["password"],
            "name": name,
            "description": description or "",
            "doi_list": doi_list
        }
        # Increase timeout for large DOI lists (base 30s + 0.1s per DOI, max 300s = 5 minutes)
        timeout = min(30 + (len(doi_list) * 0.1), 300)
        
        # Show progress message for large lists
        if total_submitted > 50:
            # This is a workaround - ideally we'd show a spinner during the request
            # but Dash callbacks are synchronous
            pass
        
        r = requests.post(API_ADMIN_PROJECTS, json=payload, timeout=timeout)
        if r.ok:
            result = r.json()
            if result.get("ok"):
                project_id = result.get('project_id')
                valid_count = result.get('valid_count', 0)
                
                # Build success message with warnings if applicable
                message_parts = [f"✅ Project created successfully! ID: {project_id}"]
                message_parts.append(f"Added {valid_count} valid DOI(s).")
                
                # Check for discrepancies
                if total_submitted != valid_count:
                    excluded_count = total_submitted - valid_count
                    message_parts.append(f"⚠️ {excluded_count} DOI(s) were excluded (duplicates or invalid).")
                
                # Show details about invalid DOIs if provided
                if result.get("warning"):
                    message_parts.append(result.get("warning"))
                
                if result.get("invalid_dois"):
                    invalid_dois = result.get("invalid_dois", [])
                    if len(invalid_dois) <= 5:
                        # Show all if few
                        details = "\n".join([f"  • {item.get('doi', '')}: {item.get('reason', '')}" 
                                           for item in invalid_dois])
                        message_parts.append(f"Invalid DOIs:\n{details}")
                    else:
                        # Show first 5 if many
                        details = "\n".join([f"  • {item.get('doi', '')}: {item.get('reason', '')}" 
                                           for item in invalid_dois[:5]])
                        message_parts.append(f"Invalid DOIs (showing first 5 of {len(invalid_dois)}):\n{details}")
                
                message_text = "\n".join(message_parts)
                alert_color = "warning" if total_submitted != valid_count else "success"
                return dbc.Alert(message_text, color=alert_color, style={"whiteSpace": "pre-wrap"}), False
            else:
                return dbc.Alert(f"Failed: {result.get('error', 'Unknown error')}", color="danger"), False
        else:
            return dbc.Alert(f"Failed: {r.status_code} - {r.text[:200]}", color="danger"), False
    except requests.exceptions.Timeout:
        return dbc.Alert(
            f"⏱️ Request timed out while validating {total_submitted} DOIs.\n\n"
            f"This usually means the validation is taking longer than expected. "
            f"For large DOI lists (300+), try breaking them into smaller batches of 100-200 DOIs.\n\n"
            f"The backend may still be processing your request. Please refresh the projects list in a moment to check if it completed.",
            color="danger"
        ), False
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), False

# Display projects list
@app.callback(
    Output("projects-list", "children"),
    Input("btn-refresh-projects", "n_clicks"),
    Input("project-message", "children"),  # Trigger refresh when project message changes
    Input("delete-project-confirm", "n_clicks"),
    Input("admin-auth-store", "data"),  # Trigger refresh when auth changes
    prevent_initial_call=False,
)
def display_projects_list(refresh_clicks, project_message, delete_clicks, auth_data):
    if not auth_data:
        return dbc.Alert("Please login to view projects", color="info")
    
    try:
        r = requests.get(API_PROJECTS, timeout=5)
        if r.ok:
            projects = r.json()
            if not projects:
                return dbc.Alert("No projects found", color="info")
            
            # Create a table of projects
            project_items = []
            for p in projects:
                doi_count = len(p.get("doi_list", []))
                project_id = p["id"]
                
                # Check if download is stale for this project
                is_stale = False
                try:
                    status_url = f"{API_BASE}/api/admin/projects/{project_id}/download-pdfs/status"
                    progress_resp = requests.get(status_url, timeout=2)
                    if progress_resp.ok:
                        progress_data = progress_resp.json()
                        # Only show force restart button if download is running and stale
                        if progress_data.get("status") == "running":
                            is_stale = progress_data.get("is_stale", False)
                except Exception as e:
                    # Log error but continue - download status check is not critical for listing projects
                    if ENABLE_DEBUG_LOGGING:
                        logger.debug(f"Could not check download status for project {project_id}: {e}")
                
                # Build button list for this project
                button_list = [
                    dbc.Button("View DOIs", id={"type": "view-project-dois", "index": project_id}, 
                             color="info", size="sm", outline=True),
                    dbc.Button("Edit DOIs", id={"type": "edit-project-dois", "index": project_id}, 
                             color="primary", size="sm", outline=True),
                    dbc.Button("Download PDFs", id={"type": "download-project-pdfs", "index": project_id}, 
                             color="success", size="sm", outline=True),
                ]
                
                # Add Force Restart button if download is stale
                if is_stale:
                    button_list.append(
                        dbc.Button(
                            [
                                html.I(className="bi bi-arrow-clockwise me-1"),
                                "Force Restart"
                            ],
                            id={"type": "force-restart-download", "index": project_id},
                            color="warning",
                            size="sm",
                            outline=True,
                            title="Download appears stale. Click to restart from beginning."
                        )
                    )
                
                # Add remaining buttons
                button_list.extend([
                    dbc.Button("Upload PDFs", id={"type": "upload-project-pdfs", "index": project_id}, 
                             color="warning", size="sm", outline=True),
                    dbc.Button("Delete", id={"type": "delete-project", "index": project_id}, 
                             color="danger", size="sm", outline=True),
                ])
                
                card = dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.H6(p["name"], className="card-title"),
                                html.P(p.get("description", "No description"), className="card-text small"),
                                html.P([
                                    html.Strong("DOIs: "), f"{doi_count}",
                                    html.Br(),
                                    html.Strong("Created by: "), p.get("created_by", "Unknown"),
                                    html.Br(),
                                    html.Strong("ID: "), str(project_id)
                                ], className="card-text small text-muted mb-2"),
                                dbc.ButtonGroup(
                                    button_list,
                                    size="sm",
                                ),
                            ]
                        )
                    ],
                    className="mb-2",
                )
                
                # Add inline progress container for this project
                project_container = html.Div([
                    card,
                    html.Div(
                        id={"type": "project-pdf-progress", "index": project_id},
                        className="mb-2"
                    )
                ])
                
                project_items.append(project_container)
            
            return html.Div(project_items)
        else:
            return dbc.Alert(f"Failed to load projects: {r.status_code}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")

# Handle View DOIs button click
@app.callback(
    Output("project-message", "children", allow_duplicate=True),
    Input({"type": "view-project-dois", "index": ALL}, "n_clicks"),
    State("projects-store", "data"),
    prevent_initial_call=True,
)
def view_project_dois(n_clicks_list, projects):
    """
    Display DOIs in a project, split into two sections:
    1. DOIs with associated PDFs (already downloaded)
    2. DOIs without PDFs (need manual upload)
    
    This helps administrators identify which papers still need manual PDF uploads.
    """
    if not any(n_clicks_list) or not projects:
        return no_update
    
    # Find which button was clicked
    trigger = ctx.triggered_id
    if not trigger:
        return no_update
    
    project_id = trigger["index"]
    project = next((p for p in projects if p["id"] == project_id), None)
    
    if not project:
        return dbc.Alert("Project not found", color="danger")
    
    doi_list = project.get("doi_list", [])
    
    # Split DOIs into those with PDFs and those without
    # Check if PDF file exists for each DOI
    # PDF filename is generated using SHA256 hash (first 16 chars) of the DOI
    # This matches the logic in pdf_manager.py and harvest_store.py
    dois_with_pdfs = []
    dois_without_pdfs = []
    
    # Get the correct project PDF directory (format: project_pdfs/project_{id}/)
    project_pdf_dir = get_project_pdf_dir(project_id, PDF_STORAGE_DIR)
    
    for doi in doi_list:
        # Generate the expected PDF filename using same hash algorithm as pdf_manager.py
        doi_hash = generate_doi_hash(doi)
        pdf_filename = f"{doi_hash}.pdf"
        pdf_path = os.path.join(project_pdf_dir, pdf_filename)
        
        if os.path.exists(pdf_path):
            dois_with_pdfs.append(doi)
        else:
            dois_without_pdfs.append(doi)
    
    # Build the display with two sections
    display_content = [
        html.H6(f"DOIs in {project['name']}:", className="alert-heading"),
        html.Hr(),
    ]
    
    # Section 1: DOIs with PDFs
    if dois_with_pdfs:
        display_content.extend([
            html.Div([
                html.H6([
                    html.I(className="bi bi-file-pdf-fill me-2", style={"color": "#28a745"}),
                    f"DOIs with PDFs ({len(dois_with_pdfs)})"
                ], className="mb-2", style={"color": "#28a745"}),
                html.Ul([html.Li(doi) for doi in dois_with_pdfs], className="mb-3")
            ])
        ])
    else:
        display_content.extend([
            html.Div([
                html.H6([
                    html.I(className="bi bi-file-pdf me-2", style={"color": "#6c757d"}),
                    "DOIs with PDFs (0)"
                ], className="mb-2", style={"color": "#6c757d"}),
                html.P("No PDFs downloaded yet", className="text-muted small mb-3")
            ])
        ])
    
    # Section 2: DOIs without PDFs (needs manual upload)
    if dois_without_pdfs:
        display_content.extend([
            html.Div([
                html.H6([
                    html.I(className="bi bi-exclamation-triangle-fill me-2", style={"color": "#ffc107"}),
                    f"DOIs without PDFs - Need Manual Upload ({len(dois_without_pdfs)})"
                ], className="mb-2", style={"color": "#ffc107"}),
                html.Ul([html.Li(doi) for doi in dois_without_pdfs], className="mb-2"),
                html.Small([
                    html.I(className="bi bi-info-circle me-1"),
                    "These papers could not be downloaded automatically. Use the 'Upload PDFs' button to manually upload them."
                ], className="text-muted d-block")
            ])
        ])
    else:
        display_content.extend([
            html.Div([
                html.H6([
                    html.I(className="bi bi-check-circle-fill me-2", style={"color": "#28a745"}),
                    "All PDFs Downloaded!"
                ], className="mb-2", style={"color": "#28a745"}),
                html.P("All papers have associated PDFs", className="text-success small")
            ])
        ])
    
    return dbc.Alert(
        display_content,
        color="info",
        dismissable=True,
    )

# Handle Edit DOIs button click - Open modal and populate with project data
@app.callback(
    Output("edit-dois-modal", "is_open"),
    Output("edit-dois-project-id-store", "data"),
    Output("edit-dois-project-info", "children"),
    Output("edit-dois-current-list", "children"),
    Output("edit-dois-add-input", "value"),
    Output("edit-dois-remove-input", "value"),
    Output("edit-dois-delete-pdfs", "value"),
    Output("edit-dois-message", "children"),
    Input({"type": "edit-project-dois", "index": ALL}, "n_clicks"),
    Input("edit-dois-modal-close", "n_clicks"),
    Input("btn-add-dois-to-project", "n_clicks"),
    Input("btn-remove-dois-from-project", "n_clicks"),
    State("projects-store", "data"),
    State("edit-dois-modal", "is_open"),
    State("edit-dois-project-id-store", "data"),
    State("edit-dois-add-input", "value"),
    State("edit-dois-remove-input", "value"),
    State("edit-dois-delete-pdfs", "value"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def handle_edit_dois_modal(edit_clicks_list, close_clicks, add_clicks, remove_clicks, 
                           projects, is_open, current_project_id, add_input, remove_input, 
                           delete_pdfs, auth_data):
    """Handle opening/closing the edit DOIs modal and performing add/remove operations"""
    trigger = ctx.triggered_id
    
    # Close modal
    if trigger == "edit-dois-modal-close":
        return False, None, "", "", "", "", False, ""
    
    # Open modal with project data
    if trigger and isinstance(trigger, dict) and trigger.get("type") == "edit-project-dois":
        if not any(edit_clicks_list) or not projects:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        project_id = trigger["index"]
        project = next((p for p in projects if p["id"] == project_id), None)
        
        if not project:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        doi_list = project.get("doi_list", [])
        doi_items = [html.Div(f"• {doi}", className="small") for doi in doi_list]
        
        project_info = dbc.Alert([
            html.Strong(f"Project: {project['name']}"),
            html.Br(),
            html.Small(f"ID: {project['id']} | Total DOIs: {len(doi_list)}")
        ], color="info")
        
        return True, project_id, project_info, doi_items, "", "", False, ""
    
    # Add DOIs
    if trigger == "btn-add-dois-to-project":
        if not auth_data or not current_project_id or not add_input:
            return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                   dbc.Alert("Missing authentication or DOI input", color="danger")
        
        # Parse DOIs from input
        dois_to_add = [doi.strip() for doi in add_input.strip().split('\n') if doi.strip()]
        
        if not dois_to_add:
            return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                   dbc.Alert("No valid DOIs to add", color="warning")
        
        try:
            payload = {
                "email": auth_data.get("email"),
                "password": auth_data.get("password"),
                "dois": dois_to_add
            }
            # Scale timeout based on number of DOIs being added
            timeout = min(30 + (len(dois_to_add) * 0.1), 300)
            r = requests.post(f"{API_ADMIN_PROJECTS}/{current_project_id}/add-dois", json=payload, timeout=timeout)
            
            if r.ok:
                result = r.json()
                
                # Build message with warnings if applicable
                message_parts = [result.get("message", "DOIs added successfully")]
                added_count = result.get("added_count", 0)
                
                # Check for warnings about invalid DOIs
                if result.get("warning"):
                    message_parts.append(f"⚠️ {result.get('warning')}")
                
                # Show details about invalid DOIs if provided
                if result.get("invalid_dois"):
                    invalid_dois = result.get("invalid_dois", [])
                    if len(invalid_dois) <= 3:
                        details = "\n".join([f"  • {item.get('doi', '')}: {item.get('reason', '')}" 
                                           for item in invalid_dois])
                        message_parts.append(f"Invalid DOIs:\n{details}")
                    else:
                        details = "\n".join([f"  • {item.get('doi', '')}: {item.get('reason', '')}" 
                                           for item in invalid_dois[:3]])
                        message_parts.append(f"Invalid DOIs (showing first 3 of {len(invalid_dois)}):\n{details}")
                
                message_text = "\n".join(message_parts)
                alert_color = "warning" if result.get("invalid_dois") else "success"
                
                # Refresh project list
                projects_r = requests.get(API_PROJECTS, timeout=5)
                if projects_r.ok:
                    updated_projects = projects_r.json()
                    updated_project = next((p for p in updated_projects if p["id"] == current_project_id), None)
                    if updated_project:
                        doi_list = updated_project.get("doi_list", [])
                        doi_items = [html.Div(f"• {doi}", className="small") for doi in doi_list]
                        
                        project_info = dbc.Alert([
                            html.Strong(f"Project: {updated_project['name']}"),
                            html.Br(),
                            html.Small(f"ID: {updated_project['id']} | Total DOIs: {len(doi_list)}")
                        ], color="info")
                        
                        return True, current_project_id, project_info, doi_items, "", no_update, no_update, \
                               dbc.Alert(message_text, color=alert_color, dismissable=True, style={"whiteSpace": "pre-wrap"})
                
                return True, current_project_id, no_update, no_update, "", no_update, no_update, \
                       dbc.Alert(message_text, color=alert_color, dismissable=True, style={"whiteSpace": "pre-wrap"})
            else:
                error_msg = r.json().get("error", f"Failed: {r.status_code}")
                return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                       dbc.Alert(f"Error: {error_msg}", color="danger", dismissable=True)
        except requests.exceptions.Timeout:
            return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                   dbc.Alert(
                       f"Request timed out while processing {len(dois_to_add)} DOIs. "
                       f"Please try again or contact support.",
                       color="danger", dismissable=True
                   )
        except Exception as e:
            return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                   dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)
    
    # Remove DOIs
    if trigger == "btn-remove-dois-from-project":
        if not auth_data or not current_project_id or not remove_input:
            return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                   dbc.Alert("Missing authentication or DOI input", color="danger")
        
        # Parse DOIs from input
        dois_to_remove = [doi.strip() for doi in remove_input.strip().split('\n') if doi.strip()]
        
        if not dois_to_remove:
            return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                   dbc.Alert("No valid DOIs to remove", color="warning")
        
        try:
            payload = {
                "email": auth_data.get("email"),
                "password": auth_data.get("password"),
                "dois": dois_to_remove,
                "delete_pdfs": delete_pdfs
            }
            # Scale timeout based on number of DOIs being removed
            timeout = min(30 + (len(dois_to_remove) * 0.1), 300)
            r = requests.post(f"{API_ADMIN_PROJECTS}/{current_project_id}/remove-dois", json=payload, timeout=timeout)
            
            if r.ok:
                result = r.json()
                # Refresh project list
                projects_r = requests.get(API_PROJECTS, timeout=5)
                if projects_r.ok:
                    updated_projects = projects_r.json()
                    updated_project = next((p for p in updated_projects if p["id"] == current_project_id), None)
                    if updated_project:
                        doi_list = updated_project.get("doi_list", [])
                        doi_items = [html.Div(f"• {doi}", className="small") for doi in doi_list]
                        
                        project_info = dbc.Alert([
                            html.Strong(f"Project: {updated_project['name']}"),
                            html.Br(),
                            html.Small(f"ID: {updated_project['id']} | Total DOIs: {len(doi_list)}")
                        ], color="info")
                        
                        message = result.get("message", "DOIs removed successfully")
                        if result.get("deleted_pdfs", 0) > 0:
                            message += f" | {result['deleted_pdfs']} PDF(s) deleted"
                        
                        return True, current_project_id, project_info, doi_items, no_update, "", False, \
                               dbc.Alert(message, color="success", dismissable=True)
                
                return True, current_project_id, no_update, no_update, no_update, "", False, \
                       dbc.Alert(result.get("message", "DOIs removed successfully"), color="success", dismissable=True)
            else:
                error_msg = r.json().get("error", f"Failed: {r.status_code}")
                return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                       dbc.Alert(f"Error: {error_msg}", color="danger", dismissable=True)
        except requests.exceptions.Timeout:
            return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                   dbc.Alert(
                       f"Request timed out while processing {len(dois_to_remove)} DOIs. "
                       f"Please try again or contact support.",
                       color="danger", dismissable=True
                   )
        except Exception as e:
            return True, current_project_id, no_update, no_update, no_update, no_update, no_update, \
                   dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)
    
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

# Handle Download PDFs button click - Start download and enable progress polling
@app.callback(
    Output("pdf-download-project-id", "data"),
    Output("pdf-download-progress-interval", "disabled"),
    Output("pdf-download-state-store", "data"),
    Input({"type": "download-project-pdfs", "index": ALL}, "n_clicks"),
    State("admin-auth-store", "data"),
    State("pdf-download-project-id", "data"),
    State("pdf-download-state-store", "data"),
    prevent_initial_call=True,
)
def start_download_project_pdfs(n_clicks_list, auth_data, current_active_projects, current_state_store):
    """Start PDF download and enable progress polling - supports multiple concurrent downloads"""
    if not any(n_clicks_list):
        return no_update, no_update, no_update
    
    if not auth_data:
        print("[Frontend] PDF Download: No auth data")
        return no_update, no_update, no_update
    
    email = auth_data.get("email")
    password = auth_data.get("password")
    if not email or not password:
        print("[Frontend] PDF Download: Missing credentials")
        return no_update, no_update, no_update
    
    # Find which button was clicked
    trigger = ctx.triggered_id
    if not trigger:
        return no_update, no_update, no_update
    
    project_id = trigger["index"]
    
    print(f"[Frontend] PDF Download: Starting download for project {project_id}")
    
    # Initialize tracking structures if needed
    active_projects = current_active_projects if isinstance(current_active_projects, dict) else {}
    state_store = current_state_store if isinstance(current_state_store, dict) else {}
    
    try:
        # Call backend to start download
        # Using short timeout (10s) because this only starts the background task
        # The actual download happens asynchronously, so we don't need to wait
        # If timeout occurs, the task may still be running on the server
        r = requests.post(
            f"{API_BASE}/api/admin/projects/{project_id}/download-pdfs",
            json={"email": email, "password": password},
            timeout=10
        )
        
        if r.ok:
            data = r.json()
            print(f"[Frontend] PDF Download: Download started - {data.get('total_dois', 0)} DOIs")
            
            # Add this project to active projects tracking
            active_projects[project_id] = True
            
            # Initialize download state for this project
            state_store[project_id] = {
                "project_id": project_id,
                "active": True,
                "status": "running",
                "current": 0,
                "total": data.get('total_dois', 0)
            }
            
            # Return: updated active projects dict, enable interval, updated state store
            # The polling callback will update the progress divs for all active projects
            return active_projects, False, state_store
        else:
            error_msg = r.json().get("error", "Unknown error") if r.headers.get("content-type") == "application/json" else f"HTTP {r.status_code}"
            print(f"[Frontend] PDF Download: Failed to start - {error_msg}")
            return no_update, no_update, no_update
            
    except Exception as e:
        print(f"[Frontend] PDF Download: Error starting download - {str(e)}")
        return no_update, no_update, no_update

# Restore PDF download polling on page load if there's an active download
@app.callback(
    Output("pdf-download-progress-interval", "disabled", allow_duplicate=True),
    Output("pdf-download-project-id", "data", allow_duplicate=True),
    Input("pdf-download-state-store", "data"),
    prevent_initial_call='initial_duplicate',
)
def restore_pdf_download_polling(download_state):
    """Restore polling on page load if there are active downloads in progress"""
    if download_state and isinstance(download_state, dict):
        # Check if any projects are active
        active_projects = {}
        for project_id, state in download_state.items():
            if isinstance(state, dict) and state.get("active"):
                active_projects[int(project_id)] = True
                print(f"[Frontend] PDF Download: Restoring polling for project {project_id} after refresh")
        
        if active_projects:
            # Enable polling and return active projects dict
            return False, active_projects
    
    # No active downloads, keep polling disabled
    return no_update, no_update

def _build_progress_outputs(progress_div_ids, active_projects_content):
    """
    Helper function to build output list for ALL pattern-matching outputs.
    Supports multiple concurrent downloads by matching project IDs.
    
    Args:
        progress_div_ids: List of progress div ID dicts from State
        active_projects_content: Dict mapping project_id -> content (dash component or HTML element)
                                 e.g., {7: dbc.Alert(...), 8: dbc.Alert(...)}
    
    Returns:
        List of outputs for each progress div
    """
    outputs = []
    for div_id in progress_div_ids:
        project_id = div_id["index"]
        if project_id in active_projects_content:
            outputs.append(active_projects_content[project_id])
        else:
            outputs.append(html.Div())  # Empty div for non-active projects
    return outputs

# Poll for PDF download progress
@app.callback(
    Output({"type": "project-pdf-progress", "index": ALL}, "children", allow_duplicate=True),
    Output("pdf-download-progress-interval", "disabled", allow_duplicate=True),
    Output("pdf-download-project-id", "data", allow_duplicate=True),
    Output("pdf-download-state-store", "data", allow_duplicate=True),
    Input("pdf-download-progress-interval", "n_intervals"),
    State({"type": "project-pdf-progress", "index": ALL}, "id"),
    State("pdf-download-project-id", "data"),
    State("admin-auth-store", "data"),
    State("pdf-download-state-store", "data"),
    prevent_initial_call=True,
)
def poll_pdf_download_progress(n_intervals, progress_div_ids, active_projects, auth_data, download_state):
    """Poll the backend for PDF download progress - supports multiple concurrent downloads"""
    # Initialize tracking structures if needed
    active_projects = active_projects if isinstance(active_projects, dict) else {}
    download_state = download_state if isinstance(download_state, dict) else {}
    
    # Normalize keys to integers for consistent handling
    # State store comes from JSON and has string keys, active_projects uses int keys
    # Filter out empty/None keys to handle edge cases
    normalized_state = {int(k): v for k, v in download_state.items() if k not in (None, '')}
    
    # Restore active projects from download state if needed (after refresh)
    if not active_projects and normalized_state:
        for project_id, state in normalized_state.items():
            if isinstance(state, dict) and state.get("active"):
                active_projects[project_id] = True
    
    if not active_projects:
        return [no_update] * len(progress_div_ids), no_update, no_update, no_update
    
    # Continue polling even without auth if we have stored download states
    # (downloads were started before logout/refresh)
    has_active = any(normalized_state.get(pid, {}).get("active") for pid in active_projects.keys())
    if not auth_data and not has_active:
        return [no_update] * len(progress_div_ids), True, {}, {}  # Disable polling if not authenticated and no active downloads
    
    print(f"[Frontend] PDF Download: Polling progress for {len(active_projects)} project(s) (interval {n_intervals})")
    
    # Dictionary to store content for each active project
    progress_contents = {}
    updated_state_store = {}  # Will use int keys consistently
    projects_to_remove = []
    
    # Fetch download config once per poll (not per project) - cache for display
    config_info = None
    try:
        config_resp = requests.get(f"{API_BASE}/api/pdf-download-config", timeout=3)
        if config_resp.ok:
            config_data = config_resp.json()
            sources = config_data.get("sources", [])
            enabled_sources = [s for s in sources if s.get("enabled") and s.get("available")]
            if enabled_sources:
                config_info = enabled_sources
    except Exception as e:
        print(f"[Frontend] Could not fetch PDF config: {e}")
    
    # Poll each active project
    for project_id in list(active_projects.keys()):
        try:
            # Get progress from backend
            r = requests.get(
                f"{API_BASE}/api/admin/projects/{project_id}/download-pdfs/status",
                timeout=5
            )
            
            if r.status_code == 404:
                # Not started or no progress info
                print(f"[Frontend] PDF Download: No progress info for project {project_id}")
                # Mark for removal
                projects_to_remove.append(project_id)
                continue
            
            if not r.ok:
                print(f"[Frontend] PDF Download: Error fetching progress for project {project_id} - {r.status_code}")
                continue  # Keep polling this project
            
            data = r.json()
            status = data.get("status")
            total = data.get("total", 0)
            current = data.get("current", 0)
            current_doi = data.get("current_doi", "")
            current_source = data.get("current_source", "")
            
            print(f"[Frontend] PDF Download: Project {project_id} - Status={status}, Progress={current}/{total}")
            
            # Update download state for this project (use int keys for consistency)
            # Note: project_id is stored in both key and value for clarity and backend compatibility
            updated_state_store[project_id] = {
                "project_id": project_id,
                "active": status == "running",
                "status": status,
                "current": current,
                "total": total
            }
            
            if status == "running":
                # Check if download is stale
                is_stale = data.get("is_stale", False)
                time_since_update = data.get("time_since_update_seconds", 0)
                
                # Show progress
                # Format the source name for display
                source_display = ""
                if current_source:
                    source_map = {
                        "unpaywall": "Unpaywall",
                        "unpywall": "Unpywall",
                        "metapub": "Metapub",
                        "habanero": "Habanero",
                        "habanero_proxy": "Habanero (via proxy)",
                        "cached": "Cached",
                        "none": "All sources attempted"
                    }
                    source_display = source_map.get(current_source, current_source)
                
                # Build progress text content
                progress_content = [
                    html.Strong(f"Progress: {current} / {total} DOIs processed"),
                    html.Br(),
                    html.Strong("Currently processing: "), current_doi or "...",
                ]
                
                # Add source information if available
                if source_display:
                    progress_content.extend([
                        html.Br(),
                        html.Strong("Last source used: "),
                        source_display
                    ])
                
                # Add stale warning if applicable
                if is_stale:
                    progress_content.extend([
                        html.Br(),
                        html.Br(),
                        html.Div([
                            html.I(className="bi bi-exclamation-triangle-fill me-2", style={"color": "#ffc107"}),
                            html.Strong("⚠️ Download appears stale", style={"color": "#ffc107"}),
                        ]),
                        html.Br(),
                        html.Small(
                            f"No updates for {time_since_update} seconds. The download may have been interrupted by a server restart.",
                            className="text-muted"
                        ),
                    ])
                
                # Add download configuration info (fetched once at start of poll)
                if config_info:
                    progress_content.extend([
                        html.Br(),
                        html.Br(),
                        html.Strong("Active download mechanisms: "),
                        html.Br(),
                    ])
                    for src in config_info:
                        progress_content.extend([
                            f"  • {src['name']}: {src['description']}",
                            html.Br(),
                        ])
                
                # Build the alert components
                alert_children = [
                    html.H6("PDF Download In Progress", className="alert-heading"),
                    html.Hr(),
                    html.P(progress_content),
                    dbc.Progress(value=current, max=total, striped=True, animated=True, className="mb-2"),
                    html.P([
                        html.Strong("Downloaded: "), str(data.get("downloaded_count", 0)),
                        html.Br(),
                        html.Strong("Need Manual Upload: "), str(data.get("needs_upload_count", 0)),
                        html.Br(),
                        html.Strong("Errors: "), str(data.get("errors_count", 0)),
                    ], className="mb-2"),
                ]
                
                # Note: Force Restart button is in the Projects card (button row), not here
                
                progress_message = dbc.Alert(
                    alert_children,
                    color="warning" if is_stale else "info",
                    dismissable=False
                )
                
                progress_contents[project_id] = progress_message
                # Keep this project active
            
            elif status == "completed":
                print(f"[Frontend] PDF Download: Project {project_id} completed!")
                # Show final report
                full_results = data.get("full_results", {})
                downloaded = full_results.get("downloaded", [])
                needs_upload = full_results.get("needs_upload", [])
                errors = full_results.get("errors", [])
                
                report_items = [
                    html.H6("PDF Download Complete!", className="alert-heading"),
                    html.Hr(),
                    html.P([
                        html.Strong("Total DOIs: "), str(total),
                        html.Br(),
                        html.Strong("Downloaded: "), str(len(downloaded)),
                        html.Br(),
                        html.Strong("Need Manual Upload: "), str(len(needs_upload)),
                        html.Br(),
                        html.Strong("Errors: "), str(len(errors)),
                    ]),
                ]
                
                if downloaded:
                    report_items.append(html.H6("Successfully Downloaded:", className="mt-2"))
                    download_list_items = []
                    for item in downloaded[:10]:
                        # Handle both formats: 4-tuple (doi, filename, msg, source) or 3-tuple (doi, filename, msg)
                        if len(item) >= 4:
                            doi, filename, msg, source = item[0], item[1], item[2], item[3]
                            download_list_items.append(html.Li(f"{doi} → {filename} (via {source})"))
                        elif len(item) >= 3:
                            doi, filename, msg = item[0], item[1], item[2]
                            download_list_items.append(html.Li(f"{doi} → {filename}"))
                        else:
                            # Unexpected format, log and skip
                            print(f"[Frontend] PDF Download: Unexpected item format: {item}")
                            continue
                    report_items.append(html.Ul(download_list_items))
                    if len(downloaded) > 10:
                        report_items.append(html.P(f"... and {len(downloaded) - 10} more", className="text-muted"))
                
                if needs_upload:
                    report_items.append(html.H6("Needs Manual Upload:", className="mt-2 text-warning"))
                    report_items.append(html.Ul([html.Li(f"{doi} → {filename} ({reason})") for doi, filename, reason in needs_upload[:10]]))
                    if len(needs_upload) > 10:
                        report_items.append(html.P(f"... and {len(needs_upload) - 10} more", className="text-muted"))
                
                if errors:
                    report_items.append(html.H6("Errors:", className="mt-2 text-danger"))
                    report_items.append(html.Ul([html.Li(f"{doi}: {error}") for doi, error in errors[:5]]))
                
                report_items.append(html.Hr())
                report_items.append(html.P(f"PDFs stored in: {data.get('project_dir', 'N/A')}", className="small text-muted"))
                
                completed_alert = dbc.Alert(report_items, color="success", dismissable=True)
                progress_contents[project_id] = completed_alert
                # Mark for removal from active tracking
                projects_to_remove.append(project_id)
            
            elif status == "error":
                error_message = data.get("error_message", "Unknown error")
                print(f"[Frontend] PDF Download: Project {project_id} error - {error_message}")
                error_alert = dbc.Alert(f"Download error: {error_message}", color="danger", dismissable=True)
                progress_contents[project_id] = error_alert
                # Mark for removal from active tracking
                projects_to_remove.append(project_id)
            
            else:
                # Unknown status, keep polling
                print(f"[Frontend] PDF Download: Project {project_id} unknown status: {status}")
                
        except Exception as e:
            print(f"[Frontend] PDF Download: Error polling project {project_id} - {str(e)}")
            # Don't remove on error, might be temporary
            continue
    
    # Remove completed/error projects from active tracking
    updated_active_projects = dict(active_projects)
    for project_id in projects_to_remove:
        if project_id in updated_active_projects:
            del updated_active_projects[project_id]
        # Keep state for completed/error to show final message
        # State will be cleared when user navigates away or dismisses alert
    
    # Build outputs for ALL progress divs
    progress_outputs = _build_progress_outputs(progress_div_ids, progress_contents)
    
    # Disable polling if no active projects remain
    should_disable_polling = len(updated_active_projects) == 0
    
    return (
        progress_outputs,
        should_disable_polling,
        updated_active_projects if not should_disable_polling else {},
        updated_state_store
    )


# Handle Force Restart Download button click
@app.callback(
    Output("pdf-download-progress-interval", "disabled", allow_duplicate=True),
    Output("pdf-download-project-id", "data", allow_duplicate=True),
    Output("pdf-download-state-store", "data", allow_duplicate=True),
    Input({"type": "force-restart-download", "index": ALL}, "n_clicks"),
    State("admin-auth-store", "data"),
    State("pdf-download-project-id", "data"),
    State("pdf-download-state-store", "data"),
    prevent_initial_call=True,
)
def force_restart_download(n_clicks_list, auth_data, current_active_projects, current_state_store):
    """Force restart a stale PDF download - supports multiple concurrent downloads"""
    if not any(n_clicks_list):
        return no_update, no_update, no_update
    
    if not auth_data:
        return no_update, no_update, no_update
    
    email = auth_data.get("email")
    password = auth_data.get("password")
    if not email or not password:
        return no_update, no_update, no_update
    
    # Find which button was clicked
    trigger = ctx.triggered_id
    if not trigger:
        return no_update, no_update, no_update
    
    project_id = trigger["index"]
    
    print(f"[Frontend] Force Restart: Starting force restart for project {project_id}")
    
    # Initialize tracking structures if needed
    active_projects = current_active_projects if isinstance(current_active_projects, dict) else {}
    state_store = current_state_store if isinstance(current_state_store, dict) else {}
    
    try:
        # Call backend to start download with force_restart flag
        r = requests.post(
            f"{API_BASE}/api/admin/projects/{project_id}/download-pdfs",
            json={"email": email, "password": password, "force_restart": True},
            timeout=10
        )
        
        if r.ok:
            data = r.json()
            print(f"[Frontend] Force Restart: Download restarted - {data.get('total_dois', 0)} DOIs")
            
            # Add this project to active projects tracking
            active_projects[project_id] = True
            
            # Initialize download state for this project
            state_store[project_id] = {
                "project_id": project_id,
                "active": True,
                "status": "running",
                "current": 0,
                "total": data.get('total_dois', 0)
            }
            
            # Enable polling and return updated state
            return False, active_projects, state_store
        else:
            error_msg = r.json().get("error", "Unknown error") if r.headers.get("content-type") == "application/json" else f"HTTP {r.status_code}"
            print(f"[Frontend] Force Restart: Failed - {error_msg}")
            return no_update, no_update, no_update
            
    except Exception as e:
        print(f"[Frontend] Force Restart: Error - {str(e)}")
        return no_update, no_update, no_update


# Handle Delete project button click - opens modal
@app.callback(
    Output("delete-project-modal", "is_open"),
    Output("delete-project-id-store", "data"),
    Output("delete-project-triple-count", "children"),
    Output("delete-project-target", "options"),
    Input({"type": "delete-project", "index": ALL}, "n_clicks"),
    Input("delete-project-cancel", "n_clicks"),
    State("projects-store", "data"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def toggle_delete_project_modal(delete_clicks_list, cancel_click, projects, auth_data):
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update
    
    trigger = ctx.triggered_id
    
    # Cancel button closes modal
    if trigger == "delete-project-cancel":
        return False, None, "", []
    
    # Delete button opens modal
    if isinstance(trigger, dict) and trigger.get("type") == "delete-project":
        if not any(delete_clicks_list) or not auth_data or not projects:
            return no_update, no_update, no_update, no_update
        
        project_id = trigger["index"]
        project = next((p for p in projects if p["id"] == project_id), None)
        
        if not project:
            return no_update, no_update, no_update, no_update
        
        # Get triple count for this project
        try:
            r = requests.get(f"{API_RECENT}?project_id={project_id}", timeout=5)
            if r.ok:
                rows = r.json()
                triple_count = len(set(row.get("triple_id") for row in rows if row.get("triple_id")))
            else:
                triple_count = 0
        except:
            triple_count = 0
        
        # Create options for target project (exclude current project)
        target_options = [{"label": p["name"], "value": p["id"]} for p in projects if p["id"] != project_id]
        
        message = f"Project '{project['name']}' has {triple_count} associated triple(s)."
        
        return True, project_id, message, target_options
    
    return no_update, no_update, no_update, no_update

# Show/hide target project selector based on option
@app.callback(
    Output("delete-project-target-container", "style"),
    Input("delete-project-option", "value"),
    prevent_initial_call=False,
)
def toggle_target_project_selector(option):
    if option == "reassign":
        return {"display": "block"}
    return {"display": "none"}

# Confirm project deletion with options
@app.callback(
    Output("project-message", "children", allow_duplicate=True),
    Output("projects-list", "children", allow_duplicate=True),
    Output("delete-project-modal", "is_open", allow_duplicate=True),
    Input("delete-project-confirm", "n_clicks"),
    State("delete-project-id-store", "data"),
    State("delete-project-option", "value"),
    State("delete-project-target", "value"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def confirm_delete_project(n_clicks, project_id, option, target_project_id, auth_data):
    if not project_id or not auth_data:
        return no_update, no_update, no_update
    
    # Validate reassign option
    if option == "reassign" and not target_project_id:
        return dbc.Alert("Please select a target project for reassignment", color="warning"), no_update, True
    
    try:
        payload = {
            "email": auth_data["email"],
            "password": auth_data["password"],
            "handle_triples": option
        }
        if option == "reassign":
            payload["target_project_id"] = target_project_id
        
        r = requests.delete(f"{API_ADMIN_PROJECTS}/{project_id}", json=payload, timeout=10)
        
        if r.ok:
            result = r.json()
            if result.get("ok"):
                # Refresh the projects list
                try:
                    projects_r = requests.get(API_PROJECTS, timeout=5)
                    if projects_r.ok:
                        projects = projects_r.json()
                        if not projects:
                            return dbc.Alert(result.get("message", "Project deleted successfully!"), color="success"), dbc.Alert("No projects found", color="info"), False
                        
                        project_items = []
                        for p in projects:
                            doi_count = len(p.get("doi_list", []))
                            card = dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            html.H6(p["name"], className="card-title"),
                                            html.P(p.get("description", "No description"), className="card-text small"),
                                            html.P([
                                                html.Strong("DOIs: "), f"{doi_count}",
                                                html.Br(),
                                                html.Strong("Created by: "), p.get("created_by", "Unknown"),
                                                html.Br(),
                                                html.Strong("ID: "), str(p["id"])
                                            ], className="card-text small text-muted mb-2"),
                                            dbc.ButtonGroup(
                                                [
                                                    dbc.Button("View DOIs", id={"type": "view-project-dois", "index": p["id"]}, 
                                                             color="info", size="sm", outline=True),
                                                    dbc.Button("Delete", id={"type": "delete-project", "index": p["id"]}, 
                                                             color="danger", size="sm", outline=True),
                                                ],
                                                size="sm",
                                            ),
                                        ]
                                    )
                                ],
                                className="mb-2",
                            )
                            project_items.append(card)
                        
                        return dbc.Alert(result.get("message", "Project deleted successfully!"), color="success"), html.Div(project_items), False
                except Exception:
                    return dbc.Alert(result.get("message", "Project deleted successfully!"), color="success"), no_update, False
            else:
                return dbc.Alert(f"Failed: {result.get('error', 'Unknown error')}", color="danger"), no_update, False
        else:
            try:
                error_data = r.json()
                error_msg = error_data.get("error", f"Failed: {r.status_code}")
            except:
                error_msg = f"Failed: {r.status_code}"
            return dbc.Alert(error_msg, color="danger"), no_update, False
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), no_update, False

# Handle Upload PDFs button click - Open modal
@app.callback(
    Output("upload-pdf-modal", "is_open"),
    Output("upload-project-id-store", "data"),
    Output("upload-single-doi-input", "value"),
    Output("upload-file-doi-inputs", "children"),
    Output("upload-status-message", "children"),
    Input({"type": "upload-project-pdfs", "index": ALL}, "n_clicks"),
    Input("upload-pdf-cancel", "n_clicks"),
    Input("upload-pdf-confirm", "n_clicks"),
    State("upload-project-id-store", "data"),
    State("upload-single-doi-input", "value"),
    State({"type": "file-doi-input", "index": ALL}, "value"),
    State("upload-pdf-files", "contents"),
    State("upload-pdf-files", "filename"),
    State("admin-auth-store", "data"),
    State("projects-store", "data"),
    prevent_initial_call=True,
)
def handle_upload_pdf_modal(upload_clicks_list, cancel_click, confirm_click, 
                            stored_project_id, single_doi, file_dois, file_contents, filenames, auth_data, projects):
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update
    
    trigger = ctx.triggered_id
    
    # Cancel button closes modal
    if trigger == "upload-pdf-cancel":
        return False, None, "", None, None
    
    # Upload button opens modal
    if isinstance(trigger, dict) and trigger.get("type") == "upload-project-pdfs":
        if not any(upload_clicks_list):
            return no_update, no_update, no_update, no_update, no_update
        
        if not auth_data:
            return True, None, "", None, dbc.Alert("Please login first", color="danger")
        
        if not projects:
            return True, None, "", None, dbc.Alert("No projects available. Please refresh.", color="warning")
        
        project_id = trigger["index"]
        project = next((p for p in projects if p["id"] == project_id), None)
        
        if not project:
            return no_update, no_update, no_update, no_update, no_update
        
        return True, project_id, "", None, None
    
    # Confirm button - upload files
    if trigger == "upload-pdf-confirm":
        if not stored_project_id or not auth_data:
            return True, stored_project_id, single_doi, None, dbc.Alert("Authentication required", color="danger")
        
        if not file_contents or not filenames:
            return True, stored_project_id, single_doi, None, dbc.Alert("Please select at least one PDF file", color="warning")
        
        # Determine DOIs to use for each file
        # Priority: single_doi if provided, otherwise use individual file DOIs
        if not isinstance(file_contents, list):
            file_contents = [file_contents]
            filenames = [filenames]
        
        dois_to_use = []
        if single_doi and single_doi.strip():
            # Use single DOI for all files
            dois_to_use = [single_doi.strip()] * len(filenames)
        elif file_dois:
            # Use individual DOIs from file inputs
            dois_to_use = file_dois
        else:
            return True, stored_project_id, single_doi, None, dbc.Alert("Please provide either a single DOI or DOI for each file", color="warning")
        
        # Validate we have DOI for each file
        if len(dois_to_use) != len(filenames):
            return True, stored_project_id, single_doi, None, dbc.Alert(f"Mismatch: {len(filenames)} files but {len(dois_to_use)} DOIs provided", color="warning")
        
        # Process uploads
        upload_results = []
        
        
        for idx, (content, filename, doi) in enumerate(zip(file_contents, filenames, dois_to_use)):
            if not filename.endswith('.pdf'):
                upload_results.append(f"❌ {filename}: Not a PDF file")
                continue
            
            if not doi or not doi.strip():
                upload_results.append(f"❌ {filename}: No DOI provided")
                continue
            
            try:
                # Decode base64 content
                content_type, content_string = content.split(',')
                decoded = base64.b64decode(content_string)
                
                # Upload to backend
                files = {'file': (filename, decoded, 'application/pdf')}
                data = {
                    'email': auth_data.get('email'),
                    'password': auth_data.get('password'),
                    'doi': doi.strip()
                }
                
                r = requests.post(
                    f"{API_BASE}/api/admin/projects/{stored_project_id}/upload-pdf",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                if r.ok:
                    result = r.json()
                    upload_results.append(f"✓ {filename}: Uploaded successfully as {result.get('filename', 'unknown')}")
                else:
                    try:
                        error_data = r.json()
                        error_msg = error_data.get("error", f"Failed: {r.status_code}")
                    except Exception:
                        error_msg = f"Failed: {r.status_code}"
                    upload_results.append(f"❌ {filename}: {error_msg}")
            
            except Exception as e:
                upload_results.append(f"❌ {filename}: {str(e)}")
        
        # Show results
        result_message = dbc.Alert(
            [html.P(result) for result in upload_results],
            color="info"
        )
        
        # Keep modal open to show results, but clear DOI input
        return True, stored_project_id, "", None, result_message
    
    return no_update, no_update, no_update, no_update, no_update

# Display DOI input fields for each selected file
# Note: allow_duplicate=True is required because handle_upload_pdf_modal also
# updates upload-file-doi-inputs (to clear it when opening/closing modal)
@app.callback(
    Output("upload-file-doi-inputs", "children", allow_duplicate=True),
    Input("upload-pdf-files", "filename"),
    prevent_initial_call=True,
)
def display_upload_file_doi_inputs(filenames):
    if not filenames:
        return None
    
    if not isinstance(filenames, list):
        filenames = [filenames]
    
    # Create DOI input field for each file
    inputs = []
    for idx, filename in enumerate(filenames):
        inputs.append(
            html.Div([
                dbc.Label(f"DOI for {filename}:"),
                dbc.Input(
                    id={"type": "file-doi-input", "index": idx},
                    type="text",
                    placeholder="10.1234/example",
                    className="mb-2",
                ),
            ])
        )
    
    return html.Div([
        html.P(html.Strong("Enter DOI for each file:"), className="mb-2"),
        html.Div(inputs)
    ])

# Populate triple editor project filter
@app.callback(
    Output("triple-editor-project-filter", "options"),
    Input("load-trigger", "n_intervals"),
    Input("btn-refresh-projects", "n_clicks"),
    Input("main-tabs", "value"),
    prevent_initial_call=False,
)
def populate_triple_editor_project_filter(load_trigger, refresh_click, tab_value):
    try:
        r = requests.get(API_PROJECTS, timeout=5)
        if r.ok:
            projects = r.json()
            options = [{"label": "All triples (no filter)", "value": "all"}] + \
                     [{"label": f"{p['name']} (ID: {p['id']})", "value": p["id"]} for p in projects]
            return options
        else:
            return [{"label": "All triples (no filter)", "value": "all"}]
    except Exception:
        return [{"label": "All triples (no filter)", "value": "all"}]

# Load triple data
@app.callback(
    Output("triple-load-message", "children"),
    Output("edit-src-name", "value"),
    Output("edit-src-attr", "value"),
    Output("edit-rel-type", "value"),
    Output("edit-sink-name", "value"),
    Output("edit-sink-attr", "value"),
    Input("btn-load-triple", "n_clicks"),
    State("triple-id-input", "value"),
    State("triple-editor-project-filter", "value"),
    prevent_initial_call=True,
)
def load_triple_data(n_clicks, triple_id, project_filter):
    if not triple_id:
        return dbc.Alert("Please enter a triple ID", color="warning"), "", "", "", "", ""
    
    try:
        # Fetch triple data from the rows endpoint with optional project filter
        url = API_RECENT
        if project_filter and project_filter != "all":
            url = f"{API_RECENT}?project_id={project_filter}"
        
        r = requests.get(url, timeout=5)
        if r.ok:
            rows = r.json()
            # Find the triple with matching ID
            triple_data = next((row for row in rows if row.get("triple_id") == triple_id), None)
            
            if triple_data:
                project_info = ""
                if triple_data.get("project_id"):
                    project_info = f" (Project ID: {triple_data['project_id']})"
                return (
                    dbc.Alert(f"Loaded triple {triple_id}{project_info}", color="success"),
                    triple_data.get("source_entity_name", ""),
                    triple_data.get("source_entity_attr", ""),
                    triple_data.get("relation_type", ""),
                    triple_data.get("sink_entity_name", ""),
                    triple_data.get("sink_entity_attr", "")
                )
            else:
                if project_filter and project_filter != "all":
                    return dbc.Alert(f"Triple {triple_id} not found in the selected project. Try 'All triples' filter.", color="warning"), "", "", "", "", ""
                else:
                    return dbc.Alert(f"Triple {triple_id} does not exist in the database.", color="danger"), "", "", "", "", ""
        else:
            error_msg = f"Failed to load triple: {r.status_code}"
            try:
                error_data = r.json()
                if "error" in error_data:
                    error_msg = f"Error: {error_data['error']}"
            except:
                pass
            return dbc.Alert(error_msg, color="danger"), "", "", "", "", ""
    except Exception as e:
        return dbc.Alert(f"Error loading triple: {str(e)}", color="danger"), "", "", "", "", ""

# Update triple
@app.callback(
    Output("triple-edit-message", "children"),
    Input("btn-update-triple", "n_clicks"),
    Input("btn-delete-triple", "n_clicks"),
    State("triple-id-input", "value"),
    State("edit-src-name", "value"),
    State("edit-src-attr", "value"),
    State("edit-rel-type", "value"),
    State("edit-sink-name", "value"),
    State("edit-sink-attr", "value"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def edit_triple_callback(update_clicks, delete_clicks, triple_id, src_name, src_attr, rel_type, sink_name, sink_attr, auth_data):
    if not auth_data:
        return dbc.Alert("Please login first", color="danger")
    
    if not triple_id:
        return dbc.Alert("Please enter a triple ID", color="danger")
    
    trigger = ctx.triggered_id
    
    try:
        if trigger == "btn-update-triple":
            # Update triple
            payload = {
                "email": auth_data["email"],
                "password": auth_data["password"],
            }
            if src_name:
                payload["source_entity_name"] = src_name
            if src_attr:
                payload["source_entity_attr"] = src_attr
            if rel_type:
                payload["relation_type"] = rel_type
            if sink_name:
                payload["sink_entity_name"] = sink_name
            if sink_attr:
                payload["sink_entity_attr"] = sink_attr
            
            if not any([src_name, src_attr, rel_type, sink_name, sink_attr]):
                return dbc.Alert("Please provide at least one field to update", color="warning")
            
            r = requests.put(f"{API_ADMIN_TRIPLE}/{triple_id}", json=payload, timeout=10)
            if r.ok:
                result = r.json()
                if result.get("ok"):
                    return dbc.Alert("Triple updated successfully!", color="success")
                else:
                    return dbc.Alert(f"Failed: {result.get('error', 'Unknown error')}", color="danger")
            else:
                return dbc.Alert(f"Failed: {r.status_code} - {r.text[:200]}", color="danger")
        
        elif trigger == "btn-delete-triple":
            # Delete triple
            r = requests.delete(
                f"{API_BASE}/api/triple/{triple_id}",
                json={"email": auth_data["email"], "password": auth_data["password"]},
                timeout=10
            )
            if r.ok:
                result = r.json()
                if result.get("ok"):
                    return dbc.Alert("Triple deleted successfully!", color="success")
                else:
                    return dbc.Alert(f"Failed: {result.get('error', 'Unknown error')}", color="danger")
            else:
                return dbc.Alert(f"Failed: {r.status_code} - {r.text[:200]}", color="danger")
    
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")
    
    return no_update


# ============================================================================
# Admin Batch Management Callbacks
# ============================================================================

@app.callback(
    Output("batch-mgmt-project-selector", "options"),
    Input("admin-auth-store", "data"),
    Input("btn-refresh-projects", "n_clicks"),
    prevent_initial_call=False,
)
def populate_batch_mgmt_projects(auth_data, _):
    """Populate project selector for batch management"""
    if not auth_data:
        return []
    
    try:
        r = requests.get(API_PROJECTS, timeout=5)
        if r.ok:
            projects = r.json()
            return [{"label": f"{p['name']} ({len(p.get('doi_list', []))} DOIs)", "value": p["id"]} for p in projects]
        else:
            return []
    except Exception as e:
        logger.error(f"Failed to load projects for batch management: {e}")
        return []


@app.callback(
    Output("batch-creation-message", "children"),
    Output("batch-list-display", "children"),
    Input("btn-create-batches", "n_clicks"),
    State("batch-mgmt-project-selector", "value"),
    State("batch-size-input", "value"),
    State("batch-strategy-selector", "value"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def create_batches_callback(n_clicks, project_id, batch_size, strategy, auth_data):
    """Handle batch creation for a project"""
    if not auth_data:
        return dbc.Alert("Please login first", color="danger"), ""
    
    if not project_id:
        return dbc.Alert("Please select a project", color="warning"), ""
    
    try:
        # Call backend API to create batches
        response = requests.post(
            f"{API_BASE}/api/admin/projects/{project_id}/batches",
            json={
                "admin_email": auth_data["email"],
                "admin_password": auth_data["password"],
                "batch_size": batch_size or 20,
                "strategy": strategy or "sequential"
            },
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            batches = data.get("batches", [])
            total = data.get("total_batches", 0)
            
            # Build batch list display
            batch_items = []
            for batch in batches:
                card = dbc.Card([
                    dbc.CardBody([
                        html.H6(f"Batch {batch['batch_number']}: {batch['batch_name']}", className="mb-2"),
                        html.P([
                            html.Strong("DOIs: "), str(batch['doi_count']), html.Br(),
                            html.Strong("Created: "), batch['created_at']
                        ], className="small text-muted mb-0")
                    ])
                ], className="mb-2")
                batch_items.append(card)
            
            message = dbc.Alert(f"✓ Created {total} batches successfully!", color="success")
            display = html.Div(batch_items)
            
            return message, display
        else:
            # Try to parse JSON error, but handle case where response is not JSON
            try:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
            except json.JSONDecodeError:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            return dbc.Alert(f"Failed to create batches: {error_msg}", color="danger"), ""
            
    except Exception as e:
        logger.error(f"Failed to create batches: {e}")
        return dbc.Alert(f"Error: {str(e)}", color="danger"), ""


@app.callback(
    Output("batch-list-display", "children", allow_duplicate=True),
    Input("batch-mgmt-project-selector", "value"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def display_existing_batches(project_id, auth_data):
    """Display existing batches when project is selected"""
    if not project_id or not auth_data:
        return ""
    
    try:
        # Get existing batches
        response = requests.get(f"{API_BASE}/api/projects/{project_id}/batches", timeout=5)
        
        if response.ok:
            data = response.json()
            batches = data.get("batches", [])
            
            if not batches:
                return dbc.Alert("No batches found for this project. Create batches above.", color="info", className="small")
            
            # Get status summary
            status_response = requests.get(f"{API_BASE}/api/projects/{project_id}/doi-status", timeout=5)
            status_data = status_response.json() if status_response.ok else {}
            batch_breakdown = status_data.get("by_batch", [])
            
            # Build batch list with status
            batch_items = []
            for batch in batches:
                # Find matching status data
                batch_status = next((b for b in batch_breakdown if b['batch_id'] == batch['batch_id']), {})
                
                completed = batch_status.get('completed', 0)
                in_progress = batch_status.get('in_progress', 0)
                total = batch_status.get('total', batch['doi_count'])
                
                card = dbc.Card([
                    dbc.CardBody([
                        html.H6(f"Batch {batch['batch_number']}: {batch['batch_name']}", className="mb-2"),
                        html.P([
                            html.Strong("DOIs: "), str(batch['doi_count']), html.Br(),
                            html.Strong("Status: "), 
                            f"✓ {completed} completed, ⏳ {in_progress} in progress, ○ {total - completed - in_progress} unstarted"
                        ], className="small text-muted mb-2"),
                        dbc.Progress([
                            dbc.Progress(value=(completed/total)*100 if total > 0 else 0, color="success", bar=True),
                            dbc.Progress(value=(in_progress/total)*100 if total > 0 else 0, color="warning", bar=True),
                        ]) if total > 0 else None
                    ])
                ], className="mb-2")
                batch_items.append(card)
            
            return html.Div(batch_items)
        else:
            return ""
            
    except Exception as e:
        logger.error(f"Failed to display batches: {e}")
        return ""


# Export triples database
@app.callback(
    Output("export-triples-message", "children"),
    Input("btn-export-triples", "n_clicks"),
    State("admin-auth-store", "data"),
    State("export-project-filter", "value"),
    prevent_initial_call=True,
)
def export_triples_callback(n_clicks, auth_data, export_project):
    """Handle exporting triples database as JSON"""
    if not auth_data:
        return dbc.Alert("Please login first", color="danger")
    
    try:
        # Call the export API endpoint with POST and credentials in body
        r = requests.post(
            f"{API_BASE}/api/admin/export/triples",
            json={
                "email": auth_data["email"],
                "password": auth_data["password"],
                "project_id": export_project
            },
            timeout=30
        )
        
        if r.ok:
            result = r.json()
            if result.get("ok"):
                # Create download link with the JSON data
                json_str = json.dumps(result.get("data", {}), indent=2)
                
                # Create a data URI for download
                b64_data = base64.b64encode(json_str.encode()).decode()
                download_href = f"data:application/json;base64,{b64_data}"
                
                stats = result.get("data", {}).get("statistics", {})
                export_timestamp = result.get("data", {}).get("export_timestamp", "")
                
                # Use timestamp from API response for filename, fallback to current time
                if export_timestamp:
                    # Parse ISO timestamp and format for filename
                    try:
                        dt = datetime.fromisoformat(export_timestamp.replace('Z', '+00:00'))
                        filename_timestamp = dt.strftime('%Y%m%d_%H%M%S')
                    except (ValueError, AttributeError):
                        filename_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                else:
                    filename_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                return html.Div([
                    dbc.Alert([
                        html.Strong("✓ Export successful!"),
                        html.Br(),
                        html.Small(f"Exported {stats.get('total_triples', 0)} triples from {stats.get('total_projects', 0)} projects"),
                        html.Br(),
                        html.Small(f"Export time: {export_timestamp}"),
                    ], color="success", className="mb-2"),
                    html.A(
                        dbc.Button(
                            [html.I(className="bi bi-download me-2"), "Download JSON"],
                            color="primary",
                            size="sm"
                        ),
                        href=download_href,
                        download=f"triples_export_{filename_timestamp}.json",
                    )
                ])
            else:
                return dbc.Alert(f"Failed: {result.get('error', 'Unknown error')}", color="danger")
        else:
            return dbc.Alert(f"Failed: {r.status_code} - {r.text[:200]}", color="danger")
    
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")

# -----------------------
# Markdown Auto-Reload Callbacks
# -----------------------
# Note: Markdown auto-reload feature has been COMPLETELY DISABLED to prevent callback errors.
# Markdown files are loaded once on startup. Restart the server to reload changes.
#
# Previously, there was a markdown-reload-interval component and associated callbacks that
# would update the markdown content divs (annotator-guide-content, schema-tab-content, etc.)
# on a timer. This caused KeyError: "Callback function not found" errors in production.
#
# The problematic components and callbacks have been REMOVED:
#  - dcc.Interval(id="markdown-reload-interval") - REMOVED from layout
#  - @app.callback with Outputs for the 5 markdown content divs - REMOVED
#
# If you're still seeing KeyError messages about these component IDs, it's likely due to:
#  1. Python bytecode cache (.pyc files) - Clear with: find . -name "*.pyc" -delete
#     Or set environment variable: HARVEST_CLEAR_CACHE=true (development only)
#  2. Cached imports in running process - Restart the service completely
#     Recommended: Use python -B flag to prevent bytecode generation
#  3. Browser cache - Hard refresh (Ctrl+Shift+R) or clear browser cache
#
# For production deployments, consider:
#  - Running with: python -B harvest_fe.py (disables bytecode generation)
#  - Setting: export PYTHONDONTWRITEBYTECODE=1 (prevents .pyc creation)
#  - Using systemd service with proper restart policies

# COMPATIBILITY CALLBACK: Handle legacy markdown reload with 4 outputs (PRIMARY)
# This is the main callback that handles the most common cached browser request.
# It matches the exact callback ID format that cached browsers are looking for:
# ..annotator-guide-content.children...schema-tab-content.children...admin-guide-content.children...dbmodel-tab-content.children..
# This callback does NOT use allow_duplicate=True, making it the primary callback for these outputs.
@app.callback(
    Output("annotator-guide-content", "children"),
    Output("schema-tab-content", "children"),
    Output("admin-guide-content", "children"),
    Output("dbmodel-tab-content", "children"),
    Input("load-trigger", "n_intervals"),
    prevent_initial_call=True,
)
def handle_legacy_markdown_reload_request_4_primary(n):
    """
    PRIMARY compatibility callback for legacy markdown reload with 4 outputs.
    This handles the most common cached browser request without allow_duplicate=True,
    matching the exact callback ID format that cached browsers expect.
    
    The error message "Callback function not found for output '..annotator-guide-content.children...
    schema-tab-content.children...admin-guide-content.children...dbmodel-tab-content.children..'"
    indicates that cached browsers are looking for this exact callback signature.
    """
    if ENABLE_DEBUG_LOGGING:
        logger.debug("Legacy markdown reload request caught (4 outputs PRIMARY) - returning no_update")
    return no_update, no_update, no_update, no_update


# COMPATIBILITY CALLBACK: Handle legacy markdown reload requests with 5 outputs
# This handles cached browsers that expect all 5 markdown divs to be updated.
# Uses allow_duplicate=True to coexist with the 4-output primary callback.
@app.callback(
    Output("annotator-guide-content", "children", allow_duplicate=True),
    Output("schema-tab-content", "children", allow_duplicate=True),
    Output("admin-guide-content", "children", allow_duplicate=True),
    Output("dbmodel-tab-content", "children", allow_duplicate=True),
    Output("participate-tab-content", "children"),
    Input("load-trigger", "n_intervals"),
    prevent_initial_call=True,
)
def handle_legacy_markdown_reload_request_5(n):
    """
    Compatibility callback to gracefully handle legacy markdown reload requests (5 outputs).
    Old versions of the frontend had a markdown-reload-interval that would trigger
    updates to these 5 markdown content divs. Even though that component is removed,
    browsers with cached JavaScript may still try to trigger this callback.
    
    This callback catches those requests and returns no_update, preventing KeyError.
    Once all users have cleared their browser cache, this callback can be removed.
    """
    if ENABLE_DEBUG_LOGGING:
        logger.debug("Legacy markdown reload request caught (5 outputs) - returning no_update")
    # Always return no_update - markdown is loaded once at startup
    return no_update, no_update, no_update, no_update, no_update


# COMPATIBILITY CALLBACK: Handle legacy markdown reload with 4 outputs (variant 2)
# Another cached browser variant that requests the same 4 outputs with different trigger
@app.callback(
    Output("annotator-guide-content", "children", allow_duplicate=True),
    Output("schema-tab-content", "children", allow_duplicate=True),
    Output("admin-guide-content", "children", allow_duplicate=True),
    Output("dbmodel-tab-content", "children", allow_duplicate=True),
    Input("main-tabs", "value"),
    prevent_initial_call=True,
)
def handle_legacy_markdown_reload_request_4_v2(tab_value):
    """
    Compatibility callback for legacy markdown reload with only 4 outputs (variant 2).
    This handles yet another variant that triggers on tab changes.
    """
    if ENABLE_DEBUG_LOGGING:
        logger.debug("Legacy markdown reload request caught (4 outputs variant 2) - returning no_update")
    return no_update, no_update, no_update, no_update


# COMPATIBILITY CALLBACK: Handle legacy markdown reload with 4 outputs (variant 3)
# Yet another cached browser variant with BOTH load-trigger and main-tabs inputs
@app.callback(
    Output("annotator-guide-content", "children", allow_duplicate=True),
    Output("schema-tab-content", "children", allow_duplicate=True),
    Output("admin-guide-content", "children", allow_duplicate=True),
    Output("dbmodel-tab-content", "children", allow_duplicate=True),
    Input("load-trigger", "n_intervals"),
    Input("main-tabs", "value"),
    prevent_initial_call=True,
)
def handle_legacy_markdown_reload_request_4_v3(n, tab_value):
    """
    Compatibility callback for legacy markdown reload with only 4 outputs (variant 3).
    This handles a variant that has BOTH load-trigger and main-tabs inputs.
    The error message format '..output1...output2..' suggests a callback with multiple inputs.
    """
    if ENABLE_DEBUG_LOGGING:
        logger.debug("Legacy markdown reload request caught (4 outputs variant 3 - dual inputs) - returning no_update")
    return no_update, no_update, no_update, no_update


# Callback to save browse field configuration
@app.callback(
    Output("browse-field-config", "data", allow_duplicate=True),
    Input("browse-field-selector", "value"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def save_browse_field_config(selected_fields, admin_auth):
    """Persist selected browse fields globally via the backend and store locally."""
    fields = [f for f in (selected_fields or []) if f in ALLOWED_BROWSE_FIELDS] or DEFAULT_BROWSE_FIELDS

    payload = {"fields": fields}
    if admin_auth:
        email = admin_auth.get("email")
        password = admin_auth.get("password")
        if email and password:
            payload["email"] = email
            payload["password"] = password

    try:
        resp = requests.post(API_ADMIN_BROWSE_FIELDS, json=payload, timeout=5)
        if not resp.ok:
            logger.warning(
                "Browse fields persistence failed (status=%s): %s",
                resp.status_code,
                resp.text[:200],
            )
    except Exception as exc:
        logger.warning(f"Failed to persist browse fields to backend: {exc}")

    return fields


# Callback to load initial browse field configuration into dropdown
@app.callback(
    Output("browse-field-selector", "value"),
    Output("browse-field-config", "data", allow_duplicate=True),
    Input("load-trigger", "n_intervals"),
    prevent_initial_call="initial_duplicate",
)
def load_browse_field_config(n):
    """Load the global browse field configuration on page load."""
    fields = DEFAULT_BROWSE_FIELDS
    try:
        r = requests.get(API_BROWSE_FIELDS, timeout=5)
        if r.ok:
            data = r.json()
            api_fields = data.get("fields") if isinstance(data, dict) else None
            if api_fields:
                fields = api_fields
    except Exception as exc:
        logger.warning(f"Failed to load browse fields from backend: {exc}")

    fields = [f for f in fields if f in ALLOWED_BROWSE_FIELDS] or DEFAULT_BROWSE_FIELDS
    return fields, fields


# Callback to toggle advanced per-source limits
@app.callback(
    Output("collapse-per-source-limits", "is_open"),
    Input("toggle-per-source-limits", "n_clicks"),
    State("collapse-per-source-limits", "is_open"),
    prevent_initial_call=True,
)
def toggle_per_source_limits(n_clicks, is_open):
    """Toggle the per-source limits collapse"""
    if n_clicks:
        return not is_open
    return is_open


# Callback to show/hide privacy policy modal
@app.callback(
    Output("privacy-policy-modal", "is_open"),
    Input("btn-view-privacy-policy", "n_clicks"),
    Input("privacy-policy-close", "n_clicks"),
    State("privacy-policy-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_privacy_policy_modal(open_click, close_click, is_open):
    """Toggle the privacy policy modal"""
    return not is_open


# -----------------------
# Dashboard Callbacks
# -----------------------
# Dashboard statistics callback
@app.callback(
    [
        Output("dashboard-total-triples", "children"),
        Output("dashboard-total-projects", "children"),
        Output("dashboard-total-dois", "children"),
        Output("dashboard-recent-activity", "children"),
    ],
    Input("load-trigger", "n_intervals"),
)
def update_dashboard_stats(n):
    """Update dashboard statistics"""
    try:
        # Get total triples count from /api/recent endpoint
        r_recent = requests.get(f"{API_BASE}/api/recent", timeout=5)
        if r_recent.ok:
            recent_data = r_recent.json()
            # Count unique triple IDs (excluding None values from LEFT JOIN)
            triple_ids = [item.get("triple_id") for item in recent_data if item.get("triple_id")]
            total_triples = len(set(triple_ids))
            
            # Get unique DOIs count
            dois = [item.get("doi") for item in recent_data if item.get("doi")]
            unique_dois = len(set(dois))
            
            # Get recent activity (last 7 days)
            # Note: This uses string comparison and created_at field if available
            # For now, we'll estimate based on the top 200 records (LIMIT in query)
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_count = 0
            # Since created_at is not in the recent endpoint, we'll use a simplified estimate
            # assuming most recent 50 entries are within last 7 days (rough estimate)
            recent_count = min(50, len(triple_ids))
        else:
            total_triples = 0
            unique_dois = 0
            recent_count = 0
        
        # Get total projects count
        r_projects = requests.get(f"{API_BASE}/api/projects", timeout=5)
        if r_projects.ok:
            projects_data = r_projects.json()
            total_projects = len(projects_data)
        else:
            total_projects = 0
        
        return str(total_triples), str(total_projects), str(unique_dois), str(recent_count)
    except Exception as e:
        logger.error(f"Error updating dashboard stats: {e}")
        return "—", "—", "—", "—"


# Dashboard quick action callbacks
@app.callback(
    Output("main-tabs", "value"),
    [
        Input("dashboard-goto-literature", "n_clicks"),
        Input("dashboard-goto-annotate", "n_clicks"),
        Input("dashboard-goto-browse", "n_clicks"),
        Input("dashboard-goto-admin", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def dashboard_quick_actions(lit_clicks, ann_clicks, browse_clicks, admin_clicks):
    """Handle dashboard quick action button clicks"""
    trigger_id = ctx.triggered_id
    
    if trigger_id == "dashboard-goto-literature":
        return "tab-literature"
    elif trigger_id == "dashboard-goto-annotate":
        return "tab-annotate"
    elif trigger_id == "dashboard-goto-browse":
        return "tab-browse"
    elif trigger_id == "dashboard-goto-admin":
        return "tab-admin"
    
    return no_update


# -----------------------
# Literature Review (ASReview) Callbacks
# -----------------------
@app.callback(
    [
        Output("lit-review-availability-check", "children"),
        Output("lit-review-content", "style"),
        Output("lit-review-unavailable", "style"),
        Output("asreview-service-url", "children"),
        Output("asreview-direct-link", "href"),
    ],
    [
        Input("load-trigger", "n_intervals"),
        Input("admin-auth-store", "data"),
    ],
    prevent_initial_call=False
)
def check_literature_review_availability(n, auth_data):
    """
    Check if ASReview service is configured (only when authenticated).
    
    Note: This no longer checks service availability via proxy since ASReview
    cannot be embedded in an iframe. Instead, it simply checks if the service
    URL is configured and displays it for users to access directly.
    """
    try:
        # First check if user is authenticated
        if not auth_data or not ("email" in auth_data or "token" in auth_data):
            # User not authenticated - don't check service, just return initial state
            return (
                "",  # Clear loading spinner
                {"display": "none"},  # Hide content
                {"display": "none"},  # Hide unavailable message (auth message is shown instead)
                "",  # No service URL
                "#"  # Default href
            )
        
        # User is authenticated, now check if ASReview is configured
        if not ASREVIEW_SERVICE_URL:
            return (
                "",  # Clear loading spinner
                {"display": "none"},  # Hide content
                {"display": "block"},  # Show unavailable message
                "ASReview service URL not configured in config.py",
                "#"  # Default href
            )
        
        # ASReview service is configured - show the screenshot/preview
        return (
            "",  # Clear loading spinner
            {"display": "block"},  # Show content (screenshot and link)
            {"display": "none"},  # Hide unavailable message
            ASREVIEW_SERVICE_URL,  # Show service URL
            ASREVIEW_SERVICE_URL  # Set href for direct link
        )
    
    except Exception as e:
        logger.error(f"Error in check_literature_review_availability: {e}", exc_info=True)
        return (
            "",
            {"display": "none"},
            {"display": "block"},
            f"Internal error: {str(e)}",
            "#"  # Default href
        )


# Callback to load privacy policy content
@app.callback(
    Output("privacy-policy-content", "children"),
    Input("privacy-policy-modal", "is_open"),
    prevent_initial_call=False,
)
def load_privacy_policy_content(is_open):
    """Load the GDPR privacy policy content from markdown file"""
    if is_open:
        try:
            privacy_file_path = os.path.join(os.path.dirname(__file__), "docs", "GDPR_PRIVACY.md")
            with open(privacy_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Error loading privacy policy: {e}")
            return "Privacy policy content could not be loaded. Please contact your administrator."
    return ""


# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    # Run:  python harvest_fe.py
    # Then open http://127.0.0.1:8050
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8050")), debug=False)
