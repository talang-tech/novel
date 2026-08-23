#!/usr/bin/env python3
"""技术密度分析 —— 找出零编程基础读者会卡住的地方。

区分三类技术内容：
  A 类（保留）：数字、金额、时长、次数 —— 任何人都懂
  B 类（需翻译）：术语、表名、字段名 —— 需要一句话解释或换说法
  C 类（需削减）：代码块、SQL 原文、commit message、日志行 —— 视觉上就吓人

用法：
    python3 scripts/analyze_tech.py            # 全书概览
    python3 scripts/analyze_tech.py --detail 23  # 看某章的具体条目
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

CHAPTERS = Path(__file__).resolve().parent.parent / "chapters"

# ── C 类：视觉上就让人跳过的硬块 ────────────────────────
HARD_BLOCKS = {
    "代码块": r"```[\s\S]*?```",
    "行内代码": r"`[^`\n]{4,}`",
    "SQL语句": r"(?i)\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+\w+",
    "commit": r"(?:commit message|feat:|fix:|chore:|refactor:)",
    "日志行": r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}",
}

# ── B 类：术语，需要翻译或首次出现时解释 ──────────────────
JARGON = [
    "连接池", "索引", "全表扫描", "分区", "归档", "拦截器", "灰度",
    "资源池", "topic", "MR", "review", "合入", "回滚", "事务",
    "视图", "字段", "主键", "哈希", "binlog", "DHCP", "并发",
    "接口", "服务", "模块", "重构", "解耦", "单测", "覆盖率",
    "OKR", "PIP", "P0", "SQL", "IP", "varchar", "decimal",
    "datetime", "timestamp", "int", "root", "localhost",
]

# ── A 类：人人都懂的具体量 ──────────────────────────────
PLAIN_NUMBERS = r"[0-9０-９]+(?:[,，][0-9]{3})*(?:\.[0-9]+)?|[一二三四五六七八九十百千万亿]{2,}"


def analyze(text: str) -> dict:
    body = re.sub(r"^#.*$", "", text, flags=re.M)
    total = len(re.sub(r"\s", "", body))

    hard: dict[str, int] = {}
    hard_chars = 0
    for name, pat in HARD_BLOCKS.items():
        hits = re.findall(pat, body)
        hard[name] = len(hits)
        hard_chars += sum(len(h if isinstance(h, str) else "".join(h)) for h in hits)

    jargon: dict[str, int] = {}
    for w in JARGON:
        c = body.count(w)
        if c:
            jargon[w] = c

    return {
        "总字数": total,
        "硬块": hard,
        "硬块字数": hard_chars,
        "硬块占比": hard_chars / total * 100 if total else 0,
        "术语种类": len(jargon),
        "术语总次数": sum(jargon.values()),
        "术语密度": sum(jargon.values()) / total * 1000 if total else 0,
        "术语明细": jargon,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", type=int, help="查看某一章的术语明细")
    args = ap.parse_args()

    files = sorted(CHAPTERS.glob("第*.md"))

    if args.detail:
        matches = [f for f in files if f"第{args.detail:02d}章" in f.name]
        if not matches:
            print(f"未找到第 {args.detail} 章")
            return 1
        f = matches[0]
        r = analyze(f.read_text(encoding="utf-8"))
        print(f"\n{f.stem}  {r['总字数']:,} 字")
        print(f"硬块占比 {r['硬块占比']:.1f}%（{r['硬块字数']} 字）")
        for k, v in r["硬块"].items():
            if v:
                print(f"  {k}: {v} 处")
        print(f"\n术语 {r['术语种类']} 种 / {r['术语总次数']} 次"
              f"（每千字 {r['术语密度']:.1f} 次）：")
        for w, c in sorted(r["术语明细"].items(), key=lambda kv: -kv[1]):
            print(f"  {c:>3}  {w}")
        return 0

    print("=" * 68)
    print("技术密度分析（面向零编程基础读者的可读性）")
    print("=" * 68)
    print(f"\n{'章节':<22} {'字数':>6} {'硬块%':>6} {'术语/千字':>9} {'代码块':>6}")
    print("─" * 68)

    all_jargon: dict[str, int] = {}
    rows = []
    for f in files:
        r = analyze(f.read_text(encoding="utf-8"))
        rows.append((f.stem, r))
        for w, c in r["术语明细"].items():
            all_jargon[w] = all_jargon.get(w, 0) + c
        print(f"{f.stem:<22} {r['总字数']:>6,} {r['硬块占比']:>5.1f}% "
              f"{r['术语密度']:>8.1f} {r['硬块']['代码块']:>6}")

    print("─" * 68)
    avg_hard = sum(r["硬块占比"] for _, r in rows) / len(rows)
    avg_jar = sum(r["术语密度"] for _, r in rows) / len(rows)
    print(f"{'平均':<22} {'':>6} {avg_hard:>5.1f}% {avg_jar:>8.1f}")

    print(f"\n全书最高频术语 top 25（这些是零基础读者的主要障碍）：")
    for w, c in sorted(all_jargon.items(), key=lambda kv: -kv[1])[:25]:
        print(f"  {c:>4}  {w}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
