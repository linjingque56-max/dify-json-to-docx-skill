# dify-json-to-docx-skill

> 适用于 [Dify](https://github.com/langgenius/dify) 的 DOCX 文档生成 Skill — 在 Workflow 中将结构化 JSON 数据与 DOCX 模板合并，自动生成 Word 文件。

---

## 项目用途

企业自动化场景中，业务系统或 Dify Agent 经常产出结构化数据（JSON），而最终交付物往往是一份正式的 Word 文档——合同、结算单、报价单、对账单、质检报告等。本 Skill 就是连接「数据」与「文档」的那座桥梁：接收 JSON 数据和 DOCX 模板，完成变量替换、表格填充、条件渲染，输出可直接下载的 `.docx` 文件。

不涉及任何业务系统逻辑，只负责「模板渲染 + 文件生成」，因此可以被任意 Dify Workflow 复用。

---

## 使用场景

**财务结算自动化** — ERP / 业务系统输出结算明细 JSON，Skill 根据结算单模板生成正式 Word 结算单，自动归档或通过邮件 / 企微下发。

**合同批量生成** — CRM 中的客户信息与合同条款参数以 JSON 传入，Skill 渲染合同模板，批量产出签署用 Word 文件。

**质检 / 审计报告** — IoT 或质检系统产出检测数据 JSON，Skill 填充报告模板中的指标表格、结论段落，生成标准化报告。

**报价单 / 方案书** — 销售在 Dify 中配置参数后，Skill 将参数注入报价模板，生成带品牌样式的 Word 报价单。

**任何「JSON → Word」的自动化链路** — 只要你的 Dify Workflow 能产出结构化数据，本 Skill 就能把它变成文档。

---

## 架构概览

```
Dify Agent / Workflow
        |
        | JSON 数据 + 文件名 + DOCX 模板
        v
  +---------------------+
  |  DOCX Generator Skill|
  |  (OpenAPI Endpoint)  |
  +---------------------+
        |
        | 渲染后的 .docx 文件
        v
  Dify 文件输出 / 下载链接
```

详细架构设计见 [docs/architecture.md](docs/architecture.md)。

---

## Dify 接入方式

本 Skill 以 **Dify Custom Tool（自定义 API 工具）** 的形式接入。核心步骤概述如下，完整图文指南见 [docs/dify-integration.md](docs/dify-integration.md)。

1. **部署 Skill 服务** — 将本 Skill 的后端服务部署到可被 Dify 访问的服务器（内网 / 云主机均可），获得一个 `https://your-host/v1` 的 Base URL。
2. **导入 OpenAPI Schema** — 在 Dify 控制台「工具 → 自定义 → 创建自定义工具」中，粘贴 [skill/openapi.yaml](skill/openapi.yaml) 的完整内容。
3. **配置鉴权** — 如果 Skill 服务启用了 API Key 鉴权，在 Dify 工具配置中填入 Authorization Header。
4. **在 Workflow 中调用** — 在 Dify Workflow 画布中添加「Tool」节点，选择 `generate_docx`，将上游节点的 JSON 输出绑定到 `data` 参数，设置 `title` 和 `template`。
5. **接收输出文件** — Tool 节点返回的响应中包含生成的 `.docx` 文件下载 URL，可在下游节点中引用或通过消息节点下发给用户。

---

## 参数说明

### 接口：`generate_docx`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `data` | `string` (JSON) | 是 | JSON 格式的结构化数据，将与 DOCX 模板中的变量进行匹配替换。支持嵌套对象、数组（用于表格行循环填充）。 |
| `title` | `string` | 是 | 生成文件的名称（不含扩展名），例如 `2026年8月结算单-客户A`。最终输出文件为 `2026年8月结算单-客户A.docx`。 |
| `template` | `file` | 是 | DOCX 模板文件。模板中使用 `{{变量名}}` 语法标记占位符，使用 `{{#数组名}}...{{/数组名}}` 标记循环区域。详见 [模板变量规范](examples/template_variables_spec.md)。 |

### 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `file_url` | `string` | 生成的 DOCX 文件下载地址（临时链接，有效期由服务端配置决定）。 |
| `file_name` | `string` | 完整文件名，含 `.docx` 扩展名。 |
| `file_size` | `integer` | 文件大小（字节）。 |
| `generated_at` | `string` | 生成时间（ISO 8601）。 |

---

## 项目结构

```
dify-json-to-docx-skill/
├── README.md                          # 本文件
├── skill/
│   └── openapi.yaml                   # Dify OpenAPI Skill 接口定义
├── docs/
│   ├── architecture.md                # 架构设计文档
│   └── dify-integration.md            # Dify 集成指南
└── examples/
    ├── settlement_statement.json      # 结算单 JSON 数据示例
    └── template_variables_spec.md     # DOCX 模板变量规范
```

---

## 快速开始（开发者）

### 前置条件

- Python 3.10+
- 可选：Docker（推荐容器化部署）

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/<your-org>/dify-json-to-docx-skill.git
cd dify-json-to-docx-skill

# （实现后端服务后）安装依赖
pip install -r requirements.txt

# 启动服务
python app.py  # 默认监听 http://0.0.0.0:8080
```

### Docker 部署

```bash
docker build -t dify-json-to-docx-skill .
docker run -d -p 8080:8080 --name docx-skill dify-json-to-docx-skill
```

> **注意**：本仓库当前提供 Skill 接口定义、架构文档和示例数据。后端服务实现（模板渲染引擎）需基于 [python-docx](https://python-docx.readthedocs.io/) 或 [docxtpl](https://docxtpl.readthedocs.io/) 等库完成，可按团队技术栈灵活实现。

---

## 技术选型建议

本 Skill 的后端实现推荐以下技术栈（非强制）：

- **Web 框架**：FastAPI（原生支持 OpenAPI / 文件上传 / 异步）
- **模板引擎**：[docxtpl](https://github.com/elapouya/python-docx-template)（基于 Jinja2 语法，与 DOCX 模板完美配合）
- **文件存储**：本地临时目录 + 定时清理，或对接 MinIO / OSS
- **容器化**：Docker + Docker Compose

---

## License

MIT License - 可自由用于企业内部项目和商业产品。
