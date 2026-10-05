FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    TOKEN_FILE=data/tokens.json

WORKDIR /app

# 先装依赖，利用缓存
COPY pyproject.toml README.md LICENSE ./
COPY guangyaclient ./guangyaclient
RUN pip install --upgrade pip && pip install ".[api]"

# 再拷贝 API 源码
COPY api ./api

RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else 1)"

CMD ["python", "-m", "api.main"]
