**Q&A**

- *Why do I see "Other…" inputs?*  
  To allow adding new entity types or relations not in the base schema.

- *Where do values come from?*  
  The app tries `GET /api/choices` on the backend. If that fails, it falls back to the JSON schema embedded in the app.

- *Can I browse saved items?*  
  Yes — see the **Browse** tab (fetches from `/api/recent`).
