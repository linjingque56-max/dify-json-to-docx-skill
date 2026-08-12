"""
模板渲染模块 — 基于 docxtpl (Jinja2 + python-docx)。

支持：
  - 变量替换          {{field}}
  - 嵌套对象访问      {{customer.name}}
  - 表格行循环        {%tr for item in items %} ... {%tr endfor %}
  - 条件渲染          {% if condition %} ... {% endif %}
  - 图片插入          {{ image_field }}  (配合 InlineImage)
"""
import io
import re
import base64
from datetime import datetime
from typing import Any

from docxtpl import DocxTemplate
from docx import Document


class TemplateError(Exception):
    """模板相关错误，带错误码。"""
    def __init__(self, code: str, message: str, details: str = ""):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def decode_template(template_field: str) -> bytes:
    """
    把 template 参数（base64 字符串或 data URI）解码为 DOCX 二进制内容。

    Raises:
        TemplateError: MISSING_FIELD / INVALID_TEMPLATE
    """
    if not template_field or not template_field.strip():
        raise TemplateError("MISSING_FIELD", "template 参数不能为空")

    raw = template_field.strip()

    # 处理 data URI: data:application/...;base64,XXXX
    if raw.startswith("data:"):
        comma_idx = raw.find(",")
        if comma_idx == -1:
            raise TemplateError("INVALID_TEMPLATE", "data URI 格式不正确，缺少逗号分隔符")
        raw = raw[comma_idx + 1:]

    try:
        content = base64.b64decode(raw, validate=False)
    except Exception as e:
        raise TemplateError(
            "INVALID_TEMPLATE",
            "template 不是合法的 Base64 编码",
            str(e),
        )

    if len(content) < 4:
        raise TemplateError("INVALID_TEMPLATE", "解码后内容过小，不像合法的 DOCX 文件")

    # DOCX 本质是 ZIP，magic bytes = PK\x03\x04
    if content[:2] != b"PK":
        raise TemplateError(
            "INVALID_TEMPLATE",
            "解码后内容不是合法的 DOCX 文件（缺少 ZIP 魔术头 PK）",
        )

    return content


def render_docx(template_bytes: bytes, data: dict) -> tuple[bytes, dict]:
    """
    用 data 渲染 DOCX 模板，返回 (渲染后的 bytes, 渲染统计信息)。

    Raises:
        TemplateError: TEMPLATE_RENDER_ERROR
    """
    try:
        tpl = DocxTemplate(io.BytesIO(template_bytes))
    except Exception as e:
        raise TemplateError(
            "INVALID_TEMPLATE",
            "无法解析 DOCX 模板文件，文件可能已损坏",
            str(e),
        )

    # 渲染前收集模板中的变量名，用于统计和报错
    template_vars = _extract_template_variables(tpl)

    try:
        tpl.render(data)
    except Exception as e:
        raise TemplateError(
            "TEMPLATE_RENDER_ERROR",
            f"模板渲染失败: {e}",
            str(e),
        )

    # 渲染后输出
    out_buf = io.BytesIO()
    tpl.save(out_buf)
    out_bytes = out_buf.getvalue()

    # 统计
    summary = {
        "variables_replaced": len(template_vars),
        "table_rows_generated": _count_table_rows(data),
        "conditions_evaluated": 0,
        "images_inserted": 0,
    }

    return out_bytes, summary


def _extract_template_variables(tpl: DocxTemplate) -> set[str]:
    """提取模板中出现的所有 {{变量名}}，用于统计。"""
    vars_found: set[str] = set()
    try:
        # docxtpl 0.16+ 有 undeclared_template_variables
        undeclared = tpl.undeclared_template_variables
        if undeclared:
            vars_found = set(undeclared)
    except Exception:
        pass
    return vars_found


def _count_table_rows(data: dict) -> int:
    """粗略统计：data 中数组类型的值视为表格行数据。"""
    count = 0
    for v in data.values():
        if isinstance(v, list):
            count += len(v)
    return count


def sanitize_filename(title: str) -> str:
    """清理文件名，移除非法字符。"""
    if not title or not title.strip():
        title = "untitled"
    # Windows / 通用非法字符
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title.strip())
    cleaned = cleaned.rstrip(". ")
    if not cleaned:
        cleaned = "untitled"
    # 截断长度
    return cleaned[:200]
