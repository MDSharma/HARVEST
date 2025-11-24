# PDF Download Stale Detection and Recovery

## Problem

When a PDF download process is started for a project and the backend or frontend is restarted during the download, the background thread dies but the database still shows the download as "running". This causes subsequent attempts to start the download to fail with:

```
"PDF Download: Failed to start - Download already in progress for this project"
```

## Solution

Implemented a robust recovery system that automatically detects and recovers from stale downloads.

## How It Works

### 1. Stale Detection

A download is considered "stale" if:
- Status is "running" in the database
- The `updated_at` timestamp hasn't been updated in the last 5 minutes (configurable)

This indicates the background thread has died (e.g., from a restart) while the database still shows it as active.

### 2. Automatic Recovery

When attempting to start a new download:
1. Check if a download is marked as "running"
2. If yes, check if it's stale (no updates in 5+ minutes)
3. If stale, automatically reset it to "interrupted" status
4. Proceed with starting a new download

### 3. Manual Force Restart

Users can also manually force restart a download by passing `force_restart: true`:

```json
POST /api/admin/projects/{project_id}/download-pdfs
{
  "email": "admin@example.com",
  "password": "secret",
  "force_restart": true
}
```

This immediately resets any existing download, regardless of staleness.

### 4. Status Reporting

The status endpoint now provides additional information for active downloads:

```json
GET /api/admin/projects/{project_id}/download-pdfs/status

Response:
{
  "status": "running",
  "is_stale": true,
  "time_since_update_seconds": 350,
  "warning": "Download appears to be stale (not updated recently). You can force restart it.",
  ...
}
```

## API Changes

### POST `/api/admin/projects/{project_id}/download-pdfs`

**New Parameter:**
- `force_restart` (optional, boolean): Force restart any existing download

**Behavior:**
- Automatically detects and resets stale downloads (>5 min without updates)
- If `force_restart=true`, immediately resets any active download
- Returns helpful error message with hint if download is active but not stale

**Example Request:**
```json
{
  "email": "admin@example.com",
  "password": "secret",
  "force_restart": false
}
```

**Error Response (when download is active but not stale):**
```json
{
  "error": "Download already in progress for this project",
  "hint": "If the download appears stuck, you can force restart it by setting 'force_restart': true"
}
```

### GET `/api/admin/projects/{project_id}/download-pdfs/status`

**New Response Fields (for running downloads):**
- `is_stale` (boolean): Whether the download is stale
- `time_since_update_seconds` (integer): Seconds since last update
- `warning` (string): Warning message if download is stale

## Configuration

The stale threshold is configurable:
- Default: 300 seconds (5 minutes)
- Can be adjusted in the code if needed

## Benefits

1. **Resilient to restarts**: Downloads can be resumed after backend/frontend restarts
2. **Automatic recovery**: No manual intervention needed in most cases
3. **Manual control**: Force restart option for immediate control
4. **Cross-session persistence**: Download progress stored in database, viewable from any browser session
5. **Clear status reporting**: Users know when downloads are stuck and can act accordingly

## Implementation Details

### New Functions (`harvest_store.py`)

```python
def is_download_stale(db_path: str, project_id: int, stale_threshold_seconds: int = 300) -> bool:
    """
    Check if a download is stale (not updated recently despite being 'running').
    Returns True if status is 'running' but updated_at is older than threshold.
    """

def reset_stale_download(db_path: str, project_id: int) -> bool:
    """
    Reset a stale download to allow it to be restarted.
    Changes status from 'running' to 'interrupted' so it can be resumed.
    """
```

### Status Workflow

```
Download Start → Running → Updates every ~30s → Completed
                    ↓
                   (Restart happens)
                    ↓
               No updates for 5 min
                    ↓
                 Detected as Stale
                    ↓
            Automatically Reset to "interrupted"
                    ↓
            Ready for New Download Start
```

## Testing

Comprehensive unit tests verify all functionality:
- Stale detection with various time thresholds
- Reset functionality
- Multiple concurrent projects
- Edge cases (completed downloads, non-existent downloads)

See `test_scripts/test_pdf_download_stale_detection.py` for details.

## Logging

The system logs all recovery actions:
```
[PDF Download] Detected stale download for project 123, resetting...
[PDF Download] Reset stale download for project 123
[PDF Download] Force restart requested for project 123
```

## Future Enhancements

Possible future improvements:
- Resume downloads from where they left off (instead of restarting)
- Configurable stale threshold per project
- Admin dashboard showing all stale downloads across projects
- Email notifications when downloads become stale
