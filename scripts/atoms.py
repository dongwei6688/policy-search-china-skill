#!/usr/bin/env python3
"""
policy-search-china 原子操作库 v2.0

18 个纯函数原子操作，每个只做一件事。
所有函数均可独立调用，也可被 chain_runner.py 编排。
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

# ═══════════════════════════════════════════════════════
#  Stage 0: 环境准备
# ═══════════════════════════════════════════════════════

def check_cache_freshness(cache_dir: Path) -> dict:
    """
    0.1 检查缓存新鲜度

    返回: {"latest_date": "2026-07-28", "needs_web_update": bool}
    - needs_web_update: 最新缓存早于今年 → 建议联网更新
    """
    latest = ""
    for jf in cache_dir.glob("*.json"):
        for e in json.loads(jf.read_text()):
            d = e.get("searched_at", "") or e.get("date", "")
            if d > latest:
                latest = d
    try:
        needs = (datetime.strptime(latest[:10], "%Y-%m-%d").year
                 < datetime.now().year) if latest else True
    except ValueError:
        needs = True
    return {"latest_date": latest, "needs_web_update": needs}


# ═══════════════════════════════════════════════════════
#  Stage 1: 搜索与命中
# ═══════════════════════════════════════════════════════

def search_cache_title(
    cache_dir: Path, keyword: str, sources: Optional[list] = None
) -> list[dict]:
    """
    1.1 缓存关键词搜索（标题级）

    在 title + summary + tags 中匹配 keyword。
    sources 不传则搜索所有信源。
    """
    hits = []
    for jf in sorted(cache_dir.glob("*.json")):
        stem = jf.stem
        if sources and stem not in sources:
            continue
        for e in json.loads(jf.read_text()):
            text = e.get("title", "") + " " + e.get("summary", "") + " " \
                   + " ".join(e.get("tags", []))
            if keyword in text:
                e["_source_file"] = stem
                hits.append(e)
    return hits


# 1.2 search_cache_fulltext 已移至 rebuild_policy_html.py
# （需要 extract_paragraphs → 文件 I/O，不属于 atoms 纯数据层）


# Stage 1 附属函数（load_source / extract_paragraphs）已移至 rebuild_policy_html.py
# atoms.py 只保留纯数据操作，不涉及文件 I/O 和外部进程调用


# ═══════════════════════════════════════════════════════
#  Stage 2: 过滤
# ═══════════════════════════════════════════════════════

def filter_date_range(
    entries: list[dict], start: str, end: str
) -> list[dict]:
    """
    2.1 时间范围过滤

    start/end: "2024-01-01" 格式，可只传一端（None 表示不限）。
    """
    def ok(e):
        d = e.get("date", "") or e.get("searched_at", "")
        if not d:
            return True  # 无日期不过滤
        d = d[:10]
        if start and d < start:
            return False
        if end and d > end:
            return False
        return True
    return [e for e in entries if ok(e)]


def filter_issuer(
    entries: list[dict], issuers: list[str]
) -> list[dict]:
    """
    2.2 发文机关过滤

    issuers: ["国家能源局", "国务院"]，子串匹配。
    """
    return [e for e in entries
            if any(iss in e.get("issuer", "") for iss in issuers)]


def filter_doctype(
    entries: list[dict], doctypes: list[str]
) -> list[dict]:
    """
    2.3 文件类型过滤

    doctypes: ["意见", "规划", "通知", "行动方案"]，标题子串匹配。
    """
    return [e for e in entries
            if any(typ in e.get("title", "") for typ in doctypes)]


def intersect_entries(entries_a: list[dict], entries_b: list[dict]) -> list[dict]:
    """2.4 AND 交集 — 两个列表都存在的条目（按 title 匹配）"""
    titles_b = {e.get("title", "") for e in entries_b}
    return [e for e in entries_a if e.get("title", "") in titles_b]


def union_entries(entries_a: list[dict], entries_b: list[dict]) -> list[dict]:
    """2.5 OR 并集 — 两个列表合并去重（按 title 去重）"""
    seen = {}
    for e in entries_a + entries_b:
        t = e.get("title", "")
        if t not in seen:
            seen[t] = e
    return list(seen.values())


def exclude_entries(
    entries: list[dict], exclude_keywords: list[str]
) -> list[dict]:
    """
    2.6 NOT 排除

    从 entries 中移除 title 含 exclude_keywords 的条目。
    """
    return [e for e in entries
            if not any(kw in e.get("title", "") for kw in exclude_keywords)]


# ═══════════════════════════════════════════════════════
#  Stage 3: 提取
# ═══════════════════════════════════════════════════════

def extract_metadata(entry: dict) -> dict:
    """
    3.1 提取元信息

    从缓存条目中提取标准化元数据。
    """
    return {
        "title": entry.get("title", ""),
        "doc_number": entry.get("doc_number", ""),
        "issuer": entry.get("issuer", ""),
        "date": entry.get("date", ""),
        "source_url": entry.get("source_url", ""),
        "format": entry.get("format", ""),
        "local_path": entry.get("local_path", ""),
    }


# 3.2 extract_paragraphs 已实现在 rebuild_policy_html.py 中，此处复用


def extract_chapters(text: str) -> list[tuple[str, str]]:
    """
    3.3 提取章节结构

    返回: [("第X章 标题", "一级"), ...]，层级标注（一级/二级）。
    """
    # 章节
    chapters = re.findall(
        r'(第[一二三四五六七八九十百零]+[篇章节].*?)(?=第[一二三四五六七八九十百零]+[篇章节]|$)', text
    )
    # 条款
    articles = re.findall(r'(第[一二三四五六七八九十百零]+条 .*?)(?=第[一二三四五六七八九十百零]+条|$)', text)
    result = []
    for c in chapters:
        c_clean = c.strip()[:80]
        result.append((c_clean, "一级"))
    for a in articles:
        a_clean = a.strip()[:80]
        result.append((a_clean, "二级"))
    return result


# ═══════════════════════════════════════════════════════
#  Stage 4: 验证
# ═══════════════════════════════════════════════════════

def deduplicate_entries(entries: list[dict]) -> list[dict]:
    """
    4.1 去重

    按 title + doc_number 去重，保留第一个。
    """
    seen = set()
    result = []
    for e in entries:
        key = (e.get("title", ""), e.get("doc_number", ""))
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result


# Stage 4: 验证 — 逐字校验已嵌入 build_html 输出标签（<div class="verify">），不单独作为原子操作。


# ═══════════════════════════════════════════════════════
#  Stage 5: 输出
# ═══════════════════════════════════════════════════════

# 5.1/5.3 build_html 已实现在 rebuild_policy_html.py 中，此处复用


def generate_summary_list(entries: list[dict]) -> str:
    """
    5.2 生成摘要列表

    返回格式化的 Markdown 表格，仅含标题、文号、发文机关、日期。
    """
    lines = ["| # | 标题 | 文号 | 发文机关 | 日期 |",
             "|---|------|------|----------|------|"]
    for i, e in enumerate(entries, 1):
        title = e.get("title", "")[:50]
        dn = e.get("doc_number", "")[:20]
        issuer = e.get("issuer", "")[:30]
        date = e.get("date", "")[:10]
        lines.append(f"| {i} | {title} | {dn} | {issuer} | {date} |")
    return "\n".join(lines)
