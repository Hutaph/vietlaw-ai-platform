import logging
from typing import List
from app.services.llm import get_llm
from app.services.provider_registry import SUMMARIZER_ROLE
from app.services.storage import get_session_summary, upsert_session_summary
from app.config import CHAT_STORAGE_MODE
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger("vietlaw.memory_manager")

SUMMARIZER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a legal AI memory manager.
Your task is to merge the "Old Summary" with the "New Interaction" to create a "New Summary".

RULES:
1. Ignore casual greetings or polite filler words.
2. RETAIN ALL legal entities (Law names, Decrees, Articles, Clauses).
3. RETAIN the user's core intent or factual background.
4. Keep the summary under 100 words. Format as a concise paragraph or short bullet points.

[OLD SUMMARY]:
{old_summary}

[NEW INTERACTION]:
{new_interaction}

Generate the [NEW SUMMARY]:""")
])

async def summarize_session(session_id: str, new_user_msg: str, new_ai_msg: str, runtime_config=None):
    """
    Asynchronously summarize the session by taking the old summary from DB,
    combining it with the latest turn, and saving it back.
    """
    try:
        if CHAT_STORAGE_MODE != "postgres":
            logger.debug("Skipping memory summarization in browser chat storage mode.")
            return
        if not session_id or session_id == "unknown":
            logger.debug("Skipping memory summarization for unknown session_id.")
            return

        session_data = get_session_summary(session_id)
        
        old_summary = ""
        turn_count = 0
        
        if session_data:
            old_summary = session_data.get("summary", "")
            turn_count = session_data.get("turn_count", 0)

        turn_count += 1
        
        new_interaction = f"User: {new_user_msg}\nAI: {new_ai_msg}"
        
        # Use a lightweight model for summarization
        llm = get_llm(
            model_name="qwen2.5:1.5b",
            temperature=0.1,
            runtime_config=runtime_config,
            role=SUMMARIZER_ROLE,
        )
        chain = SUMMARIZER_PROMPT | llm | StrOutputParser()
        
        new_summary = await chain.ainvoke({
            "old_summary": old_summary if old_summary else "No previous history.",
            "new_interaction": new_interaction
        })
        
        upsert_session_summary(session_id, new_summary.strip(), turn_count)
        logger.info("Updated memory summary for session %s (Turn %d)", session_id, turn_count)
        
    except Exception as e:
        logger.error("Failed to summarize session %s: %s", session_id, e)
