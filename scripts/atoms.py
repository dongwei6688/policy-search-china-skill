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


def search_cache_fulltext(
    cache_dir: Path, keyword: str, hit_entries: list[dict]
) -> list[dict]:
    """
    1.2 缓存关键词搜索（全文级）
    """
    result = []
    for e in hit_entries:
        lp = e.get("local_path", "")
        if not lp or not Path(lp).exists():
            continue
        paras = extract_paragraphs(e, keyword)
        if paras:
            e["_body_hits"] = len(paras)
            result.append(e)
    return result


# ═══════════════════════════════════════════════════════
#  Stage 1 附属：原文读取（被 Stage 3 使用）
# ═══════════════════════════════════════════════════════

def load_source(entry: dict) -> str:
    """
    读取原文纯文本 — 内置五层URL降级

    按 format 字段分流：HTML → 提取 pages_content 容器 → 去标签
                      PDF → 读取配套 .txt 文件
    若 local_path 不存在，自动通过 fetch_url_with_fallback() 从 source_url 重新获取。
    """
    lp = Path(entry.get("local_path", ""))
    if not lp.exists():
        # 本地文件丢失，尝试从 source_url 重新获取
        url = entry.get("source_url", "")
        if url:
            r = fetch_url_with_fallback(url)
            if r["success"]:
                return re.sub(r"<[^>]+>", "", r["content"])
        return ""

    fmt = entry.get("format", "")
    if fmt == "html":
        html = lp.read_text(encoding="utf-8")
        for cls in ["pages_content mhide", "pages_content pchide",
                     "pages_content", "article_con"]:
            m = re.search(rf'class="{cls}"[^>]*>(.*?)</div>', html, re.DOTALL)
            if m:
                return re.sub(r"<[^>]+>", "", m.group(1))
        return re.sub(r"<[^>]+>", "", html)
    elif fmt == "pdf":
        txt = lp.with_suffix(".txt")
        return txt.read_text(encoding="utf-8") if txt.exists() else ""
    return ""


def extract_paragraphs(entry: dict, keyword: str) -> list[tuple[str, str]]:
    """
    从原文中逐段提取含关键词的段落

    返回: [(段落文本, 章节归属), ...]
    """
    text = load_source(entry)
    if not text:
        return []

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    results = []
    for line in lines:
        if keyword not in line:
            continue
        if len(line) < 15:
            continue  # 跳过大标题/页码等短行
        # 尝试提取章名
        ch = re.findall(r"第[一二三四五六七八九十百零]+[篇章节]|第[一二三四五六七八九十百零]+条", line)
        chapter = ch[0] if ch else ""
        results.append((line, chapter))
    return results


# ═══════════════════════════════════════════════════════
#  Stage 1.3/1.4: URL分级降级策略
# ═══════════════════════════════════════════════════════

FALLBACK_DOMAINS = {
    # 域名 → HTTPS 不通过时的降级方案
    "sasac.gov.cn": {"http_works": True, "alt_search": "site:gov.cn"},
    "miit.gov.cn":  {"http_works": False, "alt_search": "site:gov.cn"},
}


def fetch_url_with_fallback(url: str, timeout: int = 5) -> dict:
    """
    URL 五层降级访问策略

    每层失败自动降级到下一层。
    返回: {"success": bool, "content": str, "layer": int, "method": str}

    Layer 1: HTTPS (curl)
    Layer 2: HTTP 降级 (curl)
    Layer 3: 浏览器 (browser_navigate — 需 Agent 环境)
    Layer 4: 搜索引擎检索
    Layer 5: 替代源 (gov.cn 转载等)
    """
    import subprocess

    # Layer 1: HTTPS
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         "-m", str(timeout), "-H", "User-Agent: Mozilla/5.0", url],
        capture_output=True, text=True
    )
    if r.stdout.strip() == "200":
        r2 = subprocess.run(
            ["curl", "-s", "-m", str(timeout), "-H", "User-Agent: Mozilla/5.0", url],
            capture_output=True, text=True
        )
        return {"success": True, "content": r2.stdout, "layer": 1, "method": "HTTPS"}

    # Layer 2: HTTP 降级
    http_url = url.replace("https://", "http://")
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         "-m", str(timeout), http_url],
        capture_output=True, text=True
    )
    if r.stdout.strip() == "200":
        r2 = subprocess.run(
            ["curl", "-s", "-m", str(timeout), http_url],
            capture_output=True, text=True
        )
        return {"success": True, "content": r2.stdout, "layer": 2, "method": "HTTP 降级"}

    # Layer 3-5 无法在纯 Python 中实现（需 browser_navigate / web_search）
    return {"success": False, "content": "", "layer": 2, "method": "失败",
            "suggestion": "Layer 3: 尝试 browser_navigate; Layer 4: web_search; Layer 5: 替代源"}


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


def verify_verbatim(paragraph: str, original_path: Path) -> bool:
    """
    4.2 逐字验证

    检查 paragraph 是否能在 original_path 中找到逐字匹配。
    """
    if not original_path.exists():
        return False
    text = original_path.read_text(encoding="utf-8")
    clean_text = re.sub(r'<[^>]+>', '', text)
    return paragraph.strip() in clean_text


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
