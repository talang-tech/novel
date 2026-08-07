#!/usr/bin/env bash
# Cloudflare Pages 构建入口
#
# 在 CF Pages 项目设置里填：
#   Build command        : bash build.sh
#   Build output directory: site
#   Python version       : 3.11（用环境变量 PYTHON_VERSION=3.11）
#
# 本地也可以直接跑：bash build.sh

set -euo pipefail

echo "=== 1/3 安装依赖 ==="
pip install --quiet --no-cache-dir -r requirements.txt

echo "=== 2/3 从 chapters/ 生成 docs/ ==="
python3 scripts/build_site.py

echo "=== 3/3 MkDocs 构建 ==="
mkdocs build --strict

echo
echo "✓ 构建完成，输出目录 site/"
ls -1 site | head -20
