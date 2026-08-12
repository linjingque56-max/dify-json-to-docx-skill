# ──────────────────────────────────────────────────────
#  Dockerfile — DOCX Generator Skill
# ──────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY app/ ./app/
COPY skill/ ./skill/
COPY examples/ ./examples/

# 存储目录
RUN mkdir -p /app/generated_files
ENV SKILL_STORAGE_DIR=/app/generated_files

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
