# Dify 集成指南

> 手把手将 dify-json-to-docx-skill 接入 Dify Workflow，从部署到调用的完整流程。

---

## 前置条件

在开始集成之前，请确认以下条件已满足：

- Dify 实例已部署并可访问（自建或 Dify Cloud）
- 拥有 Dify 工作区的管理员或开发者权限（可创建自定义工具和 Workflow）
- DOCX Generator Skill 服务已部署并可通过 HTTP 访问
- 准备好 DOCX 模板文件（已按 [模板变量规范](../examples/template_variables_spec.md) 标记占位符）

---

## 1. 导入 Skill

### 1.1 部署 Skill 服务

首先需要将 Skill 的后端服务部署到可被 Dify 访问的服务器。以 Docker 部署为例：

```bash
# 构建镜像
docker build -t dify-json-to-docx-skill .

# 启动容器（映射端口、设置环境变量）
docker run -d \
  --name docx-skill \
  -p 8080:8080 \
  -e API_KEY=your-secret-api-key \
  -e FILE_TTL_HOURS=24 \
  -e STORAGE_BACKEND=local \
  -e STORAGE_PATH=/app/files \
  -v /data/docx-files:/app/files \
  dify-json-to-docx-skill
```

部署完成后，验证服务是否正常运行：

```bash
curl http://your-host:8080/v1/health
# 期望返回: {"status":"ok","version":"1.0.0","timestamp":"..."}
```

记下服务的访问地址（如 `https://skill.your-company.com/v1`），后续在 Dify 中配置时需要使用。

### 1.2 在 Dify 中创建自定义工具

1. 登录 Dify 控制台，进入目标工作区。
2. 在左侧导航栏选择 **工具** → **自定义**。
3. 点击 **创建自定义工具**。
4. 填写工具基本信息：
   - **工具名称**：`DOCX 文档生成`
   - **工具描述**：`接收 JSON 数据和 DOCX 模板，生成 Word 文件。适用于结算单、合同、报价单等企业文档自动化场景。`
5. 在 **Schema** 文本框中，粘贴 [skill/openapi.yaml](../skill/openapi.yaml) 的完整内容。
6. 将 `servers` 部分的 URL 替换为你的 Skill 服务实际地址：
   ```yaml
   servers:
     - url: https://skill.your-company.com/v1
       description: 生产环境
   ```
7. 如果 Skill 服务启用了 API Key 鉴权，在 **鉴权方式** 中选择 **API Key**，填入你的 API Key。Dify 会自动在每次请求中添加 `Authorization: Bearer <api-key>` Header。
8. 点击 **保存**。

保存后，Dify 会解析 OpenAPI Schema 并自动识别出 `generate_docx` 接口。你可以在工具列表中看到该工具，并查看其参数定义。

### 1.3 测试工具

在工具详情页点击 **测试**，手动验证工具是否可用：

- `data`：粘贴一段测试 JSON（可使用 [examples/settlement_statement.json](../examples/settlement_statement.json) 的内容）
- `title`：输入 `测试文档`
- `template`：上传一个 DOCX 模板文件

点击 **发送** 后，如果返回包含 `file_url` 的 JSON 响应，说明工具配置正确。点击 `file_url` 可下载生成的文件进行验证。

---

## 2. 配置 URL

### 2.1 网络可达性

Dify 需要通过 HTTP 访问 Skill 服务。根据部署方式不同，网络配置有所区别：

**Dify Cloud（SaaS）+ Skill 自建** — Skill 服务必须部署在公网可访问的位置。建议配置 HTTPS（通过 Nginx 反向代理 + Let's Encrypt 证书），并在防火墙中仅放行 Dify 服务器 IP。

**Dify 自建（Docker Compose）+ Skill 同机部署** — 如果 Dify 和 Skill 部署在同一台服务器，使用 Docker 内部网络通信。在 `docker-compose.yml` 中将 Skill 服务加入 Dify 的网络，使用容器名作为主机名（如 `http://docx-skill:8080/v1`）。

**Dify 自建 + Skill 跨机部署** — 确保两台服务器内网互通。使用内网 IP 访问，如 `http://10.0.1.50:8080/v1`。

### 2.2 OpenAPI Schema 中的 URL 配置

OpenAPI Schema 中的 `servers.url` 决定了 Dify 发送请求的目标地址。确保该地址：

- 以 `/v1` 结尾（API 版本前缀）
- 使用正确的协议（HTTP / HTTPS）
- 端口号正确
- 可被 Dify 服务器访问（而非仅本地可访问）

如果 Skill 服务部署后地址发生变化，只需在 Dify 工具配置中更新 Schema 中的 `servers.url` 并保存，无需重新创建工具。

### 2.3 鉴权配置

如果 Skill 服务配置了 API Key，在 Dify 工具的鉴权设置中选择 **API Key** 模式，填入密钥。Dify 支持两种 API Key 传递方式：

- **Header（推荐）**：密钥通过 `Authorization: Bearer <key>` Header 传递
- **Query Parameter**：密钥通过 URL 参数 `?api_key=<key>` 传递

本 Skill 的 OpenAPI Schema 默认使用 Header 方式（`ApiKeyAuth` 安全方案）。

---

## 3. 在 Workflow 中调用

### 3.1 创建 Workflow

1. 在 Dify 控制台选择 **工作室** → **创建空白应用** → **工作流**。
2. 填写应用名称（如 `结算单自动生成`）和描述。
3. 进入 Workflow 画布编辑器。

### 3.2 设计 Workflow 节点

一个典型的「JSON → DOCX」Workflow 包含以下节点：

```
[Start] → [LLM/HTTP] → [Code: 数据处理+模板编码] → [Tool: generate_docx] → [Answer] → [End]
```

**Start 节点** — 定义 Workflow 的输入参数。例如，用户输入客户名称和结算月份，或上传业务数据文件和模板文件。

**LLM 节点（可选）** — 如果业务数据需要从非结构化文本中提取，使用 LLM 节点将自然语言转换为结构化 JSON。在 LLM 节点的提示词中指定输出 JSON 格式，确保字段名与 DOCX 模板中的变量名匹配。

**HTTP Request 节点（可选）** — 如果业务数据存储在外部系统（ERP / CRM / 数据库 API），使用 HTTP Request 节点拉取数据。设置请求方法、URL、认证信息，并将响应体映射为 JSON 变量。

**Code 节点（关键）** — 这是绕开 Dify 文件校验的核心节点。承担两个职责：将业务数据序列化为 JSON 字符串，以及将模板文件变量编码为 Base64 字符串。

Dify 的自定义工具框架对 `format: binary` 文件参数有单文件校验限制——当上游节点输出的是文件数组时，直接绑定到 Tool 节点的文件参数会触发 "This parameter only accepts one file but got multiple files" 错误。同时，工作流中动态生成的文件没有现成可访问的 URL。解决方案是在 Code 节点中将文件内容编码为 Base64 字符串，以纯文本形式传递给 Tool 节点。

Code 节点示例（Python）：

```python
import json
import base64

def main(files: list, business_data: dict) -> dict:
    # 1. 将模板文件编码为 Base64 字符串
    template_b64 = ""
    if files and len(files) > 0:
        f = files[0]
        # 方式1：文件对象包含 url 字段，先下载再编码
        url = f.get("url", "")
        if url:
            import urllib.request
            content = urllib.request.urlopen(url).read()
            template_b64 = base64.b64encode(content).decode("utf-8")
        else:
            # 方式2：文件对象包含 content / blob 字段
            content = f.get("content", f.get("blob", b""))
            if isinstance(content, str):
                content = content.encode("utf-8")
            if content:
                template_b64 = base64.b64encode(content).decode("utf-8")

    # 2. 将业务数据序列化为 JSON 字符串
    data_string = json.dumps(business_data, ensure_ascii=False)

    return {
        "template_b64": template_b64,
        "data_string": data_string
    }
```

**Tool 节点（核心）** — 这是调用 Skill 的节点。配置方式如下：

1. 在画布中拖入 **工具** 节点。
2. 在工具选择器中找到 `DOCX 文档生成` → `generate_docx`。
3. 配置参数映射（三个参数均为字符串类型，不涉及文件上传）：
   - `data`：绑定 Code 节点的 `data_string` 输出变量（已序列化的 JSON 字符串）。
   - `title`：可以引用上游变量（如 `{{#start.customer_name}}_结算单`），也可以直接输入固定文本。
   - `template`：绑定 Code 节点的 `template_b64` 输出变量（Base64 编码的模板文件内容）。

**Answer 节点** — 将 Tool 节点的输出格式化为用户可读的消息。例如：

```
您的结算单已生成：

📄 文件名：{{#tool.file_name}}
🔗 下载链接：{{#tool.file_url}}
📊 文件大小：{{#tool.file_size}} 字节
🕐 生成时间：{{#tool.generated_at}}

请在 24 小时内下载，链接将自动失效。
```

**条件分支节点（可选）** — 根据 `success` 字段判断是否生成成功，失败时展示错误信息并支持重试。

### 3.3 调试 Workflow

在 Dify 画布编辑器中点击 **运行**，输入测试数据，逐步检查每个节点的输出。重点关注：

- Code 节点的 `template_b64` 输出是否为非空字符串（Base64 编码内容）
- Code 节点的 `data_string` 输出是否为合法的 JSON 字符串
- Tool 节点的三个参数是否都正确绑定到 Code 节点的输出变量

常见调试问题：

- `template_b64` 为空 → 检查 Code 节点是否能正确访问文件变量的 url 或 content 字段
- `INVALID_TEMPLATE` 错误 → Base64 解码后不是合法的 .docx 文件，检查编码过程是否正确
- `data` 参数传入了对象而非字符串 → 确保 Code 节点执行了 `json.dumps()` 序列化
- 模板变量未匹配 → 检查 JSON 字段名与模板占位符是否完全一致（大小写敏感）

---

## 4. 接收输出文件

### 4.1 直接下载

Tool 节点返回的 `file_url` 是一个可直接访问的 HTTP 链接。在 Answer 节点中将该链接展示给用户，用户点击即可下载 DOCX 文件。这是最简单的接收方式，适用于即时使用的场景。

### 4.2 转存到永久存储

由于 `file_url` 有时效性（默认 24 小时），如果需要长期保存生成的文件，应在 Workflow 中增加转存步骤：

**方案 A：HTTP Request 节点转存到对象存储**

在 Tool 节点之后添加 HTTP Request 节点，调用对象存储的上传 API（如阿里云 OSS / 腾讯云 COS / AWS S3），将 `file_url` 指向的文件上传到永久存储。HTTP 节点先 GET 下载文件，再 PUT 上传到对象存储。

**方案 B：Code 节点 + SDK 转存**

在 Code 节点中使用 Python / JavaScript SDK 下载文件并上传到目标存储。这种方式灵活性更高，可以同时执行文件重命名、目录组织、元数据写入等操作。

**方案 C：Skill 服务直传对象存储**

在 Skill 服务的环境变量中配置对象存储作为存储后端（`STORAGE_BACKEND=oss`），这样生成的文件直接存入永久存储，`file_url` 指向的就是永久可访问的对象存储 URL。

### 4.3 通过消息渠道下发

如果 Workflow 需要将生成的文档发送给用户，可以通过 Dify 的消息节点：

**企微 / 钉钉 / 飞书消息** — 使用对应的消息节点，将 `file_url` 作为消息内容发送。注意部分即时通讯平台对文件下载有大小限制或需要文件转存到平台自身的文件服务。

**邮件** — 使用 SMTP 节点发送邮件，将 `file_url` 作为附件链接或直接下载文件作为附件发送。

### 4.4 在 Agent 应用中使用

除了 Workflow，本 Skill 也可以在 Dify Agent 应用中使用。在 Agent 的工具配置中启用 `DOCX 文档生成` 工具，Agent 会根据用户对话自动判断何时调用工具、如何组装参数。这种方式适合对话式文档生成场景——用户在聊天中说"帮我生成这个月的结算单"，Agent 自动提取参数并调用 Skill。

---

## 5. 完整 Workflow 配置示例

以下是一个结算单自动生成 Workflow 的完整配置示例：

### Start 节点

| 参数 | 类型 | 说明 |
|------|------|------|
| `customer_name` | 文本输入 | 客户名称 |
| `settlement_month` | 文本输入 | 结算月份（如 2026-08） |
| `business_data` | 段落输入 | 业务数据描述（自然语言） |

### LLM 节点：数据提取

**系统提示词**：
```
你是一个数据提取助手。根据用户提供的业务数据描述，提取结构化信息并输出 JSON。

输出格式要求：
{
  "customer": "客户名称",
  "period": "结算周期",
  "items": [
    {"name": "项目名称", "spec": "规格", "unit": "单位", "quantity": 数量, "unit_price": "单价", "amount": "金额"}
  ],
  "subtotal": "小计金额",
  "tax_rate": "税率",
  "tax_amount": "税额",
  "total": "价税合计",
  "remarks": "备注"
}

客户名称：{{#start.customer_name#}}
结算月份：{{#start.settlement_month#}}
业务数据：{{#start.business_data#}}
```

**输出变量**：`extracted_json`（字符串类型）

### Code 节点：JSON 序列化

如果 LLM 输出的是对象，需要序列化为字符串：

```python
import json
def main(extracted_json: dict) -> dict:
    return {"data_string": json.dumps(extracted_json, ensure_ascii=False)}
```

### Tool 节点：generate_docx

| 参数 | 值 |
|------|-----|
| `data` | `{{#code.data_string#}}` |
| `title` | `{{#start.settlement_month#}}_结算单_{{#start.customer_name#}}` |
| `template` | 上传结算单模板.docx |

### Answer 节点

```
✅ 结算单已成功生成！

📄 文件：{{#tool.file_name#}}
🔗 下载：{{#tool.file_url#}}
📊 大小：{{#tool.file_size#}} 字节

💡 提示：下载链接 24 小时内有效，请及时保存。
```

---

## 6. 常见问题

**Q: Tool 节点报错 "data 参数不是合法的 JSON"**

A: 检查传入 `data` 的变量是否为 JSON 字符串。如果上游输出的是 JSON 对象，需要通过 Code 节点执行 `JSON.stringify()` 转换为字符串后再传入。

**Q: 生成的文档中变量没有被替换**

A: 确认模板中的变量名与 JSON 数据中的字段名完全一致（大小写敏感）。打开生成的 DOCX 文件，检查未替换的变量名，与 JSON 数据对比。

**Q: 表格循环不生效**

A: 确保模板中循环行的标记语法正确。`{{#items}}` 和 `{{/items}}` 必须在同一个表格行的不同单元格中，且 JSON 中 `items` 的值必须是数组。

**Q: file_url 无法访问**

A: 检查 Skill 服务的网络是否对 Dify 可达。如果 Skill 部署在内网而 Dify 在云端，需要配置内网穿透或公网访问。如果是文件已过期，检查 `FILE_TTL_HOURS` 配置。

**Q: 如何支持多个模板？**

A: 在 Workflow 中使用条件分支节点，根据业务类型选择不同的模板文件传给 Tool 节点的 `template` 参数。或者在 Dify 中创建多个工具实例，每个绑定不同的默认模板。
