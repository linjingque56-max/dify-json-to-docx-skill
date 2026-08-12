#!/usr/bin/env bash
# ============================================================
# push-to-github.sh
# 一键将 dify-json-to-docx-skill 推送到 GitHub
# ============================================================
#
# 使用方法：
#   1. 获取 GitHub Personal Access Token:
#      访问 https://github.com/settings/tokens
#      点击 "Generate new token (classic)"
#      勾选 repo 权限, 生成后复制 Token
#
#   2. 运行本脚本:
#      GITHUB_TOKEN=ghp_xxxxxxxxxxxx ./push-to-github.sh
#
#   或交互式输入 Token:
#      ./push-to-github.sh
# ============================================================

set -euo pipefail

REPO_NAME="dify-json-to-docx-skill"
REPO_DESC="适用于 Dify 的 DOCX 文档生成 Skill — JSON 数据 + DOCX 模板 → Word 文件"

# 获取 Token
if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "========================================"
  echo "  GitHub Token 未设置"
  echo "========================================"
  echo ""
  echo "请访问以下网址获取 Personal Access Token:"
  echo "  https://github.com/settings/tokens"
  echo ""
  echo "勾选 repo 权限, 生成后粘贴到下方:"
  read -s -p "Token: " GITHUB_TOKEN
  echo ""
fi

if [ -z "$GITHUB_TOKEN" ]; then
  echo "错误: Token 为空, 退出"
  exit 1
fi

echo ""
echo ">>> 正在创建 GitHub 仓库: $REPO_NAME"

# 创建仓库
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST https://api.github.com/user/repos \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -d "{\"name\":\"$REPO_NAME\",\"description\":\"$REPO_DESC\",\"private\":false}")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "201" ]; then
  echo "创建仓库失败 (HTTP $HTTP_CODE):"
  echo "$BODY" | head -20
  exit 1
fi

# 提取 clone URL
CLONE_URL=$(echo "$BODY" | grep -o '"clone_url":"[^"]*"' | head -1 | cut -d'"' -f4)

echo ">>> 仓库创建成功: $CLONE_URL"

# 添加远程并推送
echo ">>> 正在推送到 GitHub..."

# 使用 token 构造认证 URL
AUTH_URL=$(echo "$CLONE_URL" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|")

git remote remove origin 2>/dev/null || true
git remote add origin "$AUTH_URL"
git push -u origin main

# 清理认证信息（安全）
git remote set-url origin "$CLONE_URL"

echo ""
echo "========================================"
echo "  推送完成!"
echo "========================================"
echo ""
echo "  仓库地址: $CLONE_URL"
echo "  仓库已设为 public, 可在 GitHub 设置中修改为 private"
echo ""
