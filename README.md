# Text2Trait: Training data builder

A web-based application for annotating biological text with entity relationships and metadata.

## Features

### Core Annotation Features
- **Email-based user identification** with validation
- **Entity and relationship annotation** with customizable types
- **Multi-user concurrency protection** with tuple ownership tracking
- **User-based deletion protection** - only creators and admins can delete tuples

### NEW: Project-Based PDF Management
- **Project organization** - Group papers into annotation projects
- **Batch PDF fetching** - Download PDFs using doi2pdf and Unpaywall APIs
- **Project/paper dropdowns** - Select papers from projects for annotation
- **Local PDF storage** - Serve PDFs without embedding restrictions
- **Text selection always works** - Copy text from any PDF to annotation

### Admin Features
- **Admin panel** - Manage projects, papers, and tuples
- **Bulk DOI input** - Add multiple papers to projects at once
- **Tuple editor** - View and edit tuples from all users
- **DOI validation and metadata** - Automatic CrossRef API integration

## Quick Start

### New Installation

1. Run the setup script:
```bash
./setup.sh
```

This will:
- Install all Python dependencies
- Create required directories
- Initialize the database

2. Configure environment variables in `.env`:
```bash
T2T_ADMIN_EMAILS=your.email@example.com
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_SUPABASE_ANON_KEY=your_supabase_key
```

3. Start all services:
```bash
./start_all.sh
```

Or start services individually:
```bash
python3 t2t_training_be.py       # Main backend (port 5001)
python3 t2t_admin_be.py          # Admin backend (port 5002)
python3 t2t_training_fe.py       # Main frontend (port 8050)
python3 t2t_admin_fe.py          # Admin frontend (port 8051)
```

4. Access the applications:
- **Main Annotation Interface**: http://localhost:8050
- **Admin Panel**: http://localhost:8051

### Upgrading from Previous Version

If upgrading from an older version, run the migration script:
```bash
python3 migrate_db.py
```
This will safely update your database schema while preserving existing data.

### Production Deployment

For production deployment with nginx reverse proxy, see **[DEPLOYMENT.md](DEPLOYMENT.md)** for detailed instructions including:
- systemd service configuration
- nginx reverse proxy setup
- SSL certificate configuration
- Performance tuning
- Monitoring and maintenance

## Admin Configuration

Admin users can delete any tuple, while regular users can only delete their own. Configure admin emails in the `.env` file using the `T2T_ADMIN_EMAILS` variable (comma-separated list).

## Database Schema

- **sentences**: Stores annotated sentences with contributor information and DOI hash
- **doi_metadata**: Stores DOI metadata separately for efficiency (title, authors, year)
- **tuples**: Stores entity relationships with contributor tracking
- **entity_types**: Entity type definitions
- **relation_types**: Relationship type definitions
- **user_sessions**: Session tracking for multi-user support

## Usage

1. Enter your email address (required for attribution)
2. Enter and validate a DOI to:
   - Fetch article metadata (title, authors, year)
   - Automatically load the PDF in the right panel (if available)
3. In the PDF viewer:
   - Select text from the PDF document
   - Click "Copy selected text to sentence" button
   - The selected text will be added to the sentence field
4. Add tuples defining relationships between entities
5. Save your annotations
6. Browse saved annotations in the Browse tab

## PDF Sources

The application finds PDF URLs from:
1. **Unpaywall.org** - Open access PDFs (primary source)
2. **CrossRef** - Publisher links when available (fallback)

The PDF is loaded directly in your browser from the publisher's server, not proxied through the application. This ensures better performance and reduces server load.

**Note:** Only open access and freely available PDFs can be displayed. Paywalled content will show an appropriate message.

## Database Schema

The application uses an efficient schema that avoids redundant data:

### Key Tables

- **`sentences`**: Stores sentence text, literature link, and DOI hash
- **`doi_metadata`**: Stores only DOI (article metadata fetched from CrossRef API when needed)
- **`tuples`**: Stores entity relationships with contributor email
- **`entity_types`** and **`relation_types`**: Configurable entity and relation taxonomies

### Design Principles

1. **No Redundant Article Metadata**: Title, authors, and year are fetched from CrossRef API during export rather than stored in the database
2. **Single Contributor Tracking**: Contributor email is stored only in the `tuples` table (not duplicated in `sentences`)
3. **Efficient DOI Storage**: DOIs are hashed using base64 encoding for compact storage and fast lookups
4. **On-Demand Metadata**: Article metadata is cached during export operations to minimize API calls

### Migration

If you have an existing database with the old schema, run the migration script:

```bash
python3 migrate_schema_cleanup.py
```

This will safely remove redundant fields while preserving all your data.

## New Workflow: Project-Based Annotation

### For Admins

1. **Create a Project** (Admin Panel)
   - Open http://localhost:8051
   - Enter admin email
   - Create a new project (e.g., "Flowering Time Study 2024")

2. **Add Papers** (Admin Panel)
   - Select the project
   - Paste DOI list (one per line)
   - Click "Add DOIs" - metadata is fetched automatically

3. **Fetch PDFs** (Admin Panel)
   - Click "Fetch PDFs" button
   - System downloads PDFs using doi2pdf → Unpaywall fallback
   - Review status: pending → fetching → success/failed

### For Annotators

1. **Select Paper** (Main Interface)
   - Open http://localhost:8050
   - Enter your email
   - Select project from dropdown
   - Select paper from dropdown (only shows successfully fetched PDFs)

2. **Annotate**
   - PDF loads automatically in viewer
   - Select text in PDF
   - Click "Copy selected text to sentence"
   - Add entity tuples
   - Save annotations

### Benefits

✅ **No iframe restrictions** - PDFs are served locally
✅ **Text selection always works** - No browser security issues
✅ **Organized by project** - Better workflow for annotation campaigns
✅ **Batch preparation** - Download all PDFs upfront
✅ **Offline friendly** - Once downloaded, no external dependencies

For detailed admin instructions, see [ADMIN_GUIDE.md](ADMIN_GUIDE.md)
