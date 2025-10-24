# t2t_frontend.py
import os
import json
import requests
from datetime import datetime

import dash
from dash import Dash, dcc, html, dash_table, Input, Output, State, MATCH, ALL, ctx, no_update
import dash_bootstrap_components as dbc

# -----------------------
# Config
# -----------------------
API_BASE = os.getenv("T2T_API_BASE", "http://127.0.0.1:5001")
API_CHOICES = f"{API_BASE}/api/choices"
API_SAVE = f"{API_BASE}/api/save"
API_RECENT = f"{API_BASE}/api/recent"
API_VALIDATE_DOI = f"{API_BASE}/api/validate-doi"

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
def tuple_row(i, entity_options, relation_options):
    """
    Build one tuple row with inputs:
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
    # Build the Markdown with explicit, balanced code fences
    schema_json_str = json.dumps(SCHEMA_JSON, indent=2)
    schema_md_text = (
        "**Current schema (essential)**\n\n"
        "```json\n" + schema_json_str + "\n```\n\n"
        "**Tables**\n\n"
        "```text\n"
        "sentences(id, text, literature_link, created_at)\n"
        "tuples(id, sentence_id, source_entity_name, source_entity_attr, relation_type,\n"
        "       sink_entity_name, sink_entity_attr, created_at)\n"
        "entity_types(name, value)\n"
        "relation_types(name)\n"
        "```\n"
    )
    schema_md = dcc.Markdown(schema_md_text)

    help_md = dcc.Markdown(
        """
**How to use**

1. Paste a *Sentence* and (optionally) a DOI/URL in *Literature Link*.
2. Click **Add tuple** to create one or more (source, relation, sink) tuples.
3. Use dropdowns for entity types and relation; choose **Other…** if you need a new label.
4. Click **Save** — the sentence is stored once, and all tuples link to it.

**Notes**
- One sentence can have multiple tuples.
- If your backend has different endpoint paths, edit `API_*` constants at the top of the file.
"""
    )

    qa_md = dcc.Markdown(
        """
**Q&A**

- *Why do I see “Other…” inputs?*  
  To allow adding new entity types or relations not in the base schema.

- *Where do values come from?*  
  The app tries `GET /api/choices` on the backend. If that fails, it falls back to the JSON schema embedded in the app.

- *Can I browse saved items?*  
  Yes — see the **Browse** tab (fetches from `/api/recent`).
"""
    )

    return dbc.Card(
        dbc.Accordion(
            [
                dbc.AccordionItem(help_md, title="Help"),
                dbc.AccordionItem(schema_md, title="Schema"),
                dbc.AccordionItem(qa_md, title="Q&A"),
            ],
            start_collapsed=True,
            always_open=False,
        ),
        body=True,
        className="mb-3"
    )

# -----------------------
# App & Layout
# -----------------------
external_stylesheets = [dbc.themes.BOOTSTRAP]
app: Dash = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = APP_TITLE
server = app.server  # for gunicorn, if needed

# Add custom JavaScript for PDF text selection
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <script>
            var pdfSelectedText = '';

            // Function to get selected text from the page
            function getSelectedText() {
                var text = "";
                if (window.getSelection) {
                    text = window.getSelection().toString();
                } else if (document.selection && document.selection.type != "Control") {
                    text = document.selection.createRange().text;
                }
                return text;
            }

            // Monitor for text selection
            document.addEventListener('mouseup', function() {
                setTimeout(function() {
                    var selectedText = getSelectedText();
                    if (selectedText.trim().length > 0) {
                        pdfSelectedText = selectedText.trim();
                        console.log("Text selected:", pdfSelectedText);
                    }
                }, 100);
            });
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = dbc.Container(
    [
        dcc.Store(id="choices-store"),
        dcc.Store(id="tuple-count", data=1),
        dcc.Store(id="email-store", storage_type="session"),
        dcc.Store(id="doi-metadata-store"),
        dcc.Store(id="pdf-url-store"),
        dcc.Interval(id="load-trigger", n_intervals=0, interval=200, max_intervals=1),

        html.H2(APP_TITLE, className="mt-3 mb-4"),

        dcc.Tabs(
            id="main-tabs",
            value="tab-annotate",
            children=[
                dcc.Tab(
                    label="Annotate",
                    value="tab-annotate",
                    children=[
                        dbc.Row(
                            [
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
                                                    className="g-3",
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
                                                        dbc.Button("Add tuple", id="btn-add-tuple", color="primary"),
                                                        dbc.Button("Remove last tuple", id="btn-remove-tuple", color="secondary"),
                                                        dbc.Button("Save", id="btn-save", color="success"),
                                                        dbc.Button("Reset", id="btn-reset", color="warning"),
                                                    ],
                                                    size="sm",
                                                    className="mb-2",
                                                ),
                                                html.Div(id="tuples-container"),
                                                html.Div(id="save-message", className="mt-2"),
                                            ],
                                            body=True,
                                        )
                                    ],
                                    md=6,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Card(
                                            [
                                                html.H5("PDF Viewer", className="mb-3"),
                                                html.Div(
                                                    id="pdf-status",
                                                    className="mb-2",
                                                    children=html.Small(
                                                        "Validate a DOI to load the PDF",
                                                        className="text-muted"
                                                    )
                                                ),
                                                html.Div(
                                                    [
                                                        html.Iframe(
                                                            id="pdf-viewer",
                                                            style={
                                                                "width": "100%",
                                                                "height": "650px",
                                                                "border": "1px solid #ddd",
                                                                "display": "none"
                                                            }
                                                        ),
                                                        dbc.Button(
                                                            "Copy selected text to sentence",
                                                            id="btn-copy-pdf-text",
                                                            color="info",
                                                            size="sm",
                                                            className="mt-2",
                                                            style={"display": "none"}
                                                        ),
                                                    ]
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
                                dbc.Button("Refresh", id="btn-refresh", color="secondary", className="mb-2"),
                                html.Div(id="recent-table"),
                            ],
                            body=True,
                        )
                    ],
                ),
            ],
        ),
    ],
    fluid=True,
    style={"maxWidth": "100%"}
)

# -----------------------
# Callbacks
# -----------------------

# Clientside callback to copy PDF text to sentence field
app.clientside_callback(
    """
    function(n_clicks, current_text) {
        if (!n_clicks) {
            return current_text || '';
        }

        // Get the selected text from the global variable
        var selectedText = window.pdfSelectedText || '';

        if (selectedText.length > 0) {
            // Append to existing text or replace if empty
            if (current_text && current_text.trim().length > 0) {
                return current_text + ' ' + selectedText;
            } else {
                return selectedText;
            }
        }

        return current_text || '';
    }
    """,
    Output("sentence-text", "value", allow_duplicate=True),
    Input("btn-copy-pdf-text", "n_clicks"),
    State("sentence-text", "value"),
    prevent_initial_call=True
)

# Show/hide copy button based on PDF viewer visibility
@app.callback(
    Output("btn-copy-pdf-text", "style"),
    Input("pdf-viewer", "style"),
    prevent_initial_call=False,
)
def toggle_copy_button(pdf_style):
    if pdf_style and pdf_style.get("display") == "block":
        return {"display": "block"}
    return {"display": "none"}

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

# Restore email from session on page load
@app.callback(
    Output("contributor-email", "value"),
    Input("email-store", "data"),
    prevent_initial_call=False,
)
def restore_email(stored_email):
    return stored_email or ""

# DOI validation callback
@app.callback(
    Output("doi-validation", "children"),
    Output("doi-validation", "style"),
    Output("doi-metadata-display", "children"),
    Output("doi-metadata-display", "style"),
    Output("doi-metadata-store", "data"),
    Output("pdf-viewer", "src"),
    Output("pdf-viewer", "style"),
    Output("pdf-status", "children"),
    Input("btn-validate-doi", "n_clicks"),
    State("literature-link", "value"),
    prevent_initial_call=True,
)
def validate_doi(n_clicks, doi_input):
    if not doi_input or not doi_input.strip():
        return (
            "Please enter a DOI",
            {"color": "red"},
            None,
            {"display": "none"},
            None,
            "",
            {"width": "100%", "height": "700px", "border": "1px solid #ddd", "display": "none"},
            html.Small("Validate a DOI to load the PDF", className="text-muted")
        )

    try:
        r = requests.post(API_VALIDATE_DOI, json={"doi": doi_input}, timeout=15)
        if r.ok:
            result = r.json()
            if result.get("valid"):
                metadata = result.get("metadata", {})
                doi = result.get("doi", "")

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

                # Try to get PDF URL from backend
                doi_encoded = doi.replace("/", "_SLASH_")
                pdf_url = None
                pdf_status_msg = html.Small("Looking for PDF...", className="text-info")
                pdf_style = {"width": "100%", "height": "650px", "border": "1px solid #ddd", "display": "none"}

                try:
                    pdf_resp = requests.get(f"{API_BASE}/api/get-pdf-url/{doi_encoded}", timeout=15)
                    if pdf_resp.ok:
                        pdf_data = pdf_resp.json()
                        if pdf_data.get("success") and pdf_data.get("pdf_url"):
                            pdf_url = pdf_data["pdf_url"]
                            pdf_status_msg = html.Small("PDF loaded. Select text and click button below to copy to sentence field.", className="text-success")
                            pdf_style = {"width": "100%", "height": "650px", "border": "1px solid #ddd", "display": "block"}
                        else:
                            pdf_status_msg = html.Small(
                                pdf_data.get("error", "PDF not available for this DOI"),
                                className="text-warning"
                            )
                    else:
                        pdf_status_msg = html.Small("PDF not available for this DOI", className="text-warning")
                except Exception as e:
                    print(f"PDF lookup error: {e}")
                    pdf_status_msg = html.Small("Could not retrieve PDF", className="text-warning")

                return (
                    "Valid DOI - metadata retrieved",
                    {"color": "green"},
                    metadata_card,
                    {"display": "block"},
                    {
                        "doi": doi,
                        "title": metadata.get("title", ""),
                        "authors": metadata.get("authors", ""),
                        "year": metadata.get("year", ""),
                    },
                    pdf_url or "",
                    pdf_style,
                    pdf_status_msg
                )
            else:
                error_msg = result.get("error", "Invalid DOI")
                return (
                    error_msg,
                    {"color": "red"},
                    None,
                    {"display": "none"},
                    None,
                    "",
                    {"width": "100%", "height": "700px", "border": "1px solid #ddd", "display": "none"},
                    html.Small("Validate a DOI to load the PDF", className="text-muted")
                )
        else:
            return (
                f"Validation failed: {r.status_code}",
                {"color": "red"},
                None,
                {"display": "none"},
                None,
                "",
                {"width": "100%", "height": "700px", "border": "1px solid #ddd", "display": "none"},
                html.Small("Validate a DOI to load the PDF", className="text-muted")
            )
    except Exception as e:
        return (
            f"Error: {str(e)}",
            {"color": "red"},
            None,
            {"display": "none"},
            None,
            "",
            {"width": "100%", "height": "700px", "border": "1px solid #ddd", "display": "none"},
            html.Small("Validate a DOI to load the PDF", className="text-muted")
        )

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

# Add/remove tuple rows
@app.callback(
    Output("tuple-count", "data"),
    Input("btn-add-tuple", "n_clicks"),
    Input("btn-remove-tuple", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    State("tuple-count", "data"),
    prevent_initial_call=True,
)
def modify_tuple_count(add_clicks, remove_clicks, reset_clicks, current_count):
    trigger = ctx.triggered_id
    count = current_count or 1
    if trigger == "btn-add-tuple":
        return count + 1
    elif trigger == "btn-remove-tuple":
        return max(1, count - 1)
    elif trigger == "btn-reset":
        return 1
    return count

# Render tuple rows whenever count or choices change
@app.callback(
    Output("tuples-container", "children"),
    Input("tuple-count", "data"),
    Input("choices-store", "data"),
)
def render_tuple_rows(count, choices_data):
    if not choices_data:
        entity_options = build_entity_options(SCHEMA_JSON)
        relation_options = build_relation_options(SCHEMA_JSON)
    else:
        entity_options = choices_data["entity_options"]
        relation_options = choices_data["relation_options"]

    rows = [tuple_row(i, entity_options, relation_options) for i in range(count or 1)]
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
def save_tuples(n_clicks, sentence_text, literature_link, contributor_email, email_validated,
                doi_metadata,
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

    tuples = []
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
            tuples.append(
                {
                    "source_entity_name": src_name,
                    "source_entity_attr": src_attr_final,
                    "relation_type": rel_final,
                    "sink_entity_name": sink_name,
                    "sink_entity_attr": sink_attr_final,
                }
            )

    if not tuples:
        return dbc.Alert("At least one complete tuple is required (source, relation, sink).", color="danger", dismissable=True, duration=4000)

    payload = {
        "sentence": sentence_text.strip(),
        "literature_link": (literature_link or "").strip(),
        "contributor_email": email_validated,
        "tuples": tuples,
    }

    if doi_metadata:
        payload["doi"] = doi_metadata.get("doi", "")
        payload["article_title"] = doi_metadata.get("title", "")
        payload["article_authors"] = doi_metadata.get("authors", "")
        payload["article_year"] = doi_metadata.get("year", "")

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
            num_tuples = len(tuples)
            return dbc.Alert(
                f"Saved successfully! Sentence ID: {new_id}, Tuples saved: {num_tuples}",
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

# Browse recent
@app.callback(
    Output("recent-table", "children"),
    Input("btn-refresh", "n_clicks"),
    Input("load-trigger", "n_intervals"),
    prevent_initial_call=False,
)
def refresh_recent(btn_clicks, interval_trigger):
    try:
        print(f"Fetching recent data from {API_RECENT}")
        r = requests.get(API_RECENT, timeout=8)
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

# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    # Run:  python t2t_frontend.py
    # Then open http://127.0.0.1:8050
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8050")), debug=False)
