"""

 policy-search-china 编排器 v2.64.3

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

try:  # 标题归一化与去重键保持同一口径
    from atoms import _norm_title as _norm_title_key
except Exception:  # pragma: no cover
    def _norm_title_key(t):
        return t or ""

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

    去重键：有 source_url 用 URL，没有则退化为标题（此前无 URL 的条目一律被丢弃，
    导致"接口说新增、实际没并入"）；同标题不同镜像 URL 也视为同一政策。
    返回去重后的合并列表。
    """
    def key(e):
        return (e.get("source_url") or "").strip() or ""

    def yr(e):
        return ((e.get("date") or "")[:4]) or ""

    def tkey(e):
        """同一条政策的三元组：归一化标题 + 年份 + 文号或机关。

        只用标题会把「同年度修订版/同名通知」误合；只用标题+年份又会把同年的不同
        文件误合。带上文号（没有则用发文机关）才能区分。
        """
        return (_norm_title_key(e.get("title", "")), yr(e),
                (e.get("doc_number") or e.get("issuer") or "").strip())

    seen_urls = {k for k in (key(e) for e in cache_hits) if k}
    seen_tkeys = {tkey(e) for e in cache_hits if e.get("title")}
    merged = list(cache_hits)
    for e in web_hits:
        url = key(e)
        tk = tkey(e)
        if url and url in seen_urls:
            continue
        if e.get("title") and tk in seen_tkeys:
            continue
        # 没有 URL 的条目：靠上面的三元组判重，不把标题当 URL 塞进 seen（否则跨年同名会互斥）
        merged.append(e)
        if url:
            seen_urls.add(url)
        if e.get("title"):
            seen_tkeys.add(tk)
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

    result = deduplicate_entries(result)
    pre_filter_count = len(result)          # 归因要用过滤前的数

    # 2.1-2.6 可选过滤链
    if start_date or end_date:
        result = filter_date_range(result, start_date, end_date)
    if issuers:
        result = filter_issuer(result, issuers)
    if doctypes:
        result = filter_doctype(result, doctypes)

    return {
        "entries": result,
        "freshness": freshness,
        "count": len(result),
        "pre_filter_count": pre_filter_count,
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
    hits = deduplicate_entries(hits)
    pre_filter_count = len(hits)            # 归因要用过滤前的数
    if start_date or end_date:
        hits = filter_date_range(hits, start_date, end_date)

    return {
        "entries": hits,
        "freshness": freshness,
        "count": len(hits),
        "pre_filter_count": pre_filter_count,
    }


def _norm_doc_number(s) -> str:
    """文号归一化：全角转半角（NFKC），统一括号写法，去空白与「第」。

    保留括号（而不是全删）：去掉「〕」后年份数字会和序号连成一片（`〔2026〕40号`→`202640号`），
    边界判断就会把「40号」当成数字串尾部而拒掉；但括号写法有全半角/两种形状，必须统一成同一个。
    """
    if not s:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFKC", str(s))
    trans = {"〔": "(", "［": "(", "[": "(", "（": "(", "(": "(",
             "〕": ")", "］": ")", "]": ")", "）": ")", ")": ")"}
    out = []
    for ch in s:
        if ch.isspace() or ch == "第":
            continue
        out.append(trans.get(ch, ch))
    return "".join(out)


def _dn_forms(s) -> set:
    """文号的可比较形态：保留括号的规范形 + 去掉括号的紧凑形。

    两种写法（`测发〔2026〕11号`、`测发2026 11号`）都要能对上，所以两种都算。
    """
    n = _norm_doc_number(s)
    return {n, n.replace("(", "").replace(")", "")} - {""}


def _dn_match(query_norm: str, candidate) -> bool:
    """文号命中判定：先全等，再要求「后缀 + 前一位不是数字」。

    只用子串会让「5号」命中「745号」；这里用后缀+数字边界挡掉这类误命中，
    同时 `〔2026〕40号` 里「40号」前一位是「）」，仍能正常命中。
    """
    if not query_norm:
        return False
    cand_forms = _dn_forms(candidate)
    if not cand_forms:
        return False
    for q in _dn_forms(query_norm):
        for c in cand_forms:
            if c == q:
                return True
            if not c.endswith(q):
                continue
            i = len(c) - len(q)
            if i == 0 or not c[i - 1].isdigit():
                return True
    return False


def _f(filters, name, default=None):
    """从 dict 或 argparse.Namespace 取过滤参数"""
    if filters is None:
        return default
    if isinstance(filters, dict):
        return filters.get(name, default)
    return getattr(filters, name, default)


def _apply_filters(entries: list[dict], filters) -> list[dict]:
    """统一后置过滤：时间 / 机关 / 类型 / 排除。

    纯谓词、无副作用，重复应用结果相同（幂等）。
    """
    start, end = _f(filters, "start"), _f(filters, "end")
    issuer, doctype = _f(filters, "issuer"), _f(filters, "doctype")
    exclude = _f(filters, "exclude")
    if start or end:
        entries = filter_date_range(entries, start, end)
    if issuer:
        entries = filter_issuer(entries, issuer)
    if doctype:
        entries = filter_doctype(entries, doctype)
    if exclude:
        entries = exclude_entries(entries, exclude)
    return entries


def chain_precise_locate(
    keyword: str,
    doc_number: str = None,
    title_keyword: str = None,
    filters=None,
) -> dict:
    """
    精准定位链：找到具体政策的具体段落

    场景: "数据二十条里关于确权的条款"
    检索分支只有两个：文号（doc_number）与标题关键词（title_keyword）。
    keyword 仅用于命中后的段落提取，不参与检索。

    给了 doc_number 却查不到时**不自动降级**为标题检索（避免"文号写错却拿到一堆
    无关政策"被下游当作命中）；需要降级请显式给 --title-keyword。
    """
    all_entries = load_all_cache()

    hits = []
    match_mode = None
    dn = _norm_doc_number(doc_number)
    if dn:
        hits = [e for e in all_entries
                if _dn_match(dn, e.get("doc_number"))
                or _dn_match(dn, e.get("title"))]
        if hits:
            match_mode = "doc_number"
        elif title_keyword:
            # 显式给了 --title-keyword 才降级（这是文档承诺的行为）
            hits = search_cache_title(all_entries, title_keyword)
            match_mode = "title_keyword_fallback" if hits else "doc_number_miss"
        else:
            match_mode = "doc_number_miss"
    elif title_keyword:
        hits = search_cache_title(all_entries, title_keyword)
        if hits:
            match_mode = "title_keyword"

    hits = deduplicate_entries(hits)
    pre_filter_count = len(hits)

    # 过滤在抽段之前：避免为最终被排除的条目读原文
    hits = _apply_filters(hits, filters)

    # 「命中多份不同文件」要看过滤后的结果：同一政策被不同排版收录不算多份
    files = {(str(e.get("local_path") or e.get("title") or ""),) for e in hits}
    dn_ambiguous = match_mode == "doc_number" and len(hits) > 1 and len(files) > 1

    # Stage 3: 段落提取
    for e in hits:
        paras = extract_paragraphs(e, keyword)
        e["_matched_paragraphs"] = paras

    return {
        "entries": hits,
        "count": len(hits),
        "match_mode": match_mode,
        "pre_filter_count": pre_filter_count,
        "dn_ambiguous": dn_ambiguous,
    }


def chain_trace_source(
    exact_phrase: str,
    filters=None,
) -> dict:
    """
    溯源引用链：句子 → 政策出处

    场景: "这句话出自哪个政策"

    先按元数据过滤，再读原文（读全文是最重的 I/O，不为必被排除的条目付代价）。
    """
    entries = deduplicate_entries(load_all_cache())
    pre_filter_count = len(entries)          # 过滤前候选数（归因要用，别在过滤后取）
    entries = _apply_filters(entries, filters)

    results = []
    read_count = 0          # 真正读到正文的条数
    unreadable = 0          # 原文取不到/为空（PDF 无文字层、路径失效等）
    for e in entries:
        try:
            text = rebuild_load_source(e)
        except Exception:
            unreadable += 1
            continue
        if not text:
            unreadable += 1
            continue
        read_count += 1
        if exact_phrase in text:
            idx = text.find(exact_phrase)
            context = text[max(0, idx-40):idx+len(exact_phrase)+40]
            e["_match_context"] = context
            results.append(e)

    return {
        "entries": results,
        "count": len(results),
        "match_mode": "phrase",
        "pre_filter_count": pre_filter_count,
        "scanned_count": read_count,
        "unreadable_count": unreadable,
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
    import re

    CACHE_DIR = SKILL_DIR / "cache"

    def _date_arg(s):
        s = (s or "").strip()
        if not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", s):
            raise argparse.ArgumentTypeError(
                f"日期格式应为 YYYY-MM-DD / YYYY-MM / YYYY，收到 {s!r}")
        import datetime as _dt
        try:
            parts = [int(x) for x in s.split("-")]
            _dt.date(parts[0], parts[1] if len(parts) > 1 else 1,
                     parts[2] if len(parts) > 2 else 1)
        except ValueError:
            raise argparse.ArgumentTypeError(f"日期不存在：{s!r}")
        return s

    def _docno_arg(s):
        s = (s or "").strip()
        if not s or not _norm_doc_number(s) or not any(ch.isdigit() for ch in s):
            raise argparse.ArgumentTypeError("--doc-number 需含数字（如 网信办令第15号）")
        return s

    p = argparse.ArgumentParser(description="政策搜索编排器")
    p.add_argument("--chain", choices=["cross", "broad", "locate", "trace"],
                   default="broad", help="执行链类型")
    p.add_argument("--keywords", nargs="+", required=True, help="关键词")
    p.add_argument("--start", type=_date_arg, help="起始日期 YYYY-MM-DD / YYYY-MM / YYYY")
    p.add_argument("--end", type=_date_arg, help="截止日期 YYYY-MM-DD / YYYY-MM / YYYY")
    p.add_argument("--issuer", nargs="+", help="发文机关过滤（可多个，子串匹配）")
    p.add_argument("--doctype", nargs="+", help="文件类型过滤（如 意见 规划）")
    p.add_argument("--exclude", nargs="+", help="排除关键词（按标题匹配）")
    p.add_argument("--web", action="store_true", help="启用 Web 补充搜索（含政策库搜索接口）")
    p.add_argument("--pages", type=int, default=1, help="政策库搜索页数（--web 时生效）")
    p.add_argument("--doc-number", dest="doc_number", type=_docno_arg,
                   help="locate 链：按文号检索（如 网信办令第15号），括号全半角均可")
    p.add_argument("--title-keyword", dest="title_keyword",
                   help="locate 链：按标题关键词检索（未给 --doc-number 时缺省取 --keywords 首个词）")
    args = p.parse_args()

    if args.start and args.end and args.start > args.end:
        raise SystemExit(f"--start（{args.start}）晚于 --end（{args.end}），区间为空")

    # 过滤条件集中一处，链内部与 --web 合并后共用同一套（幂等）
    filters = {
        "start": args.start, "end": args.end,
        "issuer": args.issuer, "doctype": args.doctype, "exclude": args.exclude,
    }

    # 未给 --doc-number 时，才把首个关键词当作标题检索词
    title_keyword = args.title_keyword
    if title_keyword is None and not args.doc_number:
        title_keyword = args.keywords[0]

    if args.chain == "cross":
        r = chain_cross_analysis(args.keywords,
                                 args.start, args.end,
                                 args.issuer, args.doctype)
    elif args.chain == "broad":
        r = chain_broad_scan(args.keywords[0],
                             args.start, args.end)
    elif args.chain == "locate":
        r = chain_precise_locate(args.keywords[0],
                                 doc_number=args.doc_number,
                                 title_keyword=title_keyword,
                                 filters=filters)
    elif args.chain == "trace":
        r = chain_trace_source(args.keywords[0], filters=filters)
    else:
        raise SystemExit(f"未知的 chain 类型: {args.chain}")

    # ═══ --web：政策库接口补充 ═══
    # locate / trace 的语义是「文号命中」「原文里有这句话」，接口补回来的条目没经过这两道核验，
    # 混进结果会让「结果数」「定位方式」变成假话 —— 它们只单列为未核验候选。
    new_entries = []
    unverified = []
    if args.web:
        if not 1 <= args.pages <= 5:
            raise SystemExit("--pages 需在 1–5 之间")
        try:
            from gov_library_search import search_gov_library
            gl = search_gov_library(args.keywords, args.start, args.end,
                                    pages=args.pages)
            web_hits = _apply_filters(gl.get("entries") or [], filters)
            if args.chain in ("broad", "cross"):
                before = {id(e) for e in r["entries"]}
                merged = deduplicate_entries(_merge_search_results(r["entries"], web_hits))
                new_entries = [e for e in merged if id(e) not in before]
                r["entries"] = merged
            else:
                unverified = deduplicate_entries(web_hits)
        except SystemExit:
            raise
        except Exception as e:
            print(f"[政策库搜索接口] 不可用: {e}")

    # 统一过滤 + 去重（幂等：链内部已过滤过一次）
    before_main_filter = len(r["entries"])
    r["entries"] = deduplicate_entries(_apply_filters(r["entries"], filters))
    r["count"] = len(r["entries"])
    pre = r.get("pre_filter_count")
    if pre is None:
        pre = before_main_filter

    print(f"结果数: {r['count']}")
    if r["count"] > 0:
        if r.get("match_mode") == "doc_number":
            print("定位方式: 文号")
        elif r.get("match_mode") == "title_keyword":
            print("定位方式: 标题关键词")
        elif r.get("match_mode") == "title_keyword_fallback":
            print("定位方式: 标题关键词（文号未命中，按 --title-keyword 降级）")
        elif r.get("match_mode") == "phrase":
            print("溯源方式: 原文全文匹配")
        if r.get("dn_ambiguous"):
            print("提示: 该文号命中多份不同文件，建议补 --issuer 或写全文号。")

    for e in r["entries"][:20]:
        meta = extract_metadata(e)
        print(f"  {meta['title'][:70]}")
        print(f"    {meta['doc_number']} | {meta['issuer'][:30]} | {meta['date']}")

    if new_entries:
        print(f"\n[政策库搜索接口] 新增 {len(new_entries)} 条（缓存外新政策，已过过滤条件）:")
        for e in new_entries[:10]:
            print(f"  + {e.get('title', '')[:60]} | {e.get('date', '')} | {e.get('doc_number', '')}")

    if unverified:
        print(f"\n[政策库搜索接口] 另有 {len(unverified)} 条缓存外候选（未经文号/原文核验，未计入结果数）:")
        for e in unverified[:10]:
            print(f"  ? {e.get('title', '')[:60]} | {e.get('date', '')} | {e.get('issuer', '')[:20]}")

    # 0 条时区分成因，避免把"被过滤掉"误导成"关键词没搜到"
    if r["count"] == 0:
        if r.get("match_mode") == "phrase":
            scanned = r.get("scanned_count") or 0
            unreadable = r.get("unreadable_count") or 0
            considered = scanned + unreadable      # 通过过滤、真正进入比对的条数
            if considered == 0 and pre:
                print(f"提示: 检索命中 {pre} 条，但被过滤条件（--start/--end/--issuer/--doctype/--exclude）全部排除。")
            else:
                tail = f"（另有 {unreadable} 条原文无法解析，未参与比对）" if unreadable else ""
                print(f"提示: 已读 {scanned} 条原文，都没有这句话{tail}；核对措辞，或换更短的片段。")
        elif pre:
            print(f"提示: 检索命中 {pre} 条，但被过滤条件（--start/--end/--issuer/--doctype/--exclude）全部排除。")
        elif r.get("match_mode") == "doc_number_miss":
            print("提示: 该文号在缓存中没有对应条目。核对文号（全半角括号、可省「第」），"
                  "或显式加 --title-keyword 改用标题检索，或 --chain broad 做全文检索。")
        elif args.chain == "locate":
            print("提示: 定位链只按「文号 / 标题关键词」检索；未命中可改用 --chain broad 做全文检索，或核对关键词。")
