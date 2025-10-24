#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Admin interface for managing projects, papers, and tuples.
"""

import os
import json
import requests
from dash import Dash, dcc, html, dash_table, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc

# -----------------------
# Config
# -----------------------
API_BASE = os.getenv("T2T_API_BASE", "http://127.0.0.1:5001")
ADMIN_API_BASE = os.getenv("T2T_ADMIN_API_BASE", "http://127.0.0.1:5002")

APP_TITLE = "Text2Trait: Admin Panel"

# -----------------------
# Initialize Dash App
# -----------------------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = APP_TITLE

# -----------------------
# Layout
# -----------------------
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Admin Panel", className="text-center my-4"),
            html.Hr()
        ])
    ]),

    # Email input (for admin authentication)
    dbc.Row([
        dbc.Col([
            dbc.Label("Admin Email:"),
            dbc.Input(
                id="admin-email",
                type="email",
                placeholder="Enter your admin email",
                debounce=True
            )
        ], width=6)
    ], className="mb-4"),

    # Tabs for different admin sections
    dbc.Tabs([
        dbc.Tab(label="Projects & Papers", tab_id="tab-projects"),
        dbc.Tab(label="Tuple Editor", tab_id="tab-tuples"),
    ], id="admin-tabs", active_tab="tab-projects"),

    html.Div(id="tab-content", className="mt-4")
], fluid=True)

# -----------------------
# Tab Content Layouts
# -----------------------

def projects_tab_layout():
    """Layout for projects and papers management."""
    return dbc.Container([
        # Create Project Section
        dbc.Card([
            dbc.CardHeader(html.H4("Create New Project")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Project Name:"),
                        dbc.Input(id="new-project-name", placeholder="Enter project name", debounce=True)
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Description:"),
                        dbc.Input(id="new-project-desc", placeholder="Optional description", debounce=True)
                    ], width=6)
                ]),
                dbc.Button("Create Project", id="btn-create-project", color="primary", className="mt-3"),
                html.Div(id="create-project-status", className="mt-2")
            ])
        ], className="mb-4"),

        # Project List
        dbc.Card([
            dbc.CardHeader([
                html.H4("Projects", className="d-inline"),
                dbc.Button("Refresh", id="btn-refresh-projects", color="secondary", size="sm", className="float-end")
            ]),
            dbc.CardBody([
                dcc.Loading(
                    html.Div(id="projects-list")
                )
            ])
        ], className="mb-4"),

        # Add Papers Section
        dbc.Card([
            dbc.CardHeader(html.H4("Add Papers to Project")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Select Project:"),
                        dcc.Dropdown(id="select-project-for-papers", placeholder="Choose a project...")
                    ], width=6)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("DOI List (one per line):"),
                        dbc.Textarea(
                            id="doi-list-input",
                            placeholder="10.1234/example1\n10.5678/example2\n...",
                            style={"height": "150px"}
                        )
                    ], width=12)
                ], className="mt-3"),
                dbc.Button("Add DOIs", id="btn-add-dois", color="primary", className="mt-3"),
                html.Div(id="add-dois-status", className="mt-2")
            ])
        ], className="mb-4"),

        # Papers List & Fetch Section
        dbc.Card([
            dbc.CardHeader([
                html.H4("Papers in Project", className="d-inline"),
                dbc.Button("Fetch PDFs", id="btn-fetch-pdfs", color="success", size="sm", className="float-end ms-2"),
                dbc.Button("Refresh", id="btn-refresh-papers", color="secondary", size="sm", className="float-end")
            ]),
            dbc.CardBody([
                dbc.Label("Select Project to View Papers:"),
                dcc.Dropdown(id="select-project-for-view", placeholder="Choose a project..."),
                html.Div(id="fetch-status", className="mt-2"),
                dcc.Loading(
                    html.Div(id="papers-list", className="mt-3")
                )
            ])
        ])
    ])

def tuples_tab_layout():
    """Layout for tuple editing."""
    return dbc.Container([
        dbc.Card([
            dbc.CardHeader([
                html.H4("All Tuples", className="d-inline"),
                dbc.Button("Refresh", id="btn-refresh-tuples", color="secondary", size="sm", className="float-end")
            ]),
            dbc.CardBody([
                dcc.Loading(
                    html.Div(id="tuples-list")
                )
            ])
        ])
    ])

# -----------------------
# Callbacks
# -----------------------

@app.callback(
    Output("tab-content", "children"),
    Input("admin-tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "tab-projects":
        return projects_tab_layout()
    elif active_tab == "tab-tuples":
        return tuples_tab_layout()
    return html.Div("Select a tab")

@app.callback(
    Output("projects-list", "children"),
    [Input("btn-refresh-projects", "n_clicks")],
    prevent_initial_call=False
)
def load_projects(n_clicks):
    """Load and display all projects."""
    try:
        resp = requests.get(f"{ADMIN_API_BASE}/api/admin/projects", timeout=10)
        if resp.ok:
            projects = resp.json()
            if not projects:
                return html.P("No projects found.", className="text-muted")

            rows = []
            for proj in projects:
                rows.append(dbc.ListGroupItem([
                    html.H5(proj["name"]),
                    html.P(proj["description"] or "No description", className="text-muted mb-1"),
                    html.Small(f"Created by: {proj['created_by']} on {proj['created_at'][:10]}")
                ]))

            return dbc.ListGroup(rows)
        else:
            return html.P(f"Error loading projects: {resp.text}", className="text-danger")
    except Exception as e:
        return html.P(f"Error: {e}", className="text-danger")

@app.callback(
    [Output("select-project-for-papers", "options"),
     Output("select-project-for-view", "options")],
    [Input("btn-refresh-projects", "n_clicks")],
    prevent_initial_call=False
)
def update_project_dropdowns(n_clicks):
    """Update project dropdown options."""
    try:
        resp = requests.get(f"{ADMIN_API_BASE}/api/admin/projects", timeout=10)
        if resp.ok:
            projects = resp.json()
            options = [{"label": p["name"], "value": p["id"]} for p in projects]
            return options, options
    except Exception:
        pass
    return [], []

@app.callback(
    Output("create-project-status", "children"),
    Input("btn-create-project", "n_clicks"),
    [State("admin-email", "value"),
     State("new-project-name", "value"),
     State("new-project-desc", "value")],
    prevent_initial_call=True
)
def create_project(n_clicks, email, name, desc):
    """Create a new project."""
    if not email or not name:
        return dbc.Alert("Please provide admin email and project name.", color="warning")

    try:
        resp = requests.post(
            f"{ADMIN_API_BASE}/api/admin/projects",
            json={"email": email, "name": name, "description": desc or ""},
            timeout=10
        )

        if resp.ok:
            return dbc.Alert("Project created successfully!", color="success")
        else:
            return dbc.Alert(f"Error: {resp.json().get('error', 'Unknown error')}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {e}", color="danger")

@app.callback(
    Output("add-dois-status", "children"),
    Input("btn-add-dois", "n_clicks"),
    [State("admin-email", "value"),
     State("select-project-for-papers", "value"),
     State("doi-list-input", "value")],
    prevent_initial_call=True
)
def add_dois_to_project(n_clicks, email, project_id, doi_text):
    """Add DOIs to selected project."""
    if not email or not project_id or not doi_text:
        return dbc.Alert("Please provide admin email, select a project, and enter DOIs.", color="warning")

    dois = [line.strip() for line in doi_text.split("\n") if line.strip()]

    if not dois:
        return dbc.Alert("No valid DOIs found.", color="warning")

    try:
        resp = requests.post(
            f"{ADMIN_API_BASE}/api/admin/projects/{project_id}/papers",
            json={"email": email, "dois": dois},
            timeout=30
        )

        if resp.ok:
            data = resp.json()
            added_count = len(data.get("added", []))
            error_count = len(data.get("errors", []))

            msg = f"Successfully added {added_count} papers."
            if error_count > 0:
                msg += f" {error_count} failed."

            return dbc.Alert(msg, color="success" if error_count == 0 else "warning")
        else:
            return dbc.Alert(f"Error: {resp.json().get('error', 'Unknown error')}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {e}", color="danger")

@app.callback(
    Output("papers-list", "children"),
    [Input("btn-refresh-papers", "n_clicks"),
     Input("select-project-for-view", "value")],
    prevent_initial_call=False
)
def load_papers(n_clicks, project_id):
    """Load and display papers for selected project."""
    if not project_id:
        return html.P("Select a project to view papers.", className="text-muted")

    try:
        resp = requests.get(f"{ADMIN_API_BASE}/api/admin/projects/{project_id}/papers", timeout=10)
        if resp.ok:
            papers = resp.json()
            if not papers:
                return html.P("No papers in this project.", className="text-muted")

            # Create table data
            table_data = []
            for paper in papers:
                status_badge = {
                    "pending": "secondary",
                    "fetching": "info",
                    "success": "success",
                    "failed": "danger"
                }.get(paper["fetch_status"], "secondary")

                table_data.append({
                    "DOI": paper["doi"],
                    "Title": paper["title"] or "N/A",
                    "Authors": paper["authors"] or "N/A",
                    "Year": paper["year"] or "N/A",
                    "Status": paper["fetch_status"],
                    "Error": paper["error_message"] or ""
                })

            return dash_table.DataTable(
                data=table_data,
                columns=[
                    {"name": "DOI", "id": "DOI"},
                    {"name": "Title", "id": "Title"},
                    {"name": "Authors", "id": "Authors"},
                    {"name": "Year", "id": "Year"},
                    {"name": "Status", "id": "Status"},
                    {"name": "Error", "id": "Error"}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'fontWeight': 'bold'},
                page_size=20
            )
        else:
            return html.P(f"Error loading papers: {resp.text}", className="text-danger")
    except Exception as e:
        return html.P(f"Error: {e}", className="text-danger")

@app.callback(
    Output("fetch-status", "children"),
    Input("btn-fetch-pdfs", "n_clicks"),
    [State("admin-email", "value"),
     State("select-project-for-view", "value")],
    prevent_initial_call=True
)
def fetch_pdfs(n_clicks, email, project_id):
    """Fetch PDFs for all pending papers in project."""
    if not email or not project_id:
        return dbc.Alert("Please provide admin email and select a project.", color="warning")

    try:
        resp = requests.post(
            f"{ADMIN_API_BASE}/api/admin/projects/{project_id}/fetch",
            json={"email": email},
            timeout=120  # Allow time for multiple PDF downloads
        )

        if resp.ok:
            data = resp.json()
            results = data.get("results", [])

            success_count = sum(1 for r in results if r["status"] == "success")
            failed_count = sum(1 for r in results if r["status"] == "failed")

            msg = f"Fetched {success_count} PDFs successfully."
            if failed_count > 0:
                msg += f" {failed_count} failed."

            return dbc.Alert(msg, color="success" if failed_count == 0 else "warning")
        else:
            return dbc.Alert(f"Error: {resp.json().get('error', 'Unknown error')}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {e}", color="danger")

@app.callback(
    Output("tuples-list", "children"),
    [Input("btn-refresh-tuples", "n_clicks")],
    prevent_initial_call=False
)
def load_tuples(n_clicks):
    """Load and display all tuples."""
    try:
        resp = requests.get(f"{ADMIN_API_BASE}/api/admin/tuples?limit=100", timeout=10)
        if resp.ok:
            tuples = resp.json()
            if not tuples:
                return html.P("No tuples found.", className="text-muted")

            # Create table data
            table_data = []
            for t in tuples:
                table_data.append({
                    "ID": t["id"],
                    "Sentence": t["sentence_text"][:100] + "..." if len(t["sentence_text"]) > 100 else t["sentence_text"],
                    "Source": f"{t['source_entity_name']} ({t['source_entity_attr']})",
                    "Relation": t["relation_type"],
                    "Sink": f"{t['sink_entity_name']} ({t['sink_entity_attr']})",
                    "Contributor": t["contributor_email"],
                    "Created": t["created_at"][:10] if t["created_at"] else ""
                })

            return dash_table.DataTable(
                data=table_data,
                columns=[
                    {"name": "ID", "id": "ID"},
                    {"name": "Sentence", "id": "Sentence"},
                    {"name": "Source", "id": "Source"},
                    {"name": "Relation", "id": "Relation"},
                    {"name": "Sink", "id": "Sink"},
                    {"name": "Contributor", "id": "Contributor"},
                    {"name": "Created", "id": "Created"}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'fontWeight': 'bold'},
                page_size=20,
                editable=False,
                row_selectable='single'
            )
        else:
            return html.P(f"Error loading tuples: {resp.text}", className="text-danger")
    except Exception as e:
        return html.P(f"Error: {e}", className="text-danger")

# -----------------------
# Run Server
# -----------------------
if __name__ == "__main__":
    PORT = int(os.environ.get("T2T_ADMIN_FRONTEND_PORT", "8051"))
    HOST = os.environ.get("T2T_HOST", "0.0.0.0")
    app.run_server(host=HOST, port=PORT, debug=True)
