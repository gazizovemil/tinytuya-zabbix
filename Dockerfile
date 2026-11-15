FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/monitor.py /app/monitor.py
ENTRYPOINT ["python", "/app/monitor.py"]
