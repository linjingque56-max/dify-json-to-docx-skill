"""
配置模块 — 通过环境变量覆盖默认值。
"""
import os
from pathlib import Path

# ── 服务 ──────────────────────────────────────────────
HOST = os.getenv("SKILL_HOST", "0.0.0.0")
PORT = int(os.getenv("SKILL_PORT", "8080"))

# 对外可访问的基础 URL（Dify 下载文件用）。
# 本地开发用 http://localhost:8080；部署到服务器时改成公网域名。
PUBLIC_BASE_URL = os.getenv("SKILL_PUBLIC_BASE_URL", f"http://localhost:{PORT}")

# ── 鉴权 ──────────────────────────────────────────────
# 留空则不校验 API Key
API_KEY = os.getenv("SKILL_API_KEY", "")

# ── 文件存储 ──────────────────────────────────────────
# 生成的 DOCX 文件存放目录
STORAGE_DIR = Path(os.getenv("SKILL_STORAGE_DIR", "./generated_files"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# 文件链接有效期（秒），默认 24 小时
FILE_TTL_SECONDS = int(os.getenv("SKILL_FILE_TTL", str(24 * 3600)))

# ── 大小限制 ──────────────────────────────────────────
MAX_DATA_SIZE = int(os.getenv("SKILL_MAX_DATA_SIZE", str(5 * 1024 * 1024)))        # 5 MB
MAX_TEMPLATE_SIZE = int(os.getenv("SKILL_MAX_TEMPLATE_SIZE", str(15 * 1024 * 1024)))  # 15 MB 原始文件

# ── 模板下载（URL 方式，预留） ────────────────────────
TEMPLATE_DOWNLOAD_TIMEOUT = int(os.getenv("SKILL_TEMPLATE_TIMEOUT", "30"))
