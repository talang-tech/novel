#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《向上兼容》站点构建脚本

作用：把 chapters/ 里的 Markdown 章节，自动生成 MkDocs 需要的 docs/ 目录。

设计原则：
  * chapters/ 是唯一数据源，人（和定时任务）只往那里写
  * docs/ 完全由本脚本生成，不手工编辑，已在 .gitignore 里忽略
  * 新增章节后无需修改 mkdocs.yml —— nav 由 SUMMARY.md 自动生成

用法：
  python3 scripts/build_site.py          # 生成 docs/
  python3 scripts/build_site.py --check  # 只校验不写文件（CI 用）
"""

import os
import re
import sys
import json
import shutil
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAPTERS = os.path.join(ROOT, "chapters")
SETTING = os.path.join(ROOT, "setting")
NOTES = os.path.join(ROOT, "notes")
DOCS = os.path.join(ROOT, "docs")

CST = timezone(timedelta(hours=8))

# 卷的划分（章号区间 → 卷名）
VOLUMES = [
    (1, 12, "卷壹 · 老办法"),
    (13, 29, "卷贰 · 翻译"),
    (30, 48, "卷叁 · 代价"),
    (49, 62, "卷肆 · 第三条路"),
]

CN_NUM = "零一二三四五六七八九十"


def cn_number(n: int) -> str:
    """数字转中文，用于章节标题。1→一, 11→十一, 23→二十三"""
    if n <= 10:
        return CN_NUM[n]
    if n < 20:
        return "十" + (CN_NUM[n - 10] if n % 10 else "")
    tens, ones = divmod(n, 10)
    return CN_NUM[tens] + "十" + (CN_NUM[ones] if ones else "")


def volume_of(num: int) -> str:
    for lo, hi, name in VOLUMES:
        if lo <= num <= hi:
            return name
    return "其他"


def count_chars(text: str) -> int:
    """不含空白字符的字数"""
    return len("".join(text.split()))


def count_dialogue(text: str) -> int:
    """对话段数：以引号开头的行"""
    return sum(
        1 for line in text.split("\n")
        if line.strip().startswith(('"', "\u201c"))
    )


def scan_chapters():
    """扫描 chapters/，返回按章号排序的章节信息列表"""
    if not os.path.isdir(CHAPTERS):
        return []
    items = []
    for fn in os.listdir(CHAPTERS):
        if not fn.endswith(".md"):
            continue
        m = re.match(r"^第(\d+)章[-—－](.+)\.md$", fn)
        if not m:
            print(f"  ! 跳过不符合命名规范的文件: {fn}", file=sys.stderr)
            continue
        num = int(m.group(1))
        title = m.group(2).strip()
        path = os.path.join(CHAPTERS, fn)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        items.append({
            "num": num,
            "title": title,
            "src": path,
            "src_name": fn,
            # 输出成纯 ASCII 文件名，URL 干净：/chapters/ch03/
            "slug": f"ch{num:02d}",
            "chars": count_chars(text),
            "dialogue": count_dialogue(text),
            "volume": volume_of(num),
            "text": text,
        })
    items.sort(key=lambda x: x["num"])
    return items


def strip_h1(text: str):
    """移除正文首个 H1（标题由本脚本统一生成），返回 (剩余正文, 原标题)"""
    lines = text.split("\n")
    out, h1, removed = [], None, False
    for line in lines:
        if not removed and line.startswith("# "):
            h1 = line[2:].strip()
            removed = True
            continue
        out.append(line)
    return "\n".join(out).lstrip("\n"), h1


def build(check_only=False):
    chapters = scan_chapters()
    if not chapters:
        print("✗ chapters/ 下没有找到符合规范的章节文件")
        return 1

    total_chars = sum(c["chars"] for c in chapters)
    print(f"→ 找到 {len(chapters)} 章，合计 {total_chars:,} 字")

    # 逐章体检（不阻断构建，只提示）
    warnings = []
    for c in chapters:
        if not (5000 <= c["chars"] <= 6500):
            warnings.append(
                f"第{c['num']:02d}章《{c['title']}》字数 {c['chars']} 不在 5000-6500"
            )
    for w in warnings:
        print(f"  ⚠ {w}")

    if check_only:
        print("✓ --check 模式，未写入文件")
        return 0

    # 重建 docs/
    if os.path.isdir(DOCS):
        shutil.rmtree(DOCS)
    os.makedirs(os.path.join(DOCS, "chapters"), exist_ok=True)
    os.makedirs(os.path.join(DOCS, "about"), exist_ok=True)

    # ---------- 章节页 ----------
    for i, c in enumerate(chapters):
        body, _ = strip_h1(c["text"])
        prev_c = chapters[i - 1] if i > 0 else None
        next_c = chapters[i + 1] if i < len(chapters) - 1 else None

        parts = [
            "---",
            f"title: 第{cn_number(c['num'])}章 · {c['title']}",
            "---",
            "",
            f"# 第{cn_number(c['num'])}章 · {c['title']}",
            "",
            body.rstrip(),
            "",
            "---",
            "",
        ]

        # 章末上下章导航
        nav = []
        if prev_c:
            nav.append(
                f"[← 第{cn_number(prev_c['num'])}章 {prev_c['title']}]"
                f"(../{prev_c['slug']}/)"
            )
        nav.append("[目录](../../)")
        if next_c:
            nav.append(
                f"[第{cn_number(next_c['num'])}章 {next_c['title']} →]"
                f"(../{next_c['slug']}/)"
            )
        parts.append(" · ".join(nav))
        parts.append("")

        dst = os.path.join(DOCS, "chapters", f"{c['slug']}.md")
        with open(dst, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))

    # ---------- 首页 ----------
    latest = chapters[-1]
    idx = [
        "---",
        "title: 向上兼容",
        "hide:",
        "  - navigation",
        "---",
        "",
        "# 向上兼容",
        "",
        "> 一个沉默的后端工程师，被迫学习「向上管理」的故事。",
        "",
        "他做的系统跑着全公司的钱，但没有人知道他的名字。",
        "他写三千字的复盘，领导回他两个字：「收到。」",
        "",
        "这不是一个「三年后我王者归来」的故事。",
        "这是一个普通人在结构性困境里，一寸一寸把自己捞出来的故事。",
        "",
        f"**已更新 {len(chapters)} 章 · {total_chars:,} 字 · 每晚 20:00 更新**",
        "",
        f"[开始阅读](chapters/{chapters[0]['slug']}/){{ .md-button .md-button--primary }} "
        f"[读最新一章](chapters/{latest['slug']}/){{ .md-button }}",
        "",
        "---",
        "",
        "## 目录",
        "",
    ]

    cur_vol = None
    for c in chapters:
        if c["volume"] != cur_vol:
            cur_vol = c["volume"]
            lo = next((l for l, h, n in VOLUMES if n == cur_vol), 0)
            hi = next((h for l, h, n in VOLUMES if n == cur_vol), 0)
            idx += ["", f"### {cur_vol}", "",
                    f"<small>共 {hi - lo + 1} 章</small>", ""]
        idx.append(
            f"- [**第{cn_number(c['num'])}章 · {c['title']}**]"
            f"(chapters/{c['slug']}/)"
            f"<small> — {c['chars']:,} 字</small>"
        )

    # 未写的章节提示
    written = {c["num"] for c in chapters}
    pending = [n for n in range(1, 63) if n not in written]
    if pending:
        idx += [
            "",
            "---",
            "",
            f"<small>后续 {len(pending)} 章待更新，每晚 20:00 自动发布。</small>",
            "",
        ]

    with open(os.path.join(DOCS, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx))

    # ---------- SUMMARY.md：literate-nav 用它生成侧边栏 ----------
    # 注意：列表项之间不能有空行。有空行会被 Markdown 解析为松散列表，
    # 每项包进 <p> 标签，literate-nav 会抛 LiterateNavParseError。
    summary = ["# 目录", "", "- [首页](index.md)"]
    cur_vol = None
    for c in chapters:
        if c["volume"] != cur_vol:
            cur_vol = c["volume"]
            summary.append(f"- {cur_vol}")
        summary.append(
            f"    - [第{cn_number(c['num'])}章 · {c['title']}]"
            f"(chapters/{c['slug']}.md)"
        )
    summary += [
        "- 关于",
        "    - [人物关系](about/characters.md)",
        "    - [写作规约](about/style.md)",
        "    - [更新记录](about/changelog.md)",
    ]
    with open(os.path.join(DOCS, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")

    # ---------- 关于页：从 setting/ 复制（去掉剧透部分） ----------
    def copy_setting(src_name, dst_name, title, cut_at=None):
        src = os.path.join(SETTING, src_name)
        if not os.path.exists(src):
            return
        with open(src, encoding="utf-8") as f:
            t = f.read()
        if cut_at and cut_at in t:
            t = t.split(cut_at)[0]
            t += "\n\n---\n\n*（后续设定涉及剧透，暂不公开）*\n"
        body, _ = strip_h1(t)
        with open(os.path.join(DOCS, "about", dst_name), "w",
                  encoding="utf-8") as f:
            f.write(f"# {title}\n\n{body}")

    copy_setting("01-世界观与人物.md", "characters.md", "人物关系",
                 cut_at="## 结局")
    copy_setting("03-文风基线与写作规约.md", "style.md", "写作规约")

    # ---------- 更新记录 ----------
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    chg = [
        "# 更新记录", "",
        f"最后构建：{now} (UTC+8)", "",
        "| 章 | 标题 | 字数 | 对话段 |",
        "|---|---|---:|---:|",
    ]
    for c in reversed(chapters):
        chg.append(
            f"| {c['num']:02d} | {c['title']} | {c['chars']:,} | {c['dialogue']} |"
        )
    chg += ["", f"**合计 {len(chapters)} 章，{total_chars:,} 字**", ""]
    with open(os.path.join(DOCS, "about", "changelog.md"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(chg))

    # ---------- 静态资源（阅读样式） ----------
    assets_src = os.path.join(ROOT, "docs_assets")
    if os.path.isdir(assets_src):
        assets_dst = os.path.join(DOCS, "assets")
        shutil.copytree(assets_src, assets_dst)
        print(f"  · 已复制 {len(os.listdir(assets_dst))} 个静态资源")

    # ---------- 构建元信息 ----------
    with open(os.path.join(DOCS, "build-info.json"), "w",
              encoding="utf-8") as f:
        json.dump({
            "built_at": now,
            "chapters": len(chapters),
            "total_chars": total_chars,
            "latest": f"第{latest['num']:02d}章 {latest['title']}",
        }, f, ensure_ascii=False, indent=2)

    print(f"✓ docs/ 生成完毕：{len(chapters)} 章页 + 首页 + 3 个关于页")
    return 0


if __name__ == "__main__":
    sys.exit(build(check_only="--check" in sys.argv))
