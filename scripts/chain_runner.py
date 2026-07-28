#!/usr/bin/env python3
"""
policy-search-china 编排器 v2.0

将 18 个原子操作按用户意图编排成执行链。
每个原子操作只做一件事，编排器负责串联。
"""

import sys
import json
from pathlib import Path
from typing import Optional

# 确保 skills 目录在 path 中
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
    extract_chapters,
    deduplicate_entries,
    generate_summary_list,
)

from rebuild_policy_html import (
    extract_paragraphs,
    load_source as rebuild_load_source,
)


# ═══════════════════════════════════════════════════════
#  预设执行链
# ═══════════════════════════════════════════════════════

def chain_cross_analysis(
    cache_dir: Path,
    keywords: list[str],
    start_date: str = None,
    end_date: str = None,
    issuers: list[str] = None,
    doctypes: list[str] = None,
) -> dict:
    """
    交叉分析链：多关键词 AND + 过滤
    
    场景: "近两年 AI 和能源结合的政策有哪些"
    """
    # Stage 0
    freshness = check_cache_freshness(cache_dir)
    
    # Stage 1: 每个关键词独立搜索标题
    all_hits = []
    for kw in keywords:
        hits = search_cache_title(cache_dir, kw)
        all_hits.append(hits)
    
    # Stage 2.4: AND 交集
    result = all_hits[0]
    for h in all_hits[1:]:
        result = intersect_entries(result, h)
    
    # Stage 2: 可选过滤
    if start_date or end_date:
        result = filter_date_range(result, start_date, end_date)
    if issuers:
        result = filter_issuer(result, issuers)
    if doctypes:
        result = filter_doctype(result, doctypes)
    
    # Stage 4: 去重
    result = deduplicate_entries(result)
    
    return {
        "entries": result,
        "freshness": freshness,
        "count": len(result),
    }


def chain_broad_scan(
    cache_dir: Path,
    keyword: str,
    start_date: str = None,
    end_date: str = None,
) -> dict:
    """
    全面扫描链：单个关键词广撒网

    场景: "近两年所有人工智能相关政策"
    """
    freshness = check_cache_freshness(cache_dir)
    hits = search_cache_title(cache_dir, keyword)
    
    if start_date or end_date:
        hits = filter_date_range(hits, start_date, end_date)
    
    hits = deduplicate_entries(hits)
    
    return {
        "entries": hits,
        "freshness": freshness,
        "count": len(hits),
    }


def chain_precise_locate(
    cache_dir: Path,
    keyword: str,
    doc_number: str = None,
    title_keyword: str = None,
) -> dict:
    """
    精准定位链：找到具体政策的具体段落

    场景: "数据二十条里关于确权的条款"
    """
    hits = []
    
    # 优先文号搜索
    if doc_number:
        for jf in cache_dir.glob("*.json"):
            for e in json.loads(jf.read_text()):
                if doc_number in e.get("doc_number", "") or doc_number in e.get("title", ""):
                    hits.append(e)
    
    # 次选标题关键词
    if not hits and title_keyword:
        hits = search_cache_title(cache_dir, title_keyword)
    
    # 提取命中段落
    for e in hits:
        paras = extract_paragraphs(e, keyword)
        e["_matched_paragraphs"] = paras
    
    return {
        "entries": hits,
        "count": len(hits),
    }


def chain_trace_source(
    cache_dir: Path,
    exact_phrase: str,
) -> dict:
    """
    溯源引用链：句子 → 政策出处

    场景: "这句话出自哪个政策"
    """
    results = []
    for jf in cache_dir.glob("*.json"):
        for e in json.loads(jf.read_text()):
            try:
                text = rebuild_load_source(e)
            except Exception:
                continue
            if not text:
                continue
            if exact_phrase in text:
                # 找到后提取上下文
                idx = text.find(exact_phrase)
                context = text[max(0, idx-40):idx+len(exact_phrase)+40]
                e["_match_context"] = context
                results.append(e)
    
    return {
        "entries": results,
        "count": len(results),
    }


# ═══════════════════════════════════════════════════════
#  命令行入口（用于测试）
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    CACHE_DIR = SKILL_DIR / "cache"
    
    import argparse
    import json as _json
    
    p = argparse.ArgumentParser(description="政策搜索编排器")
    p.add_argument("--chain", choices=["cross", "broad", "locate", "trace"],
                   default="broad", help="执行链类型")
    p.add_argument("--keywords", nargs="+", required=True, help="关键词")
    p.add_argument("--start", help="起始日期 YYYY-MM-DD")
    p.add_argument("--end", help="截止日期 YYYY-MM-DD")
    args = p.parse_args()
    
    if args.chain == "cross":
        r = chain_cross_analysis(CACHE_DIR, args.keywords, args.start, args.end)
    elif args.chain == "broad":
        r = chain_broad_scan(CACHE_DIR, args.keywords[0], args.start, args.end)
    elif args.chain == "locate":
        r = chain_precise_locate(CACHE_DIR, args.keywords[0])
    elif args.chain == "trace":
        r = chain_trace_source(CACHE_DIR, args.keywords[0])
    
    print(f"结果数: {r['count']}")
    for e in r["entries"][:20]:
        meta = extract_metadata(e)
        print(f"  {meta['title'][:70]}")
        print(f"    {meta['doc_number']} | {meta['issuer'][:30]} | {meta['date']}")
