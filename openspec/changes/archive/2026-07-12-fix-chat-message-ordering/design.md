## Context

The backend uses `asyncio.create_task` to asynchronously save both the User query and AI response to PostgreSQL via `save_chat_message()`. Since these DB insertions run concurrently, they can enter the database in non-deterministic order. The SQL `INSERT` statement currently uses `NOW()` to assign the `created_at` timestamp. In Postgres, `NOW()` is evaluated at the start of the transaction. Because they race, the AI message sometimes gets an earlier or identical timestamp, causing it to render before the user query in the UI.

## Goals / Non-Goals

**Goals:**
- Guarantee that a user's query always has an earlier timestamp than the subsequent AI response in the same turn.
- Fix the frontend rendering order bug on page refresh.

**Non-Goals:**
- Implement a strictly sequential database insertion pipeline (we want to retain the performance benefit of concurrent asynchronous writes).

## Decisions

- **Decision 1: Generate explicit timestamps in the API layer**
  - **Rationale**: Instead of relying on Postgres `NOW()` inside the `save_chat_message` function, the `api/chat.py` handlers will generate explicit ISO 8601 string timestamps or Python `datetime` objects. 
  - We will generate a base timestamp for the user message, and a base + 1 millisecond (or just 1 second) timestamp for the AI message to guarantee explicit chronological order.
- **Decision 2: Update `save_chat_message` signature**
  - **Rationale**: The function will accept an optional `created_at` parameter. The SQL statement will be updated from `NOW()` to `COALESCE(%s, NOW())` or a similar pattern, allowing backward compatibility while supporting deterministic timestamps.

## Risks / Trade-offs

- **Risk**: Clock synchronization issues between different server instances (if scaled out).
  - **Mitigation**: Since both timestamps (user and AI) are generated sequentially on the exact same request thread in `chat.py`, they are guaranteed to be relatively ordered, regardless of absolute server clock skew.
