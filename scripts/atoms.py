"""
 policy-search-china 原子操作库 v2.64.3

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
    """时间范围过滤（按区间重叠判定，兼容只精确到年/月的日期）

    - 条目日期 "2025" 视为 2025-01-01 ~ 2025-12-31；"2025-05" 视为整月。
    - 只有整段完全落在区间外才剔除；此前用字符串比较，会把 "2025" 判成 < "2025-01-01"
      而误剔（年/月精度条目静默消失）。
    - 条目没有 date 时不参与判定（保留），不再回退到 searched_at——写入时间与
      政策日期不是一回事，用它过滤会误伤。
    """
    import re
    import calendar

    def span(raw: str) -> tuple[str, str]:
        """把各种日期写法展开成区间；认不出格式的条目按「不参与过滤」处理。

        外部数据（gov 政策库 pubTime、检索页文本）实际存在 2025.05.01 / 2025年5月1日 /
        2025-5-1 / "2026-11-04 18:00" 这些写法，只认 ISO 会让它们在 --end 下被静默剔除。
        """
        d = (raw or "").strip()
        m = re.match(r"^(\d{4})(?:[^\d]?(\d{1,2}))?(?:[^\d]?(\d{1,2}))?", d)
        if not m:
            return "0000", "9999"
        y = m.group(1)
        mo, dy = m.group(2), m.group(3)
        try:
            if not mo:
                return f"{y}-01-01", f"{y}-12-31"
            mi = int(mo)
            if not 1 <= mi <= 12:
                return f"{y}-01-01", f"{y}-12-31"
            if not dy:
                last = calendar.monthrange(int(y), mi)[1]
                return f"{y}-{mi:02d}-01", f"{y}-{mi:02d}-{last:02d}"
            di = min(max(int(dy), 1), 31)
            return f"{y}-{mi:02d}-{di:02d}", f"{y}-{mi:02d}-{di:02d}"
        except Exception:
            return "0000", "9999"

    def edge(s: str, is_end: bool) -> str:
        """查询边界也要展开：--end 2025 表示到 2025-12-31，--start 2025 表示从 2025-01-01。

        只展开条目日期而不展开边界，会让 --end 2025 变成"--end 2025-01-01"，
        整年数据被静默剔除（年/月方向必须对称）。
        """
        lo, hi = span(s)
        return hi if is_end else lo

    lo_bound = edge(start, False) if start else "0000"
    hi_bound = edge(end, True) if end else "9999"

    def ok(e):
        d = e.get("date", "")
        if not d:
            return True
        lo, hi = span(d)
        if hi < lo_bound:
            return False
        if lo > hi_bound:
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
    """排除过滤（按标题子串）

    空串/纯空白的关键词必须丢掉：`--exclude ""` 时 `"" in title` 恒真，
    会把全部条目剔光（shell 变量为空时很容易踩到）。
    """
    kws = [k for k in (exclude_keywords or []) if k and k.strip()]
    if not kws:
        return entries
    return [e for e in entries
            if not any(kw in e.get("title", "") for kw in kws)]


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

def _norm_title(t: str) -> str:
    """标题归一化：去掉书名号/引号/空白，用于识别「同一政策的不同排版」
    （真实库里存在《…》与“…”、全半角引号混用的重复条目）"""
    import re
    return re.sub(r"[\s《》〈〉「」『』“”\"'‘’]", "", t or "")


def deduplicate_entries(entries: list[dict]) -> list[dict]:
    """按 归一化标题 + 文号 去重"""
    seen = set()
    result = []
    for e in entries:
        key = (_norm_title(e.get("title", "")),
               _norm_doc_number_str(e.get("doc_number", "")))
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result


def _norm_doc_number_str(s: str) -> str:
    """文号归一（去重键用）：NFKC + 去空白与「第」，保留括号等分隔符"""
    import unicodedata
    s = unicodedata.normalize("NFKC", str(s or ""))
    return "".join(ch for ch in s if not ch.isspace() and ch != "第")


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
