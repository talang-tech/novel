#!/usr/bin/env python3
"""位移链压缩 —— 机械删除零信息的移动描写。

只处理**明确安全**的模式：一句话里连续 3 个以上位移动作，
且中间没有任何信息（无对话、无数字、无技术名词）。

用法：
    python3 scripts/compress_moves.py --dry-run      # 只看会改什么
    python3 scripts/compress_moves.py --apply        # 真的改

保守原则：宁可漏改，不可改错。改完必须人工过一遍 diff。
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

CHAPTERS = Path(__file__).resolve().parent.parent / "chapters"

# 精确匹配的冗余位移链 → 替换文本
# 每条都是在全书里实际出现、且删掉不损失任何信息的
RULES: list[tuple[str, str]] = [
    # 电梯全流程：读者不需要知道电梯怎么运行的
    (
        r"他走到电梯口，等电梯，电梯来了，门打开，里面没有人。"
        r"他走进去，按了(一楼|[一二三四五六七八九十]+楼)，"
        r"电梯(往下走|往上走|开始往下|开始往上)",
        r"电梯里没有人。",
    ),
    # 起立→走→接水→站着 四连
    (
        r"他站起来，走到茶水间，接了一杯热水，在窗边站了一会儿。",
        r"他在茶水间窗边站了一会儿，手里一杯热水。",
    ),
    # 停下→起立→走 三连（写作场景）
    (
        r"停下来，站起来，走到茶水间，接了一杯热水，在窗边站了一会儿。",
        r"停下来，去茶水间接了一杯热水，在窗边站了一会儿。",
    ),
    # 起立→走→回工位→坐下 四连
    (
        r"他站起来，走出会议室，走回工位。他坐下来，",
        r"回到工位，他",
    ),
    # 收拾→关电脑→走出→走到电梯
    (
        r"他收拾东西，关掉电脑，走出办公室。他走到电梯口，",
        r"他关掉电脑，收拾东西。电梯口，",
    ),
    # 起立→走到走廊→进小会议室→关门→坐下→拿手机 六连
    (
        r"陈稳站起来，走到走廊尽头，有一间小会议室，门开着，里面没有人。"
        r"他走进去，关上门，坐在会议桌旁，拿出手机，",
        r"走廊尽头那间小会议室门开着，里面没有人。陈稳进去关上门，",
    ),
    # 散会的通用四连
    (
        r"会议室里的人开始站起来，收拾东西，往外走。"
        r"陈稳站起来，把手机装进口袋，往外走。他走到门口的时候，",
        r"会议室里的人开始收拾东西往外走。陈稳把手机装进口袋，走到门口的时候，",
    ),
    # 拔电脑→走回座位→坐下
    (
        r"他拔掉电脑，走回座位，坐下来。",
        r"他拔掉电脑，回到座位。",
    ),
    # 起立→走到窗边→拉窗帘
    (
        r"他站起来，走到窗边，拉开窗帘。",
        r"他拉开窗帘。",
    ),
]


def process(text: str) -> tuple[str, list[tuple[str, str]]]:
    """返回 (新文本, [(原文片段, 新文本片段)])。"""
    changes: list[tuple[str, str]] = []
    for pat, repl in RULES:
        for m in re.finditer(pat, text):
            old = m.group(0)
            new = re.sub(pat, repl, old)
            changes.append((old, new))
        text = re.sub(pat, repl, text)
    return text, changes


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    total = 0
    for f in sorted(CHAPTERS.glob("第*.md")):
        original = f.read_text(encoding="utf-8")
        new, changes = process(original)
        if not changes:
            continue
        total += len(changes)
        print(f"\n{'─' * 56}\n{f.stem}  ({len(changes)} 处)")
        for old, repl in changes:
            print(f"  - {old[:70]}")
            print(f"  + {repl[:70]}")
        if args.apply:
            f.write_text(new, encoding="utf-8")

    print(f"\n{'=' * 56}")
    if args.apply:
        print(f"✓ 已应用 {total} 处压缩")
    else:
        print(f"共 {total} 处可压缩（未改动，加 --apply 生效）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
