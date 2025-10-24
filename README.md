# Text2Trait: Training data builder

A web-based application for annotating biological text with entity relationships and metadata.

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
