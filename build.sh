#!/usr/bin/env bash
# Cloudflare Pages 构建入口
#
# ⚠ CF Pages 项目设置里必须填：
#   Build command          : bash build.sh
#   Build output directory : site
#   环境变量 PYTHON_VERSION : 3.11
#
# 如果 Build command 填成了 "mkdocs build"，构建会失败并报
# "Config value 'docs_dir': The path .../docs isn't an existing directory"
# —— 因为 docs/ 是由 scripts/build_site.py 生成的，不在 git 里。
#
# 本地也可直接跑：bash build.sh

set -euo pipefail

echo "=========================================="
echo " 《向上兼容》站点构建"
echo "=========================================="
echo "Python : $(python3 --version 2>&1)"
echo "工作目录: $(pwd)"
echo

echo "--- 1/4 安装依赖 ---"
pip install --quiet --no-cache-dir -r requirements.txt
echo "✓ 依赖就绪（mkdocs $(mkdocs --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)）"
echo

echo "--- 2/4 从 chapters/ 生成 docs/ ---"
python3 scripts/build_site.py
echo

echo "--- 3/4 校验生成结果 ---"
# 显式检查，避免 mkdocs 抛出难懂的 docs_dir 报错
if [ ! -d docs ]; then
  echo "✗ docs/ 未生成 —— scripts/build_site.py 执行异常" >&2
  exit 1
fi
if [ ! -f docs/index.md ]; then
  echo "✗ docs/index.md 缺失" >&2
  exit 1
fi
if [ ! -f docs/SUMMARY.md ]; then
  echo "✗ docs/SUMMARY.md 缺失，侧边栏将为空" >&2
  exit 1
fi
CH_COUNT=$(find docs/chapters -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
if [ "$CH_COUNT" -eq 0 ]; then
  echo "✗ docs/chapters/ 下没有章节页" >&2
  exit 1
fi
echo "✓ docs/ 校验通过：${CH_COUNT} 个章节页 + 首页 + 侧边栏"
echo

echo "--- 4/4 MkDocs 构建 ---"
mkdocs build --strict
echo

echo "=========================================="
echo " ✓ 构建完成"
echo "=========================================="
echo "输出目录 site/ ($(du -sh site 2>/dev/null | cut -f1))"
echo "首页       : $([ -f site/index.html ] && echo '✓' || echo '✗')"
echo "章节页     : $(find site/chapters -name 'index.html' 2>/dev/null | wc -l | tr -d ' ') 个"
echo "搜索索引   : $([ -f site/search/search_index.json ] && echo '✓' || echo '✗')"
echo "阅读样式   : $([ -f site/assets/reading.css ] && echo '✓' || echo '✗')"
