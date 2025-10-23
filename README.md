# Text2Trait: Training data builder

A web-based application for annotating biological text with entity relationships and metadata.

## Features

- **Email-based user identification** with validation
- **DOI validation and metadata fetching** from CrossRef API
- **Entity and relationship annotation** with customizable types
- **Multi-user concurrency protection** with tuple ownership tracking
- **User-based deletion protection** - only creators and admins can delete tuples
- **Efficient DOI storage** using reversible base64 hashing

## Setup

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
T2T_PORT=5001
T2T_HOST=0.0.0.0
```

4. Run the backend:
```bash
python3 t2t_training_be.py
```

5. Run the frontend (in a separate terminal):
```bash
python3 t2t_training_fe.py
```

6. Access the application at `http://localhost:8050`

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
2. Optionally enter and validate a DOI to fetch article metadata
3. Enter the sentence to annotate
4. Add tuples defining relationships between entities
5. Save your annotations
6. Browse saved annotations in the Browse tab
