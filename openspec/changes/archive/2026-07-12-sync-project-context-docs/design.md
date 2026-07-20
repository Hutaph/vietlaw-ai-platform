## Context

The system has evolved rapidly, incorporating PostgreSQL, Qdrant, Semantic Caching, and a Conversational Memory Manager. However, the `openspec/specs/project-context.md` file, which serves as the architectural overview for the AI agents and developers, has not been updated and still describes the legacy state (JSON + FAISS, localStorage sessions).

## Goals / Non-Goals

**Goals:**
- Update `openspec/specs/project-context.md` to reflect the actual tech stack and data flow.
- Ensure future AI agents have correct context about the system's database and state management.

**Non-Goals:**
- No changes to application code.
- No changes to existing capability specs, as they are already accurate.

## Decisions

- **Decision 1: Direct update to `project-context.md`**: We will directly rewrite the outdated sections of `project-context.md` rather than creating a new file, as this is the standard entry point for project context.

## Risks / Trade-offs

- **Risk**: Missing some recent architectural changes in the update.
  - **Mitigation**: Carefully review the `backend/app/services/storage.py` and `backend/app/api/chat.py` to ensure all new backend mechanisms are captured.
