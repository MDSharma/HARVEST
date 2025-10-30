**HARVEST Help Guide for End Users (Annotators)**

HARVEST is a human-in-the-loop tool for extracting actionable insights from scientific literature, focusing on biological text. As an annotator, you can label entities (e.g., genes, proteins, diseases) and their relationships in sentences from papers (identified by DOI), creating (source, relation, sink) triples for a queryable knowledge graph. Annotations include provenance like DOI, your email, and project (if selected). Follow these steps for the annotator workflow.

**1. Enter Your Email**
   - Provide your email address in the required field for attribution and session tracking.
   - This is mandatory and helps credit your contributions.

**2. Select a Project (Optional)**
   - Choose an existing project from the dropdown menu if your annotation relates to a specific campaign (e.g., biodiversity traits).
   - Projects organize annotations and may filter suggested DOIs.
   - Note: Creating new projects is admin-only. Contact an admin if you need a new one.

**3. Enter and Validate a DOI**
   - In the "DOI" input field, enter the DOI of the paper (e.g., 10.1038/nature12345).
   - The system will validate it automatically and store a hash for reference.
   - If the DOI is part of a selected project, it may auto-suggest or confirm from the project's list.
   - For paywalled papers, admins handle PDF uploads; as an annotator, you can view available PDFs.
   - Note: Literature search features, such as automatic PDF downloading for DOIs, are admin-only. If a PDF is needed but not available, request it from an admin.

**4. View the PDF (If Available)**
   - If a PDF is associated with the DOI (fetched or uploaded by admins), it will load in the side panel using the PDF viewer.
   - Toggle the viewer as needed.
   - Read the content to identify relevant sentences.
   - Optional: Enable highlighting mode with the "Highlight" button, select text, choose a color from the picker, and use "Save" or "Clear All" to manage highlights (saved directly to the PDF).
   - Keyboard shortcuts: H for highlight, Ctrl+S to save, arrow keys for navigation.
   - Note: PDF downloading and uploading are admin-only features.

**5. Input the Sentence**
   - Manually type or paste the sentence you want to annotate into the "Sentence" text area.
   - Currently, sentences do not auto-populate from PDF selections; you must enter them yourself.
   - Focus on sentences describing entities, traits, or relationships for best results.

**6. Annotate with Triples**
   - Click "Add Triple" to create one or more (source, relation, sink) triples.
     - **Source**: The starting entity (e.g., a gene or species; select entity type from dropdown).
     - **Relation**: The connection (e.g., "causes" or "associated with"; select from relation types).
     - **Sink**: The ending entity (select entity type).
   - Use dropdowns for predefined entity and relation types.
     - If a needed label isn't available, choose "Other..." to suggest a new one (admins can add to the database).
   - Repeat to add multiple triples for the same sentence.

**7. Save Your Annotations**
   - Review the sentence, DOI, and triples.
   - Click "Save" — the sentence is stored once, with all triples linked to it, plus your email, DOI, and project (if selected).
   - Annotations are added to the database and contribute to the community-curated knowledge graph.

**8. Browse Annotations**
   - Switch to the "Browse" tab to review saved sentences and triples.
   - Filter by project, DOI, or other criteria for quality checks or exports.

**Notes**
   - One sentence can have multiple triples, enabling detailed extractions from complex text.
   - Annotations are human-validated to refine AI models over time.
   - Entity and relation types are predefined in the database; suggest new ones via "Other..." for potential admin updates.
   - Privacy: Emails are used for attribution only; data from public literature is handled securely.
   - Troubleshooting: If PDF doesn't load, it may not be available—ask an admin. For DOI validation errors, ensure the format is correct.
   - Feedback: Report issues or suggest features through GitHub or contact the project maintainers.

For advanced queries, use the Browse tab to search the knowledge graph. If you need admin features like literature search or project creation, contact an admin.
