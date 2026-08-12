#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
#  start.sh — 一键启动 DOCX Generator Skill 服务
# ────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

# ── 创建 / 激活虚拟环境 ──────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo ">>> 创建虚拟环境 $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# ── 安装依赖 ──────────────────────────────────────────
echo ">>> 安装依赖 ..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r requirements.txt

# ── 环境变量（可通过 export 覆盖） ────────────────────
export SKILL_HOST="${SKILL_HOST:-0.0.0.0}"
export SKILL_PORT="${SKILL_PORT:-8080}"
export SKILL_PUBLIC_BASE_URL="${SKILL_PUBLIC_BASE_URL:-http://localhost:8080}"
export SKILL_API_KEY="${SKILL_API_KEY:-}"

echo ">>> 启动服务: http://${SKILL_HOST}:${SKILL_PORT}"
echo ">>> 健康检查: http://${SKILL_HOST}:${SKILL_PORT}/v1/health"
echo ">>> 按 Ctrl+C 停止"

# ── 启动 ──────────────────────────────────────────────
exec "$VENV_DIR/bin/uvicorn" app.main:app \
    --host "$SKILL_HOST" \
    --port "$SKILL_PORT" \
    --reload
