**HARVEST Help Guide for Admin Users**

HARVEST is a human-in-the-loop tool for extracting actionable insights from scientific literature, focusing on biological text. As an admin, you have access to all annotator features plus management tools for projects, PDFs, and triples. This includes literature search capabilities like automatic PDF downloading via Unpaywall for open-access articles. Annotations include provenance like DOI, contributor email, and project. Follow these steps for the admin workflow, building on the annotator process.

**1. Access the Admin Panel**
   - Go to the "Admin" tab and log in with your admin credentials (created via script or environment variable).
   - This unlocks all advanced features.

**2. Manage Projects**
   - Create new projects to organize annotation campaigns, including predefined DOI lists.
   - View, edit, or delete existing projects.
   - When deleting, choose options for associated triples: keep as uncategorized (recommended), reassign to another project, or delete them.
   - Projects help filter and suggest DOIs for annotators.

**3. Handle Literature Search and PDFs**
   - For projects, trigger automatic PDF downloads for DOIs using the Unpaywall API (configure your email in config.py).
   - This searches for open-access PDFs and downloads available ones, skipping existing files.
   - View download reports to identify DOIs needing manual intervention (e.g., paywalled articles).
   - Manually upload PDFs for paywalled or failed downloads, naming files with the DOI hash.
   - PDFs are stored in project-specific directories.
   - Note: Literature search (e.g., automatic PDF fetching via Unpaywall) is admin-only to manage access and compliance.

**4. Enter and Validate a DOI (Enhanced for Admins)**
   - Same as annotators, but you can add DOIs to projects for team-wide use.
   - Validate and link to PDFs directly.

**5. View and Annotate PDFs**
   - Load PDFs in the side panel viewer.
   - Use highlighting: toggle with "Highlight" button, select text, pick colors, save (Ctrl+S), or clear all.
   - Keyboard shortcuts: H for highlight mode, arrow keys for navigation.
   - As admin, you control enabling/disabling PDF features via config (e.g., ENABLE_PDF_DOWNLOAD, ENABLE_PDF_HIGHLIGHTING).

**6. Input Sentences and Annotate with Triples**
   - Same as annotators: Manually enter sentences, add (source, relation, sink) triples using dropdowns, and save.
   - Use "Other..." to suggest new entity/relation types, which you can later add to the database.

**7. Edit and Manage Annotations**
   - In the Admin panel, edit triples: update entity names or relationships for accuracy.
   - Delete incorrect or duplicate triples.
   - Filter triples by project when searching or browsing.

**8. Browse and Maintain Annotations**
   - Use the "Browse" tab to review all annotations, with advanced filters.
   - Run database maintenance: Clean up orphaned sentences (dry run or execute), assign custom names for default projects.

**Notes**
   - One sentence can have multiple triples for rich extractions.
   - Annotations improve AI models; track contributors via email.
   - Security: Limits on highlights (50 max per save), file sizes (100 MB), and input sanitization.
   - Privacy: Handle data securely; PDFs from public/open-access sources.
   - Troubleshooting: Configure Unpaywall email for downloads. For errors, check config.py settings.
   - Feedback: As admin, you can contribute to GitHub for feature enhancements.

Use admin tools for quality control and to support annotators with literature search and PDF management. For annotator-specific guidance, refer to the end-user guide.
