FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_INFERENCE_ENDPOINT="https://router.huggingface.co/hf-inference"

COPY backend/requirements.txt ./
COPY backend/requirements-local.txt ./
RUN pip install uv && \
    uv pip install --system --no-cache-dir -r requirements.txt && \
    uv pip install --system --no-cache-dir -r requirements-local.txt && \
    uv pip install --system --no-cache-dir faiss-cpu

RUN echo "bust cache 2"
COPY backend/ .

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
