#!/usr/bin/env python3
"""空转句形态分析 —— 判断哪些能机械替换，哪些必须人工改写。

只做统计，不改文件。
"""
from __future__ import annotations

import collections
import re
from pathlib import Path

CHAPTERS = Path(__file__).resolve().parent.parent / "chapters"

SILENCE = r"没有说话|没有回答|没有接话|没说什么|没有出声"
MOVE = r"站起来|坐下|走到|走出|走进|走回"


def main() -> None:
    files = sorted(CHAPTERS.glob("第*.md"))

    sil_standalone: collections.Counter[str] = collections.Counter()
    sil_embedded = 0
    move_lines: collections.Counter[str] = collections.Counter()
    per_chapter: dict[str, tuple[int, int]] = {}

    for f in files:
        text = f.read_text(encoding="utf-8")
        s_cnt = m_cnt = 0
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if re.search(SILENCE, line):
                s_cnt += 1
                # 纯空转：整行就是一句「X没有说话。」
                if len(line) <= 14:
                    sil_standalone[line] += 1
                else:
                    sil_embedded += 1
            if re.search(MOVE, line):
                m_cnt += 1
                # 提取连续位移动作的行
                n_moves = len(re.findall(MOVE, line))
                if n_moves >= 3:
                    move_lines[line[:60]] += 1
        per_chapter[f.stem] = (s_cnt, m_cnt)

    total_sil = sum(sil_standalone.values()) + sil_embedded
    print("=" * 60)
    print("空转句形态分析")
    print("=" * 60)
    print(f"\n沉默句总计 {total_sil} 行")
    print(f"  独立成段（≤14字，可机械替换）: {sum(sil_standalone.values())}")
    print(f"  嵌入长句（需人工判断）:        {sil_embedded}")

    print(f"\n最高频独立沉默句 top 15：")
    for s, n in sil_standalone.most_common(15):
        print(f"  {n:>4}  {s}")

    print(f"\n一行含 3+ 位移动作的句子 top 10（最该压缩）：")
    for s, n in move_lines.most_common(10):
        print(f"  {n:>3}  {s}")

    print(f"\n各章 (沉默行, 位移行)：")
    for name, (s, m) in sorted(
        per_chapter.items(), key=lambda kv: -(kv[1][0] + kv[1][1])
    )[:12]:
        print(f"  {name:<22} 沉默 {s:>3}  位移 {m:>3}")


if __name__ == "__main__":
    main()
