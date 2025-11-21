# DOI Batch Management Feature - Implementation Plan

## Overview
Add batch management capabilities to the HARVEST annotation workflow to handle projects with 100+ DOIs more efficiently. This feature will allow annotators to work on manageable subsets of papers and track annotation progress across the team.

## Problem Statement
Currently, the Annotate tab has two dropdowns:
1. Project selector
2. DOI/paper selector (shows all DOIs in project)

For projects with 100+ DOIs, this becomes unwieldy:
- Long dropdown lists are hard to navigate
- No visibility into which papers are being worked on
- No way to divide work among multiple annotators
- Difficult to track progress

## Proposed Solution

### 1. Batch Organization System

#### Backend Changes

**Database Schema Updates** (`harvest_store.py` or migration script):

```python
# Add batch tracking table
CREATE TABLE IF NOT EXISTS doi_batches (
    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    batch_name TEXT NOT NULL,
    batch_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    UNIQUE(project_id, batch_number)
)

# Add DOI-to-batch mapping
CREATE TABLE IF NOT EXISTS doi_batch_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    doi TEXT NOT NULL,
    batch_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (batch_id) REFERENCES doi_batches(batch_id),
    UNIQUE(project_id, doi)
)

# Add annotation status tracking
CREATE TABLE IF NOT EXISTS doi_annotation_status (
    status_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    doi TEXT NOT NULL,
    annotator_email TEXT,
    status TEXT DEFAULT 'unstarted',  -- 'unstarted', 'in_progress', 'completed'
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    UNIQUE(project_id, doi)
)
```

**Backend API Endpoints** (`harvest_be.py`):

```python
# 1. Create/manage batches
@app.post("/api/admin/projects/<int:project_id>/batches")
def create_batches(project_id):
    """
    Auto-create batches for a project.
    Request body:
    {
        "batch_size": 20,  # DOIs per batch
        "strategy": "sequential"  # or "random" or "by_date"
    }
    """
    # Fetch all DOIs for project
    # Divide into batches of specified size
    # Create batch records
    # Return batch information

@app.get("/api/projects/<int:project_id>/batches")
def get_project_batches(project_id):
    """
    Get all batches for a project.
    Returns: List of batches with metadata
    """

@app.get("/api/projects/<int:project_id>/batches/<int:batch_id>/dois")
def get_batch_dois(project_id, batch_id):
    """
    Get all DOIs in a specific batch with their status.
    Returns: List of DOIs with annotation status
    """

# 2. Track annotation status
@app.post("/api/projects/<int:project_id>/dois/<doi>/status")
def update_doi_status(project_id, doi):
    """
    Update the annotation status of a DOI.
    Request body:
    {
        "status": "in_progress" | "completed",
        "annotator_email": "user@example.com"
    }
    """

@app.get("/api/projects/<int:project_id>/doi-status")
def get_doi_status_summary(project_id):
    """
    Get annotation status summary for all DOIs in project.
    Returns:
    {
        "total": 150,
        "unstarted": 100,
        "in_progress": 30,
        "completed": 20,
        "by_batch": {...}
    }
    """
```

#### Frontend Changes

**Layout Updates** (`frontend/layout.py`):

In the Annotate tab, modify the paper selection section:

```python
# Current structure:
# - Project dropdown
# - DOI dropdown (all DOIs)

# New structure:
# - Project dropdown
# - Batch dropdown (if project has batches)
# - DOI dropdown (filtered by selected batch, with status indicators)

dbc.Row([
    dbc.Col([
        dbc.Label("Select Batch"),
        dcc.Dropdown(
            id="batch-selector",
            placeholder="Select a batch to work on...",
            disabled=True
        ),
    ], width=6),
    dbc.Col([
        html.Div([
            dbc.Label("Batch Progress"),
            html.Div(id="batch-progress-indicator"),
        ]),
    ], width=6),
]),
dbc.Row([
    dbc.Col([
        dbc.Label("Select Paper (DOI)"),
        dcc.Dropdown(
            id="project-doi-selector",
            placeholder="Select a paper to annotate...",
            disabled=True,
            # Options will now include status indicators
        ),
    ], width=12),
]),
```

**Add visual status indicators** for DOIs in dropdown:
- 🔴 Red circle = Unstarted
- 🟡 Yellow circle = In progress (by someone)
- 🟢 Green circle = Completed
- 🔵 Blue circle = In progress (by you)

**Callback Updates** (`frontend/callbacks.py` or new `frontend/callbacks_batch.py`):

```python
@app.callback(
    Output("batch-selector", "options"),
    Output("batch-selector", "disabled"),
    Input("project-selector", "value"),
    prevent_initial_call=True,
)
def load_project_batches(project_id):
    """Load batches for selected project"""
    if not project_id:
        return [], True
    
    # Call backend API to get batches
    response = requests.get(f"{API_BASE}/api/projects/{project_id}/batches")
    if response.ok:
        batches = response.json()
        options = [
            {
                "label": f"Batch {b['batch_number']}: {b['batch_name']} ({b['doi_count']} papers)",
                "value": b['batch_id']
            }
            for b in batches
        ]
        return options, False
    return [], True

@app.callback(
    Output("project-doi-selector", "options"),
    Output("batch-progress-indicator", "children"),
    Input("batch-selector", "value"),
    State("project-selector", "value"),
    State("email-store", "data"),
    prevent_initial_call=True,
)
def load_batch_dois(batch_id, project_id, user_email):
    """Load DOIs for selected batch with status indicators"""
    if not batch_id or not project_id:
        return [], ""
    
    # Call backend API to get DOIs with status
    response = requests.get(
        f"{API_BASE}/api/projects/{project_id}/batches/{batch_id}/dois"
    )
    if response.ok:
        dois_data = response.json()
        
        # Build options with status indicators
        options = []
        for doi_info in dois_data:
            status = doi_info.get('status', 'unstarted')
            annotator = doi_info.get('annotator_email', '')
            doi = doi_info['doi']
            
            # Choose indicator based on status
            if status == 'completed':
                indicator = '🟢'
            elif status == 'in_progress':
                if annotator == user_email:
                    indicator = '🔵'  # Your work
                else:
                    indicator = '🟡'  # Someone else's work
            else:
                indicator = '🔴'
            
            options.append({
                "label": f"{indicator} {doi}",
                "value": doi
            })
        
        # Build progress indicator
        total = len(dois_data)
        completed = sum(1 for d in dois_data if d.get('status') == 'completed')
        in_progress = sum(1 for d in dois_data if d.get('status') == 'in_progress')
        
        progress = dbc.Progress([
            dbc.Progress(value=(completed/total)*100, color="success", bar=True, label=f"{completed} done"),
            dbc.Progress(value=(in_progress/total)*100, color="warning", bar=True, label=f"{in_progress} in progress"),
        ])
        
        return options, progress
    
    return [], ""

@app.callback(
    Output("doi-status-update-result", "children"),
    Input("project-doi-selector", "value"),
    State("project-selector", "value"),
    State("email-store", "data"),
    prevent_initial_call=True,
)
def mark_doi_in_progress(doi, project_id, user_email):
    """Automatically mark DOI as in-progress when selected"""
    if not doi or not project_id or not user_email:
        return ""
    
    # Update status in backend
    response = requests.post(
        f"{API_BASE}/api/projects/{project_id}/dois/{doi}/status",
        json={
            "status": "in_progress",
            "annotator_email": user_email
        }
    )
    
    return ""  # Silent update
```

### 2. Admin Batch Management Interface

Add a new section in the Admin tab for batch management:

```python
dbc.Card([
    dbc.CardHeader("Batch Management"),
    dbc.CardBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("Project"),
                dcc.Dropdown(
                    id="batch-mgmt-project-selector",
                    placeholder="Select project..."
                ),
            ], width=6),
            dbc.Col([
                dbc.Label("Batch Size"),
                dbc.Input(
                    id="batch-size-input",
                    type="number",
                    value=20,
                    min=5,
                    max=100
                ),
            ], width=3),
            dbc.Col([
                html.Br(),
                dbc.Button(
                    "Create Batches",
                    id="btn-create-batches",
                    color="primary",
                    className="w-100"
                ),
            ], width=3),
        ]),
        html.Hr(),
        html.Div(id="batch-management-status"),
        html.Div(id="batch-list-display"),
    ])
])
```

### 3. Migration Strategy

**Phase 1: Backend Foundation**
1. Add database tables for batches and status tracking
2. Implement backend API endpoints
3. Add batch auto-creation logic
4. Test with existing projects

**Phase 2: Frontend Integration**
1. Update layout with batch selector
2. Implement batch loading callbacks
3. Add status indicators to DOI dropdown
4. Test UI flow

**Phase 3: Admin Interface**
1. Add batch management section to Admin tab
2. Implement batch creation/viewing callbacks
3. Add batch statistics display

**Phase 4: Status Tracking**
1. Auto-update status when DOI selected
2. Track annotation completion
3. Display progress indicators

### 4. Configuration Options

Add to `config.py`:

```python
# Batch Management Configuration
ENABLE_BATCH_MANAGEMENT = True  # Enable/disable feature
DEFAULT_BATCH_SIZE = 20  # Default papers per batch
MAX_BATCH_SIZE = 100  # Maximum papers per batch
AUTO_CREATE_BATCHES = True  # Auto-create batches for new projects with >50 DOIs
```

### 5. Backward Compatibility

- If a project has no batches, show all DOIs as before
- Batch selector only appears if project has batches
- Existing projects work without modification
- Admin can create batches for existing projects

## Implementation Checklist

### Backend (harvest_be.py, harvest_store.py)
- [ ] Add database schema for batches
- [ ] Add database schema for status tracking
- [ ] Implement batch creation API
- [ ] Implement batch retrieval API
- [ ] Implement DOI status update API
- [ ] Add batch auto-creation logic
- [ ] Add tests for batch management

### Frontend (frontend/)
- [ ] Update layout with batch selector
- [ ] Add batch progress indicator
- [ ] Update DOI dropdown with status colors
- [ ] Implement batch loading callback
- [ ] Implement DOI status update callback
- [ ] Add admin batch management interface
- [ ] Add batch creation controls

### Documentation
- [ ] Update user guide with batch workflow
- [ ] Document batch management APIs
- [ ] Add admin guide for batch creation
- [ ] Create video tutorial for batch workflow

### Testing
- [ ] Test with small project (<20 DOIs)
- [ ] Test with medium project (50-100 DOIs)
- [ ] Test with large project (200+ DOIs)
- [ ] Test multi-user annotation conflicts
- [ ] Test batch progress tracking

## Timeline Estimate

- Backend implementation: 2-3 days
- Frontend implementation: 2-3 days
- Testing and refinement: 1-2 days
- Documentation: 1 day

**Total: 6-9 days**

## Alternative Approaches Considered

1. **Simple pagination**: Just paginate the DOI list without batches
   - Pros: Simpler to implement
   - Cons: Doesn't provide work division or progress tracking

2. **Assignee-based filtering**: Filter DOIs by assigned annotator
   - Pros: Clear ownership
   - Cons: Requires explicit assignment, less flexible

3. **Tag-based grouping**: Let admins tag DOIs with custom labels
   - Pros: Very flexible
   - Cons: More complex UI, requires manual tagging

The batch approach was selected because it provides:
- Clear work division
- Automatic organization
- Progress visibility
- Minimal admin overhead

## Questions for Discussion

1. Should batches be created automatically or manually by admins?
2. Should we allow annotators to work across batches or restrict to one at a time?
3. Should batch assignments be strict (locked to specific annotators) or flexible?
4. How should we handle DOI status conflicts (two people start same paper)?
5. Should completed papers be hidden from the dropdown or just marked?

## Next Steps

1. Review and approve this plan
2. Create database migration script
3. Implement backend APIs (can be done in parallel with frontend)
4. Create feature branch for development
5. Implement and test incrementally
6. Deploy to staging for user testing
