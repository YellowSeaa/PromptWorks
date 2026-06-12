FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 预先复制必要文件，加速 Docker 层缓存
COPY pyproject.toml README.md alembic.ini /app/
COPY frontend/src/version.json /app/frontend/src/version.json
COPY app /app/app
COPY alembic /app/alembic

RUN pip install --upgrade pip && \
    pip install --no-cache-dir .

# 拷贝入口脚本
COPY docker/backend/entrypoint.sh /app/docker/backend/entrypoint.sh
RUN chmod +x /app/docker/backend/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/backend/entrypoint.sh"]
