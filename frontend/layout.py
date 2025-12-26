# frontend/layout.py
"""
Layout building functions for HARVEST frontend.
Includes sidebar with info tabs and main application layout.
"""
import os
import logging
from datetime import datetime
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

# Import from parent frontend package
from frontend import (
    APP_TITLE, PARTNER_LOGOS, ENABLE_LITERATURE_SEARCH, 
    ENABLE_PDF_HIGHLIGHTING, ENABLE_LITERATURE_REVIEW,
    DASH_REQUESTS_PATHNAME_PREFIX, app, markdown_cache,
    OTHER_SENTINEL
)

logger = logging.getLogger(__name__)


def create_execution_log_display(execution_log):
    """
    Create a visual display of the search pipeline execution log.
    Shows AutoResearch, DeepResearch (Python Reimpl), and DELM steps in a compact 3-column layout.
    """
    if not execution_log:
        return None
    
    # Define colors for each step type
    step_colors = {
        'AutoResearch': '#17a2b8',  # Info blue
        'Query Processing': '#17a2b8',  # Info blue
        'DeepResearch (Python Reimpl)': '#28a745',  # Success green
        'DELM': '#ffc107',  # Warning yellow/gold
        'Result Selection': '#ffc107',  # Warning yellow/gold
        'Error': '#dc3545'  # Danger red
    }
    
    # Create compact column items
    column_items = []
    
    for idx, log_entry in enumerate(execution_log):
        step_name = log_entry.get('step', 'Unknown')
        description = log_entry.get('description', '')
        details = log_entry.get('details', '')
        elapsed_ms = log_entry.get('elapsed_ms', 0)
        status = log_entry.get('status', 'completed')
        
        # Get color for this step
        color = step_colors.get(step_name, '#6c757d')
        
        # Create status icon based on status
        if status == 'completed':
            status_icon = html.I(className="bi bi-check-circle-fill me-1", style={"color": "#28a745"})
        elif status == 'skipped':
            status_icon = html.I(className="bi bi-dash-circle-fill me-1", style={"color": "#6c757d"})
        elif status == 'error':
            status_icon = html.I(className="bi bi-x-circle-fill me-1", style={"color": "#dc3545"})
        else:
            status_icon = html.I(className="bi bi-clock-fill me-1", style={"color": "#ffc107"})
        
        # Create compact column item (4 columns layout, 3 per row)
        column_item = dbc.Col([
            dbc.Card(
                dbc.CardBody([
                    html.Div([
                        html.Span(
                            f"{idx + 1}",
                            style={
                                "display": "inline-block",
                                "width": "24px",
                                "height": "24px",
                                "borderRadius": "50%",
                                "backgroundColor": color,
                                "color": "white",
                                "textAlign": "center",
                                "lineHeight": "24px",
                                "fontWeight": "bold",
                                "fontSize": "12px",
                                "marginRight": "8px"
                            }
                        ),
                        html.Strong(step_name, style={"fontSize": "14px", "color": color})
                    ], className="mb-2"),
                    html.Div([
                        status_icon,
                        html.Span(description, style={"fontSize": "12px", "fontWeight": "500"})
                    ], className="mb-1"),
                    html.Small(details, className="text-muted d-block mb-1", style={"fontSize": "11px"}),
                    html.Small(
                        f"⏱️ {elapsed_ms}ms",
                        className="text-muted",
                        style={"fontSize": "10px", "fontStyle": "italic"}
                    ),
                ], className="p-2"),
                className="h-100",
                style={"borderLeft": f"3px solid {color}"}
            )
        ], md=3, className="mb-2")  # Changed from md=4 to md=3 for 4 columns per row
        
        column_items.append(column_item)
    
    # Create the execution log card with collapse functionality (collapsed by default)
    execution_log_card = dbc.Card(
        [
            dbc.CardHeader(
                dbc.Button(
                    [
                        html.Span([
                            html.I(className="bi bi-diagram-3-fill", style={"marginRight": "8px"}),
                            "Pipeline Execution Flow"
                        ]),
                        html.I(className="bi bi-chevron-right text-muted", id="pipeline-chevron", style={"fontSize": "0.8rem", "float": "right"})
                    ],
                    id="pipeline-collapse-button",
                    color="link",
                    style={"width": "100%", "textAlign": "left", "textDecoration": "none", "color": "#000", "fontWeight": "600"},
                    className="p-0"
                ),
                style={"backgroundColor": "#f8f9fa"}
            ),
            dbc.Collapse(
                dbc.CardBody([
                    html.P(
                        "The Semantic Paper Discovery system executed the following steps:",
                        className="text-muted mb-3",
                        style={"fontSize": "13px"}
                    ),
                    dbc.Row(column_items, className="g-2")
                ]),
                id="pipeline-collapse",
                is_open=False,  # Collapsed by default for cleaner UI
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
    Build the sidebar with information tabs in a horizontal layout.
    Uses cached markdown content with automatic reloading on file changes.
    Displays content in horizontally arranged tabs with scrollable areas for better space management.
    """
    # Get markdown content from cache
    annotator_guide_md = markdown_cache.get('annotator_guide.md', "Annotator guide not found.")
    schema_md = markdown_cache.get('schema.md', "Schema content not found.")
    admin_guide_md = markdown_cache.get('admin_guide.md', "Admin guide not found.")
    db_model_md = markdown_cache.get('db_model.md', "Database model content not found.")
    participate_md = markdown_cache.get('participate.md', "Participate content not found.")
    
    # Create tabs with horizontal layout and scrollable content
    info_tabs = dbc.Card(
        [
            dbc.Tabs(
                [
                    dbc.Tab(
                        html.Div(
                            annotator_guide_md,
                            style={
                                "maxHeight": "500px",
                                "overflowY": "auto",
                                "padding": "15px",
                                "backgroundColor": "#f8f9fa",
                                "borderRadius": "4px"
                            },
                            id="annotator-guide-content"
                        ),
                        label="👥 Annotator Guide",
                        tab_id="annotator-guide",
                    ),
                    dbc.Tab(
                        html.Div(
                            schema_md,
                            style={
                                "maxHeight": "500px",
                                "overflowY": "auto",
                                "padding": "15px",
                                "backgroundColor": "#f8f9fa",
                                "borderRadius": "4px"
                            },
                            id="schema-tab-content"
                        ),
                        label="📋 Schema",
                        tab_id="schema",
                    ),
                    dbc.Tab(
                        html.Div(
                            admin_guide_md,
                            style={
                                "maxHeight": "500px",
                                "overflowY": "auto",
                                "padding": "15px",
                                "backgroundColor": "#f8f9fa",
                                "borderRadius": "4px"
                            },
                            id="admin-guide-content"
                        ),
                        label="🔧 Admin Guide",
                        tab_id="admin-guide",
                    ),
                    dbc.Tab(
                        html.Div(
                            db_model_md,
                            style={
                                "maxHeight": "500px",
                                "overflowY": "auto",
                                "padding": "15px",
                                "backgroundColor": "#f8f9fa",
                                "borderRadius": "4px"
                            },
                            id="dbmodel-tab-content"
                        ),
                        label="🗄️ Database Model",
                        tab_id="dbmodel",
                    ),
                    dbc.Tab(
                        html.Div(
                            participate_md,
                            style={
                                "maxHeight": "500px",
                                "overflowY": "auto",
                                "padding": "15px",
                                "backgroundColor": "#f8f9fa",
                                "borderRadius": "4px"
                            },
                            id="participate-tab-content"
                        ),
                        label="🤝 Participate",
                        tab_id="participate",
                    ),
                ],
                id="info-tabs",
                active_tab="annotator-guide",
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
                # Local file - use app.get_asset_url for consistent asset loading
                logo_url = app.get_asset_url(logo_url)
            
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



def get_layout():
    """
    Build and return the main application layout.
    This includes all stores, modals, tabs, and the main content area.
    """
    return dbc.Container(
        [
            dcc.Store(id="choices-store"),
            dcc.Store(id="triple-count", data=1),
            dcc.Store(id="email-store", storage_type="session"),
            dcc.Store(id="otp-verification-store", storage_type="session"),  # NEW: OTP state
            dcc.Store(id="otp-session-store", storage_type="local"),  # NEW: Verified session (24h)
            dcc.Store(id="doi-metadata-store"),
            dcc.Store(id="admin-auth-store", storage_type="local"),  # Changed to local for persistence across refresh
            dcc.Store(id="pdf-download-state-store", storage_type="local"),  # Store PDF download state across refresh
            dcc.Store(id="projects-store"),
            dcc.Store(id="delete-project-id-store"),  # Store project ID to delete
            dcc.Store(id="upload-project-id-store"),  # Store project ID for upload
            dcc.Store(id="edit-dois-project-id-store"),  # Store project ID for editing DOIs
            dcc.Store(id="pdf-download-project-id", data=None),  # Store project ID for PDF download tracking
            dcc.Store(id="lit-search-selected-papers", data=[]),  # Store selected papers
            dcc.Store(id="lit-search-session-papers", data=[], storage_type="session"),  # Store all papers from session
            dcc.Store(id="browse-field-config", data=None, storage_type="session"),  # Store browse field configuration
            dcc.Interval(id="load-trigger", n_intervals=0, interval=200, max_intervals=1),
            dcc.Interval(id="pdf-download-progress-interval", interval=2000, disabled=True),  # Poll every 2 seconds
        
            # Modal for Privacy Policy
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Privacy Policy & GDPR Compliance")),
                    dbc.ModalBody(
                        [
                            dcc.Markdown(id="privacy-policy-content", style={"maxHeight": "60vh", "overflowY": "auto"}),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Close", id="privacy-policy-close", color="primary"),
                        ]
                    ),
                ],
                id="privacy-policy-modal",
                is_open=False,
                size="xl",
                scrollable=True,
            ),
        
            # Modal for Web of Science advanced syntax help
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Web of Science Advanced Search Syntax")),
                    dbc.ModalBody(
                        [
                            html.P("Web of Science supports powerful field-based searches with boolean operators:", className="mb-3"),
                        
                            html.H6("Common Field Tags:", className="mb-2"),
                            html.Ul([
                                html.Li([html.Strong("TS="), " Topic (title, abstract, keywords)"]),
                                html.Li([html.Strong("TI="), " Title"]),
                                html.Li([html.Strong("AB="), " Abstract"]),
                                html.Li([html.Strong("AU="), " Author"]),
                                html.Li([html.Strong("PY="), " Publication year"]),
                                html.Li([html.Strong("SO="), " Journal/publication name"]),
                                html.Li([html.Strong("DO="), " DOI"]),
                            ], className="mb-3"),
                        
                            html.H6("Boolean Operators:", className="mb-2"),
                            html.P([html.Strong("AND"), ", ", html.Strong("OR"), ", ", html.Strong("NOT")], className="mb-3"),
                        
                            html.H6("Wildcards:", className="mb-2"),
                            html.Ul([
                                html.Li([html.Strong("*"), " - multiple characters (e.g., genom* matches genomic, genomics)"]),
                                html.Li([html.Strong("?"), " - single character"]),
                            ], className="mb-3"),
                        
                            html.H6("Example Queries:", className="mb-2"),
                            dbc.Alert([
                                html.Code("AB=(genomic* OR transcriptom*)"),
                                html.Br(),
                                html.Code("TI=(CRISPR) AND PY=(2020-2024)"),
                                html.Br(),
                                html.Code("TS=(machine learning) AND SO=(Nature)"),
                                html.Br(),
                                html.Code("AU=(Smith J*) AND AB=(longevity*)"),
                            ], color="light", className="mb-3"),
                        
                            html.P([
                                "For more details, see the ",
                                html.A("WoS Advanced Search Guide", 
                                       href="https://webofscience.zendesk.com/hc/en-us/articles/20130361503249",
                                       target="_blank"),
                                " or our ",
                                html.A("complete documentation",
                                       href="docs/SEMANTIC_SEARCH.md#advanced-search-syntax",
                                       target="_blank"),
                                "."
                            ], className="small text-muted"),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Close", id="wos-syntax-help-close", color="primary"),
                        ]
                    ),
                ],
                id="wos-syntax-help-modal",
                is_open=False,
                size="lg",
            ),
        
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

            # Modal for editing project DOIs
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Edit Project DOIs")),
                    dbc.ModalBody(
                        [
                            html.Div(id="edit-dois-project-info", className="mb-3"),
                            
                            html.H6("Current DOIs", className="mb-2"),
                            html.Div(
                                id="edit-dois-current-list",
                                style={"maxHeight": "200px", "overflowY": "auto"},
                                className="mb-3 p-2 border rounded"
                            ),
                            
                            html.Hr(),
                            
                            html.H6("Add DOIs", className="mb-2"),
                            html.P("Enter DOIs to add (one per line):", className="small text-muted"),
                            dcc.Textarea(
                                id="edit-dois-add-input",
                                placeholder="10.1234/example1\n10.1234/example2\n...",
                                style={"width": "100%", "height": "100px"},
                                className="mb-3"
                            ),
                            dbc.Button(
                                "Add DOIs",
                                id="btn-add-dois-to-project",
                                color="success",
                                size="sm",
                                className="mb-3"
                            ),
                            
                            html.Hr(),
                            
                            html.H6("Remove DOIs", className="mb-2"),
                            html.P("Enter DOIs to remove (one per line):", className="small text-muted"),
                            dcc.Textarea(
                                id="edit-dois-remove-input",
                                placeholder="10.1234/example1\n10.1234/example2\n...",
                                style={"width": "100%", "height": "100px"},
                                className="mb-2"
                            ),
                            dbc.Checkbox(
                                id="edit-dois-delete-pdfs",
                                label="Also delete associated PDF files",
                                value=False,
                                className="mb-3"
                            ),
                            dbc.Button(
                                "Remove DOIs",
                                id="btn-remove-dois-from-project",
                                color="danger",
                                size="sm",
                                className="mb-3"
                            ),
                            
                            html.Div(id="edit-dois-message", className="mb-2"),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Close", id="edit-dois-modal-close", color="secondary"),
                        ]
                    ),
                ],
                id="edit-dois-modal",
                is_open=False,
                size="lg",
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                            # Logo section
                            html.Div([
                                dbc.Row([
                                    dbc.Col([
                                        html.Img(
                                            src=app.get_asset_url("HARVEST.png"),
                                            alt="HARVEST",
                                            style={
                                                "height": "120px",
                                                "transition": "transform 0.2s ease"
                                            },
                                            id="harvest-logo",
                                            className="logo-hover"
                                        ),
                                    ], width="auto", className="d-flex align-items-center"),
                                ], align="center", className="mb-4 mt-3")
                            ], className="logo-container"),

                            dcc.Tabs(
                                id="main-tabs",
                                value="tab-dashboard",
                                children=[tab for tab in [
                                    # Dashboard/Welcome Tab
                                    dcc.Tab(
                                        label="🏠 Dashboard",
                                        value="tab-dashboard",
                                        children=[
                                            dbc.Card(
                                                [
                                                    html.Div([
                                                        html.H3([
                                                            html.I(className="bi bi-house-fill me-2 text-primary-custom"),
                                                            "Welcome to HARVEST"
                                                        ], className="mb-3"),
                                                        html.P(
                                                            "Your annotation and literature review hub for biological research.",
                                                            className="text-muted mb-4"
                                                        ),
                                                    
                                                        # Quick Stats Section
                                                        html.H5([
                                                            html.I(className="bi bi-graph-up me-2"),
                                                            "Quick Statistics"
                                                        ], className="mb-3"),
                                                        dbc.Row([
                                                            dbc.Col([
                                                                dbc.Card([
                                                                    dbc.CardBody([
                                                                        html.Div([
                                                                            html.I(className="bi bi-clipboard-data", 
                                                                                  style={"fontSize": "2.5rem", "color": "var(--primary-color)"}),
                                                                        ], className="text-center mb-2"),
                                                                        html.H4(id="dashboard-total-triples", 
                                                                               children="0",
                                                                               className="text-center mb-1 text-primary-custom"),
                                                                        html.P("Total Annotations", 
                                                                              className="text-center text-muted mb-0 small"),
                                                                    ])
                                                                ], className="shadow-custom-md mb-3")
                                                            ], md=3, sm=6, xs=12),
                                                            dbc.Col([
                                                                dbc.Card([
                                                                    dbc.CardBody([
                                                                        html.Div([
                                                                            html.I(className="bi bi-folder-fill", 
                                                                                  style={"fontSize": "2.5rem", "color": "var(--secondary-color)"}),
                                                                        ], className="text-center mb-2"),
                                                                        html.H4(id="dashboard-total-projects", 
                                                                               children="0",
                                                                               className="text-center mb-1 text-secondary-custom"),
                                                                        html.P("Active Projects", 
                                                                              className="text-center text-muted mb-0 small"),
                                                                    ])
                                                                ], className="shadow-custom-md mb-3")
                                                            ], md=3, sm=6, xs=12),
                                                            dbc.Col([
                                                                dbc.Card([
                                                                    dbc.CardBody([
                                                                        html.Div([
                                                                            html.I(className="bi bi-file-earmark-text-fill", 
                                                                                  style={"fontSize": "2.5rem", "color": "var(--accent-color)"}),
                                                                        ], className="text-center mb-2"),
                                                                        html.H4(id="dashboard-total-dois", 
                                                                               children="0",
                                                                               className="text-center mb-1",
                                                                               style={"color": "var(--accent-color)"}),
                                                                        html.P("Papers Annotated", 
                                                                              className="text-center text-muted mb-0 small"),
                                                                    ])
                                                                ], className="shadow-custom-md mb-3")
                                                            ], md=3, sm=6, xs=12),
                                                            dbc.Col([
                                                                dbc.Card([
                                                                    dbc.CardBody([
                                                                        html.Div([
                                                                            html.I(className="bi bi-clock-history", 
                                                                                  style={"fontSize": "2.5rem", "color": "var(--success-color)"}),
                                                                        ], className="text-center mb-2"),
                                                                        html.H4(id="dashboard-recent-activity", 
                                                                               children="0",
                                                                               className="text-center mb-1",
                                                                               style={"color": "var(--success-color)"}),
                                                                        html.P("Recent (7 days)", 
                                                                              className="text-center text-muted mb-0 small"),
                                                                    ])
                                                                ], className="shadow-custom-md mb-3")
                                                            ], md=3, sm=6, xs=12),
                                                        ], className="mb-4"),
                                                    
                                                        # Quick Actions Section
                                                        html.H5([
                                                            html.I(className="bi bi-lightning-fill me-2"),
                                                            "Quick Actions"
                                                        ], className="mb-3"),
                                                        dbc.Row([
                                                            dbc.Col([
                                                                dbc.Button([
                                                                    html.I(className="bi bi-search me-2"),
                                                                    "Search Literature"
                                                                ], id="dashboard-goto-literature", 
                                                                   color="primary", 
                                                                   size="lg",
                                                                   className="w-100 mb-2 shadow-custom-sm"),
                                                            ], md=3, sm=6, xs=12),
                                                            dbc.Col([
                                                                dbc.Button([
                                                                    html.I(className="bi bi-pencil-square me-2"),
                                                                    "Annotate Paper"
                                                                ], id="dashboard-goto-annotate", 
                                                                   color="success", 
                                                                   size="lg",
                                                                   className="w-100 mb-2 shadow-custom-sm"),
                                                            ], md=3, sm=6, xs=12),
                                                            dbc.Col([
                                                                dbc.Button([
                                                                    html.I(className="bi bi-table me-2"),
                                                                    "Browse Data"
                                                                ], id="dashboard-goto-browse", 
                                                                   color="info", 
                                                                   size="lg",
                                                                   className="w-100 mb-2 shadow-custom-sm"),
                                                            ], md=3, sm=6, xs=12),
                                                            dbc.Col([
                                                                dbc.Button([
                                                                    html.I(className="bi bi-gear-fill me-2"),
                                                                    "Admin Panel"
                                                                ], id="dashboard-goto-admin", 
                                                                   color="secondary", 
                                                                   size="lg",
                                                                   className="w-100 mb-2 shadow-custom-sm"),
                                                            ], md=3, sm=6, xs=12),
                                                        ], className="mb-4"),
                                                    
                                                        # Getting Started Guide
                                                        html.H5([
                                                            html.I(className="bi bi-signpost-2-fill me-2"),
                                                            "Getting Started"
                                                        ], className="mb-3"),
                                                        dbc.Alert([
                                                            html.H6([
                                                                html.I(className="bi bi-info-circle-fill me-2"),
                                                                "New to HARVEST?"
                                                            ], className="mb-2"),
                                                            html.Ol([
                                                                html.Li([html.Strong("Search"), " for relevant papers in the Literature Search tab"]),
                                                                html.Li([html.Strong("Annotate"), " biological entities and relationships in the Annotate tab"]),
                                                                html.Li([html.Strong("Browse"), " and export your annotations in the Browse tab"]),
                                                                html.Li([html.Strong("Manage"), " projects and users in the Admin tab"]),
                                                            ], className="mb-2"),
                                                            html.P([
                                                                "For detailed guides, check the ",
                                                                html.I(className="bi bi-book"),
                                                                " information tabs below"
                                                            ], className="mb-0 small text-muted"),
                                                        ], color="info", className="shadow-custom-sm"),
                                                    ]),
                                                ],
                                                body=True,
                                                className="shadow-custom-md"
                                            )
                                        ]
                                    ) if True else None,  # Always show dashboard
                                    dcc.Tab(
                                        label="🔍 Literature Search",
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
                                                                "Search for relevant papers from multiple academic sources using natural language queries.",
                                                                className="text-muted mb-3"
                                                            ),
                                                        
                                                            # Source selection
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            dbc.Label(
                                                                                [
                                                                                    "Select Search Sources ",
                                                                                    html.I(
                                                                                        className="bi bi-info-circle-fill",
                                                                                        id="sources-info-icon",
                                                                                        style={"fontSize": "0.85rem", "color": "#6c757d", "cursor": "help"}
                                                                                    ),
                                                                                ],
                                                                                style={"fontWeight": "bold"}
                                                                            ),
                                                                            dbc.Tooltip(
                                                                                [
                                                                                    html.Strong("Semantic Scholar:"), " AI2's open academic database. Supports natural language queries and has good coverage of CS/AI papers.",
                                                                                    html.Br(), html.Br(),
                                                                                    html.Strong("arXiv:"), " Preprint repository for physics, math, CS, etc. Best for recent research. Supports natural language.",
                                                                                    html.Br(), html.Br(),
                                                                                    html.Strong("Web of Science:"), " Comprehensive citation database. Supports advanced search syntax (e.g., TS=(topic) AND PY=(2020-2024)).",
                                                                                    html.Br(), html.Br(),
                                                                                    html.Strong("OpenAlex:"), " Free, open catalog of scholarly works. Good coverage across all disciplines."
                                                                                ],
                                                                                target="sources-info-icon",
                                                                                placement="right",
                                                                                style={"maxWidth": "450px"}
                                                                            ),
                                                                            dbc.Checklist(
                                                                                id="lit-search-sources",
                                                                                options=[
                                                                                    {"label": " Semantic Scholar (natural language)", "value": "semantic_scholar"},
                                                                                    {"label": " arXiv (natural language)", "value": "arxiv"},
                                                                                    {"label": " Web of Science (advanced syntax)", "value": "web_of_science"},
                                                                                    {"label": " OpenAlex (natural language)", "value": "openalex"},
                                                                                ],
                                                                                value=["semantic_scholar", "arxiv"],  # Default sources
                                                                                inline=True,
                                                                                className="mb-2",
                                                                            ),
                                                                            html.Small(
                                                                                id="lit-search-sources-info",
                                                                                className="text-muted"
                                                                            ),
                                                                        ],
                                                                        md=12,
                                                                    ),
                                                                ],
                                                                className="mb-3",
                                                            ),
                                                        
                                                            # Per-source result limits (Advanced settings)
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            dbc.Button(
                                                                                [
                                                                                    html.I(className="bi bi-gear me-2"),
                                                                                    "Advanced: Results per Source"
                                                                                ],
                                                                                id="toggle-per-source-limits",
                                                                                color="link",
                                                                                size="sm",
                                                                                className="mb-2 p-0",
                                                                            ),
                                                                            dbc.Collapse(
                                                                                dbc.Card(
                                                                                    dbc.CardBody(
                                                                                        [
                                                                                            html.P("Configure how many results to fetch from each source:", className="mb-2 small"),
                                                                                            dbc.Row(
                                                                                                [
                                                                                                    dbc.Col([
                                                                                                        dbc.Label("Semantic Scholar (max 100)", className="small"),
                                                                                                        dbc.Input(
                                                                                                            id="limit-semantic-scholar",
                                                                                                            type="number",
                                                                                                            min=1,
                                                                                                            max=100,
                                                                                                            value=100,
                                                                                                            size="sm",
                                                                                                        ),
                                                                                                    ], md=3),
                                                                                                    dbc.Col([
                                                                                                        dbc.Label("arXiv (max 100)", className="small"),
                                                                                                        dbc.Input(
                                                                                                            id="limit-arxiv",
                                                                                                            type="number",
                                                                                                            min=1,
                                                                                                            max=100,
                                                                                                            value=50,
                                                                                                            size="sm",
                                                                                                        ),
                                                                                                    ], md=3),
                                                                                                    dbc.Col([
                                                                                                        dbc.Label("Web of Science (max 100)", className="small"),
                                                                                                        dbc.Input(
                                                                                                            id="limit-wos",
                                                                                                            type="number",
                                                                                                            min=1,
                                                                                                            max=100,
                                                                                                            value=100,
                                                                                                            size="sm",
                                                                                                        ),
                                                                                                    ], md=3),
                                                                                                    dbc.Col([
                                                                                                        dbc.Label("OpenAlex (max 200)", className="small"),
                                                                                                        dbc.Input(
                                                                                                            id="limit-openalex",
                                                                                                            type="number",
                                                                                                            min=1,
                                                                                                            max=200,
                                                                                                            value=200,
                                                                                                            size="sm",
                                                                                                        ),
                                                                                                    ], md=3),
                                                                                                ],
                                                                                                className="g-2"
                                                                                            ),
                                                                                            html.Small(
                                                                                                "Note: Higher limits may increase search time but return more comprehensive results.",
                                                                                                className="text-muted mt-2 d-block"
                                                                                            ),
                                                                                        ]
                                                                                    ),
                                                                                    className="border-0 bg-light"
                                                                                ),
                                                                                id="collapse-per-source-limits",
                                                                                is_open=False,
                                                                            ),
                                                                        ],
                                                                        md=12,
                                                                    ),
                                                                ],
                                                                className="mb-3",
                                                            ),
                                                        
                                                            # Results to display
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            dbc.Label("Number of Results to Display", style={"fontWeight": "bold"}),
                                                                            dbc.Input(
                                                                                id="lit-search-top-k",
                                                                                type="number",
                                                                                min=1,
                                                                                max=100,
                                                                                value=20,
                                                                                size="sm",
                                                                            ),
                                                                            html.Small(
                                                                                "After deduplication and reranking, this many top results will be displayed (1-100)",
                                                                                className="text-muted"
                                                                            ),
                                                                        ],
                                                                        md=12,
                                                                    ),
                                                                ],
                                                                className="mb-3",
                                                            ),
                                                        
                                                            # Pipeline controls section
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            dbc.Label(
                                                                                [
                                                                                    "Pipeline Workflow Controls ",
                                                                                    html.I(
                                                                                        className="bi bi-info-circle-fill",
                                                                                        id="pipeline-info-icon",
                                                                                        style={"fontSize": "0.85rem", "color": "#6c757d", "cursor": "help"}
                                                                                    ),
                                                                                ],
                                                                                style={"fontWeight": "bold"}
                                                                            ),
                                                                            dbc.Tooltip(
                                                                                [
                                                                                    html.Strong("Query Expansion (AutoResearch):"), " Disabled by default to improve precision. Modern search engines handle semantic similarity internally.",
                                                                                    html.Br(), html.Br(),
                                                                                    html.Strong("Deduplication:"), " Removes duplicate papers using DOI and fuzzy title matching (85% similarity threshold).",
                                                                                    html.Br(), html.Br(),
                                                                                    html.Strong("Semantic Reranking (DELM):"), " Reorders results by abstract similarity to your query using AI embeddings."
                                                                                ],
                                                                                target="pipeline-info-icon",
                                                                                placement="right",
                                                                                style={"maxWidth": "400px"}
                                                                            ),
                                                                            dbc.Checklist(
                                                                                id="lit-search-pipeline-controls",
                                                                                options=[
                                                                                    {
                                                                                        "label": " Query Expansion (AutoResearch) - Recommended: OFF",
                                                                                        "value": "query_expansion"
                                                                                    },
                                                                                    {
                                                                                        "label": " Deduplication - Recommended: ON",
                                                                                        "value": "deduplication",
                                                                                    },
                                                                                    {
                                                                                        "label": " Semantic Reranking (DELM) - Recommended: ON",
                                                                                        "value": "reranking",
                                                                                    },
                                                                                ],
                                                                                value=["deduplication", "reranking"],  # Query expansion OFF by default
                                                                                className="mb-2",
                                                                            ),
                                                                            html.Small(
                                                                                "Control which pipeline steps to execute. Disabling deduplication or reranking may speed up searches but affect result quality.",
                                                                                className="text-muted"
                                                                            ),
                                                                        ],
                                                                        md=12,
                                                                    ),
                                                                ],
                                                                className="mb-3",
                                                            ),
                                                        
                                                            # Query and search button
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
                                                                                [
                                                                                    "Enter a natural language query or ",
                                                                                    html.A(
                                                                                        "Web of Science advanced syntax",
                                                                                        href="#",
                                                                                        id="wos-syntax-help-link",
                                                                                        style={"cursor": "pointer"}
                                                                                    ),
                                                                                    " (e.g., AB=(genomic*) AND PY=(2020-2024))"
                                                                                ],
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
                                                                className="mb-3",
                                                            ),
                                                        
                                                            # Session options
                                                            dbc.Row(
                                                                [
                                                                    dbc.Col(
                                                                        [
                                                                            dbc.Checkbox(
                                                                                id="lit-search-build-session",
                                                                                label="Build on previous searches (cumulative)",
                                                                                value=False,
                                                                            ),
                                                                            html.Small(
                                                                                "When enabled, new searches will add to existing results instead of replacing them",
                                                                                className="text-muted"
                                                                            ),
                                                                        ],
                                                                        md=9,
                                                                    ),
                                                                    dbc.Col(
                                                                        [
                                                                            dbc.Button(
                                                                                "Clear Session",
                                                                                id="btn-clear-session",
                                                                                color="secondary",
                                                                                size="sm",
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
                                                                    # Sorting and filtering controls
                                                                    dbc.Card(
                                                                        dbc.CardBody(
                                                                            [
                                                                                dbc.Row(
                                                                                    [
                                                                                        dbc.Col(
                                                                                            [
                                                                                                dbc.Label("Sort By:", className="fw-bold mb-1", style={"fontSize": "0.9rem"}),
                                                                                                dcc.Dropdown(
                                                                                                    id="result-sort-by",
                                                                                                    options=[
                                                                                                        {"label": "Relevance (Default)", "value": "relevance"},
                                                                                                        {"label": "Citations (High to Low)", "value": "citations_desc"},
                                                                                                        {"label": "Year (Newest First)", "value": "year_desc"},
                                                                                                        {"label": "Year (Oldest First)", "value": "year_asc"},
                                                                                                    ],
                                                                                                    value="relevance",
                                                                                                    clearable=False,
                                                                                                    className="mb-2"
                                                                                                ),
                                                                                            ],
                                                                                            md=6
                                                                                        ),
                                                                                        dbc.Col(
                                                                                            [
                                                                                                dbc.Label("Filter by Source:", className="fw-bold mb-1", style={"fontSize": "0.9rem"}),
                                                                                                dcc.Dropdown(
                                                                                                    id="result-filter-source",
                                                                                                    options=[
                                                                                                        {"label": "All Sources", "value": "all"},
                                                                                                        {"label": "Semantic Scholar", "value": "Semantic Scholar"},
                                                                                                        {"label": "arXiv", "value": "arXiv"},
                                                                                                        {"label": "Web of Science", "value": "Web of Science"},
                                                                                                        {"label": "OpenAlex", "value": "OpenAlex"},
                                                                                                    ],
                                                                                                    value="all",
                                                                                                    clearable=False,
                                                                                                    className="mb-2"
                                                                                                ),
                                                                                            ],
                                                                                            md=6
                                                                                        ),
                                                                                    ],
                                                                                    className="g-2"
                                                                                ),
                                                                            ]
                                                                        ),
                                                                        className="mb-3 bg-light border-0"
                                                                    ),
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
                                                                    # Store for all papers data (for sorting/filtering)
                                                                    dcc.Store(id="all-papers-data", data=[]),
                                                                    # Stores for pagination state
                                                                    dcc.Store(id="pagination-state", data={
                                                                        'current_page': {},  # Per-source page numbers
                                                                        'total_results': {},  # Per-source total counts
                                                                        'last_query': '',
                                                                        'last_sources': []
                                                                    }),
                                                                    html.Div(id="search-results"),
                                                                    # Pagination controls (hidden by default, shown when pagination is available)
                                                                    html.Div(
                                                                        id="pagination-controls",
                                                                        children=[
                                                                            dbc.Card(
                                                                                dbc.CardBody(
                                                                                    [
                                                                                        html.Div(id="pagination-info", className="text-center mb-2"),
                                                                                        dbc.ButtonGroup(
                                                                                            [
                                                                                                dbc.Button(
                                                                                                    [html.I(className="bi bi-chevron-left me-1"), "Load Previous Page"],
                                                                                                    id="btn-prev-page",
                                                                                                    color="secondary",
                                                                                                    size="sm",
                                                                                                    disabled=True
                                                                                                ),
                                                                                                dbc.Button(
                                                                                                    ["Load Next Page", html.I(className="bi bi-chevron-right ms-1")],
                                                                                                    id="btn-next-page",
                                                                                                    color="primary",
                                                                                                    size="sm"
                                                                                                ),
                                                                                            ],
                                                                                            className="d-flex justify-content-center"
                                                                                        ),
                                                                                    ]
                                                                                ),
                                                                                className="mt-3"
                                                                            )
                                                                        ],
                                                                        style={"display": "none"}
                                                                    ),
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
                                        label="📚 Literature Review",
                                        value="tab-literature-review",
                                        children=[
                                            dbc.Card(
                                                [
                                                    html.H5("AI-Powered Literature Review (ASReview Integration)", className="mb-3"),
                                                
                                                    # Authentication message - shown when not authenticated
                                                    html.Div(
                                                        id="lit-review-auth-required",
                                                        children=[
                                                            dbc.Alert(
                                                                [
                                                                    html.I(className="bi bi-lock me-2"),
                                                                    html.Strong("Authentication Required"),
                                                                    html.Br(),
                                                                    "Please login via the ",
                                                                    html.Strong("Admin"),
                                                                    " tab to access the Literature Review feature."
                                                                ],
                                                                color="info",
                                                                className="text-center"
                                                            ),
                                                        ],
                                                        style={"display": "block"}
                                                    ),
                                                
                                                    # Service availability check - shown after authentication
                                                    html.Div(
                                                        id="lit-review-auth-content",
                                                        style={"display": "none"},
                                                        children=[
                                                            html.Div(
                                                                id="lit-review-status",
                                                                children=[
                                                                    dbc.Spinner(
                                                                        html.Div(id="lit-review-availability-check"),
                                                                        color="primary"
                                                                    )
                                                                ],
                                                                className="mb-3"
                                                            ),
                                                
                                                    # Main content - shown when service is available
                                                    html.Div(
                                                        id="lit-review-content",
                                                        style={"display": "none"},
                                                        children=[
                                                            html.P(
                                                                "Use ASReview's AI-powered active learning to efficiently screen and prioritize literature. "
                                                                "The system learns from your decisions to predict which papers are most relevant.",
                                                                className="text-muted mb-4"
                                                            ),
                                                            dbc.Alert(
                                                                [
                                                                    html.H6([
                                                                        html.I(className="bi bi-lightbulb-fill me-2"),
                                                                        "How It Works"
                                                                    ], className="mb-2"),
                                                                    html.Ol([
                                                                        html.Li("Create a review project from Literature Search results"),
                                                                        html.Li("Mark initial papers as relevant/irrelevant"),
                                                                        html.Li("AI model learns and predicts relevance for remaining papers"),
                                                                        html.Li("System shows most relevant papers first"),
                                                                        html.Li("Export results when done"),
                                                                    ]),
                                                                ],
                                                                color="info",
                                                                className="mb-4"
                                                            ),
                                                        
                                                            # ASReview Screenshot/Preview
                                                            # Note: Direct iframe embedding of ASReview is not possible due to
                                                            # how the ASReview app handles routing and CORS. Instead, we show
                                                            # a preview screenshot.
                                                            dbc.Card([
                                                                dbc.CardBody([
                                                                    html.Div([
                                                                        html.I(className="bi bi-image me-2", style={"fontSize": "1.5rem"}),
                                                                        html.H5("ASReview Interface Preview", className="d-inline"),
                                                                    ], className="mb-3"),
                                                                    html.Div([
                                                                        # Info alert about screenshot - only show if file doesn't exist
                                                                        dbc.Alert([
                                                                            html.I(className="bi bi-info-circle me-2"),
                                                                            html.Strong("Screenshot: "),
                                                                            "Add an ASReview interface screenshot as ",
                                                                            html.Code("asreview_screenshot.png"),
                                                                            " in the assets/ directory to display it here. ",
                                                                            "See ",
                                                                            html.Code("assets/ASREVIEW_SCREENSHOT_INSTRUCTIONS.md"),
                                                                            " for details."
                                                                        ], color="light", className="mb-3 small", 
                                                                        # Hide alert if screenshot file exists
                                                                        style={"display": "none"} if os.path.exists(
                                                                            os.path.join(
                                                                                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                                                "assets",
                                                                                "asreview_screenshot.png"
                                                                            )
                                                                        ) else {}),
                                                                        # Placeholder for ASReview screenshot
                                                                        # Administrators should add an 'asreview_screenshot.png' file
                                                                        # to the assets/ directory
                                                                        html.Img(
                                                                            src=app.get_asset_url("asreview_screenshot.png"),
                                                                            alt="ASReview Interface - Screenshot not available. Add asreview_screenshot.png to assets/ directory.",
                                                                            style={
                                                                                "width": "100%",
                                                                                "maxWidth": "1200px",
                                                                                "border": "1px solid #dee2e6",
                                                                                "borderRadius": "4px",
                                                                                "display": "block",
                                                                                "margin": "0 auto",
                                                                                "backgroundColor": "#f8f9fa"
                                                                            },
                                                                            className="mb-3",
                                                                        ),
                                                                        dbc.Alert([
                                                                            html.I(className="bi bi-info-circle-fill me-2"),
                                                                            html.Strong("Note: "),
                                                                            "Due to ASReview's architecture, direct embedding via iframe is not supported. ",
                                                                            "To use ASReview, please access it directly at: ",
                                                                            html.A(
                                                                                html.Span(id="asreview-service-url", className="font-monospace"),
                                                                                href="#",
                                                                                id="asreview-direct-link",
                                                                                target="_blank",
                                                                                rel="noopener noreferrer"
                                                                            )
                                                                        ], color="light", className="mb-0"),
                                                                    ]),
                                                                ])
                                                            ], className="shadow-sm"),
                                                        ]
                                                    ),
                                                
                                                    # Error/unavailable message
                                                    html.Div(
                                                        id="lit-review-unavailable",
                                                        style={"display": "none"},
                                                        children=[
                                                            dbc.Alert(
                                                                [
                                                                    html.H6([
                                                                        html.I(className="bi bi-exclamation-triangle-fill me-2"),
                                                                        "ASReview Service Not Available"
                                                                    ], className="mb-2"),
                                                                    html.P(
                                                                        "The ASReview service is not configured or not reachable. "
                                                                        "Please configure ASREVIEW_SERVICE_URL in config.py to enable this feature.",
                                                                        className="mb-2"
                                                                    ),
                                                                    html.P([
                                                                        "See ",
                                                                        html.A("Literature Review Documentation", 
                                                                              href="docs/LITERATURE_REVIEW.md", 
                                                                              target="_blank",
                                                                              className="alert-link"),
                                                                        " for setup instructions."
                                                                    ], className="mb-0"),
                                                                ],
                                                                color="warning"
                                                            ),
                                                        ]
                                                    ),
                                                        ]  # End of lit-review-auth-content children
                                                    ),  # End of lit-review-auth-content wrapper div
                                                ],
                                                body=True,
                                                className="shadow-custom-md"
                                            )
                                        ]
                                    ) if ENABLE_LITERATURE_REVIEW else None,
                                    dcc.Tab(
                                        label="✏️ Annotate",
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
                                                                                    html.Div(
                                                                                        id="annotator-id-display",
                                                                                        className="text-muted small mt-1"
                                                                                    ),
                                                                                    # NEW: OTP Verification Section (hidden by default)
                                                                                    html.Div(
                                                                                        id="otp-verification-section",
                                                                                        children=[
                                                                                            dbc.Label("Verification Code", className="mt-2", style={"fontWeight": "bold"}),
                                                                                            html.Small("Check your email for the 6-digit code", className="text-muted d-block mb-1"),
                                                                                            dbc.InputGroup(
                                                                                                [
                                                                                                    dbc.Input(
                                                                                                        id="otp-code-input",
                                                                                                        placeholder="Enter 6-digit code",
                                                                                                        type="text",
                                                                                                        maxLength=6,
                                                                                                        pattern="[0-9]{6}",
                                                                                                    ),
                                                                                                    dbc.Button(
                                                                                                        "Verify",
                                                                                                        id="otp-verify-button",
                                                                                                        color="primary",
                                                                                                        disabled=True
                                                                                                    ),
                                                                                                ],
                                                                                                className="mb-2"
                                                                                            ),
                                                                                            html.Div(id="otp-verification-feedback"),
                                                                                            dbc.Button(
                                                                                                "Resend Code",
                                                                                                id="otp-resend-button",
                                                                                                color="link",
                                                                                                size="sm",
                                                                                                className="p-0"
                                                                                            ),
                                                                                        ],
                                                                                        style={"display": "none"}  # Hidden by default
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
                                                                                md=12,
                                                                            ),
                                                                        ],
                                                                        className="g-3 mt-2",
                                                                    ),
                                                                    # Batch selector row (hidden if no batches)
                                                                    dbc.Row(
                                                                        [
                                                                            dbc.Col(
                                                                                [
                                                                                    dbc.Label("Select Batch"),
                                                                                    dcc.Dropdown(
                                                                                        id="batch-selector",
                                                                                        placeholder="Select a batch to work on...",
                                                                                        disabled=True,
                                                                                        clearable=True,
                                                                                    ),
                                                                                ],
                                                                                md=6,
                                                                            ),
                                                                            dbc.Col(
                                                                                [
                                                                                    dbc.Label("Batch Progress"),
                                                                                    html.Div(
                                                                                        id="batch-progress-indicator",
                                                                                        className="mt-2"
                                                                                    ),
                                                                                ],
                                                                                md=6,
                                                                            ),
                                                                        ],
                                                                        id="batch-selector-row",
                                                                        className="g-3 mt-2",
                                                                        style={"display": "none"}
                                                                    ),
                                                                    dbc.Row(
                                                                        [
                                                                            dbc.Col(
                                                                                [
                                                                                    dbc.Label("Select DOI from Project"),
                                                                                    dcc.Dropdown(
                                                                                        id="project-doi-selector",
                                                                                        placeholder="Select a DOI...",
                                                                                        clearable=True,
                                                                                        disabled=True,
                                                                                    ),
                                                                                    html.Small(
                                                                                        id="doi-status-indicator",
                                                                                        className="text-muted mt-1"
                                                                                    ),
                                                                                ],
                                                                                md=12,
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
                                        label="📊 Browse",
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
                                                                md=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Label("Filter by Annotator ID"),
                                                                    dbc.Input(
                                                                        id="browse-contributor-filter",
                                                                        placeholder="Enter Annotator ID (hashed)",
                                                                        type="text",
                                                                    ),
                                                                ],
                                                                md=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    html.Br(),
                                                                    dbc.Button("Refresh", id="btn-refresh", color="secondary"),
                                                                ],
                                                                md=4,
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
                                        label="👤 Admin",
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
                                                            html.Div([
                                                                dbc.Button(
                                                                    "Create Project", 
                                                                    id="btn-create-project", 
                                                                    color="success", 
                                                                    className="mb-2"
                                                                ),
                                                                dcc.Loading(
                                                                    id="loading-create-project",
                                                                    type="default",
                                                                    children=html.Div(id="project-message", className="mb-3")
                                                                ),
                                                                html.Small(
                                                                    "💡 Tip: For 300+ DOIs, validation may take 1-2 minutes. "
                                                                    "A spinner will appear while processing.",
                                                                    className="text-muted d-block mb-2"
                                                                ),
                                                            ]),
                                                        
                                                            html.H6("Existing Projects", className="mb-2 mt-3"),
                                                            dbc.Button("Refresh Projects", id="btn-refresh-projects", color="secondary", size="sm", className="mb-2"),
                                                            html.Div(id="projects-list", className="mb-3"),
                                                        
                                                            html.Div(id="pdf-download-progress-container", className="mb-3"),
                                                            html.Hr(),
                                                            
                                                            # Batch Management Section
                                                            html.H6("DOI Batch Management", className="mb-3"),
                                                            dbc.Card([
                                                                dbc.CardBody([
                                                                    html.P("Create batches to organize DOIs in projects with 100+ papers for easier annotation management.", className="text-muted small"),
                                                                    dbc.Row([
                                                                        dbc.Col([
                                                                            dbc.Label("Select Project"),
                                                                            dcc.Dropdown(
                                                                                id="batch-mgmt-project-selector",
                                                                                placeholder="Select project...",
                                                                                options=[]
                                                                            ),
                                                                        ], md=6),
                                                                        dbc.Col([
                                                                            dbc.Label("Batch Size (DOIs per batch)"),
                                                                            dbc.Input(
                                                                                id="batch-size-input",
                                                                                type="number",
                                                                                value=20,
                                                                                min=5,
                                                                                max=100
                                                                            ),
                                                                        ], md=3),
                                                                        dbc.Col([
                                                                            dbc.Label("Strategy"),
                                                                            dcc.Dropdown(
                                                                                id="batch-strategy-selector",
                                                                                options=[
                                                                                    {"label": "Sequential", "value": "sequential"},
                                                                                    {"label": "Random", "value": "random"}
                                                                                ],
                                                                                value="sequential",
                                                                                clearable=False
                                                                            ),
                                                                        ], md=3),
                                                                    ], className="mb-3"),
                                                                    dbc.Button(
                                                                        "Create Batches",
                                                                        id="btn-create-batches",
                                                                        color="primary",
                                                                        className="mb-2"
                                                                    ),
                                                                    html.Div(id="batch-creation-message", className="mb-2"),
                                                                    html.Hr(),
                                                                    html.Div(id="batch-list-display"),
                                                                ])
                                                            ], className="mb-3"),
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
                                                            html.H6("Browse Display Configuration", className="mb-3"),
                                                            html.P("Select which fields to display in the Browse tab.", className="text-muted mb-2"),
                                                            dbc.Label("Visible Fields", className="mb-2"),
                                                            dcc.Dropdown(
                                                                id="browse-field-selector",
                                                                options=[
                                                                    {"label": "Sentence ID", "value": "sentence_id"},
                                                                    {"label": "Triple ID", "value": "triple_id"},
                                                                    {"label": "Project ID", "value": "project_id"},
                                                                    {"label": "DOI", "value": "doi"},
                                                                    {"label": "DOI Hash", "value": "doi_hash"},
                                                                    {"label": "Literature Link", "value": "literature_link"},
                                                                    {"label": "Relation Type", "value": "relation_type"},
                                                                    {"label": "Source Entity Name", "value": "source_entity_name"},
                                                                    {"label": "Source Entity Attribute", "value": "source_entity_attr"},
                                                                    {"label": "Sink Entity Name", "value": "sink_entity_name"},
                                                                    {"label": "Sink Entity Attribute", "value": "sink_entity_attr"},
                                                                    {"label": "Sentence", "value": "sentence"},
                                                                    {"label": "Triple Contributor (Hashed)", "value": "triple_contributor"},
                                                                ],
                                                                value=["project_id", "sentence_id", "sentence", "source_entity_name", "source_entity_attr", "relation_type", "sink_entity_name", "sink_entity_attr", "triple_id"],
                                                                multi=True,
                                                                placeholder="Select fields to display...",
                                                                className="mb-3"
                                                            ),
                                                            html.Small("Note: Email addresses (Triple Contributor) are automatically hashed for privacy using installation-specific salt.", className="text-muted d-block mb-3"),
                                                        
                                                            html.Hr(className="mt-4"),
                                                            html.H6("Privacy & Compliance", className="mb-3"),
                                                            html.P("Review HARVEST's privacy policy and GDPR compliance.", className="text-muted mb-2"),
                                                            dbc.Button(
                                                                [
                                                                    html.I(className="bi bi-shield-check me-2"),
                                                                    "View Privacy Policy"
                                                                ],
                                                                id="btn-view-privacy-policy",
                                                                color="secondary",
                                                                outline=True,
                                                                className="mb-3"
                                                            ),
                                                        
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
                                                            dcc.Dropdown(
                                                                id="export-project-filter",
                                                                placeholder="Export scope (default: All projects)",
                                                                clearable=True,
                                                                className="mb-2",
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
                        html.Small(f"© {datetime.now().year} HARVEST"),
                        className="text-center text-muted my-3",
                    )
                )
            ),
        ],
        fluid=True,
    )
