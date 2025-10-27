# t2t_frontend.py
import os
import json
import hashlib
import requests
import base64
import time
import logging
import threading
from datetime import datetime
from functools import lru_cache

import dash
from dash import Dash, dcc, html, dash_table, Input, Output, State, MATCH, ALL, ctx, no_update
import dash_bootstrap_components as dbc
from flask import Response, request as flask_request

# Literature search module
import literature_search

# Setup logging
logger = logging.getLogger(__name__)

# Import configuration
try:
    from config import PARTNER_LOGOS, ENABLE_LITERATURE_SEARCH, ENABLE_PDF_HIGHLIGHTING
except ImportError:
    # Fallback if config not available
    PARTNER_LOGOS = []
    ENABLE_LITERATURE_SEARCH = True  # Default to enabled
    ENABLE_PDF_HIGHLIGHTING = True  # Default to enabled

# -----------------------
# Config
# -----------------------
API_BASE = os.getenv("T2T_API_BASE", "http://127.0.0.1:5001")
API_CHOICES = f"{API_BASE}/api/choices"
API_SAVE = f"{API_BASE}/api/save"
API_RECENT = f"{API_BASE}/api/recent"
API_VALIDATE_DOI = f"{API_BASE}/api/validate-doi"
API_ADMIN_AUTH = f"{API_BASE}/api/admin/auth"
API_PROJECTS = f"{API_BASE}/api/projects"
API_ADMIN_PROJECTS = f"{API_BASE}/api/admin/projects"
API_ADMIN_TRIPLE = f"{API_BASE}/api/admin/triple"

APP_TITLE = "Text2Trait: Training data builder"

# -----------------------
# Local fallback schema (used if /api/choices is not reachable)
# -----------------------
SCHEMA_JSON = {
    "orl": "opinion role labeling",
    "span-attribute": {
        "Gene": "gene",
        "Regulator": "regulator",
        "Variant": "variant",
        "Protein": "protein",
        "Trait": "phenotype",
        "Enzyme": "enzyme",
        "QTL": "qtl",
        "Coordinates": "coordinates",
        "Metabolite": "metabolite",
    },
    "relation-type": {
        "is_a": "is_a",
        "part_of": "part_of",
        "develops_from": "develops_from",
        "is_related_to": "is_related_to",
        "is_not_related_to": "is_not_related_to",
        "increases": "increases",
        "decreases": "decreases",
        "influences": "influences",
        "does_not_influence": "does_not_influence",
        "may_influence": "may_influence",
        "may_not_influence": "may_not_influence",
        "disrupts": "disrupts",
        "regulates": "regulates",
        "contributes_to": "contributes_to",
        "inhers_in": "inhers_in",
    },
}

OTHER_SENTINEL = "__OTHER__"

# Rate limiting state for data fetches
# Store last fetch times to prevent rapid successive requests
# Using threading.Lock for thread-safety in multi-user scenarios
_last_fetch_times = {
    "recent_data": 0,  # Timestamp of last fetch for recent data
}
_fetch_lock = threading.Lock()  # Thread-safe access to _last_fetch_times
FETCH_COOLDOWN_SECONDS = 2  # Minimum seconds between fetches

# Helper constant for no_update returns with many outputs
NO_UPDATE_15 = tuple([no_update] * 15)


def create_execution_log_display(execution_log):
    """
    Create a visual display of the search pipeline execution log.
    Shows AutoResearch, DeepResearch (Python Reimpl), and DELM steps.
    """
    if not execution_log:
        return None
    
    # Create timeline items for each step
    timeline_items = []
    
    # Define colors for each step type
    step_colors = {
        'AutoResearch': '#17a2b8',  # Info blue
        'DeepResearch (Python Reimpl)': '#28a745',  # Success green
        'DELM': '#ffc107',  # Warning yellow/gold
        'Error': '#dc3545'  # Danger red
    }
    
    for idx, log_entry in enumerate(execution_log):
        step_name = log_entry.get('step', 'Unknown')
        description = log_entry.get('description', '')
        details = log_entry.get('details', '')
        elapsed_ms = log_entry.get('elapsed_ms', 0)
        status = log_entry.get('status', 'completed')
        
        # Get color for this step
        color = step_colors.get(step_name, '#6c757d')
        
        # Create status icon
        if status == 'completed':
            status_icon = html.I(className="bi bi-check-circle-fill", style={"color": "#28a745"})
        elif status == 'error':
            status_icon = html.I(className="bi bi-x-circle-fill", style={"color": "#dc3545"})
        else:
            status_icon = html.I(className="bi bi-clock-fill", style={"color": "#ffc107"})
        
        # Create timeline item
        timeline_item = dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        f"{idx + 1}",
                                        style={
                                            "display": "inline-block",
                                            "width": "28px",
                                            "height": "28px",
                                            "borderRadius": "50%",
                                            "backgroundColor": color,
                                            "color": "white",
                                            "textAlign": "center",
                                            "lineHeight": "28px",
                                            "fontWeight": "bold",
                                            "fontSize": "14px",
                                            "marginRight": "12px"
                                        }
                                    ),
                                    html.Span(
                                        step_name,
                                        style={
                                            "fontWeight": "bold",
                                            "fontSize": "16px",
                                            "color": color
                                        }
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center", "marginBottom": "8px"}
                            ),
                            html.Div(
                                [
                                    html.Strong(description),
                                    html.Br(),
                                    html.Span(details, style={"fontSize": "14px", "color": "#6c757d"}),
                                    html.Br(),
                                    html.Small(
                                        f"⏱️ {elapsed_ms}ms",
                                        style={"color": "#6c757d", "fontStyle": "italic"}
                                    ),
                                ],
                                style={"marginLeft": "40px"}
                            ),
                        ]
                    )
                ]
            ),
            className="mb-2",
            style={"borderLeft": f"4px solid {color}"}
        )
        
        timeline_items.append(timeline_item)
    
    # Create the execution log card with collapse functionality
    execution_log_card = dbc.Card(
        [
            dbc.CardHeader(
                dbc.Button(
                    [
                        html.Span([
                            html.I(className="bi bi-diagram-3-fill", style={"marginRight": "8px"}),
                            "Pipeline Execution Flow"
                        ]),
                        html.I(className="bi bi-chevron-down text-muted", id="pipeline-chevron", style={"fontSize": "0.8rem", "float": "right"})
                    ],
                    id="pipeline-collapse-button",
                    color="link",
                    style={"width": "100%", "textAlign": "left", "textDecoration": "none", "color": "#000", "fontWeight": "600"},
                    className="p-0"
                ),
                style={"backgroundColor": "#f8f9fa"}
            ),
            dbc.Collapse(
                dbc.CardBody(
                    [
                        html.P(
                            "The Semantic Paper Discovery system executes the following steps:",
                            className="text-muted mb-3",
                            style={"fontSize": "14px"}
                        ),
                        html.Div(timeline_items)
                    ]
                ),
                id="pipeline-collapse",
                is_open=False,  # Collapsed by default
            )
        ],
        className="mb-3"
    )
    
    return execution_log_card


# Helper constant for no_update returns with many outputs


def build_entity_options(schema_dict):
    base = [{"label": k, "value": k} for k in schema_dict["span-attribute"].keys()]
    base.append({"label": "Other…", "value": OTHER_SENTINEL})
    return base

def build_relation_options(schema_dict):
    base = [{"label": k, "value": k} for k in schema_dict["relation-type"].keys()]
    base.append({"label": "Other…", "value": OTHER_SENTINEL})
    return base

# -----------------------
# UI Builders
# -----------------------
def triple_row(i, entity_options, relation_options):
    """
    Build one triple row with inputs:
      - source_entity_name (text)
      - source_entity_attr (dropdown) + Other text
      - relation_type (dropdown) + Other text
      - sink_entity_name (text)
      - sink_entity_attr (dropdown) + Other text
    """
    return dbc.Card(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Source Entity Name"),
                            dbc.Input(
                                id={"type": "src-name", "index": i},
                                placeholder="e.g., FLC",
                                type="text",
                                debounce=True,
                            ),
                            dbc.Label("Source Entity Attr"),
                            dcc.Dropdown(
                                id={"type": "src-attr", "index": i},
                                options=entity_options,
                                placeholder="Choose type…",
                                clearable=True,
                            ),
                            html.Div(
                                [
                                    dbc.Label("Custom Source Attr"),
                                    dbc.Input(
                                        id={"type": "src-attr-other", "index": i},
                                        placeholder="Enter new entity type",
                                        type="text",
                                        debounce=True,
                                    ),
                                ],
                                id={"type": "src-attr-other-div", "index": i},
                                style={"display": "none"},
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Relation Type"),
                            dcc.Dropdown(
                                id={"type": "rel-type", "index": i},
                                options=relation_options,
                                placeholder="Choose relation…",
                                clearable=True,
                            ),
                            html.Div(
                                [
                                    dbc.Label("Custom Relation"),
                                    dbc.Input(
                                        id={"type": "rel-type-other", "index": i},
                                        placeholder="Enter new relation",
                                        type="text",
                                        debounce=True,
                                    ),
                                ],
                                id={"type": "rel-type-other-div", "index": i},
                                style={"display": "none"},
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Sink Entity Name"),
                            dbc.Input(
                                id={"type": "sink-name", "index": i},
                                placeholder='e.g., "flowering time"',
                                type="text",
                                debounce=True,
                            ),
                            dbc.Label("Sink Entity Attr"),
                            dcc.Dropdown(
                                id={"type": "sink-attr", "index": i},
                                options=entity_options,
                                placeholder="Choose type…",
                                clearable=True,
                            ),
                            html.Div(
                                [
                                    dbc.Label("Custom Sink Attr"),
                                    dbc.Input(
                                        id={"type": "sink-attr-other", "index": i},
                                        placeholder="Enter new entity type",
                                        type="text",
                                        debounce=True,
                                    ),
                                ],
                                id={"type": "sink-attr-other-div", "index": i},
                                style={"display": "none"},
                            ),
                        ],
                        md=4,
                    ),
                ],
                className="g-3",
            )
        ],
        body=True,
        className="mb-2",
    )

def sidebar():
    """
    Build the sidebar with information tabs.
    Reads content from markdown files in the assets folder.
    """
    # Read markdown files from assets folder
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    
    # Read help content
    try:
        with open(os.path.join(assets_dir, "help.md"), "r", encoding="utf-8") as f:
            help_text = f.read()
        help_md = dcc.Markdown(help_text)
    except FileNotFoundError:
        help_md = dcc.Markdown("Help content not found.")
    
    # Read and build schema content with dynamic JSON
    try:
        with open(os.path.join(assets_dir, "schema.md"), "r", encoding="utf-8") as f:
            schema_template = f.read()
        
        # Build the JSON code block
        schema_json_str = json.dumps(SCHEMA_JSON, indent=2)
        schema_json_block = f"```json\n{schema_json_str}\n```\n\n"
        
        # Replace placeholder with actual JSON
        schema_text = schema_template.replace("{SCHEMA_JSON}", schema_json_block)
        schema_md = dcc.Markdown(schema_text)
    except FileNotFoundError:
        schema_md = dcc.Markdown("Schema content not found.")
    
    # Read Q&A content
    try:
        with open(os.path.join(assets_dir, "qa.md"), "r", encoding="utf-8") as f:
            qa_text = f.read()
        qa_md = dcc.Markdown(qa_text)
    except FileNotFoundError:
        qa_md = dcc.Markdown("Q&A content not found.")
    
    # Read DB Model content
    try:
        with open(os.path.join(assets_dir, "db_model.md"), "r", encoding="utf-8") as f:
            db_model_text = f.read()
        db_model_md = dcc.Markdown(db_model_text)
    except FileNotFoundError:
        db_model_md = dcc.Markdown("Database model content not found.")
    

    
    info_tabs = dbc.Card(
        [
            dbc.Tabs(
                [
                    dbc.Tab(help_md, label="Help", tab_id="help"),
                    dbc.Tab(schema_md, label="Schema", tab_id="schema"),
                    dbc.Tab(qa_md, label="Q&A", tab_id="qa"),
                    dbc.Tab(db_model_md, label="DB Model", tab_id="dbmodel"),
                ],
                id="info-tabs",
                active_tab="help",
            )
        ],
        body=True,
        className="mb-3"
    )
    
    # Create partner logos card if logos are configured
    if PARTNER_LOGOS:
        logo_elements = []
        for logo in PARTNER_LOGOS:
            # Construct the asset path - Dash serves files from /assets/ directory
            logo_url = logo.get("url", "")
            if logo_url and not logo_url.startswith(("http://", "https://", "/")):
                # Local file - prepend with /assets/ path
                logo_url = f"/assets/{logo_url}"
            
            logo_elements.append(
                dbc.Col(
                    html.Img(
                        src=logo_url,
                        alt=logo.get("alt", logo.get("name", "Partner Logo")),
                        style={
                            "maxHeight": "80px",  # Reduced from 120px
                            "maxWidth": "100%",
                            "objectFit": "contain"
                        },
                        title=logo.get("name", "")
                    ),
                    className="text-center d-flex align-items-center justify-content-center",
                    xs=12, sm=6, md=4
                )
            )
        
        logos_card = dbc.Card(
            dbc.CardBody(
                [
                    html.H6("Partner Institutions", className="text-center mb-2 text-muted", style={"fontSize": "0.9rem"}),
                    dbc.Row(
                        logo_elements,
                        className="g-2",  # Reduced from g-3 to g-2 for less spacing
                        justify="center"
                    )
                ],
                style={"padding": "0.75rem"}  # Reduced padding from default (usually 1.25rem)
            ),
            className="mb-3"
        )
        
        return html.Div([info_tabs, logos_card])
    
    return info_tabs

# -----------------------
# App & Layout
# -----------------------
external_stylesheets = [dbc.themes.BOOTSTRAP]
app: Dash = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = APP_TITLE
server = app.server  # for gunicorn, if needed

app.layout = dbc.Container(
    [
        dcc.Store(id="choices-store"),
        dcc.Store(id="triple-count", data=1),
        dcc.Store(id="email-store", storage_type="session"),
        dcc.Store(id="doi-metadata-store"),
        dcc.Store(id="admin-auth-store", storage_type="session"),
        dcc.Store(id="projects-store"),
        dcc.Store(id="delete-project-id-store"),  # Store project ID to delete
        dcc.Store(id="upload-project-id-store"),  # Store project ID for upload
        dcc.Store(id="pdf-download-project-id", data=None),  # Store project ID for PDF download tracking
        dcc.Store(id="lit-search-selected-papers", data=[]),  # Store selected papers
        dcc.Interval(id="load-trigger", n_intervals=0, interval=200, max_intervals=1),
        dcc.Interval(id="pdf-download-progress-interval", interval=2000, disabled=True),  # Poll every 2 seconds
        
        # Modal for exporting DOIs from literature search
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Export Selected DOIs")),
                dbc.ModalBody(
                    [
                        html.H6("Create New Project or Add to Existing", className="mb-3"),
                        dbc.RadioItems(
                            id="export-doi-action",
                            options=[
                                {"label": "Create new project", "value": "new"},
                                {"label": "Add to existing project", "value": "existing"},
                                {"label": "Copy to clipboard", "value": "clipboard"},
                            ],
                            value="new",
                            className="mb-3",
                        ),
                        html.Div(
                            [
                                dbc.Label("Project Name"),
                                dbc.Input(id="export-new-project-name", placeholder="Enter project name"),
                                dbc.Label("Description (optional)", className="mt-2"),
                                dbc.Input(id="export-new-project-description", placeholder="Enter project description"),
                            ],
                            id="export-new-project-fields",
                            className="mb-3",
                        ),
                        html.Div(
                            [
                                dbc.Label("Select Target Project"),
                                dcc.Dropdown(
                                    id="export-target-project",
                                    placeholder="Select a project...",
                                ),
                            ],
                            id="export-existing-project-fields",
                            style={"display": "none"},
                            className="mb-3",
                        ),
                        html.Div(id="export-selected-dois-list", className="mb-3"),
                        html.Div(id="export-doi-message"),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="export-doi-cancel", color="secondary"),
                        dbc.Button("Export", id="export-doi-confirm", color="primary"),
                    ]
                ),
            ],
            id="export-doi-modal",
            is_open=False,
            size="lg",
        ),
        
        # Modal for project deletion options
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Delete Project")),
                dbc.ModalBody(
                    [
                        html.P(id="delete-project-triple-count", className="mb-3"),
                        dbc.Label("What should happen to associated triples?"),
                        dbc.RadioItems(
                            id="delete-project-option",
                            options=[
                                {"label": "Keep triples as uncategorized (set project to NULL)", "value": "keep"},
                                {"label": "Reassign triples to another project", "value": "reassign"},
                                {"label": "Delete all associated triples", "value": "delete"},
                            ],
                            value="keep",
                            className="mb-3",
                        ),
                        html.Div(
                            [
                                dbc.Label("Target Project"),
                                dcc.Dropdown(
                                    id="delete-project-target",
                                    placeholder="Select target project...",
                                ),
                            ],
                            id="delete-project-target-container",
                            style={"display": "none"},
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="delete-project-cancel", color="secondary"),
                        dbc.Button("Delete Project", id="delete-project-confirm", color="danger"),
                    ]
                ),
            ],
            id="delete-project-modal",
            is_open=False,
        ),

        # Modal for PDF upload
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Upload PDFs")),
                dbc.ModalBody(
                    [
                        html.P([
                            "Upload PDF files manually for this project. ",
                            html.Strong("For each file selected, you must provide the corresponding DOI."),
                            " Files will be named according to their DOI using the generate_doi_hash function."
                        ], className="mb-3"),
                        
                        html.Div([
                            dbc.Label("Option 1: Single DOI for all files (use when uploading multiple files for the same paper)"),
                            dbc.Input(
                                id="upload-single-doi-input",
                                type="text",
                                placeholder="10.1234/example",
                                className="mb-2",
                            ),
                            html.Small("If provided, this DOI will be used for all uploaded files.", className="text-muted"),
                        ], className="mb-3"),
                        
                        html.Hr(),
                        
                        html.Div([
                            dbc.Label("Option 2: Upload files and specify DOI for each one below"),
                            dcc.Upload(
                                id="upload-pdf-files",
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select PDF Files')
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'margin': '10px 0'
                                },
                                multiple=True  # Allow multiple files
                            ),
                        ], className="mb-3"),
                        
                        html.Div(id="upload-file-doi-inputs", className="mb-3"),
                        html.Div(id="upload-status-message"),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="upload-pdf-cancel", color="secondary"),
                        dbc.Button("Upload", id="upload-pdf-confirm", color="warning"),
                    ]
                ),
            ],
            id="upload-pdf-modal",
            is_open=False,
            size="lg",
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2(APP_TITLE, className="mt-3 mb-4"),

                        dcc.Tabs(
                            id="main-tabs",
                            value="tab-literature" if ENABLE_LITERATURE_SEARCH else "tab-annotate",
                            children=[tab for tab in [
                                dcc.Tab(
                                    label="Literature Search",
                                    value="tab-literature",
                                    children=[
                                        dbc.Card(
                                            [
                                                html.H5("Semantic Paper Discovery", className="mb-3"),
                                                
                                                # Authentication message - shown when not authenticated
                                                html.Div(
                                                    id="lit-search-auth-required",
                                                    children=[
                                                        dbc.Alert(
                                                            [
                                                                html.I(className="bi bi-lock me-2"),
                                                                html.Strong("Authentication Required"),
                                                                html.Br(),
                                                                "Please login via the ",
                                                                html.Strong("Admin"),
                                                                " tab to access the Literature Search feature."
                                                            ],
                                                            color="info",
                                                            className="text-center"
                                                        ),
                                                    ],
                                                    style={"display": "block"}
                                                ),
                                                
                                                # Search content - hidden until authenticated
                                                # Search content - hidden until authenticated
                                                html.Div(
                                                    id="lit-search-content",
                                                    style={"display": "none"},
                                                    children=[
                                                        
                                                        html.P(
                                                            "Search for relevant papers from Semantic Scholar and arXiv using natural language queries.",
                                                            className="text-muted mb-4"
                                                        ),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Search Query", style={"fontWeight": "bold"}),
                                                                        dbc.Input(
                                                                            id="lit-search-query",
                                                                            placeholder="e.g., AI in drug discovery, climate change ethics, CRISPR gene editing",
                                                                            type="text",
                                                                            debounce=True,
                                                                        ),
                                                                        html.Small(
                                                                            "Enter a natural language query to find relevant papers",
                                                                            className="text-muted"
                                                                        ),
                                                                    ],
                                                                    md=9,
                                                                ),
                                                                dbc.Col(
                                                                    [
                                                                        html.Br(),
                                                                        dbc.Button(
                                                                            "Search Papers",
                                                                            id="btn-search-papers",
                                                                            color="primary",
                                                                            className="w-100",
                                                                        ),
                                                                    ],
                                                                    md=3,
                                                                ),
                                                            ],
                                                            className="mb-4",
                                                        ),
                                                        
                                                        # Export controls (shown when papers are displayed)
                                                        html.Div(
                                                            id="lit-search-export-controls",
                                                            children=[
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Col(
                                                                            [
                                                                                dbc.Button(
                                                                                    "Select All",
                                                                                    id="btn-select-all-papers",
                                                                                    color="secondary",
                                                                                    size="sm",
                                                                                    className="me-2",
                                                                                ),
                                                                                dbc.Button(
                                                                                    "Deselect All",
                                                                                    id="btn-deselect-all-papers",
                                                                                    color="secondary",
                                                                                    size="sm",
                                                                                    className="me-2",
                                                                                ),
                                                                                dbc.Button(
                                                                                    [
                                                                                        html.I(className="bi bi-download me-1"),
                                                                                        "Export Selected DOIs"
                                                                                    ],
                                                                                    id="btn-export-selected-dois",
                                                                                    color="success",
                                                                                    size="sm",
                                                                                    disabled=True,
                                                                                ),
                                                                            ],
                                                                            md=12,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                html.Div(id="selected-papers-count", className="mb-2"),
                                                            ],
                                                            style={"display": "none"},
                                                        ),
                                                        
                                                        dcc.Loading(
                                                            id="loading-search",
                                                            type="default",
                                                            children=[
                                                                html.Div(id="search-status", className="mb-3"),
                                                                html.Div(id="search-results"),
                                                            ],
                                                        ),
                                                    ],
                                                ),
                                            ],
                                            body=True,
                                        )
                                    ],
                                ) if ENABLE_LITERATURE_SEARCH else None,
                                dcc.Tab(
                                    label="Annotate",
                                    value="tab-annotate",
                                    children=[
                                        dbc.Row(
                                            [
                                                # Left column: Annotation form
                                                dbc.Col(
                                                    [
                                                        dbc.Card(
                                                            [
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Col(
                                                                            [
                                                                                dbc.Label("Your Email (required)", style={"fontWeight": "bold"}),
                                                                                dbc.Input(
                                                                                    id="contributor-email",
                                                                                    placeholder="email@example.com",
                                                                                    type="email",
                                                                                    debounce=True,
                                                                                    required=True,
                                                                                ),
                                                                                html.Small(
                                                                                    id="email-validation",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            md=12,
                                                                        ),
                                                                    ],
                                                                    className="g-3 mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Col(
                                                                            [
                                                                                dbc.Label("Select Project (optional)"),
                                                                                dcc.Dropdown(
                                                                                    id="project-selector",
                                                                                    placeholder="Choose a project or annotate freely...",
                                                                                    clearable=True,
                                                                                ),
                                                                                html.Small(
                                                                                    id="project-info",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            md=6,
                                                                        ),
                                                                        dbc.Col(
                                                                            [
                                                                                dbc.Label("Select DOI from Project"),
                                                                                dcc.Dropdown(
                                                                                    id="project-doi-selector",
                                                                                    placeholder="Select a DOI...",
                                                                                    clearable=True,
                                                                                    disabled=True,
                                                                                ),
                                                                            ],
                                                                            md=6,
                                                                        ),
                                                                    ],
                                                                    className="g-3 mt-2",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Col(
                                                                            [
                                                                                dbc.Label("DOI or Literature Link"),
                                                                                dbc.InputGroup(
                                                                                    [
                                                                                        dbc.Input(
                                                                                            id="literature-link",
                                                                                            placeholder="e.g., 10.1234/example or https://doi.org/...",
                                                                                            type="text",
                                                                                            debounce=True,
                                                                                        ),
                                                                                        dbc.Button(
                                                                                            "Validate DOI",
                                                                                            id="btn-validate-doi",
                                                                                            color="info",
                                                                                            outline=True,
                                                                                        ),
                                                                                    ],
                                                                                ),
                                                                                html.Small(
                                                                                    id="doi-validation",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            md=12,
                                                                        ),
                                                                    ],
                                                                    className="g-3 mt-2",
                                                                ),
                                                                html.Div(
                                                                    id="doi-metadata-display",
                                                                    className="mt-2",
                                                                    style={"display": "none"},
                                                                ),
                                                                html.Hr(),
                                                                dbc.Label("Sentence"),
                                                                dcc.Textarea(
                                                                    id="sentence-text",
                                                                    placeholder='e.g., "gene FLC regulates flowering time".',
                                                                    style={"width": "100%", "height": "100px"},
                                                                ),
                                                                html.Div(className="mt-3"),
                                                                dbc.ButtonGroup(
                                                                    [
                                                                        dbc.Button("Add triple", id="btn-add-triple", color="primary"),
                                                                        dbc.Button("Remove last triple", id="btn-remove-triple", color="secondary"),
                                                                        dbc.Button("Save", id="btn-save", color="success"),
                                                                        dbc.Button("Reset", id="btn-reset", color="warning"),
                                                                    ],
                                                                    size="sm",
                                                                    className="mb-2",
                                                                ),
                                                                html.Div(id="triples-container"),
                                                                html.Div(id="save-message", className="mt-2"),
                                                            ],
                                                            body=True,
                                                        )
                                                    ],
                                                    md=6,
                                                ),
                                                # Right column: PDF Viewer
                                                dbc.Col(
                                                    [
                                                        dbc.Card(
                                                            [
                                                                html.H5("PDF Viewer", className="mb-3"),
                                                                html.Div(
                                                                    id="pdf-viewer-container",
                                                                    children=[
                                                                        html.P(
                                                                            "Select a DOI from a project to view the PDF here.",
                                                                            className="text-muted text-center",
                                                                            style={"padding": "50px"}
                                                                        )
                                                                    ],
                                                                    style={
                                                                        "height": "1000px",
                                                                        "overflow": "auto",
                                                                        "border": "1px solid #dee2e6",
                                                                        "borderRadius": "4px"
                                                                    }
                                                                ),
                                                            ],
                                                            body=True,
                                                        )
                                                    ],
                                                    md=6,
                                                ),
                                            ],
                                            className="g-3",
                                        ),
                                    ],
                                ),
                                dcc.Tab(
                                    label="Browse",
                                    value="tab-browse",
                                    children=[
                                        dbc.Card(
                                            [
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            [
                                                                dbc.Label("Filter by Project"),
                                                                dcc.Dropdown(
                                                                    id="browse-project-filter",
                                                                    placeholder="All projects (no filter)",
                                                                    clearable=True,
                                                                ),
                                                            ],
                                                            md=6,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                html.Br(),
                                                                dbc.Button("Refresh", id="btn-refresh", color="secondary"),
                                                            ],
                                                            md=6,
                                                        ),
                                                    ],
                                                    className="mb-2",
                                                ),
                                                html.Div(id="recent-table"),
                                            ],
                                            body=True,
                                        )
                                    ],
                                ),
                                dcc.Tab(
                                    label="Admin",
                                    value="tab-admin",
                                    children=[
                                        dbc.Card(
                                            [
                                                html.H5("Admin Panel", className="mb-3"),
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            [
                                                                dbc.Label("Admin Email"),
                                                                dbc.Input(
                                                                    id="admin-email",
                                                                    placeholder="admin@example.com",
                                                                    type="email",
                                                                ),
                                                            ],
                                                            md=6,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                dbc.Label("Admin Password"),
                                                                dbc.Input(
                                                                    id="admin-password",
                                                                    placeholder="Password",
                                                                    type="password",
                                                                ),
                                                            ],
                                                            md=6,
                                                        ),
                                                    ],
                                                    className="g-3 mb-3",
                                                ),
                                                dbc.Row([
                                                    dbc.Col([
                                                        dbc.Button("Login", id="btn-admin-login", color="primary"),
                                                    ], width="auto"),
                                                    dbc.Col([
                                                        dbc.Button("Logout", id="btn-admin-logout", color="secondary", style={"display": "none"}),
                                                    ], width="auto"),
                                                ], className="mb-3"),
                                                html.Div(id="admin-auth-message", className="mb-3"),
                                                html.Hr(),
                                                
                                                html.Div(
                                                    id="admin-panel-content",
                                                    style={"display": "none"},
                                                    children=[
                                                        html.H6("Project Management", className="mb-3"),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Project Name"),
                                                                        dbc.Input(id="new-project-name", placeholder="Project Name"),
                                                                    ],
                                                                    md=6,
                                                                ),
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Description"),
                                                                        dbc.Input(id="new-project-description", placeholder="Project Description"),
                                                                    ],
                                                                    md=6,
                                                                ),
                                                            ],
                                                            className="g-3 mb-2",
                                                        ),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("DOI List (one per line)"),
                                                                        dcc.Textarea(
                                                                            id="new-project-doi-list",
                                                                            placeholder="10.1234/example1\n10.1234/example2\n...",
                                                                            style={"width": "100%", "height": "100px"},
                                                                        ),
                                                                    ],
                                                                    md=12,
                                                                ),
                                                            ],
                                                            className="g-3 mb-3",
                                                        ),
                                                        dbc.Button("Create Project", id="btn-create-project", color="success", className="mb-3"),
                                                        html.Div(id="project-message", className="mb-3"),
                                                        
                                                        html.H6("Existing Projects", className="mb-2 mt-3"),
                                                        dbc.Button("Refresh Projects", id="btn-refresh-projects", color="secondary", size="sm", className="mb-2"),
                                                        html.Div(id="projects-list", className="mb-3"),
                                                        
                                                        html.Div(id="pdf-download-progress-container", className="mb-3"),
                                                        html.Hr(),
                                                        
                                                        html.H6("Edit/Delete Triples", className="mb-3"),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Filter by Project"),
                                                                        dcc.Dropdown(
                                                                            id="triple-editor-project-filter",
                                                                            placeholder="All triples (no filter)",
                                                                            clearable=True,
                                                                        ),
                                                                    ],
                                                                    md=6,
                                                                ),
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Triple ID"),
                                                                        dbc.InputGroup(
                                                                            [
                                                                                dbc.Input(id="triple-id-input", placeholder="Triple ID", type="number"),
                                                                                dbc.Button("Load Triple", id="btn-load-triple", color="info", outline=True),
                                                                            ]
                                                                        ),
                                                                    ],
                                                                    md=6,
                                                                ),
                                                            ],
                                                            className="g-3 mb-3",
                                                        ),
                                                        html.Div(id="triple-load-message", className="mb-2"),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Source Entity Name"),
                                                                        dbc.Input(id="edit-src-name", placeholder="Source entity name"),
                                                                    ],
                                                                    md=6,
                                                                ),
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Source Entity Attribute"),
                                                                        dcc.Dropdown(
                                                                            id="edit-src-attr",
                                                                            placeholder="Select attribute...",
                                                                            clearable=True,
                                                                        ),
                                                                    ],
                                                                    md=6,
                                                                ),
                                                            ],
                                                            className="g-3 mb-2",
                                                        ),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Relation Type"),
                                                                        dcc.Dropdown(
                                                                            id="edit-rel-type",
                                                                            placeholder="Select relation...",
                                                                            clearable=True,
                                                                        ),
                                                                    ],
                                                                    md=12,
                                                                ),
                                                            ],
                                                            className="g-3 mb-2",
                                                        ),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Sink Entity Name"),
                                                                        dbc.Input(id="edit-sink-name", placeholder="Sink entity name"),
                                                                    ],
                                                                    md=6,
                                                                ),
                                                                dbc.Col(
                                                                    [
                                                                        dbc.Label("Sink Entity Attribute"),
                                                                        dcc.Dropdown(
                                                                            id="edit-sink-attr",
                                                                            placeholder="Select attribute...",
                                                                            clearable=True,
                                                                        ),
                                                                    ],
                                                                    md=6,
                                                                ),
                                                            ],
                                                            className="g-3 mb-3",
                                                        ),
                                                        dbc.ButtonGroup(
                                                            [
                                                                dbc.Button("Update Triple", id="btn-update-triple", color="warning"),
                                                                dbc.Button("Delete Triple", id="btn-delete-triple", color="danger"),
                                                            ],
                                                            className="mb-3",
                                                        ),
                                                        html.Div(id="triple-edit-message"),
                                                        
                                                        html.Hr(className="mt-4"),
                                                        html.H6("Database Export", className="mb-3"),
                                                        html.P("Export all triples from the database as JSON.", className="text-muted mb-3"),
                                                        dbc.Button(
                                                            [
                                                                html.I(className="bi bi-download me-2"),
                                                                "Export Triples Database"
                                                            ],
                                                            id="btn-export-triples",
                                                            color="info",
                                                            className="mb-3"
                                                        ),
                                                        html.Div(id="export-triples-message"),
                                                    ],
                                                ),
                                            ],
                                            body=True,
                                        )
                                    ],
                                ),
                            ] if tab is not None],
                        ),
                    ],
                    md=12,  # Changed from md=8 to full width
                ),
            ],
            className="g-4",
        ),
        # Move sidebar below main content
        dbc.Row(
            [
                dbc.Col(
                    [
                        sidebar()
                    ],
                    md=12,
                ),
            ],
            className="g-4 mt-3",
        ),
        html.Footer(
            dbc.Row(
                dbc.Col(
                    html.Small(f"© {datetime.now().year} Text2Trait"),
                    className="text-center text-muted my-3",
                )
            )
        ),
    ],
    fluid=True,
)

# -----------------------
# Proxy Routes for PDF Streaming
# -----------------------
# These routes proxy PDF requests from the frontend to the internal backend (127.0.0.1:5001)
# This keeps the backend private and unexposed to remote clients

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


# Literature Search Authentication check - use Admin panel auth
@app.callback(
    Output("lit-search-auth-required", "style"),
    Output("lit-search-content", "style"),
    Input("admin-auth-store", "data"),
    Input("main-tabs", "value"),
    prevent_initial_call=False,
)
def check_lit_search_auth(auth_data, active_tab):
    """Check if user is authenticated via Admin panel and show/hide Literature Search content"""
    # Only apply when Literature Search tab is active
    if active_tab != "tab-literature":
        return no_update, no_update
    
    if auth_data and ("email" in auth_data or "token" in auth_data):
        # User is authenticated, show search content and hide auth required message
        return {"display": "none"}, {"display": "block"}
    else:
        # User not authenticated, show auth required message and hide search content
        return {"display": "block"}, {"display": "none"}


# Literature Search callback
@app.callback(
    Output("search-status", "children"),
    Output("search-results", "children"),
    Output("lit-search-selected-papers", "data"),
    Output("lit-search-export-controls", "style"),
    Input("btn-search-papers", "n_clicks"),
    State("lit-search-query", "value"),
    prevent_initial_call=True,
)
def perform_literature_search(n_clicks, query):
    """
    Callback to perform literature search when button is clicked.
    Displays the execution pipeline for AutoResearch, DeepResearch, and DELM.
    """
    if not query or not query.strip():
        return (
            dbc.Alert("Please enter a search query", color="warning"),
            None,
            [],
            {"display": "none"}
        )

    try:
        # Perform search
        result = literature_search.search_papers(query.strip(), top_k=10)

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
                    {"display": "none"}
                )
            return (
                dbc.Alert(result['message'], color="danger"),
                None,
                [],
                {"display": "none"}
            )

        papers = result['papers']

        if not papers:
            return (
                dbc.Alert("No papers found. Try a different query.", color="info"),
                None,
                [],
                {"display": "none"}
            )

        # Create execution log display
        execution_log = result.get('execution_log', [])
        log_display = create_execution_log_display(execution_log)

        # Create status message with execution log
        status = html.Div([
            dbc.Alert(
                [
                    html.Strong(result['message']),
                    html.Br(),
                    html.Small(f"Total found: {result['total_found']} | Unique: {result['total_unique']} | Displaying: {result['returned']}")
                ],
                color="success"
            ),
            log_display
        ])

        # Store paper data for later use
        papers_data = []
        
        # Create results table
        results_content = []

        for i, paper in enumerate(papers, 1):
            # Store paper data including DOI
            papers_data.append({
                'index': i,
                'doi': paper.get('doi', ''),
                'title': paper.get('title', 'N/A'),
                'authors': paper.get('authors', []),
                'year': paper.get('year', 'N/A'),
                'source': paper.get('source', 'N/A')
            })
            
            # Format authors
            authors_text = ", ".join(paper.get('authors', [])[:3])
            if len(paper.get('authors', [])) > 3:
                authors_text += " et al."

            # Format year
            year_text = str(paper.get('year', 'N/A'))

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
                else:
                    doi_link = html.A(
                        doi,
                        href=f"https://doi.org/{doi}",
                        target="_blank",
                        className="text-decoration-none"
                    )
            else:
                doi_link = html.Span("N/A", className="text-muted")

            # Create paper card with checkbox
            paper_card = dbc.Card(
                [
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Checkbox(
                                                id={"type": "paper-checkbox", "index": i},
                                                className="form-check-input-lg",
                                                value=False,
                                            ),
                                        ],
                                        width="auto",
                                        className="d-flex align-items-center",
                                    ),
                                    dbc.Col(
                                        [
                                            html.H6(
                                                f"{i}. {paper.get('title', 'N/A')}",
                                                className="mb-2",
                                                style={"fontWeight": "bold"}
                                            ),
                                        ],
                                    ),
                                ],
                                className="g-2",
                            ),
                            html.P(
                                [
                                    html.Strong("Authors: "),
                                    authors_text,
                                    html.Br(),
                                    html.Strong("Year: "),
                                    year_text,
                                    html.Br(),
                                    html.Strong("Source: "),
                                    paper.get('source', 'N/A'),
                                    html.Br(),
                                    html.Strong("DOI: "),
                                    doi_link,
                                ],
                                className="mb-2 ms-5",
                                style={"fontSize": "0.9rem"}
                            ),
                            dbc.Collapse(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.Strong("Abstract:"),
                                            html.P(
                                                paper.get('abstract_snippet', 'No abstract available'),
                                                className="mt-2",
                                                style={"fontSize": "0.85rem"}
                                            ),
                                        ]
                                    ),
                                    color="light",
                                ),
                                id=f"collapse-paper-{i}",
                                is_open=False,
                                className="ms-5",
                            ),
                            dbc.Button(
                                "Show Abstract",
                                id=f"btn-toggle-paper-{i}",
                                color="link",
                                size="sm",
                                className="mt-2 p-0 ms-5",
                            ),
                        ]
                    )
                ],
                className="mb-3",
                style={"borderLeft": "3px solid #007bff"}
            )

            results_content.append(paper_card)

        return status, html.Div(results_content), papers_data, {"display": "block"}

    except Exception as e:
        logger.error(f"Literature search error: {e}")
        return (
            dbc.Alert(f"Search failed: {str(e)}", color="danger"),
            None,
            [],
            {"display": "none"}
        )


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
        chevron_class = "bi bi-chevron-up" if new_state else "bi bi-chevron-down"
        return new_state, chevron_class + " " + "text-muted" + " " + "float-end"
    return is_open, "bi bi-chevron-down text-muted float-end"


# Callbacks for paper abstract toggling
for i in range(1, 11):
    @app.callback(
        Output(f"collapse-paper-{i}", "is_open"),
        Output(f"btn-toggle-paper-{i}", "children"),
        Input(f"btn-toggle-paper-{i}", "n_clicks"),
        State(f"collapse-paper-{i}", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_collapse(n, is_open, idx=i):
        if n:
            return not is_open, "Hide Abstract" if not is_open else "Show Abstract"
        return is_open, "Show Abstract"


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
        
        # Create DOI list display
        doi_list_items = []
        for paper in selected_papers:
            doi = paper.get('doi', 'N/A')
            title = paper.get('title', 'N/A')
            doi_list_items.append(
                html.Li([
                    html.Strong(doi),
                    html.Br(),
                    html.Small(title, className="text-muted")
                ])
            )
        
        doi_list_display = html.Div([
            html.H6(f"Selected DOIs ({len(selected_papers)}):"),
            html.Ul(doi_list_items, style={"maxHeight": "200px", "overflowY": "auto"})
        ])
        
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
    
    # Use email/password from admin auth (not token-based for now)
    # Get selected DOIs
    selected_dois = [
        paper['doi'] for i, paper in enumerate(papers_data)
        if i < len(checkbox_values) and checkbox_values[i] and paper.get('doi')
    ]
    
    if not selected_dois:
        return dbc.Alert("No DOIs to export", color="warning")
    
    # Handle clipboard action
    if action == "clipboard":
        doi_text = "\n".join(selected_dois)
        return dbc.Alert([
            html.Strong("Copy these DOIs:"),
            html.Pre(doi_text, style={"marginTop": "10px", "padding": "10px", "backgroundColor": "#f8f9fa"})
        ], color="info")
    
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
                    return dbc.Alert(f"Project created successfully! ID: {result.get('project_id')}", color="success")
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
                    msg = f"Added {len(new_dois)} new DOI(s) to project"
                    if duplicates > 0:
                        msg += f" ({duplicates} duplicate(s) skipped)"
                    return dbc.Alert(msg, color="success")
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
                doi_metadata, project_id,  # Add project_id parameter
                src_names, src_attrs, src_other,
                rel_types, rel_other,
                sink_names, sink_attrs, sink_other):
    if not sentence_text or not sentence_text.strip():
        return dbc.Alert("Sentence is required.", color="danger", dismissable=True, duration=4000)

    if not email_validated:
        return dbc.Alert("Please enter a valid email address.", color="danger", dismissable=True, duration=4000)

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
    prevent_initial_call=False,
)
def refresh_recent(btn_clicks, interval_trigger, tab_value, project_filter):
    # Only refresh if Browse tab is active
    if tab_value != "tab-browse" and ctx.triggered_id == "main-tabs":
        return no_update
    
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
        # Add project_id filter if selected
        url = API_RECENT
        if project_filter:
            url = f"{API_RECENT}?project_id={project_filter}"
        
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

        columns = [{"name": k, "id": k} for k in rows[0].keys()]
        return dash_table.DataTable(
            data=rows,
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

# Show project info when selected and populate DOI list
@app.callback(
    Output("project-info", "children"),
    Output("project-doi-selector", "options"),
    Output("project-doi-selector", "disabled"),
    Input("project-selector", "value"),
    State("projects-store", "data"),
    prevent_initial_call=True,
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
    
    # Populate DOI dropdown
    doi_list = project.get("doi_list", [])
    doi_options = [{"label": doi, "value": doi} for doi in doi_list]
    
    return info_text, doi_options, False


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
                    viewer_url = f"/pdf-viewer?project_id={project_id}&filename={pdf_filename}&api_base={API_BASE}"
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
                    proxy_pdf_url = f"/proxy/pdf/{project_id}/{pdf_filename}"
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
    Input("btn-create-project", "n_clicks"),
    State("new-project-name", "value"),
    State("new-project-description", "value"),
    State("new-project-doi-list", "value"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def create_project_callback(n_clicks, name, description, doi_list_text, auth_data):
    if not auth_data:
        return dbc.Alert("Please login first", color="danger")
    
    if not name or not doi_list_text:
        return dbc.Alert("Project name and DOI list are required", color="danger")
    
    # Parse DOI list
    doi_list = [doi.strip() for doi in doi_list_text.split("\n") if doi.strip()]
    
    try:
        payload = {
            "email": auth_data["email"],
            "password": auth_data["password"],
            "name": name,
            "description": description or "",
            "doi_list": doi_list
        }
        r = requests.post(API_ADMIN_PROJECTS, json=payload, timeout=10)
        if r.ok:
            result = r.json()
            if result.get("ok"):
                return dbc.Alert(f"Project created successfully! ID: {result.get('project_id')}", color="success")
            else:
                return dbc.Alert(f"Failed: {result.get('error', 'Unknown error')}", color="danger")
        else:
            return dbc.Alert(f"Failed: {r.status_code} - {r.text[:200]}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")

# Display projects list
@app.callback(
    Output("projects-list", "children"),
    Input("btn-refresh-projects", "n_clicks"),
    Input("btn-create-project", "n_clicks"),
    Input("delete-project-confirm", "n_clicks"),
    State("admin-auth-store", "data"),
    prevent_initial_call=False,
)
def display_projects_list(refresh_clicks, create_clicks, delete_clicks, auth_data):
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
                                        dbc.Button("Download PDFs", id={"type": "download-project-pdfs", "index": p["id"]}, 
                                                 color="success", size="sm", outline=True),
                                        dbc.Button("Upload PDFs", id={"type": "upload-project-pdfs", "index": p["id"]}, 
                                                 color="warning", size="sm", outline=True),
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
    doi_items = [html.Li(doi) for doi in doi_list]
    
    return dbc.Alert(
        [
            html.H6(f"DOIs in {project['name']}:", className="alert-heading"),
            html.Hr(),
            html.Ul(doi_items),
        ],
        color="info",
        dismissable=True,
    )

# Handle Download PDFs button click - Start download and enable progress polling
@app.callback(
    Output("pdf-download-progress-container", "children"),
    Output("pdf-download-project-id", "data"),
    Output("pdf-download-progress-interval", "disabled"),
    Input({"type": "download-project-pdfs", "index": ALL}, "n_clicks"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def start_download_project_pdfs(n_clicks_list, auth_data):
    """Start PDF download and enable progress polling"""
    if not any(n_clicks_list):
        return no_update, no_update, no_update
    
    if not auth_data:
        print("[Frontend] PDF Download: No auth data")
        return dbc.Alert("Please login first", color="danger"), None, True
    
    email = auth_data.get("email")
    password = auth_data.get("password")
    if not email or not password:
        print("[Frontend] PDF Download: Missing credentials")
        return dbc.Alert("Please login first", color="danger"), None, True
    
    # Find which button was clicked
    trigger = ctx.triggered_id
    if not trigger:
        return no_update, no_update, no_update
    
    project_id = trigger["index"]
    
    print(f"[Frontend] PDF Download: Starting download for project {project_id}")
    
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
            
            # Show initial message and enable polling
            initial_message = dbc.Alert(
                [
                    html.H6("PDF Download Started", className="alert-heading"),
                    html.Hr(),
                    html.P(f"Downloading PDFs for {data.get('total_dois', 0)} DOIs..."),
                    html.Div([
                        dbc.Spinner(size="sm"),
                        html.Span(" Progress updates will appear below...", style={"margin-left": "10px"})
                    ], style={"display": "flex", "align-items": "center"})
                ],
                color="info",
                dismissable=False
            )
            
            # Return: message, project_id (to track), enable interval
            return initial_message, project_id, False
        else:
            error_msg = r.json().get("error", "Unknown error") if r.headers.get("content-type") == "application/json" else f"HTTP {r.status_code}"
            print(f"[Frontend] PDF Download: Failed to start - {error_msg}")
            return dbc.Alert(f"Download failed: {error_msg}", color="danger", dismissable=True), None, True
            
    except Exception as e:
        print(f"[Frontend] PDF Download: Error starting download - {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True), None, True

# Poll for PDF download progress
@app.callback(
    Output("pdf-download-progress-container", "children", allow_duplicate=True),
    Output("pdf-download-progress-interval", "disabled", allow_duplicate=True),
    Output("pdf-download-project-id", "data", allow_duplicate=True),
    Input("pdf-download-progress-interval", "n_intervals"),
    State("pdf-download-project-id", "data"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def poll_pdf_download_progress(n_intervals, project_id, auth_data):
    """Poll the backend for PDF download progress"""
    if not project_id:
        return no_update, no_update, no_update
    
    if not auth_data:
        return no_update, True, None  # Disable polling if not authenticated
    
    print(f"[Frontend] PDF Download: Polling progress for project {project_id} (interval {n_intervals})")
    
    try:
        # Get progress from backend
        r = requests.get(
            f"{API_BASE}/api/admin/projects/{project_id}/download-pdfs/status",
            timeout=5
        )
        
        if r.status_code == 404:
            # Not started or no progress info
            print(f"[Frontend] PDF Download: No progress info for project {project_id}")
            return no_update, True, None  # Disable polling
        
        if not r.ok:
            print(f"[Frontend] PDF Download: Error fetching progress - {r.status_code}")
            return no_update, no_update, no_update  # Keep polling
        
        data = r.json()
        status = data.get("status")
        total = data.get("total", 0)
        current = data.get("current", 0)
        current_doi = data.get("current_doi", "")
        current_source = data.get("current_source", "")
        
        print(f"[Frontend] PDF Download: Status={status}, Progress={current}/{total}, Source={current_source}")
        
        if status == "running":
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
            
            # Fetch and display download configuration
            try:
                config_resp = requests.get(f"{API_BASE}/api/pdf-download-config", timeout=3)
                if config_resp.ok:
                    config_data = config_resp.json()
                    sources = config_data.get("sources", [])
                    enabled_sources = [s for s in sources if s.get("enabled") and s.get("available")]
                    
                    if enabled_sources:
                        progress_content.extend([
                            html.Br(),
                            html.Br(),
                            html.Strong("Active download mechanisms: "),
                            html.Br(),
                        ])
                        for src in enabled_sources:
                            progress_content.extend([
                                f"  • {src['name']}: {src['description']}",
                                html.Br(),
                            ])
            except Exception as e:
                print(f"[Frontend] Could not fetch PDF config: {e}")
            
            progress_message = dbc.Alert(
                [
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
                    ], className="mb-0"),
                ],
                color="info",
                dismissable=False
            )
            return progress_message, False, project_id  # Keep polling
        
        elif status == "completed":
            print(f"[Frontend] PDF Download: Completed!")
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
            
            return dbc.Alert(report_items, color="success", dismissable=True), True, None  # Disable polling
        
        elif status == "error":
            error_message = data.get("error_message", "Unknown error")
            print(f"[Frontend] PDF Download: Error - {error_message}")
            return dbc.Alert(f"Download error: {error_message}", color="danger", dismissable=True), True, None  # Disable polling
        
        else:
            # Unknown status
            return no_update, no_update, no_update
            
    except Exception as e:
        print(f"[Frontend] PDF Download: Error polling - {str(e)}")
        # Don't disable polling on error, might be temporary
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

# Export triples database
@app.callback(
    Output("export-triples-message", "children"),
    Input("btn-export-triples", "n_clicks"),
    State("admin-auth-store", "data"),
    prevent_initial_call=True,
)
def export_triples_callback(n_clicks, auth_data):
    """Handle exporting triples database as JSON"""
    if not auth_data:
        return dbc.Alert("Please login first", color="danger")
    
    try:
        # Call the export API endpoint with POST and credentials in body
        r = requests.post(
            f"{API_BASE}/api/admin/export/triples",
            json={
                "email": auth_data["email"],
                "password": auth_data["password"]
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
# Main
# -----------------------
if __name__ == "__main__":
    # Run:  python t2t_frontend.py
    # Then open http://127.0.0.1:8050
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8050")), debug=False)
