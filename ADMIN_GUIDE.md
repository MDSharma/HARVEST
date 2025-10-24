# Admin Guide: Project & Paper Management

This guide explains how to use the new project-based PDF management system for annotation.

## Overview

The system now supports:
1. **Project Management** - Organize papers into annotation projects
2. **Batch PDF Fetching** - Download PDFs using doi2pdf and Unpaywall APIs
3. **Tuple Editing** - Admin interface to view and edit all tuples
4. **Project-Based Annotation** - Select papers from projects for annotation

## Architecture

### Backend Services

1. **Main Backend** (`t2t_training_be.py`) - Port 5001
   - Original annotation endpoints
   - Handles sentence and tuple storage

2. **Admin Backend** (`t2t_admin_be.py`) - Port 5002
   - Project management
   - PDF fetching and serving
   - Tuple editing for admins

### Frontend Services

1. **Main Frontend** (`t2t_training_fe.py`) - Port 8050
   - Annotation interface with project/paper dropdowns
   - PDF viewer and text selection

2. **Admin Frontend** (`t2t_admin_fe.py`) - Port 8051
   - Project creation and management
   - Bulk DOI input and PDF fetching
   - Tuple editor

### Database

- **SQLite** - Local tuples and sentences
- **Supabase** - Projects and papers metadata

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file to set admin email:

```bash
T2T_ADMIN_EMAILS=your.email@example.com
```

### 3. Start Services

```bash
# Terminal 1: Main backend
python t2t_training_be.py

# Terminal 2: Admin backend
python t2t_admin_be.py

# Terminal 3: Main frontend
python t2t_training_fe.py

# Terminal 4: Admin frontend (optional)
python t2t_admin_fe.py
```

## Admin Workflow

### Step 1: Create a Project

1. Open admin panel: http://localhost:8051
2. Enter your admin email
3. Go to "Projects & Papers" tab
4. Fill in:
   - Project Name (e.g., "Flowering Time Study 2024")
   - Description (optional)
5. Click "Create Project"

### Step 2: Add Papers to Project

1. Select the project from dropdown
2. Paste DOI list (one per line):
   ```
   10.1038/nature12345
   10.1126/science.abc1234
   10.1093/plcell/koac123
   ```
3. Click "Add DOIs"
   - System fetches metadata from CrossRef API
   - Papers are added with "pending" status

### Step 3: Fetch PDFs

1. Select project to view papers
2. Click "Fetch PDFs" button
3. System tries:
   - doi2pdf service first
   - Unpaywall API as fallback
4. Status updates:
   - `pending` → `fetching` → `success` or `failed`

### Step 4: Review Papers

View paper status in the table:
- **DOI** - Digital Object Identifier
- **Title** - From CrossRef metadata
- **Authors** - Author list
- **Year** - Publication year
- **Status** - pending/fetching/success/failed
- **Error** - Error message if failed

## Annotation Workflow

### For Annotators

1. Open annotation interface: http://localhost:8050
2. Enter your email
3. **Select Project** from dropdown
4. **Select Paper** from dropdown
   - Only shows papers with successfully fetched PDFs
   - Displays title and year
5. PDF loads automatically
6. Select text in PDF
7. Click "Copy selected text to sentence"
8. Add tuples and save

### Manual DOI Entry

You can still enter DOIs manually if needed:
- Use "Or Enter DOI/Literature Link Manually" field
- Click "Validate DOI"
- Works as before

## Tuple Editor (Admin Only)

1. Go to "Tuple Editor" tab in admin panel
2. View all tuples from all users
3. Features:
   - See sentence context
   - View contributor email
   - Creation timestamp
   - (Future: inline editing)

## PDF Storage

PDFs are stored locally in the `pdfs/` directory:

```
pdfs/
├── {project-id}/
│   ├── {paper-id-1}.pdf
│   ├── {paper-id-2}.pdf
│   └── ...
```

## Troubleshooting

### PDFs Not Downloading

- Check if DOI is correct
- Some publishers block automated downloads
- Unpaywall only works for open access papers
- Check error message in papers table

### Project Dropdown Empty

- Ensure admin backend is running on port 5002
- Check `T2T_ADMIN_API_BASE` in `.env`
- Verify Supabase credentials in `.env`

### Permission Denied

- Verify your email is in `T2T_ADMIN_EMAILS`
- Restart backends after changing `.env`

### PDF Not Loading

- Verify paper has "success" status
- Check browser console for errors
- Try refreshing papers list

## API Endpoints

### Admin API (Port 5002)

- `GET /api/admin/projects` - List projects
- `POST /api/admin/projects` - Create project
- `GET /api/admin/projects/{id}/papers` - List papers
- `POST /api/admin/projects/{id}/papers` - Add DOIs
- `POST /api/admin/projects/{id}/fetch` - Fetch PDFs
- `GET /api/pdfs/{project_id}/{paper_id}` - Serve PDF
- `GET /api/admin/tuples` - List all tuples
- `PUT /api/admin/tuples/{id}` - Update tuple

## Security Notes

1. Admin operations require email verification
2. Only emails in `T2T_ADMIN_EMAILS` can:
   - Create projects
   - Add papers
   - Fetch PDFs
   - Edit tuples

3. All users can:
   - View projects and papers
   - Annotate with tuples
   - View their own tuples

## Future Enhancements

- Batch tuple editing in UI
- Project-level statistics
- Paper annotation progress tracking
- Export annotations per project
- PDF text extraction for search
