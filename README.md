# HARVEST: Human-in-the-loop Actionable Research and Vocabulary Extraction Technology

A web-based application for annotating biological text with entity relationships and metadata.

## Setup

### Quick Installation

For detailed installation instructions, see **[INSTALLATION.md](INSTALLATION.md)**.

### Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

**Important**: Make sure PyMuPDF is installed for PDF highlighting features:
```bash
pip install PyMuPDF>=1.23.0
```

2. **Configure the application** (IMPORTANT):

Edit `config.py` and update the following settings:

```python
# Update this to your email address (required by Unpaywall API)
UNPAYWALL_EMAIL = "your-email@example.com"  # CHANGE THIS

# Optional: Add admin emails for access
ADMIN_EMAILS = "admin@example.com,researcher@university.edu"

# Optional: Customize ports and paths
HOST = "127.0.0.1"
PORT = 8050
BE_PORT = 5001
DB_PATH = "t2t_training.db"
```

**IMPORTANT**: The `UNPAYWALL_EMAIL` must be set to a valid email address before using PDF download features. This is required by the Unpaywall API.

3. **If upgrading from an older version**, run the migration script:
```bash
python3 migrate_db_v2.py
```
This will safely update your database schema while preserving existing data.

**Note**: The migration will:
- Remove redundant article metadata fields (title, authors, year) from the doi_metadata table
- Remove contributor_email from sentences table (tracked at triple level)
- Add `project_id` column to triples table for project association
- Add new tables for projects and admin authentication

**Important**: After upgrading, make sure to run the migration script before starting the application to avoid database errors.

## Running the Application

### Option 1: Using the Launcher (Recommended)

The easiest way to start the application is using the included launcher script, which handles both the backend and frontend:

```bash
python3 launch_t2t.py
```

This will:
- Start the backend API server on port 5001
- Start the frontend UI server on port 8050
- Verify both services launched successfully
- Monitor the processes and handle graceful shutdown when you press Ctrl+C

Then access the application at `http://localhost:8050`

### Option 2: Manual Launch

Alternatively, you can manually start each service in separate terminals:

1. Run the backend:
```bash
python3 t2t_training_be.py
```

2. Run the frontend (in a separate terminal):
```bash
python3 t2t_training_fe.py
```

3. Access the application at `http://localhost:8050`

### Configuration

You can customize the ports and hosts using environment variables:
- `T2T_PORT`: Backend API port (default: 5001)
- `PORT`: Frontend UI port (default: 8050)
- `T2T_HOST`: Backend host (default: 127.0.0.1)
- `FRONTEND_HOST`: Frontend host (default: 127.0.0.1)
- `T2T_DB`: Database file path (default: t2t.db)
- `T2T_ADMIN_EMAILS`: Comma-separated list of admin emails (optional)
- `T2T_DEPLOYMENT_MODE`: Deployment mode - "internal" or "nginx" (default: internal)
- `T2T_BACKEND_PUBLIC_URL`: Backend URL for nginx mode (required when mode is "nginx")

## Deployment

The application supports two deployment modes:

### Internal Mode (Default)
- Simple setup for development and single-server deployments
- Backend runs on localhost only, protected from external access
- Frontend proxies all backend requests internally
- No reverse proxy required

### Nginx Mode
- Production-ready deployment with reverse proxy
- Supports load balancing, SSL termination, and advanced routing
- Backend accessible at configured public URL
- Ideal for scaled deployments

**For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)**

## Admin Features

### Creating an Admin User

To access admin features, you need to create an admin user:

```bash
python3 create_admin.py
```

This will prompt you for an email and password. The password will be securely hashed and stored in the database.

Alternatively, you can set admin emails via environment variable:
```bash
export T2T_ADMIN_EMAILS="admin1@example.com,admin2@example.com"
```

### Admin Panel

The Admin panel (accessible from the Admin tab) allows you to:

1. **Manage Projects**: Create projects with lists of DOIs for organized annotation campaigns
2. **Edit Triples**: Update any triple's entity names or relationships
3. **Delete Triples**: Remove incorrect or duplicate triples

## Database Schema

- **sentences**: Stores annotated sentences with DOI hash reference
- **doi_metadata**: Stores DOI and hash (article metadata fetched on-demand from CrossRef)
- **triples**: Stores entity relationships with contributor email tracking
- **entity_types**: Entity type definitions
- **relation_types**: Relationship type definitions
- **user_sessions**: Session tracking for multi-user support
- **projects**: Project definitions with DOI lists for organized annotation
- **admin_users**: Admin user authentication (password hashed with bcrypt)

## Usage

### For Annotators

1. Enter your email address (required for attribution)
2. (Optional) Select a project to work on from the dropdown
3. (Optional) Enter and validate a DOI to link your annotation
4. Enter the sentence to annotate
5. Add triples defining relationships between entities
6. Save your annotations
7. Browse saved annotations in the Browse tab

### For Administrators

1. Go to the Admin tab
2. Login with your admin credentials
3. Create projects to organize annotation work
4. View and manage existing projects
5. Download PDFs for project DOIs (where available)
6. Upload PDFs for paywalled articles
7. Delete projects with options for handling associated triples:
   - Keep triples as uncategorized (recommended)
   - Reassign triples to another project
   - Delete all associated triples
8. Edit or delete triples as needed for quality control
9. Filter triples by project when searching for specific entries

## PDF Management

### Configuration

Before using PDF download features, you **MUST** edit `config.py` and set your email address:

```python
UNPAYWALL_EMAIL = "your-email@example.com"  # REQUIRED - Change this to your email
```

This email is required by the Unpaywall API to check open access status. Without it, PDF downloads will fail.

Other customizable settings in `config.py`:
- `HOST` and `PORT`: Server address and port settings
- `DB_PATH`: Database file location  
- `PDF_STORAGE_DIR`: Where to store downloaded PDFs
- `ADMIN_EMAILS`: Additional admin email addresses
- `ENABLE_PDF_DOWNLOAD`: Toggle PDF download feature
- `ENABLE_PDF_VIEWER`: Toggle embedded PDF viewer
- `ENABLE_PDF_HIGHLIGHTING`: Toggle PDF highlighting/annotation feature (requires ENABLE_PDF_VIEWER=True)

### PDF Viewer with Highlighting

The application includes an integrated PDF viewer with text highlighting capabilities. This feature can be enabled/disabled using the `ENABLE_PDF_HIGHLIGHTING` setting in `config.py`.

**When enabled**, the viewer allows you to:

- **Highlight text** in PDFs using a highlighter pen-like tool
- **Choose highlight colors** from a color picker
- **Save highlights** directly to the PDF file for permanent storage
- **View saved highlights** when reopening the PDF
- **Clear all highlights** if needed

**Security Features:**
- Maximum of 50 highlights per save operation (prevents abuse)
- Highlight text limited to 10,000 characters each
- File size validation (100 MB limit)
- Input sanitization and validation on all highlight data
- Protection against path traversal attacks

**How to Use the Highlighting Feature:**

1. Select a DOI from a project to load its PDF in the viewer
2. Click the "🖍️ Highlight" button to enable highlighting mode
3. Click and drag on the PDF to create a highlight
4. Change the highlight color using the color picker if desired
5. Click "💾 Save" to permanently store highlights in the PDF file
6. Use "🗑️ Clear All" to remove all highlights from the PDF

**Keyboard Shortcuts:**
- `H`: Toggle highlight mode
- `Ctrl+S`: Save highlights
- Arrow keys or Page Up/Down: Navigate pages

**Technical Details:**
- Highlights are stored as PDF annotations using the PyMuPDF library
- The viewer uses PDF.js for rendering with a custom overlay for highlighting
- All highlights are validated and sanitized before being saved
- Highlights persist in the PDF file and are readable by other PDF viewers

### Automatic PDF Download

For projects with DOI lists, administrators can automatically download open-access PDFs:

1. Create a project with DOI list
2. Click "Download PDFs" button in the project management section
3. The system will:
   - Check each DOI for open access availability (via Unpaywall API)
   - Download available open-access PDFs automatically
   - Skip DOIs where PDFs already exist
   - Provide a list of DOIs requiring manual upload

PDFs are named using the DOI hash (e.g., `abc123def456.pdf`) and stored in `project_pdfs/project_<id>/`.

### Manual PDF Upload

For paywalled articles or failed downloads:

1. The download report shows which DOIs need manual upload
2. Obtain PDFs through your institutional access
3. Use the upload function to add PDFs to the project
4. Name files according to the provided doi_hash

**Important**: This tool only downloads legally available open-access content. You must have appropriate permissions for any manually uploaded PDFs.

## Database Maintenance

### Cleanup Orphaned Sentences

Over time, you may accumulate sentences without associated triples (incomplete entries). Use the cleanup script to identify and remove them:

```bash
# Dry run (shows what would be deleted without deleting)
python3 cleanup_orphaned_sentences.py

# Actually perform cleanup
python3 cleanup_orphaned_sentences.py --execute

# Assign a custom name for the default project
python3 cleanup_orphaned_sentences.py --execute --default-project "General Annotations"
```

The cleanup script will:
1. Find and optionally delete sentences without any triples
2. Assign triples with NULL project_id to a default "Uncategorized" project

**Note**: Always run the dry-run first to see what will be affected!

### Cascade Deletion

When you delete a triple through the admin panel:
- If it's the last triple for a sentence, the sentence is automatically deleted as well
- This prevents orphaned sentences and maintains database integrity

## Project-Based Annotation

Administrators can create projects with predefined lists of DOIs. This helps organize annotation campaigns around specific papers or topics. Users can select a project from the dropdown, and the system will suggest DOIs from that project's list.
