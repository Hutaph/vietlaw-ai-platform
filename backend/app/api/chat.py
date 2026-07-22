"""
API router for /chat and /chat/stream.
Contains request/response orchestration for chat endpoints.
"""
import re
import json
import time
import traceback
import asyncio
from typing import AsyncGenerator
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import CHAT_STORAGE_MODE, PIPELINE_TIMING_ENABLED
from app.models import ChatRequest
from app.services.pipeline import get_pipeline
from app.services.llm import get_llm, CHAT_PROMPT, get_output_parser
from app.services.embedding.errors import (
    EmbeddingAuthError,
    EmbeddingServiceError,
)
from app.services.pipeline_timing import (
    PipelineTimingCollector,
    reset_current_timing,
    sanitize_request_id,
    set_current_timing,
)
from app.services.answer_validation import validate_generated_citations
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.api.chat")

router = APIRouter()

_CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\uac00-\ud7af\u3040-\u30ff]')


def _clean_chunk(text: str) -> str:
    """Remove CJK characters and repeated spaces."""
    text = _CJK_PATTERN.sub('', text)
    return re.sub(r' +', ' ', text)


def _sse(data: dict) -> str:
    """Format one Server-Sent Event line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _embedding_error_status(exc: EmbeddingServiceError) -> int:
    return 401 if isinstance(exc, EmbeddingAuthError) else 503


def _llm_error_detail(model_name: str, exc: Exception) -> str:
    """Return a user-safe LLM error message without exposing credentials."""
    text = str(exc)
    lowered = text.lower()
    if "unsupported google model" in lowered:
        return text
    if "404" in lowered or "not_found" in lowered or "no longer available" in lowered:
        return (
            f"LLM provider rejected model '{model_name}'. "
            "Choose a currently supported model and retry."
        )
    return "Tất cả các dịch vụ suy luận (LLM) đều không khả dụng. Vui lòng thử lại sau."


def _recent_messages(request: ChatRequest):
    """Return the configured messages immediately before the latest user message."""
    limit = request.historyMessages
    return request.messages[-(limit + 1):-1] if limit > 0 else []


def _filter_cited_context(output_text: str, context: list, max_citations: int) -> list:
    """Return cited contexts in citation order, capped for the client payload."""
    cited_ids = list(dict.fromkeys(re.findall(r'<cite\s+id=["\']([^"\']+)["\']>', output_text)))
    if not cited_ids:
        return context[:max_citations]
    cited_ids = cited_ids[:max_citations]
    by_id = {item.get("metadata", {}).get("id"): item for item in context}
    valid_citations = [by_id[citation_id] for citation_id in cited_ids if citation_id in by_id]
    if not valid_citations:
        return context[:max_citations]
    return valid_citations


def _rewrite_query(rewriter, query: str, history: str, runtime_config):
    try:
        return rewriter.rewrite(query, history, runtime_config)
    except TypeError:
        return rewriter.rewrite(query, history)


async def _persist_turn(session_id: str, session_title: str, user_msg_id: str, user_content: str, ai_msg_id: str, ai_content: str, ai_context: list, user_time: datetime, ai_time: datetime):
    """Helper to persist chat turns sequentially to avoid foreign key violations."""
    import asyncio
    from app.services.storage import ensure_session_exists, save_chat_message
    try:
        await asyncio.to_thread(ensure_session_exists, session_id, session_title)
        await asyncio.to_thread(save_chat_message, session_id, user_msg_id, "user", user_content, [], user_time)
        await asyncio.to_thread(save_chat_message, session_id, ai_msg_id, "assistant", ai_content, ai_context, ai_time)
    except Exception as e:
        logger.error("Failed to persist chat turn sequentially for session %s: %s", session_id, e)


async def _persist_completed_turn(request: ChatRequest, session_id: str, user_content: str, ai_content: str, ai_context: list):
    """Persist a finished turn before the client treats it as complete."""
    if CHAT_STORAGE_MODE != "postgres" or session_id == "unknown":
        return

    import uuid as _uuid

    user_msg_id = request.messageId or str(_uuid.uuid4())
    ai_msg_id = str(_uuid.uuid4())
    user_time = datetime.utcnow()
    ai_time = user_time + timedelta(milliseconds=10)
    await _persist_turn(
        session_id=session_id,
        session_title=request.sessionTitle or "Cuoc tro chuyen moi",
        user_msg_id=user_msg_id,
        user_content=user_content,
        ai_msg_id=ai_msg_id,
        ai_content=ai_content,
        ai_context=ai_context,
        user_time=user_time,
        ai_time=ai_time,
    )


def _new_timing(http_request: Request, endpoint: str, streaming: bool) -> PipelineTimingCollector:
    return PipelineTimingCollector(
        request_id=sanitize_request_id(http_request.headers.get("x-request-id")),
        endpoint=endpoint,
        streaming=streaming,
        enabled=PIPELINE_TIMING_ENABLED,
    )


@router.post("/chat")
async def chat_endpoint(request: ChatRequest, http_request: Request):
    """Endpoint non-streaming: nhan cau hoi -> truy xuat -> goi LLM -> tra JSON."""
    timing = _new_timing(http_request, "/chat", streaming=False)
    timing_token = set_current_timing(timing if PIPELINE_TIMING_ENABLED else None)
    outcome = "success"
    try:
        last_message = request.messages[-1].content

        last_message = request.messages[-1].content
        session_id = request.sessionId

        from app.services.storage import get_session_summary
        from app.services.memory_manager import summarize_session

        session_data = (
            get_session_summary(session_id)
            if CHAT_STORAGE_MODE == "postgres" and request.enableMemory and session_id != "unknown"
            else None
        )
        summary = session_data.get("summary", "") if session_data else ""

        history_lines = []
        if summary:
            history_lines.append(f"=== BỐI CẢNH TRƯỚC ĐÓ ===\n{summary}\n\n=== HỘI THOẠI GẦN NHẤT ===")
            
        for msg in _recent_messages(request): # Keep the last four messages.
            role_name = "USER" if msg.role == "user" else "AI"
            history_lines.append(f"{role_name}: {msg.content}")
            
        chat_history_str = "\n".join(history_lines) if history_lines else "(Khong co lich su tro chuyen)"

        pipeline = get_pipeline()
        
        from app.services.pipeline import _get_embedding
        
        # Short sliding-window history for the rewriter: two turns, four messages.
        recent_history_lines = []
        for msg in _recent_messages(request): # Keep up to four recent messages.
            role_name = "USER" if msg.role == "user" else "AI"
            recent_history_lines.append(f"{role_name}: {msg.content}")
        recent_history_str = "\n".join(recent_history_lines) if request.useHistoryForRewriter else ""
        
        # Run the rewriter first so retrieval uses the rewritten query.
        if request.enableQueryRewriter:
            domain, queries = await asyncio.to_thread(
                _rewrite_query,
                pipeline.rewriter,
                last_message,
                recent_history_str,
                request.inference_config,
            )
        else:
            domain, queries = "legal", [last_message]
        if domain != "chitchat":
            queries = (queries or [last_message])[:request.maxSubqueries]
        logger.info("Rewriter enabled=%s, domain=%s, queries=%s", request.enableQueryRewriter, domain, queries)
        
        hf_api_key = request.inference_config.api_key_for("huggingface") if request.inference_config else None
        from app.config import HUGGINGFACE_EMBEDDING_MODE
        embedding_api_key = hf_api_key if HUGGINGFACE_EMBEDDING_MODE == "api" else None
        reranker_api_key = embedding_api_key if request.enableReranker else None
        
        try:
            query_vector = None
            if request.enableSemanticCache and domain != "chitchat":
                rewritten_query = queries[0] if queries else last_message
                embedding = _get_embedding(embedding_api_key)
                if embedding:
                    try:
                        # Embed the rewritten query before checking semantic cache.
                        query_vector = await asyncio.to_thread(embedding.embed_query, rewritten_query)
                        
                        # Check semantic cache.
                        from app.services.semantic_cache import check_cache
                        cached_response = await asyncio.to_thread(check_cache, query_vector, request.cacheThreshold)
                        if cached_response:
                            logger.info("Phản hồi được lấy từ Semantic Cache.")
                            cached_text = cached_response.get("response_text", "")
                            cached_context = cached_response.get("context_used", [])
                            await _persist_completed_turn(
                                request,
                                session_id,
                                last_message,
                                cached_text,
                                cached_context,
                            )
                            return {
                                "text": cached_text,
                                "contextUsed": cached_context
                            }
                    except EmbeddingServiceError as e:
                        logger.warning("Cache embedding failed: %s", e)
                        raise
                    except Exception as e:
                        logger.warning("Cache check failed: %s", e)
                        if "401" in str(e) or "Unauthorized" in str(e) or "Invalid token" in str(e):
                            raise ValueError("API Key HuggingFace không hợp lệ hoặc đã hết hạn.")

            retrieved_docs, context_text = await pipeline.aretrieve(
                query=last_message,
                k=request.candidateK,
                category=request.category,
                rerank_top_k=request.topK,
                domain=domain,
                queries=queries,
                enable_reranker=request.enableReranker,
                context_token_budget=request.contextTokenBudget,
                embedding_api_key=embedding_api_key,
                reranker_api_key=reranker_api_key,
            )
        except EmbeddingServiceError as e:
            raise HTTPException(status_code=_embedding_error_status(e), detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e) or "Invalid token" in str(e):
                raise HTTPException(status_code=401, detail="API Key HuggingFace không hợp lệ hoặc đã hết hạn.")
            raise

        with timing.stage("context_building"):
            frontend_context = pipeline.format_for_frontend(retrieved_docs)

        logger.info("Đã chuẩn bị %d ký tự context (từ %d tài liệu) cho LLM", len(context_text), len(retrieved_docs))
        logger.debug("CONTEXT TEXT:\n%s", context_text)

        try:
            llm = get_llm(
                model_name=request.model, 
                temperature=request.temperature, 
                max_tokens=request.maxTokens,
                timeout=request.llmTimeout,
                runtime_config=request.inference_config,
                role="answer",
            )
            rag_chain = CHAT_PROMPT | llm | get_output_parser()

            with timing.stage("llm_generation"):
                output_text = await rag_chain.ainvoke({
                    "context": context_text,
                    "chat_history_str": chat_history_str,
                    "question": last_message
                })
        except Exception as llm_exc:
            logger.error("All LLM providers failed: %s", llm_exc)
            outcome = "error"
            raise HTTPException(status_code=503, detail=_llm_error_detail(request.model, llm_exc))

        logger.info("LLM response generated")

        output_text = _clean_chunk(output_text)
        validation = validate_generated_citations(output_text, frontend_context)
        if validation.invalid_citation_ids or validation.fallback_used:
            logger.warning(
                "Answer citation validation adjusted output: invalid=%s fallback=%s",
                list(validation.invalid_citation_ids),
                validation.fallback_used,
            )
        output_text = validation.text

        frontend_context = _filter_cited_context(
            output_text, frontend_context, request.maxCitations
        )

        if query_vector and domain != "chitchat" and "Hiện tại hệ thống chưa thể gọi mô hình" not in output_text:
            try:
                from app.services.semantic_cache import update_cache
                await asyncio.to_thread(
                    update_cache,
                    query_vector=query_vector,
                    original_query=last_message,
                    response_text=output_text,
                    context_used=frontend_context,
                    retrieved_doc_ids=[doc.metadata.get("id") for doc in retrieved_docs if doc.metadata.get("id")]
                )
            except Exception as e:
                logger.warning("Failed to update cache: %s", e)


        # Persist before returning so a refresh sees the complete turn in PostgreSQL.
        await _persist_completed_turn(
            request,
            session_id,
            last_message,
            output_text,
            frontend_context,
        )

        # Summarize memory asynchronously
        if CHAT_STORAGE_MODE == "postgres" and request.enableMemory and session_id != "unknown":
            asyncio.create_task(summarize_session(
                session_id,
                last_message,
                output_text,
                runtime_config=request.inference_config,
            ))

        return {
            "text": output_text,
            "contextUsed": frontend_context
        }

    except HTTPException:
        outcome = "error"
        raise
    except Exception as e:
        outcome = "error"
        logger.error("Loi xu ly chat: %s", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        timing.emit_once(outcome)
        reset_current_timing(timing_token)


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest, http_request: Request):
    """Endpoint streaming: tra token theo tung chunk qua Server-Sent Events."""
    timing = _new_timing(http_request, "/chat/stream", streaming=True)

    async def event_generator() -> AsyncGenerator[str, None]:
        timing_token = set_current_timing(timing if PIPELINE_TIMING_ENABLED else None)
        outcome = "success"
        try:
            last_message = request.messages[-1].content

            last_message = request.messages[-1].content
            session_id = request.sessionId
            
            from app.services.storage import get_session_summary
            from app.services.memory_manager import summarize_session

            session_data = (
                get_session_summary(session_id)
                if CHAT_STORAGE_MODE == "postgres" and request.enableMemory and session_id != "unknown"
                else None
            )
            summary = session_data.get("summary", "") if session_data else ""

            history_lines = []
            if summary:
                history_lines.append(f"=== BỐI CẢNH TRƯỚC ĐÓ ===\n{summary}\n\n=== HỘI THOẠI GẦN NHẤT ===")
                
            for msg in _recent_messages(request):
                role_name = "USER" if msg.role == "user" else "AI"
                history_lines.append(f"{role_name}: {msg.content}")
                
            chat_history_str = (
                "\n".join(history_lines) if history_lines
                else "(Khong co lich su tro chuyen)"
            )

            pipeline = get_pipeline()
            
            from app.services.pipeline import _get_embedding
            
            recent_history_lines = []
            for msg in _recent_messages(request):
                role_name = "USER" if msg.role == "user" else "AI"
                recent_history_lines.append(f"{role_name}: {msg.content}")
            recent_history_str = "\n".join(recent_history_lines) if request.useHistoryForRewriter else ""
            
            if request.enableQueryRewriter:
                domain, queries = await asyncio.to_thread(
                    _rewrite_query,
                    pipeline.rewriter,
                    last_message,
                    recent_history_str,
                    request.inference_config,
                )
            else:
                domain, queries = "legal", [last_message]
            if domain != "chitchat":
                queries = (queries or [last_message])[:request.maxSubqueries]
            logger.info("Stream rewriter enabled=%s, domain=%s, queries=%s", request.enableQueryRewriter, domain, queries)
            
            hf_api_key = request.inference_config.api_key_for("huggingface") if request.inference_config else None
            from app.config import HUGGINGFACE_EMBEDDING_MODE
            embedding_api_key = hf_api_key if HUGGINGFACE_EMBEDDING_MODE == "api" else None
            reranker_api_key = embedding_api_key if request.enableReranker else None
            
            try:
                query_vector = None
                if request.enableSemanticCache and domain != "chitchat":
                    rewritten_query = queries[0] if queries else last_message
                    embedding = _get_embedding(embedding_api_key)
                    if embedding:
                        try:
                            query_vector = await asyncio.to_thread(embedding.embed_query, rewritten_query)
                            from app.services.semantic_cache import check_cache
                            cached_response = await asyncio.to_thread(check_cache, query_vector, request.cacheThreshold)
                            if cached_response:
                                logger.info("Stream: Phản hồi được lấy từ Semantic Cache.")
                                frontend_context = cached_response.get("context_used", [])
                                yield _sse({"type": "context", "data": frontend_context})
                                
                                cached_text = cached_response.get("response_text", "")
                                words = cached_text.split(" ")
                                for i, word in enumerate(words):
                                    yield _sse({"type": "token", "text": word + (" " if i < len(words) - 1 else "")})
                                    await asyncio.sleep(0.01)
                                    
                                await _persist_completed_turn(
                                    request,
                                    session_id,
                                    last_message,
                                    cached_text,
                                    frontend_context,
                                )
                                yield _sse({"type": "done"})
                                
                                return
                        except EmbeddingServiceError as e:
                            logger.warning("Stream cache embedding failed: %s", e)
                            raise
                        except Exception as e:
                            logger.warning("Stream Cache check failed: %s", e)
                            if "401" in str(e) or "Unauthorized" in str(e) or "Invalid token" in str(e):
                                raise ValueError("API Key HuggingFace không hợp lệ hoặc đã hết hạn.")

                retrieved_docs, context_text = await pipeline.aretrieve(
                    query=last_message,
                    k=request.candidateK,
                    category=request.category,
                    rerank_top_k=request.topK,
                    domain=domain,
                    queries=queries,
                    enable_reranker=request.enableReranker,
                    context_token_budget=request.contextTokenBudget,
                    embedding_api_key=embedding_api_key,
                    reranker_api_key=reranker_api_key,
                )
            except EmbeddingServiceError as e:
                outcome = "error"
                yield _sse({"type": "error", "message": str(e)})
                return
            except ValueError as e:
                outcome = "error"
                yield _sse({"type": "error", "message": str(e)})
                return
            except Exception as e:
                if "401" in str(e) or "Unauthorized" in str(e) or "Invalid token" in str(e):
                    outcome = "error"
                    yield _sse({"type": "error", "message": "API Key HuggingFace không hợp lệ hoặc đã hết hạn."})
                    return
                raise
            with timing.stage("context_building"):
                frontend_context = pipeline.format_for_frontend(retrieved_docs)

            yield _sse({"type": "context", "data": frontend_context})

            llm = get_llm(
                model_name=request.model, 
                temperature=request.temperature, 
                max_tokens=request.maxTokens,
                timeout=request.llmTimeout,
                runtime_config=request.inference_config,
                role="answer",
            )
            rag_chain = CHAT_PROMPT | llm | get_output_parser()

            accumulated_text = ""
            llm_start_ns = time.perf_counter_ns()
            first_token_seen = False
            with timing.stage("llm_generation"):
                async for chunk in rag_chain.astream({
                    "context": context_text,
                    "chat_history_str": chat_history_str,
                    "question": last_message,
                }):
                    if chunk:
                        cleaned = _clean_chunk(chunk)
                        if cleaned:
                            if not first_token_seen:
                                first_token_seen = True
                                timing.add_duration(
                                    "llm_time_to_first_token",
                                    (time.perf_counter_ns() - llm_start_ns) / 1_000_000,
                                )
                                timing.mark_first_token()
                            accumulated_text += cleaned
                            yield _sse({"type": "token", "text": cleaned})

            frontend_context = _filter_cited_context(
                accumulated_text, frontend_context, request.maxCitations
            )
            validation = validate_generated_citations(accumulated_text, frontend_context)
            if validation.invalid_citation_ids or validation.fallback_used:
                logger.warning(
                    "Stream answer citation validation adjusted output: invalid=%s fallback=%s",
                    list(validation.invalid_citation_ids),
                    validation.fallback_used,
                )
            accumulated_text = validation.text
            frontend_context = _filter_cited_context(
                accumulated_text, frontend_context, request.maxCitations
            )
            yield _sse({"type": "context", "data": frontend_context})
            if query_vector and domain != "chitchat" and "Hiện tại hệ thống chưa thể gọi mô hình" not in accumulated_text:
                try:
                    from app.services.semantic_cache import update_cache
                    await asyncio.to_thread(
                        update_cache,
                        query_vector=query_vector,
                        original_query=last_message,
                        response_text=accumulated_text,
                        context_used=frontend_context,
                        retrieved_doc_ids=[doc.metadata.get("id") for doc in retrieved_docs if doc.metadata.get("id")]
                    )
                except Exception as e:
                    logger.warning("Stream Failed to update cache: %s", e)



            # Persist before signalling done so refresh sees the complete turn.
            await _persist_completed_turn(
                request,
                session_id,
                last_message,
                accumulated_text,
                frontend_context,
            )

            # Summarize memory asynchronously
            if CHAT_STORAGE_MODE == "postgres" and request.enableMemory and session_id != "unknown":
                asyncio.create_task(summarize_session(
                    session_id,
                    last_message,
                    accumulated_text,
                    runtime_config=request.inference_config,
                ))

            yield _sse({"type": "done"})

        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except Exception as e:
            outcome = "error"
            logger.error("Loi streaming chat: %s", str(e))
            traceback.print_exc()
            yield _sse({"type": "error", "message": _llm_error_detail(request.model, e)})
        finally:
            timing.emit_once(outcome)
            reset_current_timing(timing_token)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions")
async def get_sessions():
    """Return all persisted chat sessions."""
    if CHAT_STORAGE_MODE == "browser":
        return {"storageMode": "browser", "sessions": []}
    from app.services.storage import list_sessions
    return list_sessions()


@router.get("/chat/session/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Return all persisted messages for one session."""
    if CHAT_STORAGE_MODE == "browser":
        return {"storageMode": "browser", "messages": []}
    from app.services.storage import get_session_messages
    return get_session_messages(session_id)


@router.delete("/chat/session/{session_id}")
async def delete_session(session_id: str):
    """Delete one persisted chat session."""
    if not session_id or session_id == "unknown":
        raise HTTPException(status_code=400, detail="Invalid session_id")
    if CHAT_STORAGE_MODE == "browser":
        return {"status": "skipped", "storageMode": "browser"}
    if not session_id or session_id == "unknown":
        raise HTTPException(status_code=400, detail="Invalid session_id")
    
    try:
        import asyncio
        from app.services.storage import delete_session_summary
        
        await asyncio.to_thread(delete_session_summary, session_id)
        
        return {"status": "success", "message": f"Session {session_id} deleted."}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")
