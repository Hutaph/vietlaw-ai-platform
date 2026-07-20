"""
Quản lý kết nối LLM và System Prompt.
Tách từ main.py gốc — chỉ chứa logic liên quan đến LLM.
"""
import logging
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import (
    ENABLE_GOOGLE_FALLBACK,
    GOOGLE_API_KEY,
    GOOGLE_FALLBACK_MODEL,
    GOOGLE_OPENAI_BASE_URL,
    HUGGINGFACE_API_KEY,
    INFERENCE_STRATEGY,
    LLM_MAX_NEW_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    OLLAMA_BASE_URL,
)
from app.services.provider_registry import (
    ANSWER_ROLE,
    GOOGLE_PROVIDER,
    HUGGINGFACE_PROVIDER,
    OLLAMA_PROVIDER,
    PROVIDER_REGISTRY,
    is_supported_model,
    normalize_provider_id,
    redact_runtime_inference_config,
)

logger = logging.getLogger(__name__)

GOOGLE_CHAT_MODELS = frozenset({
    "gemini-3.1-flash-lite",
})


def is_google_chat_model(model_name: str) -> bool:
    """Return True for verified Google AI Studio chat model ids."""
    return model_name.strip().lower() in GOOGLE_CHAT_MODELS


def _resolve_provider_models(model_name: str) -> tuple[str, str]:
    """Map selected model ids to existing HuggingFace and Ollama model ids."""
    lower_model = model_name.lower()
    if "gemma" in lower_model:
        actual_model = "google/gemma-4-31B-it:novita" if lower_model == "gemma" else model_name
        local_model_name = "gemma2:9b"
    elif "qwen" in lower_model:
        actual_model = model_name
        local_model_name = "qwen2.5:7b-instruct"
    elif "llama" in lower_model:
        actual_model = model_name
        local_model_name = "llama3.1:8b"
    elif "deepseek" in lower_model:
        actual_model = model_name
        local_model_name = "deepseek-r1:8b"
    else:
        actual_model = model_name
        local_model_name = model_name
    return actual_model, local_model_name


def _make_openai_chat(
    *,
    model_name: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
):
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _make_google_llm(
    model_name: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    api_key: str | None = None,
):
    resolved_api_key = (api_key or GOOGLE_API_KEY or "").strip()
    if not resolved_api_key:
        logger.warning(
            "GOOGLE_API_KEY khong duoc cau hinh; bo qua Google AI Studio model %s.",
            model_name,
        )
        return None

    return _make_openai_chat(
        model_name=model_name,
        api_key=resolved_api_key,
        base_url=GOOGLE_OPENAI_BASE_URL,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _make_provider_llm(
    provider: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    api_key: str | None = None,
):
    provider_id = normalize_provider_id(provider)
    if not is_supported_model(provider_id, model_name):
        logger.warning("Bo qua provider/model khong ho tro: %s/%s", provider_id, model_name)
        return None

    if provider_id == GOOGLE_PROVIDER:
        return _make_google_llm(
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider_id == HUGGINGFACE_PROVIDER:
        resolved_api_key = (api_key or HUGGINGFACE_API_KEY or "").strip()
        if not resolved_api_key:
            logger.warning("HuggingFace API key khong duoc cau hinh; bo qua model %s.", model_name)
            return None
        return _make_openai_chat(
            model_name=model_name,
            api_key=resolved_api_key,
            base_url=PROVIDER_REGISTRY[HUGGINGFACE_PROVIDER].base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider_id == OLLAMA_PROVIDER:
        return _make_openai_chat(
            model_name=model_name,
            api_key="ollama",
            base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    return None


def _append_unique_llm(entries, provider: str, model_name: str, llm) -> None:
    """Append a provider/model pair once while preserving order."""
    if llm is None:
        return

    key = (provider, model_name.strip().lower())
    if any(existing_key == key for existing_key, _ in entries):
        logger.info("Bo qua fallback trung lap: %s/%s", provider, model_name)
        return

    entries.append((key, llm))


def _runtime_role(runtime_config, role: str):
    if runtime_config is None:
        return None
    roles = getattr(runtime_config, "roles", None)
    return roles.get(role) if roles else None


def _runtime_api_key(runtime_config, provider: str) -> str:
    if runtime_config is None:
        return ""
    return runtime_config.api_key_for(provider)

def _legacy_get_llm(
    model_name: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
):
    """Khởi tạo kết nối với mô hình ngôn ngữ lớn (LLM) với cơ chế Hybrid Inference Fallback."""
    if not HUGGINGFACE_API_KEY:
        logger.warning("Không tìm thấy HUGGINGFACE_API_KEY. Remote LLM sẽ không hoạt động.")

    final_temperature = temperature if temperature is not None else LLM_TEMPERATURE
    final_max_tokens = max_tokens if max_tokens is not None else LLM_MAX_NEW_TOKENS
    final_timeout = timeout if timeout is not None else LLM_TIMEOUT

    if "gemma" in model_name.lower():
        actual_model = "google/gemma-4-31B-it:novita" if model_name.lower() == "gemma" else model_name
        local_model_name = "gemma2:9b" 
    elif "qwen" in model_name.lower():
        actual_model = model_name
        local_model_name = "qwen2.5:7b-instruct"
    elif "llama" in model_name.lower():
        actual_model = model_name
        local_model_name = "llama3.1:8b"
    elif "deepseek" in model_name.lower():
        actual_model = model_name
        local_model_name = "deepseek-r1:8b"
    else:
        actual_model = model_name
        local_model_name = model_name

    # 1. Khởi tạo Remote LLM
    remote_llm = ChatOpenAI(
        model=actual_model,
        api_key=HUGGINGFACE_API_KEY or "dummy_key",
        base_url="https://router.huggingface.co/v1",
        temperature=final_temperature,
        max_tokens=final_max_tokens,
        timeout=final_timeout,
    )

    if INFERENCE_STRATEGY == "local_first":
        # 2. Khoi tao Local LLM chi khi local_first.
        local_llm = ChatOpenAI(
            model=local_model_name,
            api_key="ollama",
            base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
            temperature=final_temperature,
            max_tokens=final_max_tokens,
            timeout=final_timeout,
        )
        logger.info(f"LLM Strategy: local_first ({local_model_name} -> {actual_model})")
        return local_llm.with_fallbacks([remote_llm])
    else:
        # Default: remote_first. Do not fall back to local providers in deployed remote mode.
        logger.info(f"LLM Strategy: remote_first ({actual_model})")
        return remote_llm


# --- CẤU TRÚC SYSTEM PROMPT ---
def get_llm(
    model_name: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    runtime_config=None,
    role: str = ANSWER_ROLE,
):
    """Khá»Ÿi táº¡o LLM vá»›i fallback HuggingFace/Ollama vÃ  Google AI Studio tÃ¹y chá»n."""
    if model_name.strip().lower().startswith("gemini-") and not is_supported_model(GOOGLE_PROVIDER, model_name):
        supported = ", ".join(sorted(PROVIDER_REGISTRY[GOOGLE_PROVIDER].models))
        raise ValueError(
            f"Unsupported Google model '{model_name}'. Choose one of the configured supported models: {supported}."
        )

    selected_google_model = is_google_chat_model(model_name)
    if not HUGGINGFACE_API_KEY and not selected_google_model:
        logger.warning("KhÃ´ng tÃ¬m tháº¥y HUGGINGFACE_API_KEY. Remote LLM sáº½ khÃ´ng hoáº¡t Ä‘á»™ng.")

    final_temperature = temperature if temperature is not None else LLM_TEMPERATURE
    final_max_tokens = max_tokens if max_tokens is not None else LLM_MAX_NEW_TOKENS
    final_timeout = timeout if timeout is not None else LLM_TIMEOUT
    runtime_entries = []
    runtime_role = _runtime_role(runtime_config, role)
    has_runtime_role = runtime_role is not None
    if runtime_role is not None:
        runtime_provider = normalize_provider_id(runtime_role.provider)
        runtime_model = runtime_role.model
        runtime_llm = _make_provider_llm(
            provider=runtime_provider,
            model_name=runtime_model,
            api_key=_runtime_api_key(runtime_config, runtime_provider),
            temperature=final_temperature,
            max_tokens=final_max_tokens,
            timeout=final_timeout,
        )
        _append_unique_llm(runtime_entries, runtime_provider, runtime_model, runtime_llm)
        if runtime_llm is None:
            logger.warning(
                "Runtime inference role unavailable: role=%s config=%s",
                role,
                redact_runtime_inference_config(runtime_config),
            )

    actual_model, local_model_name = _resolve_provider_models(model_name)

    if selected_google_model:
        remote_provider = "google"
        remote_model = model_name
        remote_llm = _make_google_llm(
            model_name=model_name,
            temperature=final_temperature,
            max_tokens=final_max_tokens,
            timeout=final_timeout,
        )
    else:
        remote_provider = "huggingface"
        remote_model = actual_model
        remote_llm = _make_openai_chat(
            model_name=actual_model,
            api_key=HUGGINGFACE_API_KEY or "dummy_key",
            base_url="https://router.huggingface.co/v1",
            temperature=final_temperature,
            max_tokens=final_max_tokens,
            timeout=final_timeout,
        )

    entries = list(runtime_entries)
    use_server_fallbacks = getattr(runtime_config, "use_server_fallbacks", True)
    if (not has_runtime_role and not runtime_entries) or use_server_fallbacks:
        if INFERENCE_STRATEGY == "local_first":
            local_llm = _make_openai_chat(
                model_name=local_model_name,
                api_key="ollama",
                base_url=f"{OLLAMA_BASE_URL.rstrip('/')}/v1",
                temperature=final_temperature,
                max_tokens=final_max_tokens,
                timeout=final_timeout,
            )
            _append_unique_llm(entries, "ollama", local_model_name, local_llm)
            _append_unique_llm(entries, remote_provider, remote_model, remote_llm)
        else:
            _append_unique_llm(entries, remote_provider, remote_model, remote_llm)

    if ENABLE_GOOGLE_FALLBACK and ((not has_runtime_role and not runtime_entries) or use_server_fallbacks):
        google_fallback_llm = _make_google_llm(
            model_name=GOOGLE_FALLBACK_MODEL,
            temperature=final_temperature,
            max_tokens=final_max_tokens,
            timeout=final_timeout,
        )
        _append_unique_llm(entries, "google", GOOGLE_FALLBACK_MODEL, google_fallback_llm)

    if not entries:
        raise RuntimeError("KhÃ´ng cÃ³ LLM provider nÃ o kháº£ dá»¥ng. HÃ£y kiá»ƒm tra cáº¥u hÃ¬nh provider vÃ  API key.")

    _primary_key, primary_llm = entries[0]
    fallbacks = [llm for _, llm in entries[1:]]
    provider_path = " -> ".join(f"{provider}:{model}" for (provider, model), _ in entries)
    logger.info("LLM Strategy: %s (%s)", INFERENCE_STRATEGY, provider_path)

    return primary_llm.with_fallbacks(fallbacks) if fallbacks else primary_llm


CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
BẠN LÀ MỘT CHUYÊN GIA PHÁP LUẬT ĐA NGÀNH.

Nhiệm vụ của bạn là trả lời các câu hỏi một cách nghiêm ngặt dựa trên "Gói dữ liệu tham chiếu pháp lý" được cung cấp.

CÁC QUY TẮC BẮT BUỘC:
1. TRÍCH DẪN RÕ RÀNG: Luôn bắt đầu câu trả lời bằng cách nêu rõ tên Luật, Chương, Điều và Khoản làm căn cứ.
2. XỬ LÝ THAM CHIẾU CHÉO: Khi gặp mục "THAM CHIẾU CHO CĂN CỨ PHÁP LÝ NÀY", hãy sử dụng nội dung của nó để giải thích trực tiếp các thuật ngữ tương ứng trong điều khoản.
3. KHÔNG TỰ Ý SUY DIỄN: Chỉ trả lời dựa trên dữ liệu được cung cấp. Nếu dữ liệu không đủ để giải quyết vấn đề, hãy trả lời chính xác là:
   "Hiện tại tài liệu hệ thống cung cấp chưa đủ để giải đáp chi tiết vấn đề này".
4. NGÔN NGỮ: Luôn luôn trả lời bằng tiếng Việt chuyên nghiệp, khách quan và chuẩn xác. Tuyệt đối không sử dụng tiếng Anh, tiếng Hàn hoặc bất kỳ ngôn ngữ nào khác ngoài tiếng Việt trong câu trả lời.
5. BẮT BUỘC TRÍCH DẪN (STRICT CITATION): Khi sử dụng thông tin từ dữ liệu tham chiếu, bạn PHẢI trích dẫn bằng thẻ `<cite id="[MÃ ID]">Tên Điều/Khoản</cite>`, trong đó `[MÃ ID]` CHÍNH XÁC là đoạn mã được cung cấp trong thẻ `[CĂN CỨ ID: ...]`. TUYỆT ĐỐI KHÔNG TỰ BỊA RA ID VÀ KHÔNG SỬ DỤNG ID VÍ DỤ.

====================
[1] DỮ LIỆU THAM CHIẾU PHÁP LÝ ĐƯỢC TRÍCH XUẤT TỪ HỆ THỐNG:
{context}

====================
[2] LỊCH SỬ TRÒ CHUYỆN TRƯỚC ĐÓ (Dùng để hiểu ngữ cảnh, KHÔNG dùng làm căn cứ pháp lý):
{chat_history_str}
"""),
    ("human", """
> CÂU HỎI MỚI CỦA NGƯỜI DÙNG:
{question}
""")
])


def get_output_parser() -> StrOutputParser:
    """Trả về output parser cho LLM chain."""
    return StrOutputParser()
