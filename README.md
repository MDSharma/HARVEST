# Text2Trait: Training data builder

A web-based application for annotating biological text with entity relationships and metadata.

## Features

- **Email-based user identification** with validation
- **DOI validation and metadata fetching** from CrossRef API
- **PDF viewer with text selection** - automatically fetch and display PDFs from DOI
- **Copy text from PDF to annotation** - select text in PDF and copy to sentence field
- **Entity and relationship annotation** with customizable types
- **Multi-user concurrency protection** with tuple ownership tracking
- **User-based deletion protection** - only creators and admins can delete tuples
- **Efficient DOI storage** using reversible base64 hashing

## Quick Start

### Development Mode

1. Install dependencies:
```bash
pip install -r requirements.txt
# or if using poetry:
poetry install
```

2. **If upgrading from an older version**, run the migration script:
```bash
python3 migrate_db.py
```
This will safely update your database schema while preserving existing data.

3. Configure environment variables in `.env`:
```
T2T_ADMIN_EMAILS=admin1@example.com,admin2@example.com
T2T_DB=t2t.db
T2T_BACKEND_PORT=5001
T2T_FRONTEND_PORT=8050
T2T_HOST=0.0.0.0
```

4. Run the unified application:
```bash
python3 app.py
```

This single command starts both the backend API and frontend application.

5. Access the application at `http://localhost:8050`

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

The application attempts to fetch PDFs from:
1. **Unpaywall.org** - Open access PDFs
2. **CrossRef** - Publisher links when available

Note: Only open access and freely available PDFs can be displayed. Paywalled content will show an error message.
