#!/usr/bin/env python3
"""
gov.cn 政策库搜索接口 — Python 封装（降级链 L3）

当直接访问 gov.cn/zhengce/zhengceku/ 页面被 WAF 拦截（403 / 静默空响应）时，
改用政策库搜索接口 sousuo.www.gov.cn 获取政策数据。

实现：优先 curl 直连 search-gov/data API（未来 API 放行时可用）；
失败则回退 playwright 渲染搜索页 + DOM 提取（已实测可用）。

用法:
    python3 gov_library_search.py --keywords "人工智能" "能源" [--start 2025-01-01] [--end 2026-12-31] [--pages 1]
输出: {"count": N, "entries": [{title, doc_number, date, category, source_url, summary}]}
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

# ── NODE_PATH 探测：找到 playwright 模块 ──
def _resolve_node_path() -> str:
    """返回 playwright 模块所在目录（作为 NODE_PATH），找不到返回空"""
    # 1) 当前环境 require 可用？
    try:
        r = subprocess.run(
            ["node", "-e", "require.resolve('playwright')"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return ""
    except Exception:
        pass
    # 2) 常见 npx 缓存位置
    npx_root = Path.home() / ".npm" / "_npx"
    if npx_root.exists():
        for d in npx_root.iterdir():
            pw = d / "node_modules" / "playwright"
            if pw.exists():
                return str(d / "node_modules")
    return ""


# ── 策略 A：curl 直连 search-gov/data API（保留，API 放行时生效）──
_API_URL = ("https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q={q}"
            "&timetype=&mintime=&maxtime=&sort=score&sortType=1&searchfield=title"
            "&pcodeJiguan=&childtype=&subchildtype=&tsbq=&pubtimeyear=&puborg="
            "&pcodeYear=&pcodeNum=&filetype=&p={p}&n=10&inpro=&bmfl=&dup=&orpro=&type=gwyzcwjk")
_API_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def _search_via_curl(keyword: str, page: int = 1) -> list[dict]:
    """curl 直连 API。返回条目列表；被静默降级（totalCount=0）时返回空。"""
    import urllib.parse
    q = urllib.parse.quote(keyword)
    url = _API_URL.format(q=q, p=page)
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "20", "-H", f"User-Agent: {_API_UA}",
             "-H", "Accept: application/json, text/plain, */*",
             "-H", "Referer: https://sousuo.www.gov.cn/",
             "-o", "-", "-w", "\n%{http_code}", url],
            capture_output=True, text=True, timeout=30,
        )
        lines = r.stdout.rsplit("\n", 1)
        body, code = (lines[0], lines[1]) if len(lines) == 2 else (r.stdout, "")
        if code.strip() != "200":
            return []
        d = json.loads(body)
        sv = d.get("searchVO", {})
        if not sv.get("totalCount"):
            return []  # 静默降级：服务端未返回结果
        rows = sv.get("result") or []
        return [{
            "title": re.sub(r"<[^>]+>", "", str(x.get("title", ""))),
            "source_url": x.get("url", ""),
            "summary": re.sub(r"<[^>]+>", "", str(x.get("pubtimeStr", x.get("title", "")))),
            "category": x.get("puborg", "") or "",
            "date": str(x.get("pubTime", "") or ""),
            "_raw": x,
        } for x in rows]
    except Exception:
        return []


# ── 策略 B：playwright 渲染搜索页 + DOM 提取（主路径，已实测）──
def _search_via_playwright(keyword: str, page: int = 1) -> list[dict]:
    node_path = _resolve_node_path()
    cmd = ["node", str(SCRIPTS_DIR / "gov_library_dom.js"), keyword, str(page)]
    env = dict(os.environ)
    if node_path:
        env["NODE_PATH"] = node_path
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=env)
        d = json.loads(r.stdout.strip())
        return d.get("entries", []) or []
    except Exception:
        return []


# ── 后处理：doc_number / 日期过滤 / AND 语义 ──
_DOCNO_RE = re.compile(
    r"([国地][\u4e00-\u9fa5]{0,6}(?:〔|\[)20\d{2}(?:〕|\])\s?\d+\s*号)")

def _extract_docno(text: str) -> str:
    m = _DOCNO_RE.search(text or "")
    return m.group(1).strip() if m else ""

def _pass_date(entry: dict, start: str | None, end: str | None) -> bool:
    if not entry.get("date"):
        return True
    d = entry["date"][:10]
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True

def _pass_and(entry: dict, extra_kws: list[str]) -> bool:
    blob = (entry.get("title", "") + entry.get("summary", "")).lower()
    return all(k.lower() in blob for k in extra_kws)


def search_gov_library(keywords: list[str], start: str = None, end: str = None,
                       pages: int = 1) -> dict:
    """政策库搜索入口：curl → playwright 双策略，输出结构化条目。"""
    if not keywords:
        return {"count": 0, "entries": [], "source": "gov-library", "error": "no-keyword"}
    main_kw = keywords[0]
    extra_kws = keywords[1:]

    seen = set()
    entries = []
    for p in range(1, pages + 1):
        rows = _search_via_curl(main_kw, p) or _search_via_playwright(main_kw, p)
        for r in rows:
            url = r.get("source_url", "")
            if url and url in seen:
                continue
            if url:
                seen.add(url)
            r["doc_number"] = _extract_docno(r.get("summary", "") or r.get("title", ""))
            r["source"] = "gov-library"
            entries.append(r)
        if len(rows) < 10:  # 不足一页，无更多
            break

    # AND 语义 + 日期过滤
    entries = [e for e in entries
               if _pass_date(e, start, end) and _pass_and(e, extra_kws)]
    return {"count": len(entries), "entries": entries, "source": "gov-library"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="gov.cn 政策库搜索接口（降级链 L3）")
    p.add_argument("--keywords", nargs="+", required=True, help="关键词（多词 AND）")
    p.add_argument("--start", help="起始日期 YYYY-MM-DD")
    p.add_argument("--end", help="截止日期 YYYY-MM-DD")
    p.add_argument("--pages", type=int, default=1, help="搜索页数")
    args = p.parse_args()

    result = search_gov_library(args.keywords, args.start, args.end, args.pages)
    print(f"结果数: {result['count']}")
    for e in result["entries"][:20]:
        print(f"  {e['title'][:70]}")
        print(f"    {e.get('doc_number','')} | {e.get('category','')} | {e.get('date','')}")
        print(f"    {e.get('source_url','')}")
