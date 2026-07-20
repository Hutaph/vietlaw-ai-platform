## Why

Currently, the Vietnam Legal QA System passes the entire raw conversation history to the main LLM generator. As a chat session grows (e.g., 10-20 turns), this linear growth bloats the prompt, dilutes the LLM's attention away from retrieved legal context, slows down generation, and risks exhausting the context window limits. We need a conversational memory pruning system to summarize older messages while keeping recent context sharp.

## What Changes

- Introduce a database mechanism (e.g., in PostgreSQL) to store a compact `summary` string and a `turn_count` for each `session_id`.
- Update the `/chat` and `/chat/stream` endpoints to retrieve the `summary` and only the last 2-3 turns (Sliding Window), combining them into a concise prompt for the main LLM.
- Implement an asynchronous background task (Summarizer Agent) that runs periodically (e.g., after the LLM responds) to compress the newly added turns into the existing `summary`.

## Capabilities

### New Capabilities
- `memory-manager`: Handles the lifecycle of conversational memory, including storing summaries, retrieving compact context, and triggering background summarization tasks without blocking the main event loop.

### Modified Capabilities
- (None)

## Impact

- `backend/app/api/chat.py`: Endpoints will be modified to construct the prompt using summaries instead of full raw history, and to trigger background summarization.
- `backend/app/services/storage.py`: Needs schema updates to persist session summaries.
- `backend/app/services/pipeline.py` or a new memory service to house the Summarizer Agent logic.
