# DOI Batch Management - Admin Guide

## Overview

As an administrator, you can create and manage DOI batches to help your team efficiently annotate large projects. This guide covers batch creation, monitoring, and best practices.

## Prerequisites

- Admin account credentials (email and password)
- Logged in to the Admin tab
- At least one project with DOIs

## Creating Batches

### Step-by-Step Instructions

1. **Login to Admin Panel**
   - Navigate to the "👤 Admin" tab
   - Enter your admin email and password
   - Click "Login"

2. **Navigate to Batch Management**
   - Scroll down to the "DOI Batch Management" section
   - You'll see a card with batch creation controls

3. **Select Project**
   - Choose a project from the "Select Project" dropdown
   - The dropdown shows DOI counts: "Project Name (150 DOIs)"
   - Projects with existing batches will show them below

4. **Configure Batch Settings**
   - **Batch Size**: Number of DOIs per batch (5-100)
     - Default: 20 DOIs
     - Recommended: 20-30 for most projects
   - **Strategy**:
     - **Sequential**: DOIs divided in order (default)
     - **Random**: DOIs randomly shuffled before batching

5. **Create Batches**
   - Click "Create Batches" button
   - Wait for confirmation message
   - Existing batches will be replaced with new ones

6. **Review Created Batches**
   - New batches appear below the creation form
   - Each batch shows:
     - Batch number and name
     - DOI count
     - Progress bar (starts empty)
     - Status breakdown

## Batch Configuration Guide

### Choosing Batch Size

| Project Size | Recommended Batch Size | Number of Batches | Reasoning |
|-------------|----------------------|------------------|-----------|
| 50-100 DOIs | 15-20 | 3-5 | Small project, keep batches focused |
| 100-200 DOIs | 20-30 | 4-10 | Standard batch size for most projects |
| 200-500 DOIs | 30-50 | 5-15 | Larger batches for efficiency |
| 500+ DOIs | 40-100 | 10+ | Balance between manageability and overhead |

### Strategy Selection

**Sequential Strategy**
- Use when: DOIs are already organized (by date, topic, etc.)
- Benefits:
  - Preserves existing order
  - Predictable batch contents
  - Easier to find specific papers
- Example: Project with DOIs sorted by publication date

**Random Strategy**
- Use when: You want to distribute variety across batches
- Benefits:
  - Balances difficulty across batches
  - Prevents one batch from having all hard papers
  - Good for blind annotation scenarios
- Example: Mixed literature review with varying complexity

## Monitoring Progress

### Viewing Batch Status

After creating batches:

1. **Select the project** in Batch Management
2. **View batch list** showing:
   - Batch number and name
   - Total DOIs
   - Progress breakdown:
     - ✓ Completed papers
     - ⏳ In progress
     - ○ Unstarted
   - Visual progress bar

3. **Interpret progress**:
   - Green bar = completed annotations
   - Orange/yellow bar = work in progress
   - Empty space = unstarted

### Tracking Project-Wide Status

Use the backend API endpoint to get detailed statistics:

```bash
GET /api/projects/{project_id}/doi-status
```

Returns:
```json
{
  "total": 150,
  "unstarted": 80,
  "in_progress": 45,
  "completed": 25,
  "by_batch": [...]
}
```

## Managing Batches

### Recreating Batches

To reorganize or change batch configuration:

1. Select the project
2. Adjust batch size or strategy
3. Click "Create Batches"
4. Confirm when prompted

**Note**: This replaces existing batches but preserves DOI annotation status.

### When to Recreate Batches

- Initial batch size was too large/small
- Want to redistribute based on progress
- Need different organization strategy
- Adding new DOIs to the project

### Batch Status Persistence

- DOI annotation status is independent of batches
- Recreating batches doesn't reset progress
- Status indicators will update with new batch assignments

## Best Practices

### Initial Setup

1. **Start with standard batch size (20-30)**
   - You can always recreate with different sizes
   - See what works for your team

2. **Use sequential strategy first**
   - Easier to track and discuss specific papers
   - Random can be used later if needed

3. **Communicate with your team**
   - Announce when batches are created
   - Explain the batch numbering system
   - Set expectations for completion

### Ongoing Management

1. **Monitor progress regularly**
   - Check batch status weekly
   - Identify stalled batches
   - Reassign if needed

2. **Balance workload**
   - If some batches are fully in-progress, guide team to others
   - Consider team member capacity

3. **Don't recreate frequently**
   - Batch recreation can be confusing for active annotators
   - Only reorganize when necessary

### Team Coordination

1. **Assign batches to team members**
   - Document who works on which batches
   - Use external tracking (spreadsheet, Slack, etc.)

2. **Set batch completion goals**
   - "Complete Batch 1 by end of week"
   - Provides clear milestones

3. **Regular check-ins**
   - Team meetings to discuss progress
   - Address issues with specific papers
   - Celebrate batch completions

## Troubleshooting

### Batch creation fails

**Error**: "Project may not exist or have no DOIs"
- **Solution**: Verify project has DOIs in project management section

**Error**: "Invalid admin credentials"
- **Solution**: Re-login to admin panel

**Error**: "batch_size must be between 5 and 100"
- **Solution**: Enter a valid batch size value

### Batches don't appear in Annotate tab

**Issue**: Annotators don't see batch selector
- **Check**: Did batches create successfully? Look for success message
- **Solution**: Refresh the page, re-select project

### Progress not updating

**Issue**: Batch progress bars show incorrect data
- **Check**: Is the browser cache stale?
- **Solution**: Refresh the admin page, re-select project

### Too many/few batches

**Issue**: Batch count doesn't match expectations
- **Calculation**: Number of batches = ceil(total_dois / batch_size)
- **Example**: 150 DOIs ÷ 20 batch size = 8 batches (7 full + 1 with 10)

## API Reference for Admins

### Create Batches
```
POST /api/admin/projects/{project_id}/batches
Body: {
  "admin_email": "admin@example.com",
  "admin_password": "password",
  "batch_size": 20,
  "strategy": "sequential"
}
```

### List Batches
```
GET /api/projects/{project_id}/batches
```

### Get Batch DOIs
```
GET /api/projects/{project_id}/batches/{batch_id}/dois
```

### Get Status Summary
```
GET /api/projects/{project_id}/doi-status
```

## Database Schema

For reference, the batch management uses these tables:

- `doi_batches`: Batch metadata
- `doi_batch_assignments`: DOI-to-batch mapping
- `doi_annotation_status`: Per-DOI status tracking

Indexes ensure efficient queries even with large projects.

## Migration from Non-Batched Projects

If you have existing projects without batches:

1. **No data loss**: All existing annotations preserved
2. **Create batches anytime**: No prerequisites needed
3. **Optional feature**: Projects work fine without batches
4. **Reversible**: Can work without batches after creation

## Security Considerations

- Batch creation requires admin authentication
- Status updates authenticated via email verification
- No user can delete or corrupt batch data
- Audit trail maintained in database timestamps

## Performance Notes

- Batch operations are fast even with 1000+ DOIs
- Status queries optimized with database indexes
- No performance impact on annotation workflow
- Scales well with multiple concurrent users

## Support and Feedback

For issues or suggestions:
- Check the user guide for annotator questions
- Review database logs for backend errors
- Report bugs to your development team
- Suggest improvements based on team feedback

---

*Last updated: November 2024*
*Feature version: 1.0*
*For: HARVEST administrators and project coordinators*
