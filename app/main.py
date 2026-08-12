"""
DOCX Generator Skill — FastAPI 主应用。

端点：
  POST /v1/generate_docx   生成 DOCX 文档
  GET  /v1/health          健康检查
  GET  /files/{filename}   下载生成的文件
"""
import json
import uuid
import shutil
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel, Field

from . import config
from .renderer import decode_template, render_docx, sanitize_filename, TemplateError

# ── 时区 ──────────────────────────────────────────────
CST = timezone(timedelta(hours=8))

# ── FastAPI 实例 ──────────────────────────────────────
app = FastAPI(
    title="DOCX Generator Skill",
    description="适用于 Dify 的 DOCX 文档生成 Skill",
    version="1.0.0",
)

# CORS — Dify 调用时可能涉及跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求 / 响应模型 ───────────────────────────────────
class GenerateRequest(BaseModel):
    data: str = Field(..., description="JSON 格式的结构化数据字符串")
    title: str = Field(..., description="生成文件名称（不含 .docx）")
    template: str = Field(..., description="DOCX 模板文件内容，Base64 编码")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


# ── 工具函数 ──────────────────────────────────────────
def _check_auth(authorization: Optional[str]):
    """如果配置了 API_KEY，校验 Authorization header。"""
    if not config.API_KEY:
        return
    expected = f"Bearer {config.API_KEY}"
    if authorization != expected:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": {"code": "UNAUTHORIZED", "message": "API Key 校验失败"}},
        )


def _error_response(status: int, code: str, message: str, details: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "success": False,
            "error": {"code": code, "message": message, "details": details},
        },
    )


def _now_iso() -> str:
    return datetime.now(CST).isoformat()


# ── 文件清理后台线程 ──────────────────────────────────
def _cleanup_loop():
    """定期清理过期文件。"""
    while True:
        time.sleep(600)  # 每 10 分钟扫一次
        now = time.time()
        for f in config.STORAGE_DIR.glob("*.docx"):
            try:
                if now - f.stat().st_mtime > config.FILE_TTL_SECONDS:
                    f.unlink(missing_ok=True)
            except Exception:
                pass


_daemon = threading.Thread(target=_cleanup_loop, daemon=True)
_daemon.start()


# ──────────────────────────────────────────────────────
#  POST /v1/generate_docx
# ──────────────────────────────────────────────────────
@app.post("/v1/generate_docx")
async def generate_docx(
    req: GenerateRequest,
    authorization: Optional[str] = Header(None),
):
    _check_auth(authorization)

    # 1. 校验 data 参数
    if not req.data or not req.data.strip():
        return _error_response(400, "MISSING_FIELD", "data 参数不能为空")
    try:
        data_obj = json.loads(req.data)
    except json.JSONDecodeError as e:
        return _error_response(400, "INVALID_JSON", "data 参数不是合法的 JSON 格式", str(e))

    if not isinstance(data_obj, dict):
        return _error_response(400, "INVALID_JSON", "data 解析后必须是 JSON 对象（不能是数组或纯值）")

    # 2. 校验 title
    if not req.title or not req.title.strip():
        return _error_response(400, "MISSING_FIELD", "title 参数不能为空")

    # 3. 解码模板
    try:
        template_bytes = decode_template(req.template)
    except TemplateError as e:
        return _error_response(400, e.code, e.message, e.details)

    if len(template_bytes) > config.MAX_TEMPLATE_SIZE:
        return _error_response(
            413, "FILE_TOO_LARGE",
            f"模板文件超过 {config.MAX_TEMPLATE_SIZE // 1024 // 1024} MB 限制",
        )

    # 4. 渲染
    try:
        out_bytes, summary = render_docx(template_bytes, data_obj)
    except TemplateError as e:
        return _error_response(422, e.code, e.message, e.details)
    except Exception as e:
        return _error_response(500, "INTERNAL_ERROR", "文档生成过程中发生内部错误", str(e))

    # 5. 保存文件
    safe_name = sanitize_filename(req.title)
    timestamp = datetime.now(CST).strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{short_id}_{safe_name}.docx"

    file_path = config.STORAGE_DIR / filename
    file_path.write_bytes(out_bytes)

    # 6. 构建下载 URL
    file_url = f"{config.PUBLIC_BASE_URL.rstrip('/')}/files/{filename}"

    return JSONResponse(content={
        "success": True,
        "file_url": file_url,
        "file_name": f"{safe_name}.docx",
        "file_size": len(out_bytes),
        "generated_at": _now_iso(),
        "rendering_summary": summary,
    })


# ──────────────────────────────────────────────────────
#  GET /v1/health
# ──────────────────────────────────────────────────────
@app.get("/v1/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "timestamp": _now_iso()}


# ──────────────────────────────────────────────────────
#  GET /files/{filename}  — 文件下载
# ──────────────────────────────────────────────────────
@app.get("/files/{filename}")
async def download_file(filename: str):
    # 防路径穿越
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="非法文件名")

    file_path = config.STORAGE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ── 根路径 ────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "DOCX Generator Skill",
        "version": "1.0.0",
        "endpoints": {
            "generate": "POST /v1/generate_docx",
            "health": "GET /v1/health",
            "download": "GET /files/{filename}",
        },
    }
