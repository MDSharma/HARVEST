# DOI Batch Management - User Guide

## Overview

The DOI Batch Management feature helps teams efficiently annotate large projects with 100+ DOIs by organizing papers into manageable batches and tracking progress across annotators.

## For Annotators

### Using Batches for Annotation

1. **Navigate to the Annotate Tab**
   - Click on the "✏️ Annotate" tab in the main navigation

2. **Select Your Project**
   - Use the "Select Project" dropdown to choose your project
   - If the project has batches, a "Select Batch" dropdown will appear

3. **Choose a Batch**
   - Select a batch from the "Select Batch" dropdown
   - You'll see a progress bar showing:
     - ✓ Completed papers (green)
     - ⏳ In progress (yellow/orange)
     - ○ Unstarted (remaining)

4. **Select a DOI to Annotate**
   - The "Select DOI from Project" dropdown will show papers with status indicators:
     - 🔴 **Red circle** = Unstarted (no one has worked on this yet)
     - 🟡 **Yellow circle** = In progress by another annotator
     - 🔵 **Blue circle** = In progress by you
     - 🟢 **Green circle** = Completed
   
5. **Start Annotating**
   - Select a DOI (preferably an unstarted one 🔴)
   - The status automatically changes to "in progress" (🔵 for you)
   - Fill out the annotation form and save your triples
   - The DOI stays "in progress" until all annotations are complete

### Tips for Efficient Batch Work

- **Start with unstarted papers** (🔴) to avoid duplicating work
- **Check in-progress papers** (🟡) if someone seems stuck - you may be able to help
- **Use the progress bar** to see how much work remains in your batch
- **Switch batches** if your current batch is mostly completed or in-progress

### What If There Are No Batches?

If a project doesn't have batches configured, you'll see all DOIs in the dropdown without status indicators. The workflow is the same as before - just select any DOI and annotate.

## For Project Coordinators

### When to Create Batches

Consider creating batches for projects with:
- **100+ DOIs** - Makes navigation easier
- **Multiple annotators** - Helps coordinate work
- **Long-term projects** - Track progress over time

### Batch Size Guidelines

- **Small batches (10-15 DOIs)**: Quick wins, frequent completion satisfaction
- **Medium batches (20-30 DOIs)**: Good balance for most projects
- **Large batches (50+ DOIs)**: For experienced annotators or themed groups

### Monitoring Progress

As a coordinator, you can:
- View all project batches in the Admin tab
- See per-batch completion statistics
- Identify which batches need attention
- Re-assign batches if needed (by creating new batches)

## Frequently Asked Questions

### Q: Can I work on multiple batches simultaneously?
**A:** Yes! You can switch between batches at any time. Your in-progress papers stay marked with 🔵.

### Q: What happens if two people start the same paper?
**A:** The system shows it as "in progress" (🟡 or 🔵). The second person will see it's already being worked on. You can coordinate via your team communication channel.

### Q: Can I see who's working on a paper?
**A:** Currently, you can see if it's you (🔵) or someone else (🟡). The specific annotator email is tracked in the database but not shown in the UI.

### Q: How do I mark a paper as complete?
**A:** Papers are marked complete when you save annotations for them. The status updates automatically.

### Q: Can batches be deleted or reorganized?
**A:** Yes, admins can create new batches which will replace the old ones. This is useful if you want to reorganize based on progress or themes.

### Q: What if I prefer not to use batches?
**A:** That's fine! If a project has no batches, you'll see all DOIs in a regular dropdown. Batches are optional and meant to help with large projects.

## Troubleshooting

### Batch dropdown doesn't appear
- **Check**: Does the project have batches? Only projects with batches show the batch selector.
- **Solution**: Ask your admin to create batches for the project (see Admin Guide).

### Status indicators not updating
- **Check**: Are you logged in with your email?
- **Solution**: Refresh the page or re-select the batch.

### All papers show as "in progress"
- **Check**: This might happen if the batch was just created.
- **Solution**: Select a paper and start working - the status will update correctly.

### Can't find a specific DOI
- **Check**: Which batch is it in?
- **Solution**: Use the batch selector to switch between batches, or ask your admin about the DOI location.

## Best Practices

1. **Communicate with your team** - Use Slack, email, or your preferred tool to coordinate
2. **Finish what you start** - Try to complete papers you mark as "in progress"
3. **Leave notes** - Use the project management system to note any issues with specific papers
4. **Report problems** - If you encounter issues, tell your admin so they can help

## Support

For technical issues or questions:
- Contact your project administrator
- Check the main HARVEST documentation
- Report bugs via your team's issue tracker

---

*Last updated: November 2024*
*Feature version: 1.0*
