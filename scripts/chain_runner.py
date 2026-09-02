"""

 policy-search-china 编排器 v2.38.0

 将原子操作按用户意图编排成执行链。
 - Stage 1 (多关键词搜索) 和 Stage 3 (条目段落提取) 支持多线程并行
 - Stage 2 (过滤去重) 串行
 - Commander 通过 CLI 参数传递过滤条件，Worker 返回结构化 JSON
"""

import sys
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from atoms import (
    check_cache_freshness,
    search_cache_title,
    filter_date_range,
    filter_issuer,
    filter_doctype,
    intersect_entries,
    union_entries,
    exclude_entries,
    extract_metadata,
    deduplicate_entries,
    generate_summary_list,
)

from rebuild_policy_html import (
    load_all_cache,              # 缓存 I/O
    extract_paragraphs,          # 文件 I/O
    load_source as rebuild_load_source,
)

# 并行执行线程上限：防止文件描述符耗尽
MAX_WORKERS = 8


# ═══════════════════════════════════════════════════════
#  Stage 1 辅助：缓存 + Web 结果合并
# ═══════════════════════════════════════════════════════

def _merge_search_results(cache_hits: list[dict], web_hits: list[dict]) -> list[dict]:
    """
    合并缓存搜索结果和 web_search 新发现的政策条目

    web_hits 中的 URL 如果已在 cache_hits 中出现（按 source_url 匹配），跳过；
    全新的条目追加。返回去重后的合并列表。
    """
    cache_urls = {e.get("source_url", "") for e in cache_hits}
    merged = list(cache_hits)
    for e in web_hits:
        url = e.get("source_url", "")
        if url and url not in cache_urls:
            merged.append(e)
            cache_urls.add(url)
    return merged


# ═══════════════════════════════════════════════════════
#  预设执行链
# ═══════════════════════════════════════════════════════

def chain_cross_analysis(
    keywords: list[str],
    start_date: str = None,
    end_date: str = None,
    issuers: list[str] = None,
    doctypes: list[str] = None,
) -> dict:
    """
    交叉分析链：多关键词 AND ∩ 过滤

    场景: "近两年 AI 和能源结合的政策有哪些"
    """
    # ═══ Stage 0: 环境准备 ═══
    all_entries = load_all_cache()
    freshness = check_cache_freshness(all_entries)

    # ═══ Stage 1: 并行搜索 ═══
    # 每个关键词独立的缓存搜索，可并行
    all_hits = []
    if len(keywords) > 1:
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(keywords))) as pool:
            futures = {pool.submit(search_cache_title, all_entries, kw): kw
                       for kw in keywords}
            for f in as_completed(futures):
                all_hits.append(f.result())
    else:
        all_hits = [search_cache_title(all_entries, keywords[0])]

    # ═══ Stage 2: 过滤 + 去重（串行，依赖 Stage 1 全量结果）═══
    # 2.4 AND 交集
    result = all_hits[0]
    for h in all_hits[1:]:
        result = intersect_entries(result, h)

    # 2.1-2.6 可选过滤链
    if start_date or end_date:
        result = filter_date_range(result, start_date, end_date)
    if issuers:
        result = filter_issuer(result, issuers)
    if doctypes:
        result = filter_doctype(result, doctypes)

    # 去重
    result = deduplicate_entries(result)

    return {
        "entries": result,
        "freshness": freshness,
        "count": len(result),
    }


def chain_broad_scan(
    keyword: str,
    start_date: str = None,
    end_date: str = None,
) -> dict:
    """
    全面扫描链：单关键词广撒网

    场景: "近两年所有人工智能相关政策"
    """
    # Stage 0
    all_entries = load_all_cache()
    freshness = check_cache_freshness(all_entries)

    # Stage 1: 单关键词（无需并行）
    hits = search_cache_title(all_entries, keyword)

    # Stage 2: 过滤 + 去重
    if start_date or end_date:
        hits = filter_date_range(hits, start_date, end_date)
    hits = deduplicate_entries(hits)

    return {
        "entries": hits,
        "freshness": freshness,
        "count": len(hits),
    }


def chain_precise_locate(
    keyword: str,
    doc_number: str = None,
    title_keyword: str = None,
) -> dict:
    """
    精准定位链：找到具体政策的具体段落

    场景: "数据二十条里关于确权的条款"
    """
    # 优先文号搜索
    hits = []
    if doc_number:
        for jf in (SKILL_DIR / "cache").glob("*.json"):
            for e in json.loads(jf.read_text()):
                if doc_number in e.get("doc_number", "") or doc_number in e.get("title", ""):
                    hits.append(e)

    # 次选标题关键词
    if not hits and title_keyword:
        hits = search_cache_title(all_entries, title_keyword)

    # Stage 3: 段落提取
    for e in hits:
        paras = extract_paragraphs(e, keyword)
        e["_matched_paragraphs"] = paras

    return {
        "entries": hits,
        "count": len(hits),
    }


def chain_trace_source(
    exact_phrase: str,
) -> dict:
    """
    溯源引用链：句子 → 政策出处

    场景: "这句话出自哪个政策"
    """
    results = []
    for jf in (SKILL_DIR / "cache").glob("*.json"):
        for e in json.loads(jf.read_text()):
            try:
                text = rebuild_load_source(e)
            except Exception:
                continue
            if not text:
                continue
            if exact_phrase in text:
                idx = text.find(exact_phrase)
                context = text[max(0, idx-40):idx+len(exact_phrase)+40]
                e["_match_context"] = context
                results.append(e)

    return {
        "entries": results,
        "count": len(results),
    }


# ═══════════════════════════════════════════════════════
#  Stage 3 聚合：并行提取 + 收集
# ═══════════════════════════════════════════════════════

def extract_all_paragraphs(
    entries: list[dict], keywords: list[str]
) -> list[tuple[dict, list]]:
    """
    并行提取所有条目的命中段落，然后按条目聚合

    返回: [(entry, [(段落文本, 章节归属), ...]), ...]
    仅返回至少命中一个关键词的条目。
    """
    if not entries:
        return []

    # Stage 3a: 并行提取
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(entries))) as pool:
        futures = {}
        for e in entries:
            futures[pool.submit(
                _extract_entry_paragraphs, e, keywords
            )] = e

        # Stage 3b: 收集聚合
        groups = []
        for f in as_completed(futures):
            paras = f.result()
            entry = futures[f]
            if paras:
                groups.append((entry, paras))

    # 按条目顺序恢复（ThreadPoolExecutor 不保证顺序）
    groups.sort(key=lambda g: entries.index(g[0]))
    return groups


def _extract_entry_paragraphs(entry: dict, keywords: list[str]) -> list:
    """
    对单一条目提取所有关键词的命中段落，去重
    """
    combined = []
    for kw in keywords:
        combined.extend(extract_paragraphs(entry, kw))

    # 按段落文本去重
    import re
    seen = set()
    unique = []
    for pt, ch in combined:
        key = re.sub(r'\s+', '', pt)
        if key not in seen:
            seen.add(key)
            unique.append((pt, ch))
    return unique


# ═══════════════════════════════════════════════════════
#  命令行入口
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    CACHE_DIR = SKILL_DIR / "cache"

    p = argparse.ArgumentParser(description="政策搜索编排器")
    p.add_argument("--chain", choices=["cross", "broad", "locate", "trace"],
                   default="broad", help="执行链类型")
    p.add_argument("--keywords", nargs="+", required=True, help="关键词")
    p.add_argument("--start", help="起始日期 YYYY-MM-DD")
    p.add_argument("--end", help="截止日期 YYYY-MM-DD")
    p.add_argument("--issuer", nargs="+", help="发文机关过滤（可多个）")
    p.add_argument("--doctype", nargs="+", help="文件类型过滤（如 意见 规划）")
    p.add_argument("--exclude", nargs="+", help="排除关键词")
    p.add_argument("--web", action="store_true", help="启用 Web 补充搜索（含政策库搜索接口）")
    p.add_argument("--pages", type=int, default=1, help="政策库搜索页数（--web 时生效）")
    args = p.parse_args()

    r = None
    if args.chain == "cross":
        r = chain_cross_analysis(args.keywords,
                                 args.start, args.end,
                                 args.issuer, args.doctype)
    elif args.chain == "broad":
        r = chain_broad_scan(args.keywords[0],
                             args.start, args.end)
    elif args.chain == "locate":
        r = chain_precise_locate(args.keywords[0])
    elif args.chain == "trace":
        r = chain_trace_source(args.keywords[0])

    assert r is not None, "未知的 chain 类型"
    print(f"结果数: {r['count']}")
    for e in r["entries"][:20]:
        meta = extract_metadata(e)
        print(f"  {meta['title'][:70]}")
        print(f"    {meta['doc_number']} | {meta['issuer'][:30]} | {meta['date']}")

    # ═══ --web：政策库搜索接口补充（降级链 L3）═══
    if args.web:
        try:
            from gov_library_search import search_gov_library
            gl = search_gov_library(args.keywords, args.start, args.end,
                                    pages=min(args.pages, 5))
            merged = _merge_search_results(r["entries"], gl["entries"])
            added = len(merged) - len(r["entries"])
            r["entries"] = merged
            r["count"] = len(merged)
            if added:
                print(f"\n[政策库搜索接口] 新增 {added} 条（缓存外新政策）:")
                for e in gl["entries"][:10]:
                    print(f"  + {e.get('title', '')[:60]} | {e.get('date', '')} | {e.get('doc_number', '')}")
        except Exception as e:
            print(f"\n[政策库搜索接口] 不可用: {e}")
