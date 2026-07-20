FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_INFERENCE_ENDPOINT="https://router.huggingface.co/hf-inference"

COPY requirements.txt ./
COPY requirements-local.txt ./
RUN pip install uv && \
    uv pip install --system --no-cache-dir -r requirements.txt && \
    uv pip install --system --no-cache-dir -r requirements-local.txt && \
    uv pip install --system --no-cache-dir faiss-cpu

RUN echo "bust cache 2"
COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
