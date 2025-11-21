# HARVEST Admin Guide

HARVEST is a human-in-the-loop tool for extracting actionable insights from scientific literature, focusing on biological knowledge extraction. As an admin, you have access to all annotator features plus management tools for projects, PDFs, DOI lists, and quality control. This guide covers the admin workflow.

## Key Admin Features

### Authentication & Persistence
- Admin credentials now persist across browser refreshes (stored in local storage)
- No more logout on accidental page refresh
- PDF download status remains visible after page reload
- Background processes remain accessible

### Project Management

#### Creating & Managing Projects
- **Create Projects**: Organize annotation campaigns with predefined DOI lists
- **Edit DOI Lists**: Add or remove DOIs from existing projects
  - Case-insensitive deduplication ensures no duplicate DOIs
  - All DOIs are normalized to lowercase for consistency
  - Option to delete associated PDFs when removing DOIs
- **View Projects**: Projects list auto-refreshes after login
- **Delete Projects**: Choose how to handle associated triples:
  - Keep as uncategorized (recommended)
  - Reassign to another project
  - Delete them entirely

#### DOI List Management
- **PDF Indicators**: DOI dropdowns now show 📄 emoji for DOIs with available PDFs
- **Edit Mode**: Use the "Edit DOIs" button to:
  - View current DOI list
  - Add new DOIs (one per line)
  - Remove DOIs (one per line)
  - Optionally delete associated PDFs when removing DOIs

### Literature Search & PDF Management

#### Automatic PDF Downloads
- Trigger automatic PDF downloads for project DOIs via Unpaywall API
- Configure your email in `config.py` for API access
- System searches for open-access PDFs and downloads available ones
- Skips existing files to avoid duplication
- View download reports to identify DOIs needing manual intervention

#### Manual PDF Management
- Upload PDFs for paywalled or failed downloads
- Files named with DOI hash for automatic association
- PDFs stored in project-specific directories
- Delete PDFs when removing DOIs from projects (optional)

#### Batch Management
- Create DOI batches within projects for organized annotation workflows
- Assign annotators to specific batches
- Track progress with status indicators (🔴 unstarted, 🟡 in progress, 🟢 completed)

### Schema Management

The system now includes enhanced entity and relation types for richer biological knowledge extraction:

#### Entity Types
- Core: Gene, Protein, Variant, Enzyme, QTL, Metabolite, Trait
- Regulatory: Regulator, Coordinates
- Systems: Pathway, Process, Factor (biotic/abiotic)

#### Relation Types
- **Ontological**: is_a, part_of, develops_from
- **Regulatory**: regulates, activates, inhibits, represses
- **Molecular**: encodes, binds_to, phosphorylates, methylates, acetylates, interacts_with
- **Quantitative**: increases, decreases, contributes_to
- **Spatial/Temporal**: localizes_to, expressed_in, precedes, follows
- **Associations**: associated_with, causes, prevents, co_occurs_with
- **Influence**: influences, may_influence, does_not_influence, disrupts

See `schema.md` for full details and descriptions.

### Triple Management

#### Editing & Quality Control
- Edit triples: Update entity names or relationships for accuracy
- Delete incorrect or duplicate triples
- Filter triples by project for focused review
- Bulk operations for database maintenance

#### Browse & Filter
- Advanced filtering in Browse tab
- Filter by project, DOI, entity types, relation types
- Export data for analysis
- Customizable field display

### PDF Viewing & Highlighting

#### PDF Viewer Features
- Side panel PDF viewer with navigation controls
- Highlighting mode: Toggle, select text, pick colors
- Save highlights: Ctrl+S or Save button
- Clear all highlights option
- Keyboard shortcuts: H for highlight mode, arrow keys for navigation

#### Configuration
Control PDF features via `config.py`:
- `ENABLE_PDF_HIGHLIGHTING` - Enable/disable highlighting
- `ENABLE_LITERATURE_SEARCH` - Enable/disable literature search features
- `ENABLE_LITERATURE_REVIEW` - Enable/disable ASReview integration

### Security & Limits

- Maximum 50 highlights per save operation
- File size limit: 100 MB for PDFs
- Input sanitization for all user data
- Proper authentication checks on all admin endpoints
- Path traversal protection for file operations

### Debug Logging

For troubleshooting, enable debug logging:

**In `config.py`:**
```python
ENABLE_DEBUG_LOGGING = True
```

**Or via environment variable:**
```bash
export HARVEST_DEBUG_LOGGING=true
```

⚠️ **Important**: Disable in production to avoid filling logs!

### Privacy & Data Handling

- Emails used for attribution only
- Handle data securely
- PDFs from public/open-access sources
- Proper data retention policies

### Troubleshooting

#### Common Issues
- **DOI Downloads**: Configure Unpaywall email in `config.py`
- **PDF Not Loading**: Check file permissions and paths
- **Login Issues**: Verify admin credentials in environment or database
- **KeyError**: Clear browser cache (Ctrl+Shift+R)

#### Debug Mode
Enable `ENABLE_DEBUG_LOGGING` to track:
- Legacy callback triggers
- API request/response details
- Database operations
- File system operations

### Best Practices

1. **Project Organization**: Create projects for specific annotation campaigns
2. **DOI Management**: Use batch creation for large DOI lists
3. **Quality Control**: Regularly review and clean up annotations
4. **PDF Management**: Download PDFs in batches during off-peak hours
5. **Backups**: Regular database backups for data protection
6. **Updates**: Keep schema current with scientific domain needs

### Support & Feedback

- Report issues on GitHub
- Suggest new entity/relation types via "Other..." option
- Contact maintainers for feature requests
- Contribute to documentation improvements

---

For annotator-specific guidance, refer to `annotator_guide.md`.
