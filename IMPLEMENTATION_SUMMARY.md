# Multi-Project PDF Download Implementation - Summary

## Problem Statement
The PDF download UI had several issues:
1. Only one download progress card could be visible at a time
2. Starting a download on Project 8 would hide Project 7's progress card
3. Backend correctly prevented duplicate downloads but UI didn't handle this well
4. Force Restart button was in the right place but the endpoint URL was incorrect
5. Stale download warning needed to be in the project card button row

## Solution Overview
Refactored the entire PDF download tracking system from single-project to multi-project support.

## Key Changes

### 1. Data Structure Changes
**Before:**
- `pdf-download-project-id`: `int` (single project)
- `pdf-download-state-store`: `dict` (single project state)

**After:**
- `pdf-download-project-id`: `dict[int, bool]` (multiple active projects)
- `pdf-download-state-store`: `dict[int, dict]` (state per project)

### 2. Callback Updates

#### `start_download_project_pdfs()` (Lines 3117-3196)
- Changed from storing single project ID to adding project to dict
- Maintains existing state for other active projects
- Returns updated dict structures

#### `restore_pdf_download_polling()` (Lines 3198-3213)
- Restores ALL active projects from state on page refresh
- Loops through state store to find all active downloads
- Enables polling if any project is active

#### `poll_pdf_download_progress()` (Lines 3241-3529)
- **Major refactor** - now polls ALL active projects
- Loops through each active project independently
- Builds separate progress content for each project
- Optimized: fetches config once per poll, not per project
- Type-safe: normalizes all project IDs to integers
- Removes completed projects from active tracking

#### `force_restart_download()` (Lines 3531-3602)
- Updated to work with multi-project dict structure
- Adds restarted project to active projects dict

### 3. Helper Function Update

#### `_build_progress_outputs()` (Lines 3215-3228)
**Before:** `(progress_div_ids, active_project_id, content)`
- Only showed content for ONE project

**After:** `(progress_div_ids, active_projects_content)`
- Takes dict mapping `{project_id: content}`
- Shows content for ALL active projects simultaneously

### 4. Bug Fixes
- Fixed endpoint URL from `/api/projects/{id}/pdf-download-progress` to correct `/api/admin/projects/{id}/download-pdfs/status`
- Renamed `progress_url` to `status_url` for clarity
- Added edge case handling for project ID 0

### 5. Performance Optimizations
- Config fetched once per poll instead of per project
- Reduced unnecessary API calls

## Testing

### New Test Files
1. **test_multi_project_downloads.py** (11 tests)
   - Multi-project state structure validation
   - Concurrent download scenarios
   - Per-project stale detection
   - All tests pass ✅

2. **verify_multi_project_ui.py** (4 verification scenarios)
   - Simulates the UI logic
   - Demonstrates multi-project support
   - All scenarios pass ✅

### Test Results
```
✅ All existing tests pass (test_pdf_download_state.py)
✅ All new multi-project tests pass (11/11)
✅ All UI verification scenarios pass (4/4)
✅ Module imports successfully with no syntax errors
✅ Security scan passed (0 vulnerabilities)
```

## Files Modified
1. `frontend/callbacks.py` (309 lines changed, 247 removed)
   - 4 callbacks refactored
   - 1 helper function updated
   - Type consistency improvements
   - Performance optimizations

2. `test_scripts/test_multi_project_downloads.py` (314 lines added)
   - New comprehensive test suite

3. `test_scripts/verify_multi_project_ui.py` (336 lines added)
   - New verification script

## User Experience

### Before
1. User clicks "Download PDFs" on Project 7 → Progress card appears
2. User clicks "Download PDFs" on Project 8 → Project 7 card disappears, Project 8 card appears
3. Only one download visible at a time

### After
1. User clicks "Download PDFs" on Project 7 → Progress card appears below Project 7
2. User clicks "Download PDFs" on Project 8 → Progress card appears below Project 8
3. **Both progress cards visible and updating independently**
4. Force Restart button appears only for stale downloads in the project button row
5. Page refresh preserves all active downloads

## Code Quality
✅ All code review feedback addressed
✅ Type-safe with consistent integer project IDs
✅ Optimized for performance
✅ Well-documented with clear comments
✅ Comprehensive test coverage
✅ Security verified (CodeQL scan: 0 alerts)

## Commits
1. `5b323ab` - Initial plan
2. `804d34b` - Refactor PDF download tracking to support multiple concurrent downloads
3. `d87f25a` - Add multi-project download test and fix stale detection endpoint
4. `6d686f9` - Address code review feedback: fix type consistency and optimize config fetching
5. `3783ffb` - Final polish: address code review nitpicks

## Summary
This implementation fully addresses all requirements in the problem statement:
✅ Multiple download progress cards can be displayed simultaneously
✅ Each project's progress card updates independently
✅ Force Restart button appears only for stale downloads
✅ Stale detection works correctly in the project card button row
✅ Backend duplicate download prevention maintained
✅ Type-safe, performant, and well-tested
