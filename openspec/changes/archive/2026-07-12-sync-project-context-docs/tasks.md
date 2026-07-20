## 1. Update Project Context Documentation

- [x] 1.1 Update the "Data model and storage" section in `openspec/specs/project-context.md` to document PostgreSQL and Qdrant usage.
- [x] 1.2 Update the "Architecture and module responsibilities" section in `openspec/specs/project-context.md` to include Semantic Caching and Conversational Memory Manager.
- [x] 1.3 Update the "API conventions" section in `openspec/specs/project-context.md` to include the new backend endpoints for session management (`GET /chat/sessions`, `GET /chat/session/{session_id}/messages`, `DELETE /chat/session/{session_id}`).
- [x] 1.4 Update the "Existing product behavior and UI conventions" section in `openspec/specs/project-context.md` to reflect that chat sessions persist in the backend database rather than just localStorage.
