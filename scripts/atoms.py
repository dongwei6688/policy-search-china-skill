"""
 policy-search-china 原子操作库 v2.41.0

 纯数据操作函数集合。不涉及文件 I/O 和子进程调用。
 所有函数接收结构化数据 → 返回结构化数据。
 文件读取（缓存加载）由调用方（chain_runner / rebuild_policy_html）负责。
"""

from datetime import datetime
from typing import Optional


# ═══════════════════════════════════════════════════════
#  Stage 0: 环境准备
# ═══════════════════════════════════════════════════════

def check_cache_freshness(entries: list[dict]) -> dict:
    """
    检查缓存新鲜度（纯数据操作）

    参数: entries — 调用方已加载的缓存条目列表
    返回: {"latest_date": "2026-07-28", "needs_web_update": bool}
    """
    latest = ""
    for e in entries:
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
    entries: list[dict], keyword: str
) -> list[dict]:
    """
    缓存关键词搜索（标题级，纯数据操作）

    参数: entries — 调用方已加载的缓存条目列表
          keyword — 搜索关键词
    返回: 命中条目列表
    """
    hits = []
    for e in entries:
        text = e.get("title", "") + " " + e.get("summary", "") + " " \
               + " ".join(e.get("tags", []))
        if keyword in text:
            hits.append(e)
    return hits


# ═══════════════════════════════════════════════════════
#  Stage 2: 过滤
# ═══════════════════════════════════════════════════════

def filter_date_range(
    entries: list[dict], start: str, end: str
) -> list[dict]:
    """时间范围过滤"""
    def ok(e):
        d = e.get("date", "") or e.get("searched_at", "")
        if not d:
            return True
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
    """发文机关过滤"""
    return [e for e in entries
            if any(iss in e.get("issuer", "") for iss in issuers)]


def filter_doctype(
    entries: list[dict], doctypes: list[str]
) -> list[dict]:
    """文件类型过滤（标题子串匹配）"""
    return [e for e in entries
            if any(typ in e.get("title", "") for typ in doctypes)]


def intersect_entries(entries_a: list[dict], entries_b: list[dict]) -> list[dict]:
    """AND 交集"""
    titles_b = {e.get("title", "") for e in entries_b}
    return [e for e in entries_a if e.get("title", "") in titles_b]


def union_entries(entries_a: list[dict], entries_b: list[dict]) -> list[dict]:
    """OR 并集（按 title 去重）"""
    seen = {}
    for e in entries_a + entries_b:
        t = e.get("title", "")
        if t not in seen:
            seen[t] = e
    return list(seen.values())


def exclude_entries(
    entries: list[dict], exclude_keywords: list[str]
) -> list[dict]:
    """排除过滤"""
    return [e for e in entries
            if not any(kw in e.get("title", "") for kw in exclude_keywords)]


# ═══════════════════════════════════════════════════════
#  Stage 3: 提取（元信息）
# ═══════════════════════════════════════════════════════

def extract_metadata(entry: dict) -> dict:
    """提取标准化元数据"""
    return {
        "title": entry.get("title", ""),
        "doc_number": entry.get("doc_number", ""),
        "issuer": entry.get("issuer", ""),
        "date": entry.get("date", ""),
        "source_url": entry.get("source_url", ""),
        "format": entry.get("format", ""),
        "local_path": entry.get("local_path", ""),
    }


def extract_chapters(text: str) -> list[tuple[str, str]]:
    """提取章节结构"""
    import re
    chapters = re.findall(
        r'(第[一二三四五六七八九十百零]+[篇章节].*?)(?=第[一二三四五六七八九十百零]+[篇章节]|$)', text
    )
    articles = re.findall(r'(第[一二三四五六七八九十百零]+条 .*?)(?=第[一二三四五六七八九十百零]+条|$)', text)
    result = []
    for c in chapters:
        result.append((c.strip()[:80], "一级"))
    for a in articles:
        result.append((a.strip()[:80], "二级"))
    return result


# ═══════════════════════════════════════════════════════
#  Stage 4: 去重
# ═══════════════════════════════════════════════════════

def deduplicate_entries(entries: list[dict]) -> list[dict]:
    """按 title + doc_number 去重"""
    seen = set()
    result = []
    for e in entries:
        key = (e.get("title", ""), e.get("doc_number", ""))
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result


# ═══════════════════════════════════════════════════════
#  Stage 5: 输出
# ═══════════════════════════════════════════════════════

def generate_summary_list(entries: list[dict]) -> str:
    """生成 标题/文号/发文机关/日期 摘要表格"""
    lines = ["| # | 标题 | 文号 | 发文机关 | 日期 |",
             "|---|------|------|----------|------|"]
    for i, e in enumerate(entries, 1):
        title = e.get("title", "")[:50]
        dn = e.get("doc_number", "")[:20]
        issuer = e.get("issuer", "")[:30]
        date = e.get("date", "")[:10]
        lines.append(f"| {i} | {title} | {dn} | {issuer} | {date} |")
    return "\n".join(lines)
