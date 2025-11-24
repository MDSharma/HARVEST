# Project Creation Progress Indicator

## Overview

When creating a project with many DOIs (e.g., 394), the system now provides visual feedback during the validation process.

## What Happens During Creation

1. **DOI Validation**: Each DOI is validated against CrossRef API
   - This happens concurrently (10 DOIs at a time)
   - Each validation takes ~0.5-1 second
   - For 394 DOIs, this takes approximately 30-60 seconds

2. **Duplicate Detection**: DOIs are deduplicated automatically

3. **Project Storage**: Valid DOIs are saved to the database

## Visual Feedback

### Loading Spinner
- A spinner appears around the "Create Project" button output area while processing
- The spinner automatically disappears when validation completes

### Timeout Scaling
The timeout automatically scales based on the number of DOIs:
- **Formula**: `min(30 + (count * 0.1), 300)` seconds
- **Examples**:
  - 100 DOIs = 40 seconds
  - 394 DOIs = 69 seconds  
  - 1000 DOIs = 130 seconds
  - 3000+ DOIs = 300 seconds (5 minutes max)

### User Guidance
A helpful tip is displayed:
> 💡 Tip: For 300+ DOIs, validation may take 1-2 minutes. A spinner will appear while processing.

## Recommendations for Large DOI Lists

### For Lists of 300+ DOIs:
1. **Be patient**: The spinner indicates work is in progress
2. **Don't refresh**: Let the validation complete
3. **Wait for feedback**: You'll see detailed results when done

### For Lists of 1000+ DOIs:
1. **Consider batching**: Break into 200-500 DOI chunks for better experience
2. **Multiple projects**: You can create multiple projects and merge later if needed
3. **Monitor results**: Check the validation feedback for any issues

## Error Messages

### Timeout Error
If you see a timeout error:
```
⏱️ Request timed out while validating XXX DOIs.

This usually means the validation is taking longer than expected. 
For large DOI lists (300+), try breaking them into smaller batches of 100-200 DOIs.

The backend may still be processing your request. Please refresh the projects list in a moment to check if it completed.
```

**What to do**:
1. Wait 1-2 minutes
2. Refresh the projects list
3. Check if the project was created (it may have completed after timeout)
4. If not, try breaking the list into smaller batches

## Result Feedback

After successful creation, you'll see:
```
✅ Project created successfully! ID: 42
   Added 389 valid DOI(s).
   ⚠️ 5 DOI(s) were excluded (duplicates or invalid).
   Invalid DOIs:
     • 10.1234/invalid: Invalid DOI format
     • 10.5678/duplicate: Already exists
```

This shows:
- ✅ Success confirmation with project ID
- 📊 Count of valid DOIs added
- ⚠️ Warning if any DOIs were excluded
- 📝 Details about why specific DOIs were rejected (first 5 shown)

## Technical Details

### Backend Processing
- Concurrent validation: 10 DOIs at a time using ThreadPoolExecutor
- CrossRef API rate limiting: Built-in delays to respect API limits
- Caching: Validation results cached to avoid redundant API calls

### Frontend Behavior
- Synchronous callback: Button waits for backend response
- Loading indicator: `dcc.Loading` component shows spinner
- Button disabled: Prevents duplicate submissions during processing

## Performance Metrics

| DOI Count | Expected Time | Timeout Setting |
|-----------|---------------|-----------------|
| 50        | 5-10 seconds  | 35 seconds      |
| 100       | 10-20 seconds | 40 seconds      |
| 200       | 20-40 seconds | 50 seconds      |
| 394       | 40-70 seconds | 69 seconds      |
| 500       | 50-90 seconds | 80 seconds      |
| 1000      | 100-180 sec   | 130 seconds     |
| 2000+     | 200-300 sec   | 300 sec (max)   |

Note: Actual time varies based on:
- Network speed
- CrossRef API response time
- Server load
- Number of invalid/duplicate DOIs
